# SPDX-License-Identifier: MPL-2.0
"""Phase 1C receipt replay, adversarial self-consistent edits, SPECTRAL bridge."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import strowger_receipt as receipts
import tanner_spectral_export as spectral

BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")


class IndependentReplayTests(unittest.TestCase):
    def request(self, fault="none", **kwargs):
        values = {
            "digits": "1020", "radices": "3333",
            "linefinders": "1100", "first_bank": "0100",
            "second_bank": "0010", "fault": fault,
            "request_id": "receipt-001", "epoch": 7,
        }
        values.update(kwargs)
        return receipts.request(**values)

    def test_pure_oracle_replay_no_native_required(self):
        good = receipts.replay(self.request())
        self.assertEqual("ROUTED", good["status"])
        self.assertEqual((1, 2, 3), (good["linefinder"], good["selector_a"],
                                     good["selector_b"]))
        self.assertEqual([x["sequence"] for x in good["events"]],
                         list(range(len(good["events"]))))
        self.assertEqual(len(good["events"]), len(receipts.replay(self.request())["events"]))
        self.assertEqual("PULSE_MISMATCH",
                         receipts.replay(self.request("miss1"))["status"])
        self.assertEqual("TONE_MISMATCH",
                         receipts.replay(self.request("dark"))["status"])
        self.assertEqual("INVALID_REQUEST",
                         receipts.replay(self.request(digits="9000"))["status"])

    def test_invalid_or_ambiguous_source_input(self):
        for kwargs in ({"request_id": "a b"}, {"epoch": True},
                       {"radices": "1010"}, {"fault": "stuck3"},
                       {"linefinders": "../."}, {"digits": "000"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.request(**kwargs)

    @unittest.skipUnless(BIN.is_file(), "native qec_research not built")
    def test_native_exact_oracle_parity_and_canonical_verification(self):
        for fault in ("none", "miss1", "dup2", "stuck1", "route", "check", "dark"):
            with self.subTest(fault=fault):
                r = self.request(fault=fault)
                signed = receipts.make_receipt(r)
                raw = receipts.canonical(signed) + b"\n"
                self.assertEqual(signed, receipts.validate_bytes(raw))
                self.assertEqual(raw, receipts.canonical(receipts.make_receipt(r)) + b"\n")

    @unittest.skipUnless(BIN.is_file(), "native qec_research not built")
    def test_forged_hash_consistent_event_fails_independent_replay(self):
        p = receipts.make_receipt(self.request())
        forged = copy.deepcopy(p)
        events = forged["trace"]["events"]
        source = {key: value for key, value in events[1].items()
                  if key not in ("previous_event_sha256", "event_sha256")}
        source["value"] += 1
        events[1]["value"] += 1
        # Re-sign complete event stream and then the enclosing receipt.
        for i, event in enumerate(forged["trace"]["events"]):
            if i:
                event["previous_event_sha256"] = (
                    forged["trace"]["events"][i - 1]["event_sha256"])
            raw_event = {k: v for k, v in event.items() if k != "event_sha256"}
            event["event_sha256"] = receipts.sha(receipts.canonical(raw_event))
        unsigned = {k: v for k, v in forged.items() if k != "sha256"}
        forged["sha256"] = receipts.sha(receipts.canonical(unsigned))
        with self.assertRaisesRegex(ValueError, "independent route/event replay mismatch"):
            receipts.validate_bytes(receipts.canonical(forged) + b"\n")

    @unittest.skipUnless(BIN.is_file(), "native qec_research not built")
    def test_forged_status_with_correct_self_hash_fails(self):
        p = receipts.make_receipt(self.request())
        p["trace"]["status"] = "NO_LINEFINDER"
        p["sha256"] = receipts.sha(receipts.canonical(
            {k: v for k, v in p.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "independent route/event replay mismatch"):
            receipts.validate_bytes(receipts.canonical(p) + b"\n")

    @unittest.skipUnless(BIN.is_file(), "native qec_research not built")
    def test_bad_receipt_format_and_source_mutation(self):
        p = receipts.make_receipt(self.request())
        raw = receipts.canonical(p) + b"\n"
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            receipts.validate_bytes(raw[:-1])
        duplicate = raw.decode().replace('{"claim_boundary":',
                                         '{"claim_boundary":{},"claim_boundary":', 1)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            receipts.validate_bytes(duplicate.encode())
        p["request"]["first_bank"] = "1000"
        p["sha256"] = receipts.sha(receipts.canonical(
            {k: v for k, v in p.items() if k != "sha256"}))
        with self.assertRaisesRegex(ValueError, "independent route/event replay mismatch"):
            receipts.validate_bytes(receipts.canonical(p) + b"\n")

    @unittest.skipUnless(BIN.is_file(), "native qec_research not built")
    def test_non_overwriting_file_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            req = self.request()
            data = receipts.canonical(receipts.make_receipt(req)) + b"\n"
            with path.open("xb") as fp:
                fp.write(data)
            self.assertEqual(receipts.validate_bytes(path.read_bytes())["schema"],
                             receipts.SCHEMA)
            with self.assertRaises(FileExistsError):
                with path.open("xb"):
                    pass


@unittest.skipUnless(BIN.is_file(), "native qec_research not built")
class SpectralObservationTests(unittest.TestCase):
    def test_tanner_observation_identity_and_exact_counts(self):
        p = spectral.observe(2, ["1100", "0012"])
        self.assertEqual(spectral.SCHEMA, p["schema"])
        self.assertEqual(1, p["observation"]["four_cycles"])
        self.assertEqual(8, p["observation"]["nb_trace4"])
        self.assertEqual([2, 2], p["observation"]["variable_degrees"])
        self.assertEqual(p, spectral.observe(2, ["1100", "0012"]))
        unsigned = {k: v for k, v in p.items() if k != "sha256"}
        self.assertEqual(hashlib.sha256(spectral.canonical(unsigned)).hexdigest(),
                         p["sha256"])
        self.assertFalse(p["claim_boundary"]["spectral_radius_measured"])
        self.assertFalse(p["claim_boundary"]["spectral_qec_app_dataset_compatible"])

    def test_mixed_support_and_noncommuting_observation(self):
        mixed = spectral.observe(1, ["11"])
        self.assertEqual(1, mixed["observation"]["mixed_edges"])
        noncommuting = spectral.observe(3, ["111000", "000111"])
        self.assertEqual(3, noncommuting["observation"]["four_cycles"])
        self.assertEqual(24, noncommuting["observation"]["nb_trace4"])

    def test_bounded_bad_source_fails(self):
        for n, rows in ((0, ["01"]), (6, ["0"*12]),
                        (2, ["0000", "0009"]), (2, [])):
            with self.subTest(n=n, rows=rows), self.assertRaises(ValueError):
                spectral.observe(n, rows)


if __name__ == "__main__":
    unittest.main()
