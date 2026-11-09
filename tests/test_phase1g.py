# SPDX-License-Identifier: MPL-2.0
"""Phase 1G: pinned CSS topology, family leakage and actual QEC BP gates."""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1g_pinned_css as css

DONOR = ROOT / ".donor-qec-bp"
RECEIPT = ROOT / "evidence/phase1g/qec_css.json"


class PureAdmissionTests(unittest.TestCase):
    def test_exact_gf2_row_rank_independent_of_float(self):
        self.assertEqual(0, css.rank_gf2([0, 0]))
        self.assertEqual(2, css.rank_gf2([0b101, 0b011]))
        self.assertEqual(2, css.rank_gf2([0b101, 0b011, 0b110]))
        self.assertEqual(1, css.rank_gf2([0b101, 0b101]))
        self.assertTrue(css.css_orthogonal([0b011], [0b011]))
        self.assertFalse(css.css_orthogonal([0b001], [0b001]))

    def test_preregistered_family_holdout_not_overwritten(self):
        self.assertEqual(("rate_0.50", "rate_0.60", "rate_0.75"),
                         css.ORDER)
        self.assertEqual((17, 29, 41, 53), css.SEEDS)
        self.assertEqual((400, 800, 1200), css.NOISE_BPS)
        self.assertEqual(css.BOOTSTRAPS, 256)
        self.assertEqual(css.PRIMARY_NOISE_BPS, 800)
        self.assertEqual(
            "ee0dc4ea5868386b3e60bbdef20c9d5c2c8e4b43e5ae160847f0bb5069a69738",
            css.BASELINE_SHA
        )

    def test_provenance_failure_before_source_execution(self):
        from phase1f_qec_bp_bridge import checked_source
        with self.assertRaises((ValueError, OSError, subprocess.CalledProcessError)):
            checked_source(ROOT)

    def test_explicit_execution_optin_fails_first(self):
        p = subprocess.run([
            sys.executable, str(ROOT / "scripts/phase1g_pinned_css.py"),
            "create", "/tmp/phase1g-not-created.json",
            "--donor", str(ROOT),
        ], text=True, capture_output=True, timeout=12)
        self.assertNotEqual(0, p.returncode)
        self.assertIn("explicit --execute-pinned-donor required", p.stderr)

    def test_css_graph_replay_class_guard(self):
        # Deliberately all failures: AP and AUROC must be undefined.
        topologies = [{
            "id": index,
            "split": "heldout" if index >= 8 else "train",
            "spectrum": {"ipr": index / 10, "spectral_radius": 0.0,
                         "eeec": 0.0, "edge_density": index / 20}
        } for index in range(16)]
        trials = [{
            "code_id": index, "noise_bps": rate, "trial": t,
            "bp": {"frame_failure": True}
        } for index in range(16) for rate in css.NOISE_BPS
            for t in range(css.TRIALS)]
        for noise in css.NOISE_BPS:
            self.assertIsNone(css.code_level_ranks(
                topologies, trials, noise, "ipr"))
            blocked = css.graph_bootstrap(
                topologies, trials, noise, "fixed-source")
            self.assertEqual(256, blocked["undefined_one_class_replicates"])
            self.assertEqual(0, blocked["defined_replicates"])
            self.assertIsNone(blocked["conditional_percentile_95_ipr"])

    def test_css_orthogonality_detects_true_noncommutation(self):
        self.assertTrue(css.css_orthogonal([0b1111], [0b1111]))
        self.assertFalse(css.css_orthogonal([0b1110], [0b1000]))
        self.assertTrue(css.css_orthogonal([0b1100, 0b0011],
                                          [0b0011, 0b1100]))


@unittest.skipUnless(DONOR.is_dir() and RECEIPT.is_file(),
                     "explicit pinned QEC BP CI reference lane")
class ExecutedPinnedCSSStudies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = RECEIPT.read_bytes()
        import json
        cls.item = json.loads(cls.raw)

    def test_css_source_identity_and_all_family_blocks(self):
        item = self.item
        self.assertEqual(css.SCHEMA, item["schema"])
        self.assertEqual(css.BASELINE_SHA, item["baseline_phase1e_sha256"])
        self.assertEqual(css.qec.DONOR_COMMIT, item["generator"]["commit"])
        self.assertEqual(css.qec.SOURCE_BLOB, item["generator"]["git_blob_sha1"])
        self.assertEqual(24, len(item["topologies"]))
        self.assertEqual(24 * 3 * css.TRIALS, len(item["bp_trials"]))
        self.assertEqual(8 * 3 * css.QEC_TRIALS, len(item["qec_reference_records"]))
        self.assertEqual(8, sum(c["split"] == "heldout"
                                for c in item["topologies"]))
        self.assertTrue(all(c["family"] == "rate_0.75"
                            for c in item["topologies"]
                            if c["split"] == "heldout"))
        self.assertTrue(all(c["css_orthogonal"] for c in item["topologies"]))
        hashes = [c["hz_graph_sha256"] for c in item["topologies"]]
        self.assertEqual(len(set(hashes)), len(hashes))
        self.assertFalse(item["claim_boundary"]["physical_quantum_hardware_evidence"])

    def test_folded_family_metrics_and_qec_label_coverage(self):
        item = self.item
        self.assertIn(item["evaluation"]["primary"]["verdict"], (
            "NOT_EVALUABLE", "EXPLORATORY_ONLY_NOT_EXTERNAL_VALIDATION",
            "NO_PRE_REGISTERED_ADVANTAGE_DETECTED"))
        for noise in css.NOISE_BPS:
            values = item["evaluation"]["per_noise"][str(noise)]
            self.assertEqual(16 * css.TRIALS, values["train_trials"])
            self.assertEqual(8 * css.TRIALS, values["heldout_trials"])
            self.assertEqual(8 * css.QEC_TRIALS, values["qec_reference_cases"])
            b = values["blocked"]
            self.assertEqual(css.BOOTSTRAPS,
                             b["defined_replicates"] +
                             b["undefined_one_class_replicates"])

    def test_rehashed_bp_trace_forgery_fails_source_rerun(self):
        forged = copy.deepcopy(self.item)
        forged["bp_trials"][0]["bp"]["iterations"] += 1
        forged["sha256"] = css.digest(css.canonical(
            {k:v for k,v in forged.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "rerun mismatch"):
            css.verify(css.canonical(forged) + b"\n", DONOR)

    def test_byte_identical_pinned_source_rerun(self):
        self.assertEqual(self.item, css.verify(self.raw, DONOR))


if __name__ == "__main__":
    unittest.main()
