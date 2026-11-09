# SPDX-License-Identifier: MPL-2.0
"""Phase 1F: topology-blocked inference, undefined draws and replay tests."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1e_experiment as phase1e
import phase1f_blocked_inference as phase1f

NATIVE = ROOT / "build/bin" / ("qec_scale.exe" if os.name == "nt" else "qec_scale")


class ClusterInferencePrimitives(unittest.TestCase):
    def test_undivided_whole_graph_draws(self):
        groups = {
            0: {"ipr": 0.1, "edge_density": 0.2,
                "trial_outcomes": [False, True, False]},
            5: {"ipr": 0.9, "edge_density": 0.8,
                "trial_outcomes": [True, True, True]},
        }
        pairs = phase1f.expand([5, 0, 5], groups, "ipr")
        self.assertEqual(9, len(pairs))
        self.assertEqual([True, True, True, False, True, False, True, True, True],
                         [y for _, y in pairs])
        self.assertTrue(all(x == 0.9 for x, _ in pairs[:3]))

    def test_one_class_cluster_draws_are_undefined(self):
        groups = {
            0: {"ipr": 0.1, "edge_density": 0.2,
                "trial_outcomes": [False, False]},
            5: {"ipr": 0.9, "edge_density": 0.8,
                "trial_outcomes": [True, True]},
        }
        from phase1e_reference import auroc
        self.assertIsNone(auroc(phase1f.expand([0, 0], groups, "ipr")))
        self.assertIsNone(auroc(phase1f.expand([5, 5], groups, "ipr")))
        self.assertAlmostEqual(1.0, auroc(
            phase1f.expand([0, 5], groups, "ipr")))
        self.assertEqual(phase1f.draw_cluster(
            "1234", 800, 8, 1, 2), phase1f.draw_cluster(
            "1234", 800, 8, 1, 2))

    def test_quantile_algorithm_and_missing_values(self):
        self.assertEqual([0.075, 2.925], phase1f.intervals([0, 1, 2, 3]))
        self.assertIsNone(phase1f.intervals([]))
        with self.assertRaises(ValueError):
            phase1f.draw_cluster("x", 800, 0, 0, 0)
        for value in (15, 4097, True, 8.2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                phase1f.make(b"{}", value)

    def test_exact_graph_permutation_margins(self):
        groups = {
            n: {"ipr": score, "edge_density": 1-score,
                "trial_outcomes": [failure, failure]}
            for n, (score, failure) in enumerate((
                (0.1, False), (0.3, False),
                (0.5, True), (0.7, True)
            ))
        }
        p = phase1f.exact_permutation_p(groups, "ipr")
        self.assertIsNotNone(p)
        self.assertTrue(0 < p <= 1)
        self.assertEqual(p, phase1f.exact_permutation_p(groups, "ipr"))


@unittest.skipUnless(NATIVE.is_file(), "compiled native qec_scale required")
class EvidenceReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = {
            "graphs": 10, "trials": 2, "variables": 20, "checks": 12,
            "noise_bps": [400, 800], "seed": "phase1f-ci-smoke",
            "primary_noise_bps": 800, "max_iterations": 10,
        }
        cls.parent = phase1e.canonical(phase1e.generate(config)) + b"\n"
        cls.child = phase1f.make(cls.parent, 64)

    def test_replay_without_native_executable(self):
        raw = phase1f.canonical(self.child) + b"\n"
        from unittest.mock import patch
        with patch.object(phase1e, "SCALE", ROOT / "missing-native-binary"):
            self.assertEqual(self.child, phase1f.verify(self.parent, raw))
        self.assertEqual(self.child, phase1f.make(self.parent, 64))

    def test_holdout_unit_and_all_replicates_accounted_for(self):
        for rate in ("400", "800"):
            r = self.child["inference"]["per_noise"][rate]
            self.assertEqual([0, 5], r["heldout_graph_ids"])
            self.assertEqual(2, r["heldout_graph_count"])
            self.assertEqual(64, r["conditional_valid_bootstrap_replicates"] +
                             r["undefined_bootstrap_replicates"])

    def test_mutated_resample_interval_rehashed_still_fails(self):
        forged = copy.deepcopy(self.child)
        values = forged["inference"]["per_noise"]["800"]
        values["observed_ipr_minus_density"] = 13.0
        unsigned = {k: v for k, v in forged.items() if k != "sha256"}
        forged["sha256"] = phase1f.digest(phase1f.canonical(unsigned))
        with self.assertRaisesRegex(ValueError, "inference replay mismatch"):
            phase1f.verify(self.parent, phase1f.canonical(forged) + b"\n")

    def test_parent_mutation_or_noncanonical_form_is_rejected(self):
        raw = phase1f.canonical(self.child) + b"\n"
        with self.assertRaises(ValueError):
            phase1f.verify(self.parent, raw[:-1])
        forged_parent = self.parent.replace(b"phase1f-ci-smoke",
                                            b"phase1f-ci-spoof")
        with self.assertRaises(ValueError):
            phase1f.verify(forged_parent, raw)


if __name__ == "__main__":
    unittest.main()
