#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Paired end-to-end timing for two exactly equivalent native qutrit paths.

No speedup gate: the measurements include process startup and depend on host,
load, compiler and operating system. Correctness must pass first.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / "build/bin" / ("qec_ada.exe" if os.name == "nt" else "qec_ada")
EXPECTED_CHECKSUM = "33457"


def sample(path: str) -> int:
    before = time.perf_counter_ns()
    result = subprocess.run(
        [str(BINARY), "benchmark", "qutrit", path],
        capture_output=True, text=True, timeout=30, check=True,
    )
    elapsed = time.perf_counter_ns() - before
    data = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if (data != {"workload": "59049", "path": path,
                 "checksum": EXPECTED_CHECKSUM}):
        raise ValueError(f"native path {path} failed checksum/shape: {data!r}")
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()
    if not (3 <= args.trials <= 30 and 0 <= args.warmups <= 10):
        parser.error("bounded trials: 3..30, warmups: 0..10")
    if not BINARY.is_file():
        parser.error("native qec_ada binary not found; build first")

    for _ in range(args.warmups):
        sample("scalar")
        sample("opt")
    times = {"scalar": [], "opt": []}
    for i in range(args.trials):
        # Alternating order reduces systematic first/second-run advantage.
        for path in (("scalar", "opt") if i % 2 == 0 else ("opt", "scalar")):
            times[path].append(sample(path))

    scalar_ns = statistics.median(times["scalar"])
    opt_ns = statistics.median(times["opt"])
    report = {
        "schema": "qec-ada.opt-observation.v1",
        "status": "observational_not_performance_certification",
        "algorithm": "fixed-cyclic-5-qutrit-syndrome",
        "inputs": 59049,
        "checksum": EXPECTED_CHECKSUM,
        "warmups": args.warmups,
        "trials": args.trials,
        "environment": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "runner": os.environ.get("RUNNER_OS", "local"),
            "compiler": "see build logs / gnat version",
        },
        "duration_ns": times,
        "median_ns": {"scalar": scalar_ns, "opt": opt_ns},
        "observed_ratio_scalar_over_opt": round(scalar_ns / opt_ns, 6),
        "limitation": "subprocess and runtime startup included; no universal or end-to-end QEC speedup claim",
    }
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
