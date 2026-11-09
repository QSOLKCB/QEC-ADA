#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline Tanner observation export for independent SPECTRAL research.

This is a graph-spectrum *moment* document, not a SPECTRAL QEC/APP
event dataset; that lab's six-column import concerns decoder episodes.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")
SCHEMA = "qec-ada.tanner-spectral-observation.v1"


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=False).encode("utf-8")


def observe(n: int, rows: list[str]) -> dict:
    if (type(n) is not int or not 1 <= n <= 5 or not 1 <= len(rows) <= 4
            or any(type(row) is not str or
                   re.fullmatch(r"[012]{" + str(n*2) + r"}", row) is None
                   for row in rows)):
        raise ValueError("invalid bounded Tanner input")
    if not BIN.is_file():
        raise ValueError("native qec_research binary not available")
    p = subprocess.run([str(BIN), "tanner", str(n), *rows],
                       capture_output=True, text=True, timeout=20, check=False)
    if p.returncode:
        raise ValueError("native Tanner observation failed: " + p.stderr)
    entries: dict[str, str] = {}
    edges: list[list[int]] = []
    for line in p.stdout.splitlines():
        if "=" not in line:
            raise ValueError("invalid native Tanner output")
        k, v = line.split("=", 1)
        if k == "edge":
            record = [int(x) for x in v.split(",")]
            if len(record) != 4:
                raise ValueError("invalid edge row")
            edges.append(record)
        elif k in entries:
            raise ValueError("duplicate native observation field")
        else:
            entries[k] = v
    expected_keys = {"schema", "variables", "checks", "edges", "x_edges",
                     "z_edges", "mixed_edges", "four_cycles", "nb_trace4"}
    expected_keys |= {f"variable_degree_{i}" for i in range(1, n+1)}
    expected_keys |= {f"variable_cycle_heat_{i}" for i in range(1, n+1)}
    expected_keys |= {f"check_degree_{i}" for i in range(1, len(rows)+1)}
    if set(entries) != expected_keys or entries["schema"] != \
            "qec-ada.tanner-observation.v1":
        raise ValueError("native Tanner output membership mismatch")

    # Independent simple-graph oracle: stable check-major / site-major
    source_edges = [
        [check+1, site+1, int(row[site]), int(row[n+site])]
        for check, row in enumerate(rows)
        for site in range(n)
        if row[site] != "0" or row[n+site] != "0"
    ]
    if edges != source_edges:
        raise ValueError("native edge topology/labels disagree with source")
    checks = len(rows)
    degrees_var = [sum(edge[1] == site for edge in edges)
                   for site in range(1, n+1)]
    degrees_check = [sum(edge[0] == check for edge in edges)
                     for check in range(1, checks+1)]
    cycles = 0
    heat = [0] * n
    for first, second in itertools.combinations(range(1, checks+1), 2):
        common = [site for site in range(1, n+1)
                  if [first, site] in [edge[:2] for edge in edges]
                  and [second, site] in [edge[:2] for edge in edges]]
        for u, v in itertools.combinations(common, 2):
            cycles += 1
            heat[u-1] += 1
            heat[v-1] += 1
    actual = {
        "variables": int(entries["variables"]),
        "checks": int(entries["checks"]),
        "edges": int(entries["edges"]),
        "x_edges": int(entries["x_edges"]),
        "z_edges": int(entries["z_edges"]),
        "mixed_edges": int(entries["mixed_edges"]),
        "four_cycles": int(entries["four_cycles"]),
        "nb_trace4": int(entries["nb_trace4"]),
        "variable_degrees": [int(entries[f"variable_degree_{i}"])
                             for i in range(1, n+1)],
        "check_degrees": [int(entries[f"check_degree_{i}"])
                          for i in range(1, checks+1)],
        "variable_cycle_heat": [int(entries[f"variable_cycle_heat_{i}"])
                                for i in range(1, n+1)],
        "edge_labels": edges,
    }
    expected = {
        "variables": n, "checks": checks, "edges": len(edges),
        "x_edges": sum(x != 0 for _, _, x, z in edges),
        "z_edges": sum(z != 0 for _, _, x, z in edges),
        "mixed_edges": sum(x != 0 and z != 0 for _, _, x, z in edges),
        "four_cycles": cycles, "nb_trace4": 8*cycles,
        "variable_degrees": degrees_var, "check_degrees": degrees_check,
        "variable_cycle_heat": heat, "edge_labels": source_edges,
    }
    if actual != expected:
        raise ValueError("native/independent Tanner observation mismatch")
    source = {"sites": n, "rows_x_z": rows}
    payload = {
        "schema": SCHEMA,
        "source": source,
        "source_sha256": hashlib.sha256(canonical(source)).hexdigest(),
        "observation": actual,
        "claim_boundary": {
            "observable_classical_graph": True,
            "exact_nb_fourth_moment": True,
            "spectral_radius_measured": False,
            "eigenvector_ipr_measured": False,
            "decoder_modified": False,
            "sonification_wav_generated": False,
            "spectral_qec_app_dataset_compatible": False,
            "physical_quantum_result": False,
        },
    }
    payload["sha256"] = hashlib.sha256(canonical(payload)).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sites", type=int)
    parser.add_argument("rows", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = canonical(observe(args.sites, args.rows)) + b"\n"
        if args.output is None:
            sys.stdout.buffer.write(data)
        else:
            with args.output.open("xb") as output:
                output.write(data)
            print(f"Saved {len(data)} canonical bytes to {args.output}")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL spectral observation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
