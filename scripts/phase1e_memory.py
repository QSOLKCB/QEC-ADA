#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Native post-exec RSS evidence for a bounded sparse Tanner graph on Linux.

Ada reads /proc/self/status VmHWM *inside the executable after execve*.
Linux RUSAGE_CHILDREN.ru_maxrss is intentionally NOT used: it may include
the Python parent's pre-exec memory footprint (even with posix_spawn).
The reported VmHWM includes the native executable's runtime/loader memory
but not the Python launcher. No cross-machine benchmark claim is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
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
            [str(native), "inspect", str(path), "--native-rss"],
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
    rss_text = fields.pop("native_post_exec_peak_rss_kib_linux", None)
    if rss_text is None or re.fullmatch(r"[1-9][0-9]*", rss_text) is None:
        raise ValueError(
            "native Ada post-exec VmHWM field missing or malformed"
        )
    native_rss_kib = int(rss_text)
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
        "schema": "qec-ada.phase1e.memory-observation.v2",
        "graph": f"K_{checks}_{variables}",
        "input_source_sha256": hashlib.sha256(source).hexdigest(),
        "variables": variables,
        "checks": checks,
        "edges": len(edges),
        "directed_edges": directed,
        "expected_rho": expected,
        "observed_rho": observed,
        "dense_float64_matrix_bytes_hypothetical": 8 * directed**2,
        "native_post_exec_peak_rss_kib_linux": native_rss_kib,
        "rss_measurement_source": "linux_proc_self_status_VmHWM_read_inside_Ada_after_exec",
        "native_process_elapsed_ns": elapsed,
        "memory_claim_boundary": "Linux native post-exec high-water RSS includes Ada runtime/loader; excludes Python launcher/pre-exec pages; one-process observation, not a dense benchmark or speed guarantee",
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
