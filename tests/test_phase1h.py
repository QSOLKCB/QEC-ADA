# SPDX-License-Identifier: MPL-2.0
"""Phase 1H: external matrix parsing, provenance and publisher split gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1h_external_css as study

ARTIFACT = ROOT / "evidence/phase1h/external_css.json"
SIMULA = ROOT / ".donor-nisqec"
EXPLICIT = ROOT / ".donor-explicit-qldpc"
QEC = ROOT / ".donor-qec-bp"


class PureImportTests(unittest.TestCase):
    def test_dense_matrix_parses_exact_support(self):
        n, m, edges = study.dense01(b"1 0 1 0\n0 1 0 1\n")
        self.assertEqual((n, m), (4, 2))
        self.assertEqual([(1, 1), (1, 3), (2, 2), (2, 4)], edges)
        for bad in (
            b"1 0\n0\n", b"1 0\n0 2\n", b"1\t0\n0 1\n",
            b"1 0\n0 1", b"1 0\r\n0 1\r\n",
            b"1 0\n\n0 1\n", b"1  0\n0 1\n"
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                study.dense01(bad)

    def test_matrix_market_coo_coordinates_and_bounds(self):
        data = (b"%%MatrixMarket matrix coordinate integer general\n"
                b"% Field: GF(2)\n%\n2 4 4\n1 4 1\n2 2 1\n"
                b"1 1 1\n2 3 1\n")
        n, m, edges = study.matrix_market01(data)
        self.assertEqual((n, m), (4, 2))
        self.assertEqual([(1, 1), (1, 4), (2, 2), (2, 3)], edges)
        for bad in (
            data.replace(b"2 4 4", b"2 4 5"),
            data.replace(b"2 4 4", b"2 4 04"),
            data.replace(b"1 4 1", b"1 1 1"),
            data.replace(b"2 2 1", b"2 2 0"),
            data.replace(b"2 2 1", b"2 5 1"),
            data.replace(b"% Field: GF(2)", b"2 2 1"),
            data.replace(b"integer general", b"real general"),
        ):
            with self.subTest(bad=bad[:60]), self.assertRaises(ValueError):
                study.matrix_market01(bad)

    def test_exact_css_commutation_and_gf2_rank(self):
        self.assertTrue(study.css_valid(
            2, [(1,1),(1,2),(2,3),(2,4)],
            2, [(1,1),(1,2),(2,3),(2,4)]))
        self.assertFalse(study.css_valid(
            1, [(1,1)], 1, [(1,1)]))
        self.assertEqual(2, study.gf2_rank(3, [
            (1,1),(1,2),(2,1),(2,3),(3,2),(3,3)
        ]))
        self.assertEqual(0, study.gf2_rank(2, []))

    def test_preregistered_sources_are_pinned_and_unlicensed_not_copied(self):
        m = study.manifest()
        self.assertEqual(study.MANIFEST_SCHEMA, m["schema"])
        self.assertEqual(list(study.ORDER),
                         [x["id"] for x in m["matrix_pairs"]])
        self.assertEqual("UNSPECIFIED", m["sources"]["explicit"]["license"])
        self.assertFalse(m["sources"]["explicit"]["redistribute_raw"])
        self.assertEqual("CC-BY-4.0", m["sources"]["simula"]["license"])
        self.assertEqual("explicit", m["evaluation"]["heldout_provider"])
        self.assertTrue(m["evaluation"]["no_fitting_on_heldout"])
        self.assertEqual(800, m["evaluation"]["primary_noise_bps"])

    def test_single_outcome_cluster_is_never_promoted(self):
        records = [
            {"id": "a", "split": "heldout",
             "spectral": {"ipr":0.2,"edge_density":0.5}},
            {"id": "b", "split": "heldout",
             "spectral": {"ipr":0.8,"edge_density":0.7}}
        ]
        trials = [
            {"code_id": rec["id"], "noise_bps": 800,
             "bp": {"frame_failure": True}}
            for rec in records for _ in range(4)
        ]
        result = study.bootstrap(records, trials, 800, "test", 32)
        self.assertEqual(32, result["undefined"])
        self.assertEqual(0, result["defined"])
        self.assertIsNone(result["ipr_percentiles_conditional_95"])

    def test_opt_in_gate_prevents_implicit_qec_code_execution(self):
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts/phase1h_external_css.py"),
            "create", "/tmp/phase1h-never-writes.json",
            "--simula", ".", "--explicit", ".", "--qec", "."
        ], text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit --execute-pinned-qec", result.stderr)


@unittest.skipUnless(ARTIFACT.is_file() and SIMULA.is_dir() and
                     EXPLICIT.is_dir() and QEC.is_dir(),
                     "Phase 1H pinned donor CI lane not active")
class PinnedExternalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ARTIFACT.read_bytes()
        cls.data = json.loads(cls.raw)

    def test_complete_source_identity_and_publisher_holdout(self):
        evidence = self.data
        self.assertEqual(study.SCHEMA, evidence["schema"])
        self.assertEqual(2, len(evidence["sources"]))
        self.assertEqual(9, len(evidence["external_css_admission"]))
        self.assertEqual(108, len(evidence["trial_results"]))
        self.assertEqual(18, len(evidence["matched_qec_bp"]))
        self.assertEqual(7, sum(
            g["split"] == "heldout"
            for g in evidence["external_css_admission"]))
        hashes = [g["hz_tanner_sha256"] for g
                  in evidence["external_css_admission"]]
        self.assertEqual(len(hashes), len(set(hashes)))
        for record in evidence["external_css_admission"]:
            self.assertTrue(record["css_orthogonal"])
            self.assertLessEqual(record["n"], 128)
            self.assertLessEqual(record["m_z"], 128)
            self.assertLessEqual(record["z_edges"], 2048)
            self.assertIn(record["split"], ("train", "heldout"))
        self.assertFalse(evidence["claim_boundary"]["raw_external_matrices_redistributed"])
        self.assertFalse(evidence["claim_boundary"]["ipr_generalization_validated"])

    def test_recomputed_exploratory_scores_and_qec_label_origin(self):
        data = self.data
        self.assertEqual("explicit",
                         data["evaluation"]["primary"]["heldout_source"])
        for noise in ("400","800","1200"):
            report = data["evaluation"]["per_noise"][noise]
            self.assertEqual(28, report["heldout_trials"])
            self.assertEqual(8, report["train_trials"])
            block = report["graph_blocked"]
            self.assertEqual(256, block["defined"] + block["undefined"])
        self.assertTrue(all(case["reference_label_origin"] ==
                            "phase1h_integer_min_sum" for case
                            in data["matched_qec_bp"]))
        self.assertTrue(all(
            case["failure_labels_agree"] ==
            (case["qec_frame_failure"] == case["phase1e_frame_failure"])
            for case in data["matched_qec_bp"]))

    def test_actual_source_refetched_and_full_replay(self):
        self.assertEqual(self.data, study.verify(
            self.raw, {"simula": SIMULA, "explicit": EXPLICIT}, QEC))

    def test_self_consistent_rehash_does_not_admit_forgery(self):
        tampered = copy.deepcopy(self.data)
        tampered["evaluation"]["primary"]["verdict"] = "IPR_PROVED"
        unsigned = {key: value for key, value in tampered.items()
                    if key != "sha256"}
        tampered["sha256"] = study.sha(study.canonical(unsigned))
        with self.assertRaisesRegex(ValueError, "complete rerun|replay mismatch"):
            study.verify(study.canonical(tampered) + b"\n",
                         {"simula": SIMULA, "explicit": EXPLICIT}, QEC)


if __name__ == "__main__":
    unittest.main()
