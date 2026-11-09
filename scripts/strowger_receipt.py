#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Bounded canonical receipts and independent replay for native Ada routing.

The Ada binary generates the classical ordered event stream. This Python
standard-library verifier independently reconstructs every transition from
the explicit inputs. Hash equality alone is never treated as route validity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")
SCHEMA = "qec-ada.strowger-route-receipt.v1"
EVENT_SCHEMA = "qec-ada.strowger-event-stream.v1"
ENGINE = "qec-ada.strowger-bounded.v1"
FAULTS = {"none", "route", "check", "dark"} | {
    f"{kind}{n}" for kind, values in (
        ("miss", range(1, 5)), ("dup", range(1, 5)), ("stuck", range(1, 3)))
    for n in values
}
OUTCOMES = {"ROUTED", "INVALID_REQUEST", "NO_LINEFINDER",
            "NO_FIRST_TRUNK", "NO_SECOND_TRUNK", "PULSE_MISMATCH",
            "SELECTOR_STUCK", "TONE_MISMATCH"}
CLAIMS = {
    "classical_routing_only": True,
    "decoder_correctness_proved": False,
    "physical_quantum_hardware": False,
    "qec_strowger_schema_compatible": False,
    "independent_replay_required": True,
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request(digits: str, radices: str, linefinders: str, first_bank: str,
            second_bank: str, fault: str, request_id: str, epoch: int) -> dict:
    if not (isinstance(digits, str) and re.fullmatch(r"[0-9]{4}", digits)
            and isinstance(radices, str) and re.fullmatch(r"[2-9]{4}", radices)
            and all(isinstance(v, str) and re.fullmatch(r"[01Q]{4}", v)
                    for v in (linefinders, first_bank, second_bank))
            and fault in FAULTS
            and isinstance(request_id, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", request_id)
            and type(epoch) is int and 0 <= epoch <= 2**32 - 1):
        raise ValueError("INVALID_INPUT: route request")
    return {
        "digits": digits, "radices": radices, "linefinders": linefinders,
        "first_bank": first_bank, "second_bank": second_bank, "fault": fault,
        "request_id": request_id, "epoch": epoch,
    }


def replay(req: dict) -> dict:
    """Independent integer-only oracle; no native binary is called."""
    r = request(**req)
    events: list[dict] = []
    result = {
        "status": "INVALID_REQUEST", "linefinder": 0,
        "selector_a": 0, "selector_b": 0,
        "tone_expected": [0, 0, 0], "tone_observed": [0, 0, 0],
        "events": events,
    }

    def event(action: str, stage: int, value: int) -> None:
        index = len(events)
        if index >= 64:
            raise ValueError("event capacity exceeded")
        events.append({
            "sequence": index, "tick": index,
            "action": action, "stage": stage, "value": value,
        })

    def reject(status: str) -> dict:
        result["status"] = status
        order = ["ROUTED", "INVALID_REQUEST", "NO_LINEFINDER",
                 "NO_FIRST_TRUNK", "NO_SECOND_TRUNK",
                 "PULSE_MISMATCH", "SELECTOR_STUCK", "TONE_MISMATCH"]
        event("ROUTE_REJECTED", 0, order.index(status))
        if result["linefinder"]:
            event("RESOURCES_RELEASED", 0, result["linefinder"])
        result["linefinder"] = 0
        result["selector_a"] = 0
        result["selector_b"] = 0
        return result

    digits = [int(v) for v in r["digits"]]
    radices = [int(v) for v in r["radices"]]
    if any(d >= rad for d, rad in zip(digits, radices)):
        return reject("INVALID_REQUEST")

    def first_free(bank: str) -> int:
        return bank.find("1") + 1 if "1" in bank else 0

    result["linefinder"] = first_free(r["linefinders"])
    if result["linefinder"] == 0:
        return reject("NO_LINEFINDER")
    event("LINEFINDER_SELECTED", 0, result["linefinder"])

    for i, (digit, radix) in enumerate(zip(digits, radices), 1):
        expected = radix if digit == 0 else digit
        observed = 0
        for p in range(1, expected + 1):
            if r["fault"] == f"miss{i}" and p == 1:
                event("PULSE_MISSED", i, p)
                continue
            event("PULSE_RECEIVED", i, p)
            observed += 1
            if r["fault"] == f"dup{i}" and p == 1:
                event("PULSE_DUPLICATED", i, p)
                observed += 1
        if expected != observed:
            return reject("PULSE_MISMATCH")
        if i <= 2:
            if r["fault"] == f"stuck{i}":
                return reject("SELECTOR_STUCK")
            key = "first_bank" if i == 1 else "second_bank"
            selected = first_free(r[key])
            if selected == 0:
                return reject("NO_FIRST_TRUNK" if i == 1 else "NO_SECOND_TRUNK")
            result["selector_a" if i == 1 else "selector_b"] = selected
            event("TRUNK_SELECTED", i, selected)
        else:
            event("CONNECTOR_SELECTED", i, digit)

    linefinder = result["linefinder"]
    a, b = result["selector_a"], result["selector_b"]
    weighted = sum(i * 17 * digit for i, digit in enumerate(digits, 1))
    tones = [
        320 + weighted + 3 * linefinder + 5 * a + 7 * b,
        600 + (weighted + 11 * linefinder + 13 * a + 17 * b) % 127,
        90,
    ]
    observed = tones.copy()
    if r["fault"] in {"route", "check", "dark"}:
        observed[{"route": 0, "check": 1, "dark": 2}[r["fault"]]] += 1
    result["tone_expected"] = tones
    result["tone_observed"] = observed
    for i, (before, after) in enumerate(zip(tones, observed), 1):
        event("TONE_EXPECTED", i, before)
        event("TONE_OBSERVED", i, after)
    if tones != observed:
        return reject("TONE_MISMATCH")

    result["status"] = "ROUTED"
    event("ROUTE_COMMITTED", 0, 1)
    event("RESOURCES_RELEASED", 0, linefinder)
    return result


def native_trace(req: dict) -> dict:
    if not BINARY.is_file():
        raise ValueError("missing compiled qec_research binary")
    p = subprocess.run(
        [str(BINARY), "strowger", req["digits"], req["radices"],
         req["linefinders"], req["first_bank"], req["second_bank"],
         req["fault"]], capture_output=True, text=True, timeout=20,
    )
    values: dict[str, str] = {}
    events: list[dict] = []
    for line in p.stdout.splitlines():
        if "=" not in line:
            raise ValueError("invalid native output line")
        key, value = line.split("=", 1)
        if key == "event":
            parts = value.split(",")
            if len(parts) != 5:
                raise ValueError("invalid event encoding")
            sequence, tick, action, stage, data = parts
            events.append({
                "sequence": int(sequence), "tick": int(tick),
                "action": action, "stage": int(stage), "value": int(data),
            })
        elif key in values:
            raise ValueError("duplicate native output field")
        else:
            values[key] = value
    expected_keys = {"schema", "status", "linefinder", "selector_a", "selector_b",
                     "count"} | {
        f"tone_{kind}_{i}" for kind in ("expected", "observed")
        for i in range(1, 4)
    }
    if set(values) != expected_keys or values["schema"] != EVENT_SCHEMA:
        raise ValueError("native output contract mismatch")
    if values["status"] not in OUTCOMES:
        raise ValueError("unknown native route status")
    result = {
        "status": values["status"],
        "linefinder": int(values["linefinder"]),
        "selector_a": int(values["selector_a"]),
        "selector_b": int(values["selector_b"]),
        "tone_expected": [int(values[f"tone_expected_{i}"]) for i in range(1, 4)],
        "tone_observed": [int(values[f"tone_observed_{i}"]) for i in range(1, 4)],
        "events": events,
    }
    if int(values["count"]) != len(events) or len(events) > 64:
        raise ValueError("native event count mismatch")
    if (p.returncode == 0) != (result["status"] == "ROUTED"):
        raise ValueError("native exit/status mismatch")
    return result


def with_chain(trace: dict) -> dict:
    previous = None
    result = dict(trace)
    result["events"] = []
    for event in trace["events"]:
        signed = {**event, "previous_event_sha256": previous}
        signed["event_sha256"] = sha(canonical(signed))
        result["events"].append(signed)
        previous = signed["event_sha256"]
    return result


def make_receipt(req: dict) -> dict:
    expected = replay(req)
    actual = native_trace(req)
    if actual != expected:
        raise ValueError("native Ada trace disagrees with independent replay")
    unsigned = {
        "schema": SCHEMA, "engine": ENGINE,
        "request": req, "trace": with_chain(actual),
        "claim_boundary": CLAIMS,
    }
    return {**unsigned, "sha256": sha(canonical(unsigned))}


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def validate_bytes(raw: bytes) -> dict:
    if len(raw) > 256_000:
        raise ValueError("receipt over size limit")
    receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    if type(receipt) is not dict or set(receipt) != {
        "schema", "engine", "request", "trace", "claim_boundary", "sha256"
    }:
        raise ValueError("receipt membership mismatch")
    if receipt["schema"] != SCHEMA or receipt["engine"] != ENGINE:
        raise ValueError("wrong schema/engine")
    if canonical(receipt["claim_boundary"]) != canonical(CLAIMS):
        raise ValueError("changed claim boundary")
    req = receipt["request"]
    if type(req) is not dict or set(req) != {
        "digits", "radices", "linefinders", "first_bank", "second_bank",
        "fault", "request_id", "epoch"
    }:
        raise ValueError("invalid request membership")
    req = request(**req)
    if canonical(receipt) + b"\n" != raw:
        raise ValueError("noncanonical receipt bytes")
    unsigned = {key: value for key, value in receipt.items() if key != "sha256"}
    if sha(canonical(unsigned)) != receipt["sha256"]:
        raise ValueError("receipt SHA-256 mismatch")
    expected = with_chain(replay(req))
    if canonical(receipt["trace"]) != canonical(expected):
        raise ValueError("independent route/event replay mismatch")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    create = subs.add_parser("create", help="create new non-overwriting receipt")
    create.add_argument("output", type=Path)
    for name in ("digits", "radices", "linefinders", "first_bank",
                 "second_bank", "fault"):
        create.add_argument(name)
    create.add_argument("--request-id", default="local-001")
    create.add_argument("--epoch", type=int, default=0)
    check = subs.add_parser("verify", help="independent replay without Ada binary")
    check.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "create":
            req = request(**{name: getattr(args, name) for name in
                ("digits", "radices", "linefinders", "first_bank",
                 "second_bank", "fault", "request_id", "epoch")})
            receipt = make_receipt(req)
            data = canonical(receipt) + b"\n"
            with args.output.open("xb") as stream:
                stream.write(data)
            print(f"PASS native/oracle parity, saved receipt {receipt['sha256']}")
        else:
            if args.path.is_symlink() or not args.path.is_file():
                raise ValueError("receipt must be a regular non-symlink file")
            result = validate_bytes(args.path.read_bytes())
            print(f"PASS independent replay and SHA-256 {result['sha256']}")
        return 0
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError,
            json.JSONDecodeError) as exc:
        print(f"FAIL receipt: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
