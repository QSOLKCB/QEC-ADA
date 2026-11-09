#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Phase 1G — pinned-QEC CSS Tanner admission and family-blocked BP trial.

Source: QEC's original create_code() at the exact Phase 1F donor SHA.
This program EXECUTES that separately verified source only after explicit
opt-in. It tests *binary classical slices* of CSS checks; it is not a
depolarizing-channel QLDPC quantum decoder or external hardware dataset.
Default QEC-ADA Ada and stdlib research tools do not require NumPy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile

import phase1e_experiment as phase1e
import phase1e_reference as ref
import phase1f_blocked_inference as blocked
import phase1f_qec_bp_bridge as qec

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "qec-ada.phase1g-pinned-qec-css-cohort.v1"
LABEL = "X_error_detected_by_H_Z_classical_binary_slice"
BASELINE_SHA = "ee0dc4ea5868386b3e60bbdef20c9d5c2c8e4b43e5ae160847f0bb5069a69738"
ORDER = ("rate_0.50", "rate_0.60", "rate_0.75")
LIFTS = {"rate_0.50": (4, 5), "rate_0.60": (3, 4),
         "rate_0.75": (4, 5)}
SEEDS = (17, 29, 41, 53)
NOISE_BPS = (400, 800, 1200)
TRIALS = 4
QEC_TRIALS = 2
ITERATIONS = 14
PRIMARY_NOISE_BPS = 800
BOOTSTRAPS = 256
FEATURES = ("ipr", "spectral_radius", "eeec", "edge_density")
CLAIMS = {
    "binary_classical_css_component_only": True,
    "real_pinned_qec_generated_topologies": True,
    "separately_published_external_graph_dataset": False,
    "unseen_code_family_heldout": True,
    "source_code_execution_requires_opt_in": True,
    "native_gf3_decoder_unchanged": True,
    "original_phase1e_negative_baseline_preserved": True,
    "duplicate_topologies_pretrial_deduplicated": True,
    "cross_decoder_update_equations_identical": False,
    "generalizable_prediction_validated": False,
    "physical_quantum_hardware_evidence": False,
}


def canonical(value: object) -> bytes:
    return phase1e.canonical(value)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def import_pinned(donor: Path):
    """Admit executable reference only after exact commit, blob and bytes."""
    source = qec.checked_source(donor)
    import numpy as np
    spec = importlib.util.spec_from_file_location(
        "qecada_phase1g_verified_qec_qldpc", source
    )
    if spec is None or spec.loader is None:
        raise ValueError("QEC reference source import unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not callable(getattr(module, "create_code", None)) or \
            not callable(getattr(module, "bp_decode", None)):
        raise ValueError("pinned QEC source lacks required generator/decoder")
    return module, np, digest(source.read_bytes())


def matrix_edges(matrix, np) -> tuple[int, int, list[tuple[int, int]]]:
    arr = np.asarray(matrix)
    if arr.ndim != 2:
        raise ValueError("QEC check matrix is not 2-dimensional")
    m, n = map(int, arr.shape)
    if not 1 <= n <= ref.MAX_VARIABLES or \
            not 1 <= m <= ref.MAX_CHECKS:
        raise ValueError("QEC matrix outside Ada node capacities")
    rows = arr.tolist()
    edges = []
    for c, row in enumerate(rows, 1):
        for v, value in enumerate(row, 1):
            if type(value) is not int or value not in (0, 1):
                raise ValueError("QEC matrix is not binary")
            if value:
                edges.append((c, v))
    if len(edges) > ref.MAX_EDGES:
        raise ValueError("QEC matrix exceeds Ada sparse edge capacity")
    ref.canonical_graph(n, m, edges)
    return n, m, edges


def row_masks(n: int, m: int, edges: list[tuple[int, int]]) -> list[int]:
    rows = [0] * m
    for check, variable in edges:
        rows[check - 1] |= 1 << (variable - 1)
    return rows


def rank_gf2(masks: list[int]) -> int:
    """Independent exact GF(2) integer-row echelon rank, no floats."""
    pivots: dict[int, int] = {}
    for row in masks:
        value = row
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = value
                break
            value ^= pivots[pivot]
    return len(pivots)


def css_orthogonal(x: list[int], z: list[int]) -> bool:
    return all(((a & b).bit_count() & 1) == 0
               for a in x for b in z)


def create_source_codes(module, np) -> tuple[list[dict], list[dict]]:
    """Predeclared 24 candidates; deterministic first-topology ownership.

    Duplicate *within-family* seeds are recorded, not trialled as
    independent graphs. A duplicate across families is a hard split leak.
    Exclusions occur before noise/decoder outcomes are computed.
    """
    codes = []
    exclusions: list[dict] = []
    topology_owner: dict[str, int] = {}
    for family in ORDER:
        for lift in LIFTS[family]:
            for seed in SEEDS:
                code = module.create_code(
                    name=family, lifting_size=lift, seed=seed
                )
                nx, mx, hx = matrix_edges(code.H_X, np)
                nz, mz, hz = matrix_edges(code.H_Z, np)
                if nx != nz or nx != int(code.n):
                    raise ValueError("QEC CSS H_X/H_Z physical-width mismatch")
                x_masks = row_masks(nx, mx, hx)
                z_masks = row_masks(nz, mz, hz)
                if not css_orthogonal(x_masks, z_masks) or \
                        not bool(code.verify_css_orthogonality()):
                    raise ValueError("QEC CSS orthogonality rejected independently")
                source_bytes = ref.canonical_graph(nz, mz, hz)
                source_hash = digest(source_bytes)
                if source_hash in topology_owner:
                    first_id = topology_owner[source_hash]
                    if codes[first_id]["family"] != family:
                        raise ValueError(
                            "train/heldout or cross-family duplicate topology"
                        )
                    exclusions.append({
                        "family": family, "lift": lift, "seed": seed,
                        "hz_graph_sha256": source_hash,
                        "same_as_admitted_code_id": first_id,
                        "reason": "EXACT_DUPLICATE_TOPOLOGY_PRE_TRIAL",
                    })
                    continue
                topology_owner[source_hash] = len(codes)
                codes.append({
                    "id": len(codes),
                    "family": family,
                    "lift": lift,
                    "seed": seed,
                    "split": "heldout" if family == "rate_0.75" else "train",
                    "n": nz, "m_x": mx, "m_z": mz,
                    "x_edges": [[c, v] for c, v in hx],
                    "z_edges": [[c, v] for c, v in hz],
                    "x_rank_gf2": rank_gf2(x_masks),
                    "z_rank_gf2": rank_gf2(z_masks),
                    "css_orthogonal": True,
                    "hz_graph_sha256": source_hash,
                    "hz_matrix_sha256": digest(canonical({
                        "n": nz, "m": mz, "edges": hz,
                    })),
                })
    if len(codes) + len(exclusions) != 24 or \
            sum(code["split"] == "heldout" for code in codes) < 4 or \
            sum(code["split"] == "train" for code in codes) < 8:
        raise ValueError("source candidate admission coverage mismatch")
    return codes, exclusions


def trial_rows(codes: list[dict], seed: str):
    """Deterministic fixed channel draws; no native source in error labels."""
    for code in codes:
        edges = [tuple(edge) for edge in code["z_edges"]]
        for noise in NOISE_BPS:
            for trial in range(TRIALS):
                flips = ref.deterministic_noise(
                    seed, code["id"], noise, trial, code["n"]
                )
                bp = ref.decode_min_sum(
                    code["n"], code["m_z"], edges, flips, ITERATIONS
                )
                yield {
                    "code_id": code["id"],
                    "noise_bps": noise,
                    "trial": trial,
                    "flipped_sites": sorted(flips),
                    "bp": bp,
                }


def measure_qec(module, np, codes, trials):
    """Actual QEC floating BP on the first two heldout trials per noise."""
    by_id = {code["id"]: code for code in codes}
    results = []
    for row in trials:
        code = by_id[row["code_id"]]
        if code["split"] != "heldout" or row["trial"] >= QEC_TRIALS:
            continue
        input_row = {
            "graph_id": row["code_id"],
            "noise_bps": row["noise_bps"],
            "trial": row["trial"],
            "flipped_sites": row["flipped_sites"],
            "bp": row["bp"],
        }
        graph = {
            "edges": code["z_edges"], "variables": code["n"],
            "checks": code["m_z"],
        }
        results.append(qec.run_case(
            module.bp_decode, np, graph, input_row, ITERATIONS
        ))
    heldout_count = sum(c["split"] == "heldout" for c in codes)
    if len(results) != heldout_count * len(NOISE_BPS) * QEC_TRIALS:
        raise ValueError("QEC reference matched-sample coverage mismatch")
    return results


def code_level_ranks(codes, trials, noise, feature) -> float | None:
    group = []
    for code in codes:
        if code["split"] == "heldout":
            rows = [r for r in trials if r["code_id"] == code["id"]
                    and r["noise_bps"] == noise]
            if len(rows) != TRIALS:
                raise ValueError("missing heldout graph trials")
            group.append((
                code["spectrum"][feature],
                sum(r["bp"]["frame_failure"] for r in rows) / TRIALS
            ))
    return ref.spearman(
        [a for a, b in group], [b for a, b in group])


def heldout_pairs(codes, trials, noise, feature):
    return [
        (code["spectrum"][feature], row["bp"]["frame_failure"])
        for code in codes if code["split"] == "heldout"
        for row in trials if row["code_id"] == code["id"]
        and row["noise_bps"] == noise
    ]


def graph_bootstrap(codes, trials, noise, seed, resamples=BOOTSTRAPS):
    graph_ids = [code["id"] for code in codes
                 if code["split"] == "heldout"]
    by_id = {code["id"]: code for code in codes}
    subsets = {}
    for gid in graph_ids:
        subsets[gid] = {
            f: by_id[gid]["spectrum"][f] for f in ("ipr", "edge_density")
        }
        subsets[gid]["trial_outcomes"] = [
            r["bp"]["frame_failure"] for r in trials
            if r["code_id"] == gid and r["noise_bps"] == noise
        ]
        if len(subsets[gid]["trial_outcomes"]) != TRIALS:
            raise ValueError("incomplete cluster")
    a, b, differences = [], [], []
    invalid = 0
    for iteration in range(resamples):
        chosen = [graph_ids[blocked.draw_cluster(
            seed, noise, iteration, position, len(graph_ids)
        )] for position in range(len(graph_ids))]
        av = ref.auroc(blocked.expand(chosen, subsets, "ipr"))
        bv = ref.auroc(blocked.expand(chosen, subsets, "edge_density"))
        if av is None or bv is None:
            invalid += 1
            continue
        a.append(av)
        b.append(bv)
        differences.append(av - bv)
    return {
        "whole_graph_resamples": resamples,
        "defined_replicates": len(a),
        "undefined_one_class_replicates": invalid,
        "conditional_percentile_95_ipr": blocked.intervals(a),
        "conditional_percentile_95_edge_density": blocked.intervals(b),
        "conditional_percentile_95_ipr_minus_density":
            blocked.intervals(differences),
    }


def analyze(codes, trials, qec_records, source_identity):
    analysis = {}
    train_count = sum(code["split"] == "train" for code in codes)
    heldout_count = sum(code["split"] == "heldout" for code in codes)
    for noise in NOISE_BPS:
        train = [r for r in trials if
                 codes[r["code_id"]]["split"] == "train"
                 and r["noise_bps"] == noise]
        held = [r for r in trials if
                codes[r["code_id"]]["split"] == "heldout"
                and r["noise_bps"] == noise]
        if len(train) != train_count * TRIALS or \
                len(held) != heldout_count * TRIALS:
            raise ValueError("family split counts incorrect")
        metrics = {}
        for feature in FEATURES:
            training_pairs = [
                (codes[r["code_id"]]["spectrum"][feature],
                 r["bp"]["frame_failure"]) for r in train
            ]
            pairs = heldout_pairs(codes, trials, noise, feature)
            metrics[feature] = {
                "train_auroc": ref.auroc(training_pairs),
                "heldout_auroc": ref.auroc(pairs),
                "heldout_ap": ref.average_precision(pairs),
                "heldout_graph_failure_spearman":
                    code_level_ranks(codes, trials, noise, feature),
            }
        references = [r for r in qec_records
                      if r["noise_bps"] == noise]
        analysis[str(noise)] = {
            "train_code_instances": train_count,
            "heldout_code_instances": heldout_count,
            "train_failures": sum(r["bp"]["frame_failure"] for r in train),
            "heldout_failures": sum(r["bp"]["frame_failure"] for r in held),
            "train_trials": len(train),
            "heldout_trials": len(held),
            "qec_reference_cases": len(references),
            "qec_agree_on_frame_failure":
                sum(r["failure_labels_agree"] for r in references),
            "qec_reference_failures":
                sum(r["qec_frame_failure"] for r in references),
            "features": metrics,
            "blocked": graph_bootstrap(codes, trials, noise,
                                       source_identity),
        }
    primary = analysis[str(PRIMARY_NOISE_BPS)]["features"]
    ipr = primary["ipr"]["heldout_auroc"]
    density = primary["edge_density"]["heldout_auroc"]
    if ipr is None or density is None:
        verdict = "NOT_EVALUABLE"
    elif ipr >= 0.65 and ipr - density >= 0.05:
        verdict = "EXPLORATORY_ONLY_NOT_EXTERNAL_VALIDATION"
    else:
        verdict = "NO_PRE_REGISTERED_ADVANTAGE_DETECTED"
    return {
        "primary": {
            "noise_bps": PRIMARY_NOISE_BPS,
            "higher_ipr_predicts_failure": True,
            "baseline": "edge_density",
            "threshold_auroc": 0.65,
            "threshold_margin": 0.05,
            "heldout_family": "rate_0.75",
            "train_families": ["rate_0.50", "rate_0.60"],
            "verdict": verdict,
        },
        "per_noise": analysis,
        "inference_scope": (
            "one_pinned_QEC_css_generator_three_rates;"
            "whole_family_holdout_observational_small_cohort"
        ),
    }


def make(donor: Path) -> dict:
    module, np, source_digest = import_pinned(donor)
    codes, exclusions = create_source_codes(module, np)
    # Every topology from genuine pinned QEC CSS construction.
    with tempfile.TemporaryDirectory(prefix="qecada-1g-") as folder:
        path = Path(folder) / "graph.txt"
        for code in codes:
            edges = [tuple(pair) for pair in code["z_edges"]]
            code["spectrum"] = phase1e.graph_features(
                code["n"], code["m_z"], edges, path
            )
    # Re-check no topology is shared between train and heldout.
    train_hashes = {c["hz_graph_sha256"] for c in codes
                    if c["split"] == "train"}
    heldout_hashes = {c["hz_graph_sha256"] for c in codes
                      if c["split"] == "heldout"}
    if train_hashes & heldout_hashes:
        raise ValueError("train/heldout Tanner topology leakage")
    noise_seed = "qecada-phase1g-pinned-css-001"
    trials = list(trial_rows(codes, noise_seed))
    qec_cases = measure_qec(module, np, codes, trials)
    source_identity = digest(canonical([
        [code["family"], code["lift"], code["seed"],
         code["hz_graph_sha256"]] for code in codes]))
    report = analyze(codes, trials, qec_cases, source_identity)
    unsigned = {
        "schema": SCHEMA,
        "generator": {
            "repository": "QSOLKCB/QEC",
            "commit": qec.DONOR_COMMIT,
            "git_blob_sha1": qec.SOURCE_BLOB,
            "source_path": qec.SOURCE_PATH,
            "source_file_sha256": source_digest,
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "rate_families": list(ORDER),
            "candidate_configurations": 24,
            "admitted_unique_topologies": len(codes),
            "duplicate_configurations_excluded": len(exclusions),
            "lifting_sizes": {key: list(LIFTS[key]) for key in ORDER},
            "construction_seeds": list(SEEDS),
            "heldout_rule": "rate_0.75_only",
            "experiment_seed": noise_seed,
            "noise_bps": list(NOISE_BPS),
            "trials_per_code_noise": TRIALS,
            "qec_reference_trials_per_heldout_code_noise": QEC_TRIALS,
            "max_iterations": ITERATIONS,
            "binary_component": LABEL,
        },
        "baseline_phase1e_sha256": BASELINE_SHA,
        "topologies": codes,
        "duplicate_candidates": exclusions,
        "bp_trials": trials,
        "qec_reference_records": qec_cases,
        "evaluation": report,
        "claim_boundary": CLAIMS,
    }
    return {**unsigned, "sha256": digest(canonical(unsigned))}


def unique_pairs(pairs):
    return phase1e.unique_pairs(pairs)


def verify(raw: bytes, donor: Path) -> dict:
    if len(raw) > 12_000_000:
        raise ValueError("oversized QEC/CSS cohort evidence")
    source = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    if type(source) is not dict or set(source) != {
        "schema", "generator", "baseline_phase1e_sha256",
        "topologies", "duplicate_candidates", "bp_trials",
        "qec_reference_records",
        "evaluation", "claim_boundary", "sha256",
    } or source["schema"] != SCHEMA:
        raise ValueError("cohort receipt schema mismatch")
    if canonical(source) + b"\n" != raw:
        raise ValueError("noncanonical cohort receipt")
    if source["sha256"] != digest(canonical({
            k: v for k, v in source.items() if k != "sha256"})):
        raise ValueError("cohort evidence hash mismatch")
    # Reexecuting actual pinned source is mandatory: a self-consistent
    # hash of a forged topology, decoder word or inference is not evidence.
    expected = make(donor)
    if canonical(expected) != canonical(source):
        raise ValueError("pinned CSS source/decoder/evaluation rerun mismatch")
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    create = subs.add_parser("create")
    create.add_argument("output", type=Path)
    create.add_argument("--donor", type=Path, required=True)
    create.add_argument("--execute-pinned-donor", action="store_true")
    check = subs.add_parser("verify")
    check.add_argument("path", type=Path)
    check.add_argument("--donor", type=Path, required=True)
    check.add_argument("--execute-pinned-donor", action="store_true")
    args = parser.parse_args()
    try:
        if not args.execute_pinned_donor:
            raise ValueError("explicit --execute-pinned-donor required")
        if args.action == "create":
            receipt = make(args.donor)
            with args.output.open("xb") as destination:
                destination.write(canonical(receipt) + b"\n")
            print("PASS verified pinned QEC/CSS topology cohort")
            print("predeclared_candidates=24")
            print("unique_code_topologies=" +
                  str(len(receipt["topologies"])))
            print("pre_trial_exact_duplicate_exclusions=" +
                  str(len(receipt["duplicate_candidates"])))
            print("bp_trials=" + str(len(receipt["bp_trials"])))
            print("qec_reference_cases=" + str(
                len(receipt["qec_reference_records"])))
            for noise in NOISE_BPS:
                item = receipt["evaluation"]["per_noise"][str(noise)]
                ipr = item["features"]["ipr"]["heldout_auroc"]
                density = item["features"]["edge_density"]["heldout_auroc"]
                print(f"noise_bps={noise} heldout_failures="
                      f"{item['heldout_failures']}/{item['heldout_trials']} "
                      f"ipr_auroc={ipr} density_auroc={density} "
                      f"qec_label_agreement="
                      f"{item['qec_agree_on_frame_failure']}/"
                      f"{item['qec_reference_cases']}")
            print("verdict=" + receipt["evaluation"]["primary"]["verdict"])
            print("receipt_sha256=" + receipt["sha256"])
        else:
            if args.path.is_symlink() or not args.path.is_file():
                raise ValueError("cohort input must be a regular file")
            item = verify(args.path.read_bytes(), args.donor)
            print("PASS full pinned-QEC CSS generator and BP reexecution " +
                  item["sha256"])
        return 0
    except (OSError, ValueError, TypeError, UnicodeError,
            ImportError, ArithmeticError) as exc:
        print("FAIL Phase 1G: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
