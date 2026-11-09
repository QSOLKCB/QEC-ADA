# SPDX-License-Identifier: MPL-2.0
"""Phase 1E: independent geometry, classical min-sum BP and leakage gates."""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1e_reference as ref
import phase1e_experiment as pilot

BIN = ROOT / "build/bin" / ("qec_scale.exe" if os.name == "nt" else "qec_scale")


class ExactReferenceTests(unittest.TestCase):
    def test_analytic_spectral_radius(self):
        for m, n in ((2, 2), (2, 3), (4, 5), (8, 8)):
            edges = [(c, v) for c in range(1, m+1)
                     for v in range(1, n+1)]
            r = ref.reference_spectrum(n, m, edges)
            self.assertEqual("CONVERGED_NUMERIC", r["status"])
            self.assertAlmostEqual(math.sqrt((m-1)*(n-1)),
                                   r["spectral_radius"], delta=1e-8)

    def test_cycle_tie_and_acyclic(self):
        edges = [(c,v) for c in range(1, 3) for v in range(1, 3)]
        r = ref.reference_spectrum(2, 2, edges)
        self.assertEqual(2, r["ties"])
        self.assertEqual(1, r["root"])
        self.assertAlmostEqual(1/4, r["ipr"], places=10)
        self.assertEqual("NO_EDGES", ref.reference_spectrum(2, 2, [])["status"])
        self.assertEqual("ACYCLIC", ref.reference_spectrum(
            2, 1, [(1,1),(1,2)])["status"])

    def test_graph_generation_noise_and_identity(self):
        for gid in range(12):
            edges = ref.generated_graph(gid, 24, 16, "phase1e-test-001")
            self.assertEqual(edges, ref.generated_graph(
                gid, 24, 16, "phase1e-test-001"))
            raw = ref.canonical_graph(24, 16, edges)
            self.assertTrue(raw.startswith(b"QECADA-TANNER-EDGES-V1\n"))
            self.assertLess(len(edges), ref.MAX_EDGES)
            self.assertTrue(all(1<=c<=16 and 1<=v<=24 for c,v in edges))
            self.assertEqual(
                ref.deterministic_noise("phase1e-test-001", gid, 800, 0, 24),
                ref.deterministic_noise("phase1e-test-001", gid, 800, 0, 24),
            )

    def test_gf2_min_sum_actual_correction(self):
        # [3,1,3] classical repetition code checks b1+b2=0, b2+b3=0.
        edges = [(1,1),(1,2),(2,2),(2,3)]
        clean = ref.decode_min_sum(3, 2, edges, frozenset())
        self.assertFalse(clean["frame_failure"])
        self.assertEqual(0, clean["iterations"])
        single = ref.decode_min_sum(3, 2, edges, frozenset({1}))
        self.assertFalse(single["frame_failure"])
        self.assertTrue(single["checks_satisfied"])
        self.assertEqual(1, single["error_weight"])
        self.assertGreaterEqual(single["iterations"], 1)
        self.assertEqual(0, single["final_error_weight"])
        self.assertEqual(0, single["trace"][-1]["syndrome_weight"])

    def test_tied_auc_and_ap(self):
        pairs = [(0.1, False), (0.2, True),
                 (0.3, False), (0.4, True)]
        self.assertAlmostEqual(0.75, ref.auroc(pairs))
        self.assertAlmostEqual(5/6, ref.average_precision(pairs))
        self.assertEqual(0.4, ref.fit_threshold(pairs))
        equal = [(0.5, True), (0.5, False)]
        self.assertEqual(0.5, ref.auroc(equal))
        self.assertEqual(0.5, ref.average_precision(equal))
        self.assertIsNone(ref.auroc([(0.5, True)]))
        self.assertIsNone(ref.average_precision([(0.5, False)]))
        self.assertIsNone(ref.average_precision([(0.5, True)]))
        self.assertIsNone(ref.average_precision([(0.1, True), (0.9, True)]))
        self.assertIsNone(ref.average_precision([(0.1, False), (0.9, False)]))
        self.assertIsNone(ref.average_precision([]))
        self.assertIsNone(ref.auroc([(0.1, True), (0.9, True)]))
        self.assertIsNone(ref.auroc([(0.1, False), (0.9, False)]))

    def test_one_class_heldout_ap_is_null_in_full_report(self):
        # Two distinct held-out graphs (IDs 0 and 5) have only positive
        # outcomes; training graphs retain both classes.
        graphs = [{"spectral": {
            name: (i + 1) / 10.0
            for name in pilot.PREDICTORS
        }} for i in range(10)]
        records = [{
            "graph_id": i, "noise_bps": 5000,
            "bp": {"frame_failure": i % 5 == 0 or i % 2 == 0},
        } for i in range(10)]
        config = {"noise_bps": [5000], "primary_noise_bps": 5000}
        report = pilot.scores_report(records, graphs, config)
        self.assertEqual("NOT_EVALUABLE", report["primary"]["verdict"])
        held = report["per_noise"]["5000"]["features"]
        for name in pilot.PREDICTORS:
            self.assertIsNone(held[name]["heldout_auroc"])
            self.assertIsNone(held[name]["heldout_average_precision"])
        self.assertIsNotNone(held["ipr"]["train_auroc"])

    def test_config_and_source_fail_closed(self):
        cfg = {
            "graphs": 10, "trials": 2, "variables": 20, "checks": 12,
            "noise_bps": [400,800,1200], "seed": "abc-123",
            "primary_noise_bps": 800, "max_iterations": 12,
        }
        pilot.validate_config(cfg)
        for change in (
            {"graphs": 9}, {"trials": 0}, {"variables": 200},
            {"noise_bps": [1200,800]}, {"seed": "a bad seed"},
            {"primary_noise_bps": 600}, {"max_iterations": 300},
        ):
            bad = {**cfg, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                pilot.validate_config(bad)
        with self.assertRaises(ValueError):
            ref.canonical_graph(2, 2, [(1,1),(1,1)])
        with self.assertRaises(ValueError):
            ref.generated_graph(0, 8, 4, "seed")


@unittest.skipUnless(BIN.is_file(), "native qec_scale not built")
class ReproducibleExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = {
            "graphs": 10, "trials": 2, "variables": 20, "checks": 12,
            "noise_bps": [400,800,1200], "seed": "qecada-phase1e-001",
            "primary_noise_bps": 800, "max_iterations": 10,
        }
        cls.artifact = pilot.generate(cls.config)

    def test_graph_blocked_holdout_and_offline_replay(self):
        a = self.artifact
        self.assertEqual(10, len(a["graphs"]))
        self.assertEqual(60, len(a["trials"]))
        heldout = {g["id"] for g in a["graphs"] if g["split"] == "heldout"}
        self.assertEqual({0,5}, heldout)
        for noise in self.config["noise_bps"]:
            report = a["analysis"]["per_noise"][str(noise)]
            self.assertEqual(2, report["heldout_graphs"])
            self.assertEqual(8, report["train_graphs"])
            self.assertEqual(4, report["heldout_trials"])
            self.assertEqual(16, report["train_trials"])
        raw = pilot.canonical(a) + b"\n"
        from unittest.mock import patch
        with patch.object(pilot, "SCALE", ROOT / "binary-not-present"):
            self.assertEqual(a, pilot.verify_bytes(raw))

    def test_supported_all_failure_holdout_has_null_ap(self):
        # Reproduce the reported P2 case through the actual supported
        # graph/noise/BP pipeline; do not use synthetic result labels.
        config = {
            "graphs": 10, "trials": 2, "variables": 128, "checks": 8,
            "seed": "abc-123", "noise_bps": [5000],
            "primary_noise_bps": 5000, "max_iterations": 2,
        }
        artifact = pilot.generate(config)
        held = artifact["analysis"]["per_noise"]["5000"]
        self.assertEqual(4, held["heldout_trials"])
        self.assertEqual(4, held["heldout_failures"])
        for name in pilot.PREDICTORS:
            self.assertIsNone(held["features"][name]["heldout_auroc"])
            self.assertIsNone(
                held["features"][name]["heldout_average_precision"])
        self.assertEqual("NOT_EVALUABLE",
                         artifact["analysis"]["primary"]["verdict"])
        self.assertEqual(
            artifact,
            pilot.verify_bytes(pilot.canonical(artifact) + b"\n"),
        )

    def test_byte_identical_repeated_experiment(self):
        self.assertEqual(pilot.canonical(self.artifact),
                         pilot.canonical(pilot.generate(self.config)))

    def test_rehashed_trace_forgery_rejected(self):
        forged = copy.deepcopy(self.artifact)
        forged["trials"][0]["bp"]["trace"][0]["syndrome_weight"] += 1
        forged["sha256"] = pilot.sha(pilot.canonical(
            {k:v for k,v in forged.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "BP replay failed"):
            pilot.verify_bytes(pilot.canonical(forged) + b"\n")

    def test_rehashed_holdout_metric_forgery_rejected(self):
        forged = copy.deepcopy(self.artifact)
        forged["analysis"]["primary"]["verdict"] = "CAUSAL_PREDICTOR_PROVED"
        forged["sha256"] = pilot.sha(pilot.canonical(
            {k:v for k,v in forged.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "predictive evaluation was altered"):
            pilot.verify_bytes(pilot.canonical(forged) + b"\n")

    def test_rehashed_source_graph_and_split_manipulation_rejected(self):
        forged = copy.deepcopy(self.artifact)
        forged["graphs"][0]["split"] = "train"
        forged["sha256"] = pilot.sha(pilot.canonical(
            {k:v for k,v in forged.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "graph identity or split"):
            pilot.verify_bytes(pilot.canonical(forged) + b"\n")


if __name__ == "__main__":
    unittest.main()
