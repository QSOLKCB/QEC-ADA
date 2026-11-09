#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Phase 1F: exact-source-bound, graph-cluster uncertainty on Phase 1E.

Bootstrap the *held-out graph identities*, never individual BP trials.
Preserve the original negative Phase 1E finding and its preregistration.
Conditional percentile ranges are exploratory, not confidence-certified
physical-QEC thresholds or independent validation datasets.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

import phase1e_experiment as phase1e
import phase1e_reference as reference

SCHEMA = "qec-ada.phase1f-graph-cluster-inference.v1"
FEATURES = ("ipr", "edge_density")
ALGORITHM = "sha256-deterministic-graph-block-bootstrap-v1"
DEFAULT_RESAMPLES = 512


def canonical(obj: object) -> bytes:
    return phase1e.canonical(obj)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percentile(data: list[float], fraction: float) -> float | None:
    if not data:
        return None
    sorted_values = sorted(data)
    pos = (len(sorted_values) - 1) * fraction
    low = math.floor(pos)
    high = math.ceil(pos)
    return sorted_values[low] + (pos - low) * (
        sorted_values[high] - sorted_values[low])


def intervals(data: list[float]) -> list[float] | None:
    if not data:
        return None
    return [percentile(data, 0.025), percentile(data, 0.975)]


def graph_index(source: dict, noise_bps: int) -> dict[int, dict]:
    out = {}
    for graph in source["graphs"]:
        if graph["split"] == "heldout":
            gid = graph["id"]
            trials = [r for r in source["trials"]
                      if r["graph_id"] == gid and
                      r["noise_bps"] == noise_bps]
            if len(trials) != source["config"]["trials"]:
                raise ValueError("held-out graph trial coverage mismatch")
            if gid in out:
                raise ValueError("duplicate held-out graph")
            out[gid] = {
                "trial_outcomes": [r["bp"]["frame_failure"] for r in trials],
                "ipr": graph["spectral"]["ipr"],
                "edge_density": graph["spectral"]["edge_density"],
            }
    if len(out) < 2:
        raise ValueError("insufficient held-out topology clusters")
    return out


def expand(sample: list[int], graphs: dict[int, dict],
           feature: str) -> list[tuple[float, bool]]:
    """Each sampled cluster contributes ALL its original trials."""
    return [
        (float(graphs[gid][feature]), failure)
        for gid in sample for failure in graphs[gid]["trial_outcomes"]
    ]


def draw_cluster(seed: str, noise_bps: int, replicate: int,
                 position: int, count: int) -> int:
    if count < 1:
        raise ValueError("empty cluster draw")
    material = f"QECADA/PHASE1F/CLUSTER/{seed}/{noise_bps}/{replicate}/{position}"
    return int.from_bytes(hashlib.sha256(material.encode("ascii")).digest(),
                          "big") % count


def exact_permutation_p(graphs: dict[int, dict],
                        feature: str) -> float | None:
    """Exact two-sided graph-label Spearman permutation, max 8 clusters."""
    ids = sorted(graphs)
    if len(ids) > 8:
        return None
    risk = [float(graphs[gid][feature]) for gid in ids]
    rates = [
        sum(graphs[gid]["trial_outcomes"]) /
        len(graphs[gid]["trial_outcomes"]) for gid in ids
    ]
    observed = reference.spearman(risk, rates)
    if observed is None:
        return None
    total = 0
    extreme = 0
    for labels in itertools.permutations(rates):
        corr = reference.spearman(risk, list(labels))
        if corr is None:
            raise ValueError("permutation undefined after valid observation")
        total += 1
        if abs(corr) + 1.0e-12 >= abs(observed):
            extreme += 1
    return extreme / total


def compute(source: dict, parent_raw: bytes,
            resamples: int = DEFAULT_RESAMPLES) -> dict:
    if type(resamples) is not int or not 16 <= resamples <= 4096:
        raise ValueError("resamples must be integer 16..4096")
    # The parent is fully replayed before use; no unverifiable labels.
    phase1e.verify_bytes(parent_raw)
    rates = source["config"]["noise_bps"]
    seed = digest(parent_raw)
    report = {}
    for noise in rates:
        grouped = graph_index(source, noise)
        gids = sorted(grouped)
        observed_pairs = {
            name: expand(gids, grouped, name) for name in FEATURES
        }
        original = {
            name: reference.auroc(pairs)
            for name, pairs in observed_pairs.items()
        }
        samples: dict[str, list[float]] = {name: [] for name in FEATURES}
        differences: list[float] = []
        undefined = 0
        for i in range(resamples):
            chosen = [gids[draw_cluster(seed, noise, i, pos, len(gids))]
                      for pos in range(len(gids))]
            vals = {name: reference.auroc(expand(chosen, grouped, name))
                    for name in FEATURES}
            if any(value is None for value in vals.values()):
                undefined += 1
                continue
            for name in FEATURES:
                samples[name].append(vals[name])
            differences.append(vals["ipr"] - vals["edge_density"])
        report[str(noise)] = {
            "heldout_graph_ids": gids,
            "heldout_graph_count": len(gids),
            "trials_per_graph": source["config"]["trials"],
            "observed_auroc": original,
            "conditional_valid_bootstrap_replicates": len(differences),
            "undefined_bootstrap_replicates": undefined,
            "conditional_percentile_95_auroc": {
                name: intervals(samples[name]) for name in FEATURES
            },
            "conditional_percentile_95_ipr_minus_density":
                intervals(differences),
            "observed_ipr_minus_density":
                None if any(x is None for x in original.values())
                else original["ipr"] - original["edge_density"],
            "graph_level_exact_permutation_p_two_sided": {
                name: exact_permutation_p(grouped, name)
                for name in FEATURES
            },
        }
    return {
        "method": ALGORITHM,
        "resamples": resamples,
        "sampling_unit": "whole_heldout_tanner_graph",
        "source_receipt_sha256": source["sha256"],
        "source_file_sha256": seed,
        "primary_noise_bps": source["config"]["primary_noise_bps"],
        "preregistered_phase1e_verdict": source["analysis"]["primary"]["verdict"],
        "per_noise": report,
        "claim_boundary": {
            "exploratory_conditional_bootstrap": True,
            "graphs_are_independent_resampling_units": True,
            "undefined_one_class_samples_retained": True,
            "no_new_primary_threshold": True,
            "negative_phase1e_verdict_preserved": True,
            "independent_external_validation": False,
            "quantum_hardware_evidence": False,
            "causal_claim": False,
        },
    }


def make(raw: bytes, resamples: int) -> dict:
    source = phase1e.verify_bytes(raw)
    result = compute(source, raw, resamples)
    payload = {"schema": SCHEMA, "inference": result}
    return {**payload, "sha256": digest(canonical(payload))}


def verify(raw_parent: bytes, raw_report: bytes) -> dict:
    report = json.loads(raw_report.decode("utf-8"),
                        object_pairs_hook=phase1e.unique_pairs)
    if type(report) is not dict or set(report) != {
        "schema", "inference", "sha256"
    } or report["schema"] != SCHEMA:
        raise ValueError("inference schema mismatch")
    if raw_report != canonical(report) + b"\n":
        raise ValueError("noncanonical inference bytes")
    if report["sha256"] != digest(canonical({
            k: v for k, v in report.items() if k != "sha256"})):
        raise ValueError("inference SHA-256 mismatch")
    method = report["inference"]
    if type(method) is not dict or type(method.get("resamples")) is not int:
        raise ValueError("invalid resample contract")
    expected = make(raw_parent, method["resamples"])
    if canonical(expected) != canonical(report):
        raise ValueError("independent graph-cluster inference replay mismatch")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("parent", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    check = sub.add_parser("verify")
    check.add_argument("parent", type=Path)
    check.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        if args.cmd == "create":
            if args.parent.is_symlink() or not args.parent.is_file():
                raise ValueError("missing or symlinked Phase 1E parent")
            report = make(args.parent.read_bytes(), args.resamples)
            with args.output.open("xb") as file:
                file.write(canonical(report) + b"\n")
            primary = report["inference"]["per_noise"][
                str(report["inference"]["primary_noise_bps"])]
            print("PASS source-replayed graph-blocked uncertainty")
            print("primary_ipr_auroc=" +
                  str(primary["observed_auroc"]["ipr"]))
            print("primary_ipr_95_conditional=" +
                  str(primary["conditional_percentile_95_auroc"]["ipr"]))
            print("undefined_replicates=" +
                  str(primary["undefined_bootstrap_replicates"]))
            print("report_sha256=" + report["sha256"])
        else:
            if any(path.is_symlink() or not path.is_file()
                   for path in (args.parent, args.report)):
                raise ValueError("input must be a regular, non-symlink file")
            observed = verify(args.parent.read_bytes(),
                              args.report.read_bytes())
            print("PASS independent offline bootstrap replay " +
                  observed["sha256"])
        return 0
    except (ValueError, OSError, TypeError, UnicodeError,
            json.JSONDecodeError) as exc:
        print(f"FAIL phase1f: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
