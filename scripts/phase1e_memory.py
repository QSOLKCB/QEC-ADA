#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Observational peak-RSS evidence for a bounded native sparse Tanner graph.

Uses only Python stdlib and Linux getrusage(RUSAGE_CHILDREN). Every invocation
executes ONE Ada child, so maxrss is that child's process maximum. Numbers
depend on runner/kernel/loader and are NOT reproducible hardware-independent
benchmarks. Analytic K(m,n) rho checks numerical correctness as well.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

from phase1e_reference import canonical_graph


def run(checks: int, variables: int) -> dict:
    if (type(checks) is not int or type(variables) is not int
            or not 2 <= checks <= 128 or not 2 <= variables <= 128
            or checks * variables > 2048):
        raise ValueError("invalid complete-bipartite memory fixture")
    edges = [(c, v) for c in range(1, checks + 1)
             for v in range(1, variables + 1)]
    source = canonical_graph(variables, checks, edges)
    native = Path(__file__).resolve().parents[1] / "build/bin/qec_scale"
    if not native.is_file():
        raise ValueError("native qec_scale executable not compiled")

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "graph.txt"
        path.write_bytes(source)
        start = time.perf_counter_ns()
        completed = subprocess.run(
            [str(native), "inspect", str(path)],
            text=True, capture_output=True, check=False, timeout=90,
        )
        elapsed = time.perf_counter_ns() - start
    if completed.returncode:
        raise ValueError("native sparse observation failed: " +
                         completed.stderr[:400])
    fields = {}
    for line in completed.stdout.splitlines():
        if line.startswith("top="):
            continue
        key, value = line.split("=", 1)
        if key in fields:
            raise ValueError("duplicate native field")
        fields[key] = value
    if fields["status"] != "CONVERGED_NUMERIC":
        raise ValueError("unexpected nonconverged complete graph")
    observed = float(fields["spectral_radius"])
    expected = math.sqrt((checks - 1) * (variables - 1))
    if abs(observed - expected) > 1e-7:
        raise ValueError("analytic K(m,n) spectral radius mismatch")
    directed = 2 * len(edges)
    if int(fields["directed_edges"]) != directed:
        raise ValueError("native directed edge count mismatch")

    return {
        "schema": "qec-ada.phase1e.memory-observation.v1",
        "graph": f"K_{checks}_{variables}",
        "input_source_sha256": hashlib.sha256(source).hexdigest(),
        "variables": variables,
        "checks": checks,
        "edges": len(edges),
        "directed_edges": directed,
        "expected_rho": expected,
        "observed_rho": observed,
        "dense_float64_matrix_bytes_hypothetical": 8 * directed**2,
        "native_peak_rss_kib_linux": resource.getrusage(
            resource.RUSAGE_CHILDREN).ru_maxrss,
        "native_process_elapsed_ns": elapsed,
        "memory_claim_boundary": "one-child observational peak RSS; sparse arrays O(V+E) by code structure; no general speed guarantee",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checks", type=int, default=32)
    p.add_argument("--variables", type=int, default=64)
    a = p.parse_args()
    try:
        print(json.dumps(run(a.checks, a.variables), sort_keys=True,
                         separators=(",", ":"), allow_nan=False))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
