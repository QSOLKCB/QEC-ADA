#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Phase 1H: source-pinned, read-only external CSS matrices and BP evaluation.

The two matrix providers are NOT QSOLKCB/QEC and are never imported as
executable code. Their raw files are not copied to this repository or to
the research receipt (one provider has no declared repository licence).
Only the separate, explicitly opted-in, pinned QEC BP reference is executed.
Native Ada qec_scale is unchanged and used strictly as an observer.

Statistics are exploratory, with source/publisher held out wholesale.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

import phase1e_experiment as phase1e
import phase1e_reference as reference
import phase1f_blocked_inference as blocked
import phase1f_qec_bp_bridge as qec

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fixtures/phase1h_external_css_sources.json"
SCHEMA = "qec-ada.phase1h.external-css-evidence.v1"
MANIFEST_SCHEMA = "qec-ada.phase1h.external-css-manifest.v1"
SOURCE_PINS = {
    "simula": ("Simula-UiB/nisqec",
               "913e0f26b07919ab73d7052159196599d34a2969",
               "CC-BY-4.0"),
    "explicit": ("lilyxy/Check-weight-constrained-quantum-codes",
                 "0e6c3e281fe044315286fbdcf5295cb16f47f90d",
                 "UNSPECIFIED"),
}
ORDER = ("simula-tanner10", "simula-tanner45", "explicit-hgp10",
         "explicit-hgp41", "explicit-hgp58", "explicit-bb72",
         "explicit-lp75", "explicit-bb108", "explicit-lp125")
FEATURES = ("ipr", "edge_density", "spectral_radius", "eeec")
BOUNDARY = {
    "independent_external_css_matrix_sources": True,
    "one_external_source_has_unlicensed_repository_files": True,
    "raw_external_matrices_redistributed": False,
    "independent_gf2_css_orthogonality_checked": True,
    "publisher_level_holdout": True,
    "observed_graphs_are_not_iid": True,
    "classical_binary_hz_x_error_slice_only": True,
    "original_phase1e_and_phase1f_negative_results_preserved": True,
    "native_ada_decisions_changed": False,
    "full_quantum_depolarizing_css_decoding": False,
    "physical_quantum_fidelity_or_threshold": False,
    "ipr_generalization_validated": False,
}


def canonical(obj: object) -> bytes:
    return phase1e.canonical(obj)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True,
                       check=True, timeout=20)
    return p.stdout.strip()


def manifest() -> dict:
    raw = MANIFEST.read_bytes()
    data = json.loads(raw.decode("utf-8"),
                      object_pairs_hook=phase1e.unique_pairs)
    if type(data) is not dict or set(data) != {
        "schema", "sources", "matrix_pairs", "evaluation"
    } or data["schema"] != MANIFEST_SCHEMA:
        raise ValueError("external matrix manifest schema mismatch")
    if [x["id"] for x in data["matrix_pairs"]] != list(ORDER):
        raise ValueError("external matrix ids/order are not preregistered")
    if type(data["sources"]) is not dict or set(data["sources"]) != set(SOURCE_PINS):
        raise ValueError("unexpected external source owners")
    for key, (repo, commit, license_id) in SOURCE_PINS.items():
        source = data["sources"][key]
        if (source["repo"], source["commit"], source["license"],
            source["redistribute_raw"]) != (repo, commit, license_id, False):
            raise ValueError("external source provenance/license change")
    e = data["evaluation"]
    if (e["heldout_provider"], e["training_provider"],
        e["noise_bps"], e["primary_noise_bps"],
        e["trial_count_per_graph_and_noise"], e["max_bp_iterations"],
        e["qec_reference_primary_trials_per_graph"], e["bootstraps"],
        e["noise_seed"], e["risk_direction"], e["auroc_threshold"],
        e["auroc_uplift_vs_density"], e["no_fitting_on_heldout"]) != (
        "explicit", "simula", [400, 800, 1200], 800, 4, 14, 2, 256,
        "qecada-phase1h-external-css-001",
        "higher_Ipr_is_higher_classical_frame_failure_risk", 0.65, 0.05,
        True):
        raise ValueError("Phase 1H prespecified study protocol changed")
    for item in data["matrix_pairs"]:
        if type(item) is not dict or set(item) != {
            "id", "provider", "format", "Hx", "Hz"
        } or item["provider"] not in SOURCE_PINS or (
            item["format"] !=
            ("dense01" if item["provider"] == "simula" else "mtx01")):
            raise ValueError("unsupported external source or matrix format")
        for side in ("Hx", "Hz"):
            file = item[side]
            if type(file) is not dict or set(file) != {
                "path", "git_blob_sha1"
            }:
                raise ValueError("source manifest file membership mismatch")
            path = file["path"]
            if type(path) is not str or (
                not re.fullmatch(r"[A-Za-z0-9_./-]+", path)
                or path.startswith("/") or ".." in PurePosixPath(path).parts
                or len(path) > 240):
                raise ValueError("unsafe external matrix path")
            if type(file["git_blob_sha1"]) is not str or not re.fullmatch(
                    r"[0-9a-f]{40}", file["git_blob_sha1"]):
                raise ValueError("invalid source Git blob pin")
            if item["provider"] == "simula" and not path.startswith("QT/"):
                raise ValueError("Simula source path outside permitted QT subtree")
            if item["provider"] == "explicit" and not path.startswith("codes/"):
                raise ValueError("explicit QLDPC file outside codes subtree")
    return data


def checked_matrix(donor: Path, provider: str, file: dict) -> bytes:
    root = donor.resolve(strict=True)
    _, commit, _ = SOURCE_PINS[provider]
    if not root.is_dir() or run_git(root, "rev-parse", "HEAD") != commit:
        raise ValueError("external source checkout HEAD mismatch")
    path = file["path"]
    expected = file["git_blob_sha1"]
    candidate = root / path
    if (candidate.is_symlink() or not candidate.is_file() or
            not candidate.resolve(strict=True).is_relative_to(root)):
        raise ValueError("missing, symlinked or out-of-tree matrix")
    if (run_git(root, "rev-parse", f"HEAD:{path}") != expected or
            run_git(root, "hash-object", str(candidate)) != expected):
        raise ValueError("external matrix source Git blob mismatch")
    data = candidate.read_bytes()
    if len(data) == 0 or len(data) > 60_000:
        raise ValueError("matrix input outside 60KB byte admission cap")
    return data


def decimal_token(token: str) -> int:
    if not re.fullmatch(r"(0|[1-9][0-9]*)", token):
        raise ValueError("noncanonical matrix integer")
    return int(token)


def dense01(data: bytes) -> tuple[int, int, list[tuple[int, int]]]:
    text = data.decode("ascii")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("dense source requires LF-terminated ASCII")
    rows = text.splitlines()
    if not rows or len(rows) > reference.MAX_CHECKS:
        raise ValueError("invalid dense matrix height")
    n = None
    edges = []
    for ci, line in enumerate(rows, 1):
        # The published Simula format is one blank-separated 0/1 token
        # per bit. Reject tabs, comments and malformed delimiters.
        values = line.split(" ")
        if not values or any(value not in ("0", "1") for value in values):
            raise ValueError("nonbinary or malformed dense row")
        if n is None:
            n = len(values)
        if len(values) != n:
            raise ValueError("ragged dense parity-check matrix")
        edges.extend((ci, vi) for vi, bit in enumerate(values, 1)
                     if bit == "1")
    reference.canonical_graph(n, len(rows), edges)
    return n, len(rows), edges


def matrix_market01(data: bytes) -> tuple[int, int, list[tuple[int, int]]]:
    text = data.decode("ascii")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("Matrix Market source requires LF-terminated ASCII")
    lines = text.splitlines()
    if not lines or lines[0] != "%%MatrixMarket matrix coordinate integer general":
        raise ValueError("unsupported Matrix Market header")
    remaining = [line for line in lines[1:] if not line.startswith("%")]
    if not remaining:
        raise ValueError("missing Matrix Market dimensions")
    dimensions = remaining[0].split(" ")
    if len(dimensions) != 3:
        raise ValueError("malformed Matrix Market dimensions")
    m, n, count = [decimal_token(value) for value in dimensions]
    if len(remaining) - 1 != count:
        raise ValueError("Matrix Market declared entry count mismatch")
    if not 1 <= n <= reference.MAX_VARIABLES or \
       not 1 <= m <= reference.MAX_CHECKS or \
       count > reference.MAX_EDGES:
        raise ValueError("Matrix Market matrix outside bounded native scale")
    edges = []
    seen = set()
    for line in remaining[1:]:
        triplet = line.split(" ")
        if len(triplet) != 3:
            raise ValueError("malformed Matrix Market triple")
        ci, vi, bit = map(decimal_token, triplet)
        if not 1 <= ci <= m or not 1 <= vi <= n or bit != 1:
            raise ValueError("out-of-range or nonbinary Matrix Market entry")
        if (ci, vi) in seen:
            raise ValueError("repeated Matrix Market check/variable coordinate")
        seen.add((ci, vi))
        edges.append((ci, vi))
    edges.sort()
    reference.canonical_graph(n, m, edges)
    return n, m, edges


def gf2_rank(m: int, edges: list[tuple[int, int]]) -> int:
    basis: dict[int, int] = {}
    rows = [0] * m
    for ci, vi in edges:
        rows[ci - 1] |= 1 << (vi - 1)
    for row in rows:
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row
                break
            row ^= basis[pivot]
    return len(basis)


def css_valid(mx: int, hx: list[tuple[int, int]],
              mz: int, hz: list[tuple[int, int]]) -> bool:
    xrows = [0] * mx
    zrows = [0] * mz
    for ci, vi in hx:
        xrows[ci - 1] |= 1 << (vi - 1)
    for ci, vi in hz:
        zrows[ci - 1] |= 1 << (vi - 1)
    return all(not ((a & b).bit_count() & 1)
               for a in xrows for b in zrows)


def admit(matrix: dict, donors: dict[str, Path]) -> tuple[dict, list[tuple[int, int]]]:
    p = matrix["provider"]
    blobs = {side: checked_matrix(donors[p], p, matrix[side])
             for side in ("Hx", "Hz")}
    reader = dense01 if matrix["format"] == "dense01" else matrix_market01
    nx, mx, hx = reader(blobs["Hx"])
    nz, mz, hz = reader(blobs["Hz"])
    if nx != nz:
        raise ValueError("external CSS H_X and H_Z have differing data widths")
    if not css_valid(mx, hx, mz, hz):
        raise ValueError("external CSS orthogonality failed independent GF(2)")
    record = {
        "id": matrix["id"], "provider": p, "n": nx, "m_x": mx, "m_z": mz,
        "x_edges": len(hx), "z_edges": len(hz),
        "x_rank_gf2": gf2_rank(mx, hx),
        "z_rank_gf2": gf2_rank(mz, hz),
        "css_orthogonal": True,
        "hx_source_git_sha1": matrix["Hx"]["git_blob_sha1"],
        "hz_source_git_sha1": matrix["Hz"]["git_blob_sha1"],
        "hx_source_sha256": sha(blobs["Hx"]),
        "hz_source_sha256": sha(blobs["Hz"]),
        "hz_tanner_sha256": sha(reference.canonical_graph(nx, mz, hz)),
        "split": "heldout" if p == "explicit" else "train",
    }
    return record, hz


def bootstrap(records: list[dict], trials: list[dict], noise: int,
              seed: str, draws: int) -> dict:
    held = [record for record in records if record["split"] == "heldout"]
    indexed = {}
    for rec in held:
        gid = rec["id"]
        errors = [trial["bp"]["frame_failure"] for trial in trials
                  if trial["code_id"] == gid and trial["noise_bps"] == noise]
        if len(errors) != 4:
            raise ValueError("missing heldout BP trial cluster")
        indexed[gid] = {
            "trial_outcomes": errors, "ipr": rec["spectral"]["ipr"],
            "edge_density": rec["spectral"]["edge_density"]
        }
    ids = list(indexed)
    a, b, diff = [], [], []
    undefined = 0
    for k in range(draws):
        choice = [ids[blocked.draw_cluster(
            seed, noise, k, position, len(ids)
        )] for position in range(len(ids))]
        ipr = reference.auroc(blocked.expand(choice, indexed, "ipr"))
        density = reference.auroc(blocked.expand(
            choice, indexed, "edge_density"))
        if ipr is None or density is None:
            undefined += 1
        else:
            a.append(ipr)
            b.append(density)
            diff.append(ipr - density)
    return {
        "resamples": draws, "defined": len(a), "undefined": undefined,
        "ipr_percentiles_conditional_95": blocked.intervals(a),
        "edge_density_percentiles_conditional_95": blocked.intervals(b),
        "ipr_minus_density_percentiles_conditional_95":
            blocked.intervals(diff),
    }


def evaluate(records: list[dict], trials: list[dict], qec_cases: list[dict],
             study: dict, seed: str) -> dict:
    reports = {}
    for noise in study["noise_bps"]:
        grouped = {
            part: [trial for trial in trials
                   if trial["noise_bps"] == noise and
                   records[trial["code_index"]]["split"] == part]
            for part in ("train", "heldout")
        }
        report = {
            "train_topologies": sum(r["split"] == "train" for r in records),
            "heldout_topologies": sum(r["split"] == "heldout" for r in records),
            "train_trials": len(grouped["train"]),
            "heldout_trials": len(grouped["heldout"]),
            "train_failures": sum(r["bp"]["frame_failure"] for r in grouped["train"]),
            "heldout_failures": sum(r["bp"]["frame_failure"] for r in grouped["heldout"]),
            "features": {},
            "graph_blocked": bootstrap(
                records, trials, noise, seed, study["bootstraps"]),
        }
        for name in FEATURES:
            data = {}
            for part in ("train", "heldout"):
                pairs = [(records[row["code_index"]]["spectral"][name],
                          row["bp"]["frame_failure"])
                         for row in grouped[part]]
                data[part + "_auroc"] = reference.auroc(pairs)
                data[part + "_average_precision"] = reference.average_precision(pairs)
            report["features"][name] = data
        cases = [x for x in qec_cases if x["noise_bps"] == noise]
        report["qec_compared"] = len(cases)
        report["qec_failure_label_agreement"] = sum(
            x["failure_labels_agree"] for x in cases)
        reports[str(noise)] = report
    primary = reports[str(study["primary_noise_bps"])]["features"]
    ipr = primary["ipr"]["heldout_auroc"]
    density = primary["edge_density"]["heldout_auroc"]
    if ipr is None or density is None:
        verdict = "NOT_EVALUABLE"
    elif ipr >= study["auroc_threshold"] and \
            ipr - density >= study["auroc_uplift_vs_density"]:
        verdict = "EXPLORATORY_ONLY_NOT_GENERALIZATION"
    else:
        verdict = "NO_PRE_REGISTERED_ADVANTAGE_DETECTED"
    return {
        "primary": {
            "noise_bps": study["primary_noise_bps"],
            "risk_feature": "ipr",
            "baseline": "edge_density",
            "prespecified_higher_is_risk": True,
            "score_threshold": study["auroc_threshold"],
            "minimum_delta": study["auroc_uplift_vs_density"],
            "heldout_source": study["heldout_provider"],
            "verdict": verdict
        },
        "per_noise": reports,
        "claim_boundary": "publisher-blocked_observational_classical_x_error_only"
    }


def make(donors: dict[str, Path], qec_donor: Path) -> dict:
    spec = manifest()
    # The only executed donor is QEC's explicit reference BP module.
    bp_decode, np, source_sha256 = qec.load_reference(qec_donor)
    source_checkouts = {
        name: {"repo": info["repo"], "commit": info["commit"],
               "license": info["license"]}
        for name, info in spec["sources"].items()
    }
    records = []
    graph_support = []
    sources_seen = set()
    with tempfile.TemporaryDirectory(prefix="qecada-phase1h-") as td:
        outfile = Path(td) / "tanner.txt"
        for row in spec["matrix_pairs"]:
            record, edges = admit(row, donors)
            if record["hz_tanner_sha256"] in sources_seen:
                raise ValueError("duplicate Tanner topology across source corpus")
            sources_seen.add(record["hz_tanner_sha256"])
            record["spectral"] = phase1e.graph_features(
                record["n"], record["m_z"], edges, outfile
            )
            records.append(record)
            graph_support.append(edges)
    if len(records) != len(ORDER):
        raise ValueError("external CSS source coverage missing")
    studied = spec["evaluation"]
    trials = []
    for i, record in enumerate(records):
        for noise in studied["noise_bps"]:
            for count in range(studied["trial_count_per_graph_and_noise"]):
                flipped = reference.deterministic_noise(
                    studied["noise_seed"], i, noise, count, record["n"]
                )
                result = reference.decode_min_sum(
                    record["n"], record["m_z"], graph_support[i],
                    flipped, studied["max_bp_iterations"]
                )
                trials.append({
                    "code_index": i, "code_id": record["id"],
                    "noise_bps": noise, "trial": count,
                    "error_sites": sorted(flipped), "bp": result
                })
    qec_cases = []
    for trial in trials:
        i = trial["code_index"]
        if trial["noise_bps"] != studied["primary_noise_bps"] or \
                trial["trial"] >= studied["qec_reference_primary_trials_per_graph"]:
            continue
        rec = records[i]
        row = {
            "graph_id": i, "noise_bps": trial["noise_bps"],
            "trial": trial["trial"], "flipped_sites": trial["error_sites"],
            "bp": trial["bp"]
        }
        graph = {
            "edges": graph_support[i], "variables": rec["n"],
            "checks": rec["m_z"]
        }
        result = qec.run_case(
            bp_decode, np, graph, row, studied["max_bp_iterations"])
        # The QEC comparison helper calls its input field "phase1e", but
        # these outcomes are from Phase 1H trials using the old algorithm.
        result["reference_label_origin"] = "phase1h_integer_min_sum"
        qec_cases.append(result)
    source_seed = sha(canonical([
        (r["id"], r["hz_tanner_sha256"]) for r in records
    ]))
    evaluation = evaluate(records, trials, qec_cases, studied, source_seed)
    unsigned = {
        "schema": SCHEMA,
        "manifest_sha256": sha(MANIFEST.read_bytes()),
        "sources": source_checkouts,
        "source_manifest": [
            {"id": row["id"], "provider": row["provider"],
             "format": row["format"],
             "Hx": row["Hx"], "Hz": row["Hz"]}
            for row in spec["matrix_pairs"]
        ],
        "external_css_admission": records,
        "trial_results": trials,
        "matched_qec_bp": qec_cases,
        "qec_bp_reference": {
            "repo": "QSOLKCB/QEC",
            "commit": qec.DONOR_COMMIT,
            "blob": qec.SOURCE_BLOB,
            "source_sha256": source_sha256,
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__
        },
        "study": studied,
        "evaluation": evaluation,
        "claim_boundary": BOUNDARY
    }
    return {**unsigned, "sha256": sha(canonical(unsigned))}


def verify(raw: bytes, donors: dict[str, Path], qec_donor: Path) -> dict:
    if len(raw) > 8_000_000:
        raise ValueError("external CSS research receipt exceeds size limit")
    rec = json.loads(raw.decode("utf-8"),
                     object_pairs_hook=phase1e.unique_pairs)
    if type(rec) is not dict or set(rec) != {
        "schema", "manifest_sha256", "sources", "source_manifest",
        "external_css_admission", "trial_results", "matched_qec_bp",
        "qec_bp_reference", "study", "evaluation", "claim_boundary", "sha256"
    } or rec["schema"] != SCHEMA:
        raise ValueError("external CSS receipt membership/format mismatch")
    if canonical(rec) + b"\n" != raw:
        raise ValueError("noncanonical external CSS receipt")
    if rec["sha256"] != sha(canonical({
        k: v for k, v in rec.items() if k != "sha256"
    })):
        raise ValueError("external CSS receipt SHA-256 mismatch")
    expected = make(donors, qec_donor)
    if canonical(expected) != canonical(rec):
        raise ValueError("external matrix source/native spectrum/BP replay mismatch")
    return rec


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for cmd in ("create", "verify"):
        s = sub.add_parser(cmd)
        s.add_argument("output" if cmd == "create" else "input", type=Path)
        s.add_argument("--simula", type=Path, required=True)
        s.add_argument("--explicit", type=Path, required=True)
        s.add_argument("--qec", type=Path, required=True)
        s.add_argument("--execute-pinned-qec", action="store_true")
    args = p.parse_args()
    try:
        if not args.execute_pinned_qec:
            raise ValueError("explicit --execute-pinned-qec is required")
        donors = {"simula": args.simula, "explicit": args.explicit}
        if args.action == "create":
            result = make(donors, args.qec)
            with args.output.open("xb") as file:
                file.write(canonical(result) + b"\n")
            print("PASS Phase 1H externally sourced CSS admission")
            print("source_publishers=" + str(len(result["sources"])))
            print("unique_topologies=" + str(len(result["external_css_admission"])))
            print("controlled_bp_trials=" + str(len(result["trial_results"])))
            print("pinned_qec_bp_comparisons=" + str(len(result["matched_qec_bp"])))
            for n, data in result["evaluation"]["per_noise"].items():
                print("noise_bps=" + n + " heldout_failures=" +
                      str(data["heldout_failures"]) + "/" +
                      str(data["heldout_trials"]) + " ipr_auroc=" +
                      str(data["features"]["ipr"]["heldout_auroc"]) +
                      " density_auroc=" +
                      str(data["features"]["edge_density"]["heldout_auroc"]) +
                      " qec_agreement=" +
                      str(data["qec_failure_label_agreement"]) +
                      "/" + str(data["qec_compared"]))
            print("verdict=" + result["evaluation"]["primary"]["verdict"])
            print("receipt_sha256=" + result["sha256"])
        else:
            if args.input.is_symlink() or not args.input.is_file():
                raise ValueError("source receipt must be a non-symlink file")
            result = verify(args.input.read_bytes(), donors, args.qec)
            print("PASS pinned external CSS source/native/BP complete rerun " +
                  result["sha256"])
        return 0
    except (OSError, ValueError, TypeError, UnicodeError,
            ArithmeticError, subprocess.SubprocessError, ImportError) as exc:
        print("FAIL Phase 1H: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
