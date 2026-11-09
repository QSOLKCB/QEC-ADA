# SPDX-License-Identifier: MPL-2.0
"""Independent/forgery-aware replay of QEC-ADA Phase 1D spectrum receipts."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import nb_spectral_export as observations

BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")


@unittest.skipUnless(BIN.is_file(), "native spectral executable not built")
class SparseReceiptTests(unittest.TestCase):
    examples = (
        {"sites": 2, "rows_x_z": ["0000"]},
        {"sites": 3, "rows_x_z": ["111000"]},
        {"sites": 2, "rows_x_z": ["1100", "0012"]},
        {"sites": 3, "rows_x_z": ["110000", "011000", "101000"]},
        {"sites": 3, "rows_x_z": ["111000", "000111"]},
        {"sites": 4, "rows_x_z": [
            "11000000", "11000000", "00110000", "00110000",
        ]},
        {"sites": 5, "rows_x_z": ["1111100000"] * 4},
    )

    def test_create_and_verify_without_native_binary(self):
        for source in self.examples:
            with self.subTest(source=source):
                receipt = observations.make(source)
                raw = observations.canonical(receipt) + b"\n"
                with patch.object(observations, "BIN",
                                  ROOT / "does-not-exist-qec-research"):
                    self.assertEqual(receipt, observations.verify_bytes(raw))
                self.assertEqual(raw, observations.canonical(
                    observations.make(source)) + b"\n")
                self.assertEqual(
                    receipt["source_sha256"],
                    observations.sha(observations.canonical(source)),
                )
                self.assertEqual(
                    receipt["schema"], "qec-ada.nb-spectral-receipt.v1")

    def test_rehashed_spectral_radius_forgery_fails_independent_oracle(self):
        receipt = copy.deepcopy(observations.make(self.examples[4]))
        receipt["spectrum"]["spectral_radius"] = "9.000000000000"
        receipt["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in receipt.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "spectral radius disagrees"):
            observations.verify_bytes(observations.canonical(receipt) + b"\n")

    def test_rehashed_wrong_component_winner_fails(self):
        receipt = copy.deepcopy(observations.make(self.examples[5]))
        receipt["spectrum"]["mode_root_edge"] = 3
        receipt["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in receipt.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "mode selection mismatch"):
            observations.verify_bytes(observations.canonical(receipt) + b"\n")

    def test_rehashed_energy_vector_fails(self):
        receipt = copy.deepcopy(observations.make(self.examples[2]))
        receipt["spectrum"]["energy"][0] = "0.500000000000"
        receipt["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in receipt.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "edge energies disagree"):
            observations.verify_bytes(observations.canonical(receipt) + b"\n")

    def test_rehashed_wrong_topology_or_nested_digest_fails(self):
        receipt = copy.deepcopy(observations.make(self.examples[4]))
        receipt["source"]["rows_x_z"][0] = "000000"
        receipt["source_sha256"] = observations.sha(observations.canonical(
            receipt["source"]))
        receipt["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in receipt.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "Tanner topology"):
            observations.verify_bytes(observations.canonical(receipt) + b"\n")

        receipt = copy.deepcopy(observations.make(self.examples[2]))
        receipt["graph_observation_sha256"] = "0" * 64
        receipt["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in receipt.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "graph observation identity mismatch"):
            observations.verify_bytes(observations.canonical(receipt) + b"\n")

    def test_type_substitution_and_noncanonical_json_rejected(self):
        receipt = observations.make(self.examples[2])
        raw = observations.canonical(receipt) + b"\n"
        with self.assertRaisesRegex(ValueError, "canonical byte"):
            observations.verify_bytes(raw[:-1])
        duplicate = raw.decode().replace('{"claim_boundary":',
                                         '{"claim_boundary":{},"claim_boundary":', 1)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            observations.verify_bytes(duplicate.encode())
        altered = copy.deepcopy(receipt)
        altered["spectrum"]["directed_edges"] = True
        altered["sha256"] = observations.sha(observations.canonical(
            {k: v for k, v in altered.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "spectral integer type"):
            observations.verify_bytes(observations.canonical(altered) + b"\n")

    def test_new_file_only_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum.json"
            command = [sys.executable, str(ROOT / "scripts/nb_spectral_export.py"),
                       "create", str(path), "2", "1100", "0012"]
            p = subprocess.run(command, text=True, capture_output=True, timeout=30)
            self.assertEqual(0, p.returncode, p.stderr)
            verify = subprocess.run(
                [sys.executable, str(ROOT / "scripts/nb_spectral_export.py"),
                 "verify", str(path)], text=True, capture_output=True,
                timeout=30)
            self.assertEqual(0, verify.returncode, verify.stderr)
            self.assertIn("PASS independent offline spectral replay", verify.stdout)
            self.assertNotEqual(0, subprocess.run(
                command, text=True, capture_output=True, timeout=30).returncode)


if __name__ == "__main__":
    unittest.main()
