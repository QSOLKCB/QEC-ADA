#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Phase 1E reproducible, classical BP-vs-spectral validation.

The native Ada qec_scale is observational; its output never modifies BP.
All binary min-sum BP trials and error-channel traces are independently
generated with Python's standard library. Held-out splitting is by graph
identity (not per noise trial); risk directions are preregistered.
No quantum or QEC donor BP equivalence is asserted.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import phase1e_reference as ref


ROOT = Path(__file__).resolve().parents[1]
SCALE = ROOT / "build/bin" / "qec_scale"
SCHEMA = "qec-ada.phase1e-bp-spectral-evidence.v1"
PREDICTORS = ("ipr", "eeec", "spectral_radius", "edge_density")
PRIMARY_FEATURE = "ipr"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def integer_lines(output: str) -> tuple[dict[str, str], list[tuple[int, float]]]:
    attributes = {}
    ranked = []
    for line in output.splitlines():
        if "=" not in line:
            raise ValueError("native output has invalid non-key line")
        name, value = line.split("=", 1)
        if name == "top":
            parts = value.split(",")
            if len(parts) != 3 or int(parts[0]) != len(ranked) + 1:
                raise ValueError("bad native top ranking")
            ranked.append((int(parts[1]), float(parts[2])))
        elif name in attributes:
            raise ValueError("duplicate native output field")
        else:
            attributes[name] = value
    required = {
        "schema", "algorithm", "mode_scope", "status", "variables",
        "checks", "edges", "directed_edges", "scc_count",
        "cyclic_scc_count", "dominant_tie_count", "mode_root_edge",
        "mode_edge_count", "iterations", "spectral_radius",
        "collatz_lower", "collatz_upper", "residual_l1", "ipr",
        "eeec", "max_variables", "max_checks", "max_edges", "top_count",
    }
    if set(attributes) != required:
        raise ValueError("native sparse report membership mismatch")
    if (attributes["schema"] != "qec-ada.scaled-spectral.v1" or
            attributes["algorithm"] != "bounded-sparse-scc-lazy-perron-v1" or
            attributes["mode_scope"] != "selected-recurrent-block"):
        raise ValueError("unexpected native scaled operator")
    if len(ranked) != int(attributes["top_count"]):
        raise ValueError("native spectral ranking count mismatch")
    return attributes, ranked


def graph_features(n: int, m: int, edges: list[tuple[int, int]],
                   graph_path: Path) -> dict:
    data = ref.canonical_graph(n, m, edges)
    graph_path.write_bytes(data)
    p = subprocess.run([str(SCALE), "inspect", str(graph_path)],
                       capture_output=True, text=True, check=False,
                       timeout=45)
    if p.returncode:
        raise ValueError("native sparse spectrum failed: " + p.stderr[:600])
    out, ranked = integer_lines(p.stdout)
    oracle = ref.reference_spectrum(n, m, edges)
    if oracle["status"] != out["status"]:
        raise ValueError("native/reference SCC status mismatch")
    selected = {
        "status": out["status"],
        "spectral_radius": float(out["spectral_radius"]),
        "ipr": float(out["ipr"]),
        "eeec": float(out["eeec"]),
        "collatz_lower": float(out["collatz_lower"]),
        "collatz_upper": float(out["collatz_upper"]),
        "residual_l1": float(out["residual_l1"]),
        "scc_count": int(out["scc_count"]),
        "cyclic_scc_count": int(out["cyclic_scc_count"]),
        "root_edge": int(out["mode_root_edge"]),
        "mode_edge_count": int(out["mode_edge_count"]),
        "dominant_tie_count": int(out["dominant_tie_count"]),
        "iterations": int(out["iterations"]),
        "top_edges": [[edge, round(weight, 12)] for edge, weight in ranked],
        "edge_density": round(len(edges)/(n*m), 12),
    }
    verify_native_reference(selected, oracle)
    return selected


def verify_native_reference(native: dict, oracle: dict) -> None:
    if native["status"] != oracle["status"]:
        raise ValueError("native status differs from independent oracle")
    for metric, expected in (
        ("spectral_radius", oracle["spectral_radius"]),
        ("ipr", oracle["ipr"]),
        ("eeec", oracle["eeec"]),
    ):
        if type(native.get(metric)) is not float or \
                not math.isfinite(native[metric]) or \
                abs(native[metric] - expected) > 2e-6 * max(1.0, expected):
            raise ValueError(f"independent eigenmode disagreement: {metric}")
    for field, oracle_field in (
        ("scc_count", "scc_count"),
        ("cyclic_scc_count", "cyclic_scc_count"),
        ("root_edge", "root"),
        ("mode_edge_count", "mode_edges"),
        ("dominant_tie_count", "ties"),
    ):
        if type(native.get(field)) is not int or \
                native[field] != oracle[oracle_field]:
            raise ValueError(f"independent SCC mismatch: {field}")
    if native["status"] == "CONVERGED_NUMERIC":
        if (native["collatz_lower"] > native["spectral_radius"] + 1e-7
                or native["collatz_upper"] + 1e-7 <
                   native["spectral_radius"]
                or native["collatz_upper"] - native["collatz_lower"] > 1e-6
                or native["residual_l1"] > 1e-6
                or not 1 <= native["iterations"] <= 2000):
            raise ValueError("native numerical witness not converged")
    elif (native["spectral_radius"] != 0.0 or native["ipr"] != 0.0
          or native["mode_edge_count"] != 0):
        raise ValueError("native invented a nontrivial nilpotent mode")


def validate_config(config: dict) -> tuple[int, int, int, int, list[int], str, int]:
    if type(config) is not dict or set(config) != {
        "graphs", "trials", "variables", "checks", "noise_bps",
        "seed", "max_iterations", "primary_noise_bps",
    }:
        raise ValueError("unknown/missing experiment configuration")
    graphs, trials = config["graphs"], config["trials"]
    n, m = config["variables"], config["checks"]
    noise, seed = config["noise_bps"], config["seed"]
    iterations, primary = config["max_iterations"], config["primary_noise_bps"]
    if (any(type(v) is not int for v in
            (graphs, trials, n, m, iterations, primary)) or
            not 10 <= graphs <= 40 or not 2 <= trials <= 32 or
            not 16 <= n <= 128 or not 8 <= m <= 128 or
            not 2 <= iterations <= 50 or
            type(seed) is not str or not 1 <= len(seed) <= 64 or
            not seed.isascii() or not seed.replace("-", "").replace("_", "").isalnum() or
            type(noise) is not list or not 1 <= len(noise) <= 5 or
            sorted(set(noise)) != noise or
            any(type(x) is not int or not 0 <= x <= 5000 for x in noise) or
            primary not in noise or graphs*trials*len(noise) > 2500):
        raise ValueError("invalid bounded Phase 1E configuration")
    return graphs, trials, n, m, noise, seed, iterations


def classify(record: dict, graph: dict, field: str) -> tuple[float, bool]:
    return (float(graph["spectral"][field]), record["bp"]["frame_failure"])


def _graph_risk_spearman(records, graphs, feature, noise_bps):
    grouped = defaultdict(list)
    for item in records:
        if item["noise_bps"] == noise_bps and item["graph_id"] % 5 == 0:
            grouped[item["graph_id"]].append(item["bp"]["frame_failure"])
    graph_ids = sorted(grouped)
    return ref.spearman(
        [graphs[gid]["spectral"][feature] for gid in graph_ids],
        [sum(grouped[gid])/len(grouped[gid]) for gid in graph_ids],
    )


def scores_report(records: list[dict], graphs: list[dict], config: dict) -> dict:
    reports = {}
    for noise in config["noise_bps"]:
        train = [r for r in records if r["noise_bps"] == noise and
                 r["graph_id"] % 5 != 0]
        held = [r for r in records if r["noise_bps"] == noise and
                r["graph_id"] % 5 == 0]
        features = {}
        for name in PREDICTORS:
            training = [classify(row, graphs[row["graph_id"]], name)
                        for row in train]
            testing = [classify(row, graphs[row["graph_id"]], name)
                       for row in held]
            threshold = ref.fit_threshold(training)
            features[name] = {
                "train_auroc": ref.auroc(training),
                "heldout_auroc": ref.auroc(testing),
                "heldout_average_precision": ref.average_precision(testing),
                "heldout_graph_spearman": _graph_risk_spearman(
                    records, graphs, name, noise),
                "train_threshold": threshold,
                "heldout_confusion": ref.confusion(testing, threshold)
                  if threshold is not None else None,
            }
        reports[str(noise)] = {
            "train_graphs": len({r["graph_id"] for r in train}),
            "heldout_graphs": len({r["graph_id"] for r in held}),
            "train_trials": len(train),
            "heldout_trials": len(held),
            "train_failures": sum(r["bp"]["frame_failure"] for r in train),
            "heldout_failures": sum(r["bp"]["frame_failure"] for r in held),
            "features": features,
        }

    baseline = reports[str(config["primary_noise_bps"])]["features"]
    primary = baseline["ipr"]["heldout_auroc"]
    density = baseline["edge_density"]["heldout_auroc"]
    if primary is None or density is None:
        finding = "NOT_EVALUABLE"
    elif primary >= 0.65 and primary - density >= 0.05:
        finding = "EXPLORATORY_SIGNAL_ONLY"
    else:
        finding = "NO_PRE_REGISTERED_PREDICTIVE_ADVANTAGE_DETECTED"
    return {
        "primary": {
            "feature": PRIMARY_FEATURE,
            "noise_bps": config["primary_noise_bps"],
            "direction": "larger_score_predicts_failure",
            "graph_split_rule": "graph_id_mod_5_eq_0_is_heldout",
            "support_threshold_auroc": 0.65,
            "support_margin_vs_edge_density": 0.05,
            "verdict": finding,
            "evidence_limit": "exploratory_graph_blocked_holdout_no_confidence_interval",
        },
        "per_noise": reports,
    }


def generate(config: dict) -> dict:
    graphs_total, trials, n, m, noise_grid, seed, max_iters = \
        validate_config(config)
    if not SCALE.is_file():
        raise ValueError("native Ada qec_scale executable is missing")
    graphs: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="qecada-phase1e-") as td:
        path = Path(td) / "graph.txt"
        for graph_id in range(graphs_total):
            edges = ref.generated_graph(graph_id, n, m, seed)
            spectral = graph_features(n, m, edges, path)
            raw = ref.canonical_graph(n, m, edges)
            graphs.append({
                "id": graph_id,
                "family": graph_id % 4,
                "split": "heldout" if graph_id % 5 == 0 else "train",
                "source_sha256": sha(raw),
                "edges": [[c, v] for c, v in edges],
                "spectral": spectral,
            })
    records = []
    for graph in graphs:
        gid = graph["id"]
        edges = [tuple(pair) for pair in graph["edges"]]
        for noise in noise_grid:
            for trial in range(trials):
                flipped = ref.deterministic_noise(
                    seed, gid, noise, trial, n,
                )
                result = ref.decode_min_sum(
                    n, m, edges, flipped, max_iters,
                )
                records.append({
                    "graph_id": gid, "noise_bps": noise, "trial": trial,
                    "flipped_sites": sorted(flipped),
                    "bp": result,
                })
    unsigned = {
        "schema": SCHEMA,
        "config": config,
        "graphs": graphs,
        "trials": records,
        "analysis": scores_report(records, graphs, config),
        "claims": {
            "controlled_classical_binary_min_sum_bp": True,
            "native_spectral_only_observational": True,
            "decoder_core_unchanged": True,
            "original_qec_bp_equivalence": False,
            "physical_quantum_threshold": False,
            "causal_prediction_proved": False,
            "graph_blocked_holdout": True,
            "zero_or_negative_results_retained": True,
        },
    }
    return {**unsigned, "sha256": sha(canonical(unsigned))}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate evidence JSON key")
        result[key] = value
    return result


def verify_bytes(raw: bytes) -> dict:
    if len(raw) > 20_000_000:
        raise ValueError("evidence exceeds strict archive size limit")
    artifact = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    if type(artifact) is not dict or set(artifact) != {
        "schema", "config", "graphs", "trials", "analysis", "claims", "sha256"
    } or artifact["schema"] != SCHEMA:
        raise ValueError("evidence schema mismatch")
    if raw != canonical(artifact) + b"\n":
        raise ValueError("noncanonical evidence bytes")
    if sha(canonical({k: v for k, v in artifact.items() if k != "sha256"})) != \
            artifact["sha256"]:
        raise ValueError("evidence SHA-256 mismatch")
    config = artifact["config"]
    count, trials, n, m, noise_grid, seed, max_iters = \
        validate_config(config)
    if type(artifact["graphs"]) is not list or \
            len(artifact["graphs"]) != count:
        raise ValueError("graph coverage mismatch")
    for gid, graph in enumerate(artifact["graphs"]):
        if type(graph) is not dict or set(graph) != {
            "id", "family", "split", "source_sha256", "edges", "spectral"
        } or graph["id"] != gid or graph["family"] != gid % 4 or \
                graph["split"] != ("heldout" if gid % 5 == 0 else "train"):
            raise ValueError("graph identity or split manipulation")
        edges = ref.generated_graph(gid, n, m, seed)
        if graph["edges"] != [[c, v] for c, v in edges] or \
                graph["source_sha256"] != \
                sha(ref.canonical_graph(n, m, edges)):
            raise ValueError("generated graph topology/source mismatch")
        oracle = ref.reference_spectrum(n, m, edges)
        if type(graph["spectral"]) is not dict:
            raise ValueError("malformed spectrum")
        verify_native_reference(graph["spectral"], oracle)
        if graph["spectral"]["edge_density"] != \
                round(len(edges)/(n*m), 12):
            raise ValueError("graph density manipulation")

    records = artifact["trials"]
    if type(records) is not list or len(records) != \
            count * trials * len(noise_grid):
        raise ValueError("controlled trial coverage mismatch")
    cursor = 0
    for graph in artifact["graphs"]:
        edges = [tuple(x) for x in graph["edges"]]
        gid = graph["id"]
        for noise in noise_grid:
            for trial in range(trials):
                row = records[cursor]
                cursor += 1
                if type(row) is not dict or set(row) != {
                    "graph_id", "noise_bps", "trial", "flipped_sites", "bp"
                } or (row["graph_id"], row["noise_bps"], row["trial"]) != (
                    gid, noise, trial):
                    raise ValueError("trial order or membership manipulated")
                flipped = ref.deterministic_noise(seed, gid, noise, trial, n)
                expected = ref.decode_min_sum(n, m, edges, flipped, max_iters)
                if row["flipped_sites"] != sorted(flipped) or \
                        canonical(row["bp"]) != canonical(expected):
                    raise ValueError("native-independent classical BP replay failed")
    expected_analysis = scores_report(records, artifact["graphs"], config)
    if canonical(artifact["analysis"]) != canonical(expected_analysis):
        raise ValueError("predictive evaluation was altered")
    expected_claims = {
        "controlled_classical_binary_min_sum_bp": True,
        "native_spectral_only_observational": True,
        "decoder_core_unchanged": True,
        "original_qec_bp_equivalence": False,
        "physical_quantum_threshold": False,
        "causal_prediction_proved": False,
        "graph_blocked_holdout": True,
        "zero_or_negative_results_retained": True,
    }
    if canonical(artifact["claims"]) != canonical(expected_claims):
        raise ValueError("scientific claim boundary was altered")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="execute and save full controlled trial corpus")
    run.add_argument("output", type=Path)
    run.add_argument("--graphs", type=int, default=20)
    run.add_argument("--trials", type=int, default=12)
    run.add_argument("--variables", type=int, default=32)
    run.add_argument("--checks", type=int, default=24)
    run.add_argument("--seed", default="qecada-phase1e-001")
    run.add_argument("--noise-bps", default="400,800,1200")
    run.add_argument("--primary-noise-bps", type=int, default=800)
    run.add_argument("--max-iterations", type=int, default=18)
    verify = sub.add_parser("verify", help="fully replay archived evidence offline")
    verify.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "run":
            noise_bps = [int(value) for value in args.noise_bps.split(",")]
            config = {
                "graphs": args.graphs, "trials": args.trials,
                "variables": args.variables, "checks": args.checks,
                "seed": args.seed, "noise_bps": noise_bps,
                "primary_noise_bps": args.primary_noise_bps,
                "max_iterations": args.max_iterations,
            }
            artifact = generate(config)
            blob = canonical(artifact) + b"\n"
            with args.output.open("xb") as output:
                output.write(blob)
            primary = artifact["analysis"]["primary"]
            print("PASS controlled binary BP experiment, independent Ada/Python modes")
            print(f"graphs={args.graphs}; trials={len(artifact['trials'])}")
            print(f"verdict={primary['verdict']}")
            print(f"artifact_sha256={artifact['sha256']}")
        else:
            if args.path.is_symlink() or not args.path.is_file():
                raise ValueError("evidence must be a regular, non-symlink file")
            receipt = verify_bytes(args.path.read_bytes())
            print(f"PASS complete offline graph/BP/evaluation replay {receipt['sha256']}")
        return 0
    except (ValueError, OSError, TypeError, UnicodeError,
            subprocess.SubprocessError, ArithmeticError) as exc:
        print(f"FAIL phase1e experiment: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
