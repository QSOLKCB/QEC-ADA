#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Canonical native spectral observations with independent offline replay.

The source-bound receipt is generated only after native Ada results match an
independent Python finite-graph oracle. Verify needs NO Ada executable,
NumPy/SciPy, network or vendor runtime. All records remain observational:
the hash proves consistency, not physical truth or a global eigenvector.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

from tanner_spectral_export import canonical, observe as native_tanner

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")
SCHEMA = "qec-ada.nb-spectral-receipt.v1"
NATIVE_SCHEMA = "qec-ada.nb-spectral-observation.v1"
ALGORITHM = "scc-lazy-perron-bounded-v1"
CLAIM = {
    "classical_tanner_observation": True,
    "scc_recurrent_mode_only": True,
    "numerically_converged_not_formally_proved": True,
    "global_reducible_eigenvector": False,
    "physical_quantum_measurement": False,
    "decoder_modified": False,
    "requires_independent_replay": True,
}
DECIMAL_FIELDS = (
    "spectral_radius", "collatz_lower", "collatz_upper", "residual_l1",
    "ipr", "eeec",
)
INTEGER_FIELDS = (
    "variables", "checks", "edges", "directed_edges", "four_cycles",
    "nb_trace4", "scc_count", "cyclic_scc_count", "dominant_tie_count",
    "mode_root_edge", "mode_edge_count", "iterations",
)
STATES = {"NO_EDGES", "ACYCLIC", "CONVERGED_NUMERIC"}
DECIMAL_PATTERN = re.compile(r"^-?[0-9]+\.[0-9]{12}$")


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def require_source(source: object) -> tuple[int, list[str]]:
    if type(source) is not dict or set(source) != {"sites", "rows_x_z"}:
        raise ValueError("invalid spectral source membership")
    n, rows = source["sites"], source["rows_x_z"]
    if (type(n) is not int or not 1 <= n <= 5 or type(rows) is not list
            or not 1 <= len(rows) <= 4 or any(
                type(row) is not str or re.fullmatch(r"[012]{" +
                str(2*n) + r"}", row) is None for row in rows)):
        raise ValueError("invalid spectral source")
    return n, rows


def independent_graph(source: dict) -> dict:
    n, rows = require_source(source)
    edges = [
        [c+1, s+1, int(row[s]), int(row[n+s])]
        for c, row in enumerate(rows) for s in range(n)
        if row[s] != "0" or row[n+s] != "0"
    ]
    heat = [0] * n
    four_cycles = 0
    for first, second in itertools.combinations(range(1, len(rows)+1), 2):
        common = [
            s for s in range(1, n+1)
            if any(e[:2] == [first, s] for e in edges)
            and any(e[:2] == [second, s] for e in edges)
        ]
        for a, b in itertools.combinations(common, 2):
            heat[a-1] += 1
            heat[b-1] += 1
            four_cycles += 1
    return {
        "variables": n,
        "checks": len(rows),
        "edges": len(edges),
        "x_edges": sum(x != 0 for _, _, x, z in edges),
        "z_edges": sum(z != 0 for _, _, x, z in edges),
        "mixed_edges": sum(x != 0 and z != 0 for _, _, x, z in edges),
        "four_cycles": four_cycles,
        "nb_trace4": 8*four_cycles,
        "variable_degrees": [sum(v == s for _, v, _, _ in edges)
                             for s in range(1, n+1)],
        "check_degrees": [sum(c == r for c, _, _, _ in edges)
                          for r in range(1, len(rows)+1)],
        "variable_cycle_heat": heat,
        "edge_labels": edges,
    }


def graph_edges(source: dict) -> list[tuple[int, int]]:
    n, _ = require_source(source)
    out = []
    for c, v, _, _ in independent_graph(source)["edge_labels"]:
        out.extend(((v, n+c), (n+c, v)))
    return out


def components(edges: list[tuple[int, int]]) -> tuple[list[list[int]], list[list[int]]]:
    size = len(edges)
    # Test/replay oracle uses explicit integer graph adjacency; native Ada
    # implementation uses only edge predicates and bounded vector storage.
    neighbours = [
        [j for j, f in enumerate(edges)
         if e[1] == f[0] and e[0] != f[1]]
        for e in edges
    ]
    def reaches(root: int, reverse: bool) -> set[int]:
        found = {root}
        frontier = [root]
        while frontier:
            v = frontier.pop()
            for j in range(size):
                if j in found:
                    continue
                if (v in neighbours[j] if reverse else j in neighbours[v]):
                    found.add(j)
                    frontier.append(j)
        return found

    assigned = set()
    result = []
    for root in range(size):
        if root not in assigned:
            scc = sorted(reaches(root, False) & reaches(root, True))
            assigned.update(scc)
            result.append(scc)
    return result, neighbours


def solve_block(scc: list[int], neighbours: list[list[int]]) -> tuple[float, list[float]]:
    # Independent scalar Python reference of B right Perron mode, with
    # uniform deterministic start and lazy iteration to remove periodicity.
    weights = [1.0 / len(scc)] * len(neighbours)
    members = set(scc)
    rho = 0.0
    for _ in range(4_000):
        values = [
            sum(weights[j] for j in neighbours[i] if j in members)
            for i in scc
        ]
        ratios = [x / weights[i] for i, x in zip(scc, values)]
        lower, upper = min(ratios), max(ratios)
        rho = (lower + upper) * 0.5
        if upper - lower <= 1e-10 * max(1.0, upper):
            break
        update = [weights[i] + v for i, v in zip(scc, values)]
        norm = math.fsum(update)
        for i, v in zip(scc, update):
            weights[i] = v / norm
    else:
        raise ValueError("independent oracle did not converge")
    norm2 = math.fsum(weights[i]**2 for i in scc)
    energy = [weights[i]**2 / norm2 if i in members else 0.0
              for i in range(len(neighbours))]
    return rho, energy


def native_output(source: dict) -> dict:
    n, rows = require_source(source)
    if not BIN.is_file():
        raise ValueError("native qec_research executable missing")
    p = subprocess.run(
        [str(BIN), "spectral", str(n), *rows],
        text=True, capture_output=True, timeout=30, check=False,
    )
    if p.returncode:
        raise ValueError(f"native spectral run rejected or did not converge: {p.stderr}")
    fields, energies, ranking = {}, {}, []
    for line in p.stdout.splitlines():
        if "=" not in line:
            raise ValueError("bad spectral line")
        name, value = line.split("=", 1)
        if name == "energy":
            parts = value.split(",")
            if len(parts) != 2:
                raise ValueError("bad energy row")
            index = int(parts[0])
            if index in energies:
                raise ValueError("duplicate edge energy")
            energies[index] = parts[1]
        elif name == "ranking":
            parts = value.split(",")
            if len(parts) != 2 or int(parts[0]) != len(ranking) + 1:
                raise ValueError("invalid ranking sequence")
            ranking.append(int(parts[1]))
        elif name in fields:
            raise ValueError("duplicate spectral field")
        else:
            fields[name] = value

    names = {"schema", "algorithm", "mode_scope", "status"} | \
        set(INTEGER_FIELDS) | set(DECIMAL_FIELDS)
    if set(fields) != names:
        raise ValueError("missing/unexpected spectral fields")
    if fields["schema"] != NATIVE_SCHEMA or fields["algorithm"] != ALGORITHM \
            or fields["mode_scope"] != "selected-recurrent-block":
        raise ValueError("unsupported native spectral schema")
    if fields["status"] not in STATES:
        raise ValueError("native spectrum has unsupported solver status")

    result = {
        "status": fields["status"],
        "algorithm": fields["algorithm"],
        "mode_scope": fields["mode_scope"],
        **{k: int(fields[k]) for k in INTEGER_FIELDS},
        **{k: fields[k] for k in DECIMAL_FIELDS},
        "energy": [energies[i] for i in range(1, len(energies)+1)],
        "ranking": ranking,
    }
    if len(energies) != result["directed_edges"]:
        raise ValueError("native spectrum missing energy rows")
    return result


def verify_spectrum(source: dict, data: dict) -> None:
    graph = independent_graph(source)
    directed = graph_edges(source)
    if type(data) is not dict or set(data) != (
        {"status", "algorithm", "mode_scope", "energy", "ranking"} |
        set(INTEGER_FIELDS) | set(DECIMAL_FIELDS)
    ):
        raise ValueError("invalid spectrum fields")
    if (data["status"] not in STATES or data["algorithm"] != ALGORITHM
            or data["mode_scope"] != "selected-recurrent-block"):
        raise ValueError("spectral schema/mode mismatch")
    if any(type(data[k]) is not int or data[k] < 0 for k in INTEGER_FIELDS):
        raise ValueError("invalid spectral integer type")
    if any(type(data[k]) is not str or not DECIMAL_PATTERN.fullmatch(data[k])
           for k in DECIMAL_FIELDS):
        raise ValueError("invalid spectral decimal encoding")
    floats = {k: float(data[k]) for k in DECIMAL_FIELDS}
    if not all(math.isfinite(v) for v in floats.values()):
        raise ValueError("nonfinite spectral value")
    if any(data[k] != graph[k] for k in
           ("variables", "checks", "edges", "four_cycles", "nb_trace4")):
        raise ValueError("spectral graph identity mismatch")
    if data["directed_edges"] != len(directed):
        raise ValueError("directed-edge count mismatch")
    raw_energy = data["energy"]
    if (type(raw_energy) is not list or len(raw_energy) != len(directed)
            or any(type(v) is not str or not DECIMAL_PATTERN.fullmatch(v)
                   for v in raw_energy)):
        raise ValueError("invalid energy encoding/coverage")
    energy = [float(v) for v in raw_energy]
    if any(not math.isfinite(v) or v < 0.0 or v > 1.0 for v in energy):
        raise ValueError("invalid energy range")
    ranking = data["ranking"]
    if type(ranking) is not list or any(type(v) is not int for v in ranking):
        raise ValueError("invalid ranking")
    scc, neighbour = components(directed)
    cyclic = [block for block in scc if len(block) > 1]
    if data["scc_count"] != len(scc) or data["cyclic_scc_count"] != len(cyclic):
        raise ValueError("strongly connected components mismatch")
    if not cyclic:
        expected_status = "NO_EDGES" if not directed else "ACYCLIC"
        if data["status"] != expected_status or ranking:
            raise ValueError("invented mode on acyclic graph")
        if any(energy) or any(floats.values()):
            raise ValueError("invented spectral energy on acyclic graph")
        if any(data[k] != 0 for k in ("dominant_tie_count",
              "mode_root_edge", "mode_edge_count", "iterations")):
            raise ValueError("invented spectral metadata on acyclic graph")
        return

    if data["status"] != "CONVERGED_NUMERIC":
        raise ValueError("missing converged numerical mode")
    outcomes = [(min(scc), *solve_block(scc, neighbour), scc) for scc in cyclic]
    best_rho = max(item[1] for item in outcomes)
    tied = [item for item in outcomes if abs(item[1] - best_rho) <= 1e-9]
    chosen = min(tied, key=lambda item: item[0])
    root, expected_rho, expected_energy, selected = chosen
    if (data["mode_root_edge"] != root + 1 or
            data["mode_edge_count"] != len(selected) or
            data["dominant_tie_count"] != len(tied) or
            not 1 <= data["iterations"] <= 4_000):
        raise ValueError("spectral mode selection mismatch")
    if abs(floats["spectral_radius"] - expected_rho) > 1e-7:
        raise ValueError("dominant spectral radius disagrees with oracle")
    if any(abs(a - b) > 1e-7 for a, b in zip(energy, expected_energy)):
        raise ValueError("eigenmode edge energies disagree with oracle")
    if abs(math.fsum(energy) - 1.0) > 1e-8:
        raise ValueError("energy not normalized")
    ipr = math.fsum(v*v for v in energy)
    if abs(floats["ipr"] - ipr) > 1e-8:
        raise ValueError("IPR disagreement")
    expected_rank = sorted((i + 1 for i in selected),
                           key=lambda i: (-energy[i-1], i))
    # Native ranks use internal high-precision energies, rather than
    # rounded 12-place strings. Permit differences below print precision.
    if sorted(ranking) != sorted(expected_rank):
        raise ValueError("ranking set mismatch")
    for a, b in zip(ranking, ranking[1:]):
        if energy[a-1] + 2e-11 < energy[b-1]:
            raise ValueError("unstable energy ranking")
    top = math.isqrt(len(selected))
    if top*top < len(selected):
        top += 1
    eeec = math.fsum(energy[i-1] for i in ranking[:top])
    if abs(floats["eeec"] - eeec) > 1e-8:
        raise ValueError("EEEC disagreement")
    if (floats["collatz_lower"] > floats["spectral_radius"] + 1e-8 or
            floats["collatz_upper"] + 1e-8 < floats["spectral_radius"] or
            floats["collatz_upper"] - floats["collatz_lower"] > 1e-7 or
            floats["residual_l1"] > 1e-7):
        raise ValueError("numeric convergence witness invalid")


def make(source: dict) -> dict:
    n, rows = require_source(source)
    graph = native_tanner(n, rows)
    spectrum = native_output(source)
    verify_spectrum(source, spectrum)
    unsigned = {
        "schema": SCHEMA,
        "source": source,
        "source_sha256": sha(canonical(source)),
        "graph_observation_sha256": graph["sha256"],
        "graph": graph["observation"],
        "spectrum": spectrum,
        "claim_boundary": CLAIM,
    }
    return {**unsigned, "sha256": sha(canonical(unsigned))}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def verify_bytes(raw: bytes) -> dict:
    if len(raw) > 65_536:
        raise ValueError("spectral receipt too large")
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)
    if type(obj) is not dict or set(obj) != {
        "schema", "source", "source_sha256", "graph",
        "graph_observation_sha256", "spectrum", "claim_boundary", "sha256"
    }:
        raise ValueError("spectral receipt membership mismatch")
    if obj["schema"] != SCHEMA or canonical(obj["claim_boundary"]) != canonical(CLAIM):
        raise ValueError("spectral claim/schema mismatch")
    if canonical(obj) + b"\n" != raw:
        raise ValueError("spectral receipt not in canonical byte form")
    if obj["source_sha256"] != sha(canonical(obj["source"])):
        raise ValueError("spectral source identity mismatch")
    if canonical(obj["graph"]) != canonical(independent_graph(obj["source"])):
        raise ValueError("independent Tanner topology/metrics mismatch")
    graph_claim = {
        "observable_classical_graph": True,
        "exact_nb_fourth_moment": True,
        "spectral_radius_measured": False,
        "eigenvector_ipr_measured": False,
        "decoder_modified": False,
        "sonification_wav_generated": False,
        "spectral_qec_app_dataset_compatible": False,
        "physical_quantum_result": False,
    }
    graph_payload = {
        "schema": "qec-ada.tanner-spectral-observation.v1",
        "source": obj["source"],
        "source_sha256": obj["source_sha256"],
        "observation": obj["graph"],
        "claim_boundary": graph_claim,
    }
    if obj["graph_observation_sha256"] != sha(canonical(graph_payload)):
        raise ValueError("graph observation identity mismatch")
    if obj["sha256"] != sha(canonical(
            {k: v for k, v in obj.items() if k != "sha256"})):
        raise ValueError("spectral receipt hash mismatch")
    verify_spectrum(obj["source"], obj["spectrum"])
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("output", type=Path)
    create.add_argument("sites", type=int)
    create.add_argument("rows", nargs="+")
    verify = sub.add_parser("verify")
    verify.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "create":
            source = {"sites": args.sites, "rows_x_z": args.rows}
            artifact = make(source)
            with args.output.open("xb") as handle:
                handle.write(canonical(artifact) + b"\n")
            print(f"PASS independent spectral oracle {artifact['sha256']}")
        else:
            if args.path.is_symlink() or not args.path.is_file():
                raise ValueError("spectral receipt must be a regular file")
            artifact = verify_bytes(args.path.read_bytes())
            print(f"PASS independent offline spectral replay {artifact['sha256']}")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError,
            subprocess.SubprocessError) as exc:
        print(f"FAIL spectral receipt: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
