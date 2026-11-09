# SPDX-License-Identifier: MPL-2.0
"""Phase 1I: independent CSS coset oracles, ideal syndrome and replay tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1i_css_pauli as css
import phase1i_experiment as study

ARTIFACT = ROOT / "evidence/phase1i/css_pauli.json"
SIMULA = ROOT / ".donor-nisqec"
EXPLICIT = ROOT / ".donor-explicit-qldpc"


def four_qubit() -> css.CSS:
    # [[4,2,2]] CSS stabilizers XXXX and ZZZZ.
    # One-site X or Z leader has a nontrivial same-syndrome competitor.
    all_sites = [(1, i) for i in range(1, 5)]
    return css.prepare(4, 1, all_sites, 1, all_sites)


def two_qubit() -> css.CSS:
    # [[2,0,2]] pure CSS stabilizer state: XX and ZZ.
    return css.prepare(2, 1, [(1, 1), (1, 2)],
                       1, [(1, 1), (1, 2)])


class PureCSSMathTests(unittest.TestCase):
    def test_gf2_rowspan_exact_and_degenerate(self):
        pivots = css.echelon((0b1111, 0b1100, 0b0011))
        self.assertEqual(2, len(pivots))
        for mask in (0, 0b1111, 0b1100, 0b0011):
            self.assertTrue(css.in_span(mask, pivots))
        self.assertFalse(css.in_span(0b0001, pivots))
        self.assertFalse(css.in_span(0b1010, pivots))

    def test_anticommuting_css_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "noncommuting"):
            css.prepare(2, 1, [(1, 1)], 1, [(1, 1)])
        for bad in (-1, True, 129):
            with self.assertRaises(ValueError):
                css.prepare(bad, 1, [(1, 1)], 1, [(1, 1)])

    def test_stabilizer_coset_is_not_vector_equality(self):
        model = two_qubit()
        self.assertEqual(0, model.k)
        # Nonzero physical Pauli error that is itself a stabilizer:
        for pauli in ([(1, "X"), (2, "X")],
                      [(1, "Z"), (2, "Z")],
                      [(1, "Y"), (2, "Y")]):
            trial = css.run_case(model, pauli)
            self.assertEqual("STABILIZER_EQUIVALENT_SUCCESS", trial["outcome"])
            self.assertFalse(trial["pauli_frame_failure"])
            self.assertTrue(trial["syndrome_consistent"])
            self.assertIs(trial["logical_failure"], False)

    def test_identical_syndrome_different_true_error_same_decision(self):
        model = four_qubit()
        self.assertEqual(2, model.k)
        a = css.run_case(model, [(1, "X")])
        b = css.run_case(model, [(2, "X")])
        self.assertEqual(a["measured_syndrome_z"], b["measured_syndrome_z"])
        self.assertEqual(a["x_decoder"], b["x_decoder"])
        self.assertEqual("STABILIZER_EQUIVALENT_SUCCESS", a["outcome"])
        self.assertEqual("NONTRIVIAL_LOGICAL", b["outcome"])
        self.assertIs(b["logical_x"], True)
        self.assertIs(b["logical_z"], False)

    def test_zero_syndrome_can_be_a_nontrivial_logical(self):
        result = css.run_case(four_qubit(), [(1, "X"), (2, "X")])
        self.assertEqual([0], result["measured_syndrome_z"])
        self.assertEqual("ZERO_SYNDROME", result["x_decoder"]["method"])
        self.assertEqual("NONTRIVIAL_LOGICAL", result["outcome"])
        self.assertEqual(0, result["remaining_z_check_weight"])

    def test_y_error_has_both_correlated_pauli_components(self):
        result = css.run_case(four_qubit(), [(2, "Y")])
        self.assertEqual(1, result["y_count"])
        self.assertEqual(1, result["true_x_weight"])
        self.assertEqual(1, result["true_z_weight"])
        self.assertIs(result["logical_x"], True)
        self.assertIs(result["logical_z"], True)
        self.assertTrue(result["syndrome_consistent"])

    def test_detected_unresolved_not_misreported_as_logical(self):
        # H_Z has only syndromes 10,01 per single-site error.
        hz = [(1, 1), (1, 2), (2, 3), (2, 4)]
        hx = [(1, 1), (1, 2)]
        model = css.prepare(4, 1, hx, 2, hz)
        result = css.run_case(model, [(1, "X"), (3, "X")], rounds=2)
        self.assertEqual("DETECTED_UNRESOLVED", result["outcome"])
        self.assertIsNone(result["logical_failure"])
        self.assertIsNone(result["logical_x"])
        self.assertGreater(result["remaining_z_check_weight"], 0)

    def test_bruteforce_small_css_syndrome_and_rowspace_oracle(self):
        # Independent direct enumeration of all possible stabilizer
        # products: a zero-syndrome residual is trivial iff it equals
        # one of those exact combinations.
        for model in (two_qubit(), four_qubit()):
            xspan = {0}
            zspan = {0}
            for row in model.xrows:
                xspan |= {v ^ row for v in tuple(xspan)}
            for row in model.zrows:
                zspan |= {v ^ row for v in tuple(zspan)}
            for x in range(1 << model.n):
                for z in range(1 << model.n):
                    if (not any(css.syndrome(model.zrows, x))
                            and not any(css.syndrome(model.xrows, z))):
                        expected = x in xspan and z in zspan
                        actual = css.in_span(x, model.xbasis) and \
                                 css.in_span(z, model.zbasis)
                        self.assertEqual(expected, actual)

    def test_pauli_draw_determinism_and_replay(self):
        first = css.pauli_tape("seed-one", "code-A", 5000, 7, 128)
        self.assertEqual(first, css.pauli_tape(
            "seed-one", "code-A", 5000, 7, 128))
        self.assertTrue(any(k == "Y" for _, k in first))
        self.assertTrue(all(k in ("X", "Y", "Z") for _, k in first))
        self.assertEqual([], css.pauli_tape("seed-one", "code-A", 0, 0, 128))
        self.assertNotEqual(first, css.pauli_tape(
            "seed-two", "code-A", 5000, 7, 128))

    def test_invalid_pauli_tape_fails_before_decoding(self):
        model = two_qubit()
        for bad in ([(0, "X")], [(3, "Z")], [(1, "A")],
                    [(1, "X"), (1, "Z")], [(True, "X")]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                css.run_case(model, bad)


@unittest.skipUnless(ARTIFACT.is_file() and SIMULA.is_dir()
                     and EXPLICIT.is_dir(),
                     "pinned external CSS integration lane only")
class SourceReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ARTIFACT.read_bytes()
        cls.data = json.loads(cls.raw)
        cls.donors = {"simula": SIMULA, "explicit": EXPLICIT}

    def test_source_and_outcome_coverage(self):
        r = self.data
        self.assertEqual(study.SCHEMA, r["schema"])
        self.assertEqual(9, len(r["sources"]))
        self.assertEqual(9 * 3 * 8, len(r["pauli_trials"]))
        self.assertTrue(all(code["css_checks_commute"] for code in r["sources"]))
        self.assertFalse(r["claim_boundary"]["external_source_matrices_redistributed"])
        self.assertTrue(r["claim_boundary"]["ideal_noiseless_syndrome_only"])
        self.assertTrue(all("hx_edges" not in code and "hz_edges" not in code
                            for code in r["sources"]))

    def test_all_outcomes_accounted_and_distinct_from_logic(self):
        for rate in (400, 800, 1200):
            values = self.data["evaluation"]["per_noise"][str(rate)]
            for group, count in (("source_baseline", 2), ("heldout", 7)):
                part = values["by_publisher"][group]
                self.assertEqual(count, part["distinct_source_topologies"])
                self.assertEqual(count * 8, part["trials"])
                self.assertEqual(part["trials"],
                                 part["stabilizer_success"] +
                                 part["nontrivial_logical"] +
                                 part["detected_unresolved"])
        for record in self.data["pauli_trials"]:
            trial = record["result"]
            if trial["outcome"] == "DETECTED_UNRESOLVED":
                self.assertIsNone(trial["logical_failure"])
            else:
                self.assertIsNotNone(trial["logical_failure"])

    def test_exact_full_source_and_decoder_reexecution(self):
        self.assertEqual(self.data, study.verify(self.raw, self.donors))

    def test_rehashed_forged_logical_label_rejected(self):
        forged = copy.deepcopy(self.data)
        first = forged["pauli_trials"][0]["result"]
        first["outcome"] = "PHYSICAL_QUANTUM_PROVED"
        unsigned = {k:v for k,v in forged.items() if k != "sha256"}
        forged["sha256"] = study.digest(study.canonical(unsigned))
        with self.assertRaisesRegex(ValueError, "replay mismatch"):
            study.verify(study.canonical(forged) + b"\n", self.donors)


if __name__ == "__main__":
    unittest.main()
