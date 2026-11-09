# SPDX-License-Identifier: MPL-2.0
"""Actual opt-in QEC bp_decode integration; only in pinned NumPy CI lane."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1e_experiment as phase1e
import phase1f_qec_bp_bridge as bridge

PARENT = ROOT / "evidence/phase1e/evidence.json"
DONOR = ROOT / ".donor-qec-bp"
ENABLED = PARENT.is_file() and DONOR.is_dir()


@unittest.skipUnless(ENABLED, "explicit pinned QEC CI reference lane")
class PinnedQECBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = PARENT.read_bytes()
        cls.observation = bridge.make(cls.parent, DONOR, 1)

    def test_pinned_source_and_actual_bp_outputs(self):
        self.assertEqual(bridge.DONOR_COMMIT,
                         self.observation["qec_source"]["commit"])
        self.assertEqual(bridge.SOURCE_BLOB,
                         self.observation["qec_source"]["git_blob_sha1"])
        self.assertEqual("min_sum", self.observation["claim_boundary"]["qec_mode"])
        self.assertFalse(
            self.observation["claim_boundary"]["decoders_semantically_identical"])
        self.assertEqual(4 * 3, len(self.observation["records"]))
        for row in self.observation["records"]:
            self.assertEqual(32, len(row["qec_decoded_word"]))
            self.assertEqual(sum(row["qec_decoded_word"]) > 0,
                             row["qec_frame_failure"])
            self.assertEqual(row["qec_syndrome_weight"] == 0,
                             row["qec_checks_satisfied"])

    def test_exact_reexecution_and_rehashed_forgery(self):
        raw = bridge.canonical(self.observation) + b"\n"
        self.assertEqual(self.observation,
                         bridge.verify(self.parent, raw, DONOR))
        forged = copy.deepcopy(self.observation)
        row = forged["records"][0]
        row["qec_frame_failure"] = not row["qec_frame_failure"]
        forged["sha256"] = bridge.digest(bridge.canonical({
            k: v for k, v in forged.items() if k != "sha256"
        }))
        with self.assertRaisesRegex(ValueError, "re-execution mismatch"):
            bridge.verify(self.parent, bridge.canonical(forged) + b"\n", DONOR)

    def test_wrong_donor_checkout_rejected(self):
        import subprocess
        with self.assertRaises((ValueError, OSError,
                                subprocess.CalledProcessError)):
            bridge.checked_source(ROOT)


class QECAdmissionTests(unittest.TestCase):
    def test_opt_in_required_even_if_parent_missing(self):
        from subprocess import run
        p = run([sys.executable, str(ROOT / "scripts/phase1f_qec_bp_bridge.py"),
                 "create", "/does-not-exist/parent", "/tmp/unused-qec.json",
                 "--donor", str(ROOT)],
                text=True, capture_output=True, timeout=15)
        self.assertNotEqual(0, p.returncode)
        self.assertIn("explicit --execute-pinned-donor required", p.stderr)

    def test_trial_selection_is_frozen_and_bounded(self):
        source = {"trials": [
            {"graph_id": gid, "noise_bps": rate, "trial": trial}
            for gid in range(10)
            for rate in (400,800)
            for trial in range(3)
        ], "config": {"noise_bps":[400,800]}}
        selected = bridge.sample_indices(source, 2)
        self.assertEqual(8, len(selected))
        self.assertTrue(all(row["graph_id"] in (0,5) for row in selected))
        self.assertTrue(all(row["trial"] < 2 for row in selected))
        for trials in (0, 5, True, -1):
            with self.assertRaises(ValueError):
                bridge.sample_indices(source, trials)


if __name__ == "__main__":
    unittest.main()
