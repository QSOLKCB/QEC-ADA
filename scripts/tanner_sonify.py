#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Deterministic original Tanner graph sonification (SPECTRAL-style demo).

No imported SPECTRAL audio, no random numbers, no wave-generation libraries.
A graph observation becomes a reproducible integer-triangle-wave WAV.
This is NOT a physical quantum signal, QEC performance measurement, or a
SPECTRAL QEC/APP canonical render receipt.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
import wave

from tanner_spectral_export import canonical, observe

SAMPLE_RATE = 48_000
SAMPLE_WIDTH = 3              # 24-bit signed little-endian PCM, NOT 16-bit
CHANNELS = 1
SAMPLES_PER_SITE = 12_000      # 250ms per variable
FADE_SAMPLES = 480            # 10ms integer amplitude ramp
ENGINE = "qec-ada.tanner-sonification.v1"
SPECTRAL_SOURCE_COMMIT = "49401fa010ed673e3d3977ccd5e06d66b0d65096"


def generate(observation: dict) -> tuple[bytes, dict]:
    if observation.get("schema") != "qec-ada.tanner-spectral-observation.v1":
        raise ValueError("unsupported graph observation")
    data = observation["observation"]
    n = data["variables"]
    if type(n) is not int or not 1 <= n <= 5:
        raise ValueError("invalid graph size")
    degrees = data["variable_degrees"]
    heat = data["variable_cycle_heat"]
    if (len(degrees) != n or len(heat) != n or
            any(type(v) is not int or not 0 <= v <= 4 for v in degrees) or
            any(type(v) is not int or not 0 <= v <= 100 for v in heat)):
        raise ValueError("invalid graph metric range")
    pcm = bytearray()
    for index, (degree, cycle_heat) in enumerate(zip(degrees, heat)):
        # Deliberately compositional: frequency follows simple node degree
        # and exact four-cycle participation, not a physical eigenfrequency.
        frequency = 140 + 20 * degree + 11 * cycle_heat + 7 * index
        amplitude = min(3_000_000, 700_000 + 130_000 * degree
                        + 90_000 * cycle_heat)
        if degree == 0:
            amplitude = 0
        phase = 0
        for sample in range(SAMPLES_PER_SITE):
            phase = (phase + frequency) % SAMPLE_RATE
            triangle = (4 * abs(phase - SAMPLE_RATE // 2)
                        - SAMPLE_RATE) * amplitude // SAMPLE_RATE
            envelope = min(FADE_SAMPLES, sample,
                           SAMPLES_PER_SITE - 1 - sample)
            value = triangle * envelope // FADE_SAMPLES
            if not -(1 << 23) <= value < (1 << 23):
                raise ArithmeticError("out-of-range 24-bit PCM sample")
            pcm.extend(int(value).to_bytes(3, "little", signed=True))

    wav_io = BytesIO()
    with wave.open(wav_io, "wb") as out:
        out.setnchannels(CHANNELS)
        out.setsampwidth(SAMPLE_WIDTH)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(bytes(pcm))
    wav = wav_io.getvalue()
    unsigned = {
        "schema": ENGINE,
        "source_observation_sha256": observation["sha256"],
        "source_graph": observation["source"],
        "pcm_format": "signed-linear-24bit-little-endian",
        "channels": CHANNELS,
        "sample_rate_hz": SAMPLE_RATE,
        "frames": n * SAMPLES_PER_SITE,
        "wav_sha256": hashlib.sha256(wav).hexdigest(),
        "source_research": {
            "repository": "QSOLKCB/SPECTRAL",
            "pinned_commit": SPECTRAL_SOURCE_COMMIT,
            "mapping": "original_qec_ada_tanner_degree_and_cycle_heat",
            "imported_source_audio": False,
        },
        "claim_boundary": {
            "deterministic_demo": True,
            "quantum_hardware_or_measurement": False,
            "physical_eigenfrequency": False,
            "qec_decoder_performance": False,
            "spectral_app_engine_compatible": False,
        },
    }
    manifest = {**unsigned, "sha256": hashlib.sha256(canonical(unsigned)).hexdigest()}
    return wav, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", type=int)
    parser.add_argument("rows", nargs="+")
    parser.add_argument("--wav", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.wav.resolve(strict=False) == args.manifest.resolve(strict=False):
            raise ValueError("WAV and manifest must be distinct")
        if args.wav.exists() or args.manifest.exists():
            raise FileExistsError("outputs must not exist already")
        observation = observe(args.sites, args.rows)
        wav, receipt = generate(observation)
        manifest_bytes = canonical(receipt) + b"\n"
        # Files are small and fully materialized before any write.
        # Fail closed on existing destination; no cloud/fileserver.
        with args.wav.open("xb") as fp:
            fp.write(wav)
        with args.manifest.open("xb") as fp:
            fp.write(manifest_bytes)
        print("PASS 48kHz 24-bit mono deterministic Tanner WAV")
        print("wav_sha256=" + receipt["wav_sha256"])
        print("manifest_sha256=" + receipt["sha256"])
        return 0
    except (OSError, ValueError, ArithmeticError) as exc:
        print(f"FAIL SPECTRAL Tanner sonification: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
