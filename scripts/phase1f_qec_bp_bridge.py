#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Explicit, pinned QEC BP reference comparison on controlled Phase 1E inputs.

This adapter EXECUTES external QEC source code, with its NumPy dependency.
That execution is opt-in, isolated from the no-dependency runtime and guarded
by an exact donor commit/blob identity. It compares outcomes on shared
binary Tanner/channel inputs; QEC's floating-point BP and QEC-ADA's
integer min-sum pilot are NOT interchangeable or claimed equivalent.

The optional comparison does not update the protected native Ada decoder.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import phase1e_experiment as phase1e
import phase1e_reference as reference

DONOR_COMMIT = "27bbc798c4e38138ca5b0fff70b15c3271a1917d"
SOURCE_BLOB = "266dc35c7162adf6a895eb796760e2bc6724eff4"
SOURCE_PATH = "src/qec_qldpc_codes.py"
SCHEMA = "qec-ada.phase1f-pinned-qec-bp-comparison.v1"
BOUNDARY = {
    "pinned_external_qec_source_executed": True,
    "real_qec_bp_decode_used": True,
    "shared_binary_tanner_and_channel_inputs": True,
    "qec_mode": "min_sum",
    "qec_schedule": "flooding",
    "phase1e_mode": "integer_min_sum",
    "decoders_semantically_identical": False,
    "exact_correction_parity_expected": False,
    "claim_of_quantum_fault_tolerance": False,
    "source_provenance_requires_pinned_checkout": True,
    "offline_verification_reexecutes_donor": True,
}


def canonical(value: object) -> bytes:
    return phase1e.canonical(value)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(donor: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(donor), *args], text=True,
                       capture_output=True, check=True, timeout=20)
    return p.stdout.strip()


def checked_source(donor: Path) -> Path:
    repo = donor.resolve(strict=True)
    if not repo.is_dir() or git(repo, "rev-parse", "HEAD") != DONOR_COMMIT:
        raise ValueError("QEC donor HEAD is not pinned to expected commit")
    if git(repo, "rev-parse", f"HEAD:{SOURCE_PATH}") != SOURCE_BLOB:
        raise ValueError("QEC donor Git source blob mismatch")
    source = repo / SOURCE_PATH
    if source.is_symlink() or not source.is_file() or \
            not source.resolve(strict=True).is_relative_to(repo):
        raise ValueError("QEC source is missing or unsafe")
    if git(repo, "hash-object", str(source)) != SOURCE_BLOB:
        raise ValueError("checked-out QEC source differs from pinned Git blob")
    return source


def load_reference(donor: Path):
    source = checked_source(donor)
    try:
        import numpy as np
    except ImportError as exc:
        raise ValueError("QEC reference requires NumPy in this opt-in lane") from exc
    # Importlib intentionally runs the code in the verified source. It is
    # *not* an inert data parsing operation and is never the default path.
    spec = importlib.util.spec_from_file_location("phase1f_pinned_qec", source)
    if spec is None or spec.loader is None:
        raise ValueError("unable to load pinned QEC reference module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not callable(getattr(module, "bp_decode", None)):
        raise ValueError("pinned source has no bp_decode")
    return module.bp_decode, np, digest(source.read_bytes())


def sample_indices(parent: dict, max_trials_per_graph: int,
                   noise_bps: list[int] | None = None) -> list[dict]:
    if type(max_trials_per_graph) is not int or not 1 <= max_trials_per_graph <= 4:
        raise ValueError("sample cap must be 1..4 trials per held-out graph/noise")
    noise = parent["config"]["noise_bps"] if noise_bps is None else noise_bps
    if type(noise) is not list or not noise or \
            any(type(v) is not int or v not in parent["config"]["noise_bps"]
                for v in noise) or sorted(set(noise)) != noise:
        raise ValueError("invalid selected noise schedule")
    return [row for row in parent["trials"]
            if row["graph_id"] % 5 == 0
            and row["noise_bps"] in noise
            and row["trial"] < max_trials_per_graph]


def run_case(bp_decode, np, graph: dict, row: dict,
             iterations: int) -> dict:
    # Exact shared H support and flipped BSC error sites. This is not
    # the full QEC depolarizing channel or a quantum CSS decode.
    gid = row["graph_id"]
    n = max(v for _, v in graph["edges"])
    m = max(c for c, _ in graph["edges"])
    # Native source declares true n/m; preserve isolated nodes as well.
    n = graph["variables"] if "variables" in graph else n
    m = graph["checks"] if "checks" in graph else m
    H = np.zeros((m, n), dtype=np.uint8)
    for c, v in graph["edges"]:
        H[c-1, v-1] = 1
    flips = set(row["flipped_sites"])
    rate = row["noise_bps"] / 10_000
    if not 0 < rate < 0.5:
        raise ValueError("QEC log-channel comparison requires 0 < p < 0.5")
    magnitude = math.log((1 - rate) / rate)
    llr = np.array([
        -magnitude if v in flips else magnitude
        for v in range(1, n + 1)
    ], dtype=np.float64)
    decoded, used = bp_decode(
        H, llr, max_iters=iterations, mode="min_sum",
        schedule="flooding", damping=0.0, postprocess=None,
        syndrome_vec=np.zeros(m, dtype=np.uint8),
        llr_history=0, residual_metrics=False,
    )
    values = np.asarray(decoded)
    if values.shape != (n,) or values.ndim != 1 or \
            any(int(x) not in (0, 1) for x in values):
        raise ValueError("QEC BP result is not a binary word")
    bits = [int(v) for v in values]
    checks = [sum(bits[v-1] for v in range(1, n+1) if H[c, v-1]) % 2
              for c in range(m)]
    if type(used) not in (int, np.int64, np.int32) or \
            not 0 <= int(used) <= iterations:
        raise ValueError("QEC BP iteration count outside contract")
    qec_failure = any(bits)
    return {
        "graph_id": gid,
        "noise_bps": row["noise_bps"],
        "trial": row["trial"],
        "flip_sites": sorted(flips),
        "qec_decoded_word": bits,
        "qec_iterations": int(used),
        "qec_checks_satisfied": not any(checks),
        "qec_syndrome_weight": sum(checks),
        "qec_frame_failure": qec_failure,
        "phase1e_frame_failure": row["bp"]["frame_failure"],
        "failure_labels_agree": qec_failure == row["bp"]["frame_failure"],
    }


def make(parent_raw: bytes, donor: Path, trials_per_graph: int = 2) -> dict:
    parent = phase1e.verify_bytes(parent_raw)
    bp_decode, np, source_sha256 = load_reference(donor)
    samples = sample_indices(parent, trials_per_graph)
    graphs = {g["id"]: {**g,
             "variables": parent["config"]["variables"],
             "checks": parent["config"]["checks"]} for g in parent["graphs"]}
    results = [run_case(bp_decode, np, graphs[row["graph_id"]], row,
                        parent["config"]["max_iterations"])
               for row in samples]
    count = len(results)
    comparisons = {
        "total_cases": count,
        "agree_on_frame_failure": sum(x["failure_labels_agree"] for x in results),
        "qec_frame_failures": sum(x["qec_frame_failure"] for x in results),
        "phase1e_frame_failures": sum(x["phase1e_frame_failure"] for x in results),
        "qec_unsatisfied_syndrome": sum(not x["qec_checks_satisfied"]
                                       for x in results),
        "split": "heldout_graphs_only",
        "comparability": "same_H_BSC_input_different_message_update_algorithms",
    }
    unsigned = {
        "schema": SCHEMA,
        "parent_phase1e_sha256": parent["sha256"],
        "parent_file_sha256": digest(parent_raw),
        "qec_source": {
            "repository": "QSOLKCB/QEC",
            "commit": DONOR_COMMIT, "git_blob_sha1": SOURCE_BLOB,
            "path": SOURCE_PATH, "file_sha256": source_sha256,
        },
        "environment": {
            "python": sys.version.split()[0], "numpy": np.__version__,
        },
        "trials_per_heldout_graph_noise": trials_per_graph,
        "records": results,
        "comparisons": comparisons,
        "claim_boundary": BOUNDARY,
    }
    return {**unsigned, "sha256": digest(canonical(unsigned))}


def verify(parent_raw: bytes, receipt_raw: bytes, donor: Path) -> dict:
    supplied = json.loads(receipt_raw.decode("utf-8"),
                          object_pairs_hook=phase1e.unique_pairs)
    if type(supplied) is not dict or set(supplied) != {
        "schema", "parent_phase1e_sha256", "parent_file_sha256",
        "qec_source", "environment", "trials_per_heldout_graph_noise",
        "records", "comparisons", "claim_boundary", "sha256"
    } or supplied["schema"] != SCHEMA:
        raise ValueError("wrong QEC baseline evidence contract")
    if receipt_raw != canonical(supplied) + b"\n":
        raise ValueError("noncanonical QEC comparison bytes")
    if supplied["sha256"] != digest(canonical({
        key: value for key, value in supplied.items() if key != "sha256"
    })):
        raise ValueError("QEC comparison hash mismatch")
    # A valid self-consistent hash is not evidence of truthful decoding.
    # Re-execute the exact pinned source and compare every full byte.
    expected = make(parent_raw, donor,
                    supplied["trials_per_heldout_graph_noise"])
    if canonical(expected) != canonical(supplied):
        raise ValueError("pinned QEC reference re-execution mismatch")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("parent", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--donor", type=Path, required=True)
    create.add_argument("--trials-per-graph", type=int, default=2)
    create.add_argument("--execute-pinned-donor", action="store_true")
    check = sub.add_parser("verify")
    check.add_argument("parent", type=Path)
    check.add_argument("receipt", type=Path)
    check.add_argument("--donor", type=Path, required=True)
    check.add_argument("--execute-pinned-donor", action="store_true")
    args = parser.parse_args()
    try:
        if not args.execute_pinned_donor:
            raise ValueError("explicit --execute-pinned-donor required")
        if args.cmd == "create":
            if args.parent.is_symlink() or not args.parent.is_file():
                raise ValueError("parent evidence must be a regular file")
            item = make(args.parent.read_bytes(), args.donor,
                        args.trials_per_graph)
            with args.output.open("xb") as file:
                file.write(canonical(item) + b"\n")
            print("PASS pinned QEC BP comparison executed")
            print("matched_failure_labels=" +
                  str(item["comparisons"]["agree_on_frame_failure"]) +
                  "/" + str(item["comparisons"]["total_cases"]))
            print("comparison_sha256=" + item["sha256"])
        else:
            if any(x.is_symlink() or not x.is_file()
                   for x in (args.parent, args.receipt)):
                raise ValueError("comparison inputs must be regular files")
            item = verify(args.parent.read_bytes(),
                          args.receipt.read_bytes(), args.donor)
            print("PASS exact pinned QEC BP rerun " + item["sha256"])
        return 0
    except (OSError, ValueError, TypeError, UnicodeError,
            subprocess.SubprocessError) as exc:
        print("FAIL QEC BP comparison: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
