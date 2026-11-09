#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Phase 1I source-bound ideal-syndrome Pauli/CSS logical-frame experiment.

Read-only external files are verified against Phase 1H's exact Git blob
manifest; raw matrices never enter the receipt. Pure standard-library
decoder; no QEC reference import, no NumPy, no random clock or network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import phase1e_experiment as phase1e
import phase1e_reference as reference
import phase1h_external_css as ext
import phase1i_css_pauli as css

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "qec-ada.phase1i.css-pauli-logical-evidence.v1"
SEED = "qecada-phase1i-css-pauli-001"
RATES = (400, 800, 1200)
TRIALS = 8
ROUNDS = 14
LIMIT_BYTES = 8_000_000
BOUNDARY = {
    "ideal_noiseless_syndrome_only": True,
    "depolarizing_pauli_xyz_channel_with_y_correlation": True,
    "separate_xz_integer_syndrome_min_sum": True,
    "canonical_radius_one_syndrome_fallback": True,
    "exact_gf2_stabilizer_coset_logical_classification": True,
    "unresolved_syndromes_distinct_from_logical_failure": True,
    "external_source_matrices_redistributed": False,
    "no_circuit_level_fault_tolerance_simulation": True,
    "no_joint_css_belief_propagation": True,
    "no_quantum_hardware_measurement": True,
    "no_retroactive_phase1e_to_1h_predictive_reclassification": True,
    "no_source_executable_imported": True,
}


def canonical(value: object) -> bytes:
    return phase1e.canonical(value)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protocol() -> dict:
    m = ext.manifest()
    if (len(m["matrix_pairs"]) != 9 or
            [item["id"] for item in m["matrix_pairs"]] !=
            list(ext.ORDER)):
        raise ValueError("changed external-source admission manifest")
    return {
        "noise_bps": list(RATES), "trials_per_code_and_noise": TRIALS,
        "syndrome_min_sum_max_rounds": ROUNDS,
        "channel": "independent_qubit_X_Y_Z_equiprobable_given_depolarization",
        "channel_seed": SEED,
        "physical_error_known_only_to_evaluator": True,
        "decoder_input": "ideal_css_syndromes_uniform_positive_prior",
        "primary_report": "stabilizer_success_logical_and_unresolved_counted_separately",
        "predictor_testing": "descriptive_only_no_selection_or_new_threshold",
        "heldout_publisher": "explicit",
        "source_manifest_sha256": digest(ext.MANIFEST.read_bytes()),
    }


def sources(donors: dict[str, Path]) -> tuple[list[dict], list[css.CSS]]:
    m = ext.manifest()
    records = []
    models = []
    seen = set()
    with tempfile.TemporaryDirectory(prefix="qecada-1i-spectral-") as td:
        graph = Path(td) / "hz-graph.txt"
        for entry in m["matrix_pairs"]:
            observation, hz = ext.admit(entry, donors)
            p = entry["provider"]
            hx_raw = ext.checked_matrix(donors[p], p, entry["Hx"])
            read = ext.dense01 if entry["format"] == "dense01" else ext.matrix_market01
            nx, mx, hx = read(hx_raw)
            if nx != observation["n"] or mx != observation["m_x"]:
                raise ValueError("inconsistent admitted H_X dimensions")
            model = css.prepare(nx, mx, hx, observation["m_z"], hz)
            if model.k < 0:
                raise ValueError("invalid CSS logical dimension")
            ident = observation["hz_tanner_sha256"]
            if ident in seen:
                raise ValueError("duplicated independent source topology")
            seen.add(ident)
            # Existing native SCC and independent Python model agreement.
            spectrum = phase1e.graph_features(nx, observation["m_z"], hz, graph)
            records.append({
                "code_id": entry["id"], "provider": p,
                "split": "heldout" if p == "explicit" else "source_baseline",
                "n": model.n, "x_checks": len(model.xrows),
                "z_checks": len(model.zrows),
                "rank_x_gf2": len(model.xbasis),
                "rank_z_gf2": len(model.zbasis),
                "encoded_k": model.k,
                "hx_file_sha256": observation["hx_source_sha256"],
                "hz_file_sha256": observation["hz_source_sha256"],
                "hz_tanner_sha256": ident,
                "css_checks_commute": True,
                "native_spectral_observation": spectrum,
            })
            models.append(model)
    if len(records) != 9 or sum(r["split"] == "heldout" for r in records) != 7:
        raise ValueError("expected external publisher split absent")
    return records, models


def proportion(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate(records: list[dict], trials: list[dict]) -> dict:
    report = {}
    for bps in RATES:
        partitions = {}
        for split in ("source_baseline", "heldout"):
            rows = [r for r in trials if r["noise_bps"] == bps
                    and records[r["source_index"]]["split"] == split]
            success = sum(r["result"]["outcome"] ==
                          "STABILIZER_EQUIVALENT_SUCCESS" for r in rows)
            logical = sum(r["result"]["outcome"] ==
                          "NONTRIVIAL_LOGICAL" for r in rows)
            unresolved = sum(r["result"]["outcome"] ==
                             "DETECTED_UNRESOLVED" for r in rows)
            if success + logical + unresolved != len(rows):
                raise ValueError("CSS Pauli outcome accounting failure")
            consistent = success + logical
            partitions[split] = {
                "distinct_source_topologies": sum(
                    r["split"] == split for r in records),
                "trials": len(rows), "stabilizer_success": success,
                "nontrivial_logical": logical,
                "detected_unresolved": unresolved,
                "frame_failure_count": logical + unresolved,
                "frame_failure_fraction": proportion(
                    logical + unresolved, len(rows)),
                "logical_fraction_of_all_trials": proportion(logical, len(rows)),
                "conditional_logical_given_resolved":
                    proportion(logical, consistent),
                "resolved_fraction": proportion(consistent, len(rows)),
                "x_logical": sum(row["result"]["logical_x"] is True
                                 for row in rows),
                "z_logical": sum(row["result"]["logical_z"] is True
                                 for row in rows),
                "y_channel_errors": sum(row["result"]["y_count"] for row in rows),
            }
            if len(rows) != partitions[split]["distinct_source_topologies"] * TRIALS:
                raise ValueError("incomplete CSS source/noise trial matrix")
        heldout = [row for row in trials if row["noise_bps"] == bps
                   and records[row["source_index"]]["split"] == "heldout"
                   and row["result"]["syndrome_consistent"]]
        ipr_pairs = [(records[row["source_index"]]
                      ["native_spectral_observation"]["ipr"],
                      bool(row["result"]["logical_failure"]))
                     for row in heldout]
        density_pairs = [(records[row["source_index"]]
                          ["native_spectral_observation"]["edge_density"],
                          bool(row["result"]["logical_failure"]))
                         for row in heldout]
        report[str(bps)] = {
            "by_publisher": partitions,
            "exploratory_resolved_only_ipr_auroc": reference.auroc(ipr_pairs),
            "exploratory_resolved_only_density_auroc":
                reference.auroc(density_pairs),
            "heldout_resolved_trials_for_exploration": len(heldout),
            "selection_bias_warning":
                "resolved-only outcomes are selected by decoder performance",
        }
    return {
        "per_noise": report,
        "claim_boundary":
            "phenomenological_ideal_syndrome_css_not_circuit_fault_tolerance",
        "primary_noise_bps": 800,
        "outcome_priority":
            ["STABILIZER_EQUIVALENT_SUCCESS", "NONTRIVIAL_LOGICAL",
             "DETECTED_UNRESOLVED"],
        "predictive_verdict": "NOT_PRE_REGISTERED_FOR_PHASE1I",
    }


def make(donors: dict[str, Path]) -> dict:
    declared = protocol()
    records, models = sources(donors)
    trials = []
    for index, (record, model) in enumerate(zip(records, models)):
        for rate in RATES:
            for trial in range(TRIALS):
                planted = css.pauli_tape(SEED, record["code_id"],
                                          rate, trial, model.n)
                outcome = css.run_case(model, planted, ROUNDS)
                trials.append({
                    "source_index": index, "code_id": record["code_id"],
                    "noise_bps": rate, "trial": trial,
                    "result": outcome,
                })
    if len(trials) != 9 * len(RATES) * TRIALS:
        raise ValueError("missing deterministic Pauli trials")
    unsigned = {
        "schema": SCHEMA, "protocol": declared,
        "sources": records, "pauli_trials": trials,
        "evaluation": evaluate(records, trials),
        "original_phase1h_receipt_sha256":
            "d81f1bff2e29fa846e972320d6aca6a2d62ac65655ac8fbaf013e87d9023315a",
        "claim_boundary": BOUNDARY,
    }
    return {**unsigned, "sha256": digest(canonical(unsigned))}


def verify(raw: bytes, donors: dict[str, Path]) -> dict:
    if len(raw) > LIMIT_BYTES:
        raise ValueError("oversize Phase 1I source-bound evidence")
    doc = json.loads(raw.decode("utf-8"),
                     object_pairs_hook=phase1e.unique_pairs)
    if type(doc) is not dict or set(doc) != {
        "schema", "protocol", "sources", "pauli_trials", "evaluation",
        "original_phase1h_receipt_sha256", "claim_boundary", "sha256"
    } or doc["schema"] != SCHEMA:
        raise ValueError("invalid Phase 1I evidence membership/schema")
    if canonical(doc) + b"\n" != raw:
        raise ValueError("noncanonical Phase 1I receipt bytes")
    if doc["sha256"] != digest(canonical({
            key: value for key, value in doc.items() if key != "sha256"})):
        raise ValueError("Phase 1I evidence digest mismatch")
    expected = make(donors)
    if canonical(expected) != canonical(doc):
        raise ValueError("Phase 1I source/Pauli/syndrome/logical replay mismatch")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for command in ("create", "verify"):
        cmd = subs.add_parser(command)
        cmd.add_argument("path", type=Path)
        cmd.add_argument("--simula", type=Path, required=True)
        cmd.add_argument("--explicit", type=Path, required=True)
    args = parser.parse_args()
    donors = {"simula": args.simula, "explicit": args.explicit}
    try:
        if args.action == "create":
            result = make(donors)
            with args.path.open("xb") as handle:
                handle.write(canonical(result) + b"\n")
            print("PASS exact CSS Pauli syndrome and logical coset study")
            print("source_css_codes=" + str(len(result["sources"])))
            print("pauli_trials=" + str(len(result["pauli_trials"])))
            for rate in RATES:
                r = result["evaluation"]["per_noise"][str(rate)]
                for publisher in ("source_baseline", "heldout"):
                    o = r["by_publisher"][publisher]
                    print("noise_bps=" + str(rate) + " split=" + publisher +
                          " stabilizer_success=" + str(o["stabilizer_success"]) +
                          " logical=" + str(o["nontrivial_logical"]) +
                          " detected_unresolved=" + str(o["detected_unresolved"]) +
                          " trials=" + str(o["trials"]))
            print("receipt_sha256=" + result["sha256"])
        else:
            if args.path.is_symlink() or not args.path.is_file():
                raise ValueError("receipt must be a regular non-symlink file")
            result = verify(args.path.read_bytes(), donors)
            print("PASS independent source/Pauli/logical full replay " +
                  result["sha256"])
        return 0
    except (OSError, ValueError, TypeError, UnicodeError,
            ArithmeticError) as exc:
        print("FAIL Phase 1I: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
