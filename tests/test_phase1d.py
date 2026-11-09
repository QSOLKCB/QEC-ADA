# SPDX-License-Identifier: MPL-2.0
"""Independent finite-graph evidence for sparse native Hashimoto observatory.

Known spectra and dense *test-only* B matrices are an independent oracle.
No QEC/Python donor decoder or SciPy dependency is imported.
"""
from __future__ import annotations

import itertools
import math
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")


def run(n, *rows):
    return subprocess.run([str(BIN), "spectral", str(n), *rows],
                          capture_output=True, text=True, timeout=20)


def parse(out):
    fields = {}
    energies = {}
    ranks = []
    for line in out.splitlines():
        key, value = line.split("=", 1)
        if key == "energy":
            id_, weight = value.split(",")
            assert int(id_) not in energies, id_
            energies[int(id_)] = float(weight)
        elif key == "ranking":
            rank, edge_id = value.split(",")
            assert int(rank) == len(ranks) + 1
            ranks.append(int(edge_id))
        else:
            assert key not in fields, key
            fields[key] = value
    return fields, energies, ranks


def edges_of(n, rows):
    result = []
    for ci, row in enumerate(rows, n + 1):
        for site in range(1, n + 1):
            if row[site - 1] != "0" or row[n + site - 1] != "0":
                result.extend(((site, ci), (ci, site)))
    return result


def dense_test_operator(n, rows):
    edges = edges_of(n, rows)
    return [[int(a[1] == b[0] and a[0] != b[1])
             for b in edges] for a in edges]


def reference_trace4(B):
    size = len(B)
    total = 0
    for start in range(size):
        v = [int(i == start) for i in range(size)]
        for _ in range(4):
            v = [sum(v[i] * B[i][j] for i in range(size))
                 for j in range(size)]
        total += v[start]
    return total


@unittest.skipUnless(BIN.is_file(), "native spectral executable not built")
class SparseSpectralTests(unittest.TestCase):
    def get(self, n, *rows):
        p = run(n, *rows)
        self.assertEqual(0, p.returncode, (n, rows, p.stderr))
        f, e, ranking = parse(p.stdout)
        self.assertEqual("qec-ada.nb-spectral-observation.v1", f["schema"])
        self.assertEqual("scc-lazy-perron-bounded-v1", f["algorithm"])
        self.assertEqual("selected-recurrent-block", f["mode_scope"])
        self.assertEqual(len(edges_of(n, rows)),
                         int(f["directed_edges"]))
        self.assertEqual(set(range(1, len(edges_of(n, rows)) + 1)), set(e))
        self.assertEqual(reference_trace4(dense_test_operator(n, rows)),
                         int(f["nb_trace4"]))
        self.assertEqual(p.stdout, run(n, *rows).stdout)
        return f, e, ranking

    def test_no_edges_and_trees_have_no_mode(self):
        for n, rows, state in ((2, ("0000",), "NO_EDGES"),
                               (3, ("111000",), "ACYCLIC"),
                               (3, ("110000", "001000"), "ACYCLIC")):
            with self.subTest(rows=rows):
                f, e, ranking = self.get(n, *rows)
                self.assertEqual(state, f["status"])
                self.assertEqual(0.0, float(f["spectral_radius"]))
                self.assertEqual(0.0, float(f["ipr"]))
                self.assertEqual(0, int(f["ranking_count"])
                                 if "ranking_count" in f else len(ranking))
                self.assertEqual([], ranking)

    def test_square_periodic_and_degenerate_mode(self):
        f, e, order = self.get(2, "1100", "0012")
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertEqual(2, int(f["dominant_tie_count"]))
        self.assertEqual(4, int(f["mode_edge_count"]))
        self.assertEqual(1, int(f["mode_root_edge"]))
        self.assertAlmostEqual(1.0, float(f["spectral_radius"]), places=9)
        self.assertAlmostEqual(0.25, float(f["ipr"]), places=9)
        self.assertAlmostEqual(0.5, float(f["eeec"]), places=9)
        self.assertEqual([1, 4, 6, 7], order)
        self.assertEqual([1, 4, 6, 7],
                         [i for i, w in e.items() if w > 0])
        self.assertTrue(all(abs(w - 0.25) < 1e-9 for w in e.values() if w > 0))

    def test_hexagon_spectral_radius_without_four_cycles(self):
        f, e, order = self.get(3, "110000", "011000", "101000")
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertEqual(0, int(f["nb_trace4"]))
        self.assertEqual(0, int(f["four_cycles"]))
        self.assertAlmostEqual(1.0, float(f["spectral_radius"]), places=9)
        self.assertAlmostEqual(1.0 / 6.0, float(f["ipr"]), places=8)
        self.assertEqual(2, int(f["dominant_tie_count"]))
        self.assertEqual(6, int(f["mode_edge_count"]))
        self.assertEqual(6, len(order))

    def test_k23_known_nonintegral_radius(self):
        f, e, order = self.get(3, "111000", "000111")
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertEqual(1, int(f["cyclic_scc_count"]))
        self.assertEqual(1, int(f["dominant_tie_count"]))
        self.assertEqual(12, int(f["mode_edge_count"]))
        self.assertAlmostEqual(math.sqrt(2), float(f["spectral_radius"]),
                               places=8)
        self.assertLess(float(f["collatz_upper"]) -
                        float(f["collatz_lower"]), 1e-8)
        self.assertLess(float(f["residual_l1"]), 1e-8)
        self.assertAlmostEqual(1.0, sum(e.values()), places=9)
        self.assertAlmostEqual(sum(w * w for w in e.values()),
                               float(f["ipr"]), places=8)
        self.assertTrue(0.0 < float(f["eeec"]) < 1.0)
        self.assertEqual(12, len(order))

    def test_k33_uniform_perron(self):
        f, e, order = self.get(3, "111000", "111000", "111000")
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertAlmostEqual(2.0, float(f["spectral_radius"]), places=9)
        self.assertAlmostEqual(1.0 / 18.0, float(f["ipr"]), places=8)
        self.assertAlmostEqual(5.0 / 18.0, float(f["eeec"]), places=8)
        self.assertEqual(list(range(1, 19)), order)

    def test_two_disconnected_square_components_stable_tie(self):
        f, e, order = self.get(
            4, "11000000", "11000000", "00110000", "00110000")
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertEqual(4, int(f["dominant_tie_count"]))
        self.assertEqual(4, int(f["mode_edge_count"]))
        self.assertEqual(1, int(f["mode_root_edge"]))
        self.assertAlmostEqual(1.0, float(f["spectral_radius"]), places=9)
        self.assertEqual([1, 4, 6, 7], order)
        self.assertAlmostEqual(1.0, sum(e.values()), places=9)

    def test_empty_to_complete_binary_support_sweep(self):
        # All 64 distinct 2-check / 3-variable support masks, independent
        # of field labels, including nilpotent and multiple cyclic SCCs.
        for mask in range(64):
            rows = []
            for check in range(2):
                x = "".join(str((mask >> (check * 3 + site)) & 1)
                            for site in range(3))
                rows.append(x + "000")
            with self.subTest(mask=mask):
                f, e, order = self.get(3, *rows)
                if int(f["four_cycles"]) == 0:
                    self.assertEqual("ACYCLIC" if int(f["edges"]) else "NO_EDGES",
                                     f["status"])
                else:
                    self.assertEqual("CONVERGED_NUMERIC", f["status"])
                    self.assertAlmostEqual(1.0, float(f["spectral_radius"]),
                                           places=8)

    def test_large_bounded_complete_bipartite_k45(self):
        f, e, _ = self.get(5, *(["1111100000"] * 4))
        self.assertEqual(40, int(f["directed_edges"]))
        self.assertAlmostEqual(math.sqrt(12), float(f["spectral_radius"]),
                               places=8)
        self.assertLess(float(f["residual_l1"]), 1e-8)

    def test_label_support_invariance_and_reject(self):
        a = self.get(2, "1100", "0012")
        b = self.get(2, "0022", "1100")
        self.assertEqual(a[0]["spectral_radius"], b[0]["spectral_radius"])
        self.assertEqual(a[0]["ipr"], b[0]["ipr"])
        for args in (
            ("spectral", "0", "00"),
            ("spectral", "6", "000000000000"),
            ("spectral", "2", "001"),
            ("spectral", "2", "0090"),
            ("spectral", "1"),
        ):
            p = subprocess.run([str(BIN), *args], capture_output=True,
                               text=True, timeout=20)
            self.assertNotEqual(0, p.returncode, args)


if __name__ == "__main__":
    unittest.main()
