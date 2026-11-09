# SPDX-License-Identifier: MPL-2.0
"""Independent known-spectrum and capacity tests for scaled native Ada solver.

No scientific NumPy/SciPy dependency. K(m,n) Perron radius is
sqrt((m-1)(n-1)); degree-two cycles have unit radius. Exact small-graph
Phase 1D tests remain untouched and still run in the full suite.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCALE = ROOT / "build/bin" / ("qec_scale.exe" if os.name == "nt" else "qec_scale")
SMALL = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")


def encode_graph(variables, checks, edges):
    rows = ["QECADA-TANNER-EDGES-V1", f"variables={variables}",
            f"checks={checks}", f"edges={len(edges)}"]
    rows += [f"{c},{v}" for c, v in edges]
    return ("\n".join(rows) + "\n").encode("ascii")


def complete_graph(checks, variables):
    return [(c, v) for c in range(1, checks + 1)
            for v in range(1, variables + 1)]


def execute_raw(contents):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "graph.txt"
        path.write_bytes(contents)
        return subprocess.run([str(SCALE), "inspect", str(path)],
                              capture_output=True, text=True, timeout=40)


def execute(n, m, edges):
    return execute_raw(encode_graph(n, m, edges))


def parse(text):
    fields = {}
    top = []
    for line in text.splitlines():
        if "=" not in line:
            raise AssertionError(f"nonconforming line {line!r}")
        k, v = line.split("=", 1)
        if k == "top":
            rank, edge, energy = v.split(",")
            assert int(rank) == len(top) + 1
            top.append((int(edge), float(energy)))
        else:
            assert k not in fields, k
            fields[k] = v
    return fields, top


@unittest.skipUnless(SCALE.is_file(), "native qec_scale is not built")
class ScaledNativeTests(unittest.TestCase):
    def assert_analytic_complete(self, checks, variables):
        p = execute(variables, checks, complete_graph(checks, variables))
        self.assertEqual(0, p.returncode, (checks, variables, p.stderr))
        data, top = parse(p.stdout)
        expected = math.sqrt((checks - 1) * (variables - 1))
        self.assertEqual("CONVERGED_NUMERIC", data["status"])
        self.assertEqual("bounded-sparse-scc-lazy-perron-v1", data["algorithm"])
        self.assertEqual("selected-recurrent-block", data["mode_scope"])
        self.assertEqual(checks * variables, int(data["edges"]))
        self.assertEqual(2 * checks * variables, int(data["directed_edges"]))
        self.assertAlmostEqual(expected, float(data["spectral_radius"]),
                               delta=1e-7)
        self.assertLess(float(data["collatz_upper"]) -
                        float(data["collatz_lower"]), 1e-7)
        self.assertLess(float(data["residual_l1"]), 1e-7)
        self.assertEqual(min(10, int(data["mode_edge_count"])), len(top))
        self.assertEqual(len(set(edge for edge, _ in top)), len(top))
        self.assertTrue(all(1 <= edge <= 2 * checks * variables
                            for edge, _ in top))
        return data, top, p.stdout

    def test_known_radii_small_and_large(self):
        for c, v in ((2, 2), (2, 3), (4, 5), (8, 16),
                     (16, 24), (32, 64)):
            with self.subTest(checks=c, variables=v):
                data, _, output = self.assert_analytic_complete(c, v)
                self.assertEqual(output, execute(
                    v, c, complete_graph(c, v)).stdout)
                self.assertEqual(2_048, int(data["max_edges"]))

    def test_bounded_max_capacity_and_beyond(self):
        data, _, _ = self.assert_analytic_complete(32, 64)
        self.assertEqual(4_096, int(data["directed_edges"]))
        p = execute(65, 32, complete_graph(32, 65))
        self.assertNotEqual(0, p.returncode)
        self.assertIn("ERROR:", p.stderr)
        p = execute(129, 1, [])
        self.assertNotEqual(0, p.returncode)
        p = execute(1, 129, [])
        self.assertNotEqual(0, p.returncode)

    def test_large_cycle_with_no_four_cycles(self):
        n = 64
        edges = sorted(set(edge for c in range(1, n + 1)
                           for edge in ((c, c), (c, c % n + 1))))
        p = execute(n, n, edges)
        self.assertEqual(0, p.returncode, p.stderr)
        f, _ = parse(p.stdout)
        self.assertEqual("CONVERGED_NUMERIC", f["status"])
        self.assertEqual("2", f["dominant_tie_count"])
        self.assertEqual(str(2 * n), f["mode_edge_count"])
        self.assertAlmostEqual(1.0, float(f["spectral_radius"]), places=9)
        self.assertAlmostEqual(1 / (2 * n), float(f["ipr"]), places=9)

    def test_long_tree_is_nilpotent(self):
        n = 128
        edges = [(c, v) for c in range(1, n)
                 for v in (c, c + 1)]
        p = execute(n, n - 1, edges)
        self.assertEqual(0, p.returncode, p.stderr)
        f, top = parse(p.stdout)
        self.assertEqual("ACYCLIC", f["status"])
        self.assertEqual("0.000000000000", f["spectral_radius"])
        self.assertEqual("0", f["mode_edge_count"])
        self.assertEqual([], top)

    def test_no_edges_and_disconnected_ties(self):
        p = execute(4, 4, [])
        self.assertEqual(0, p.returncode)
        self.assertEqual("NO_EDGES", parse(p.stdout)[0]["status"])
        edges = [(c, v) for c in (1, 2) for v in (1, 2)]
        edges += [(c, v) for c in (3, 4) for v in (3, 4)]
        f, top = parse(execute(4, 4, edges).stdout)
        self.assertEqual("4", f["dominant_tie_count"])
        self.assertEqual("4", f["mode_edge_count"])
        self.assertEqual("1", f["mode_root_edge"])
        self.assertAlmostEqual(1.0, float(f["spectral_radius"]), places=10)
        self.assertEqual(4, len(top))

    def test_legacy_four_cycle_oracle(self):
        p = execute(2, 2, complete_graph(2, 2))
        self.assertEqual(0, p.returncode)
        scaled, _ = parse(p.stdout)
        old = subprocess.run(
            [str(SMALL), "spectral", "2", "1100", "0011"],
            capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(0, old.returncode, old.stderr)
        baseline = dict(line.split("=", 1) for line in old.stdout.splitlines()
                        if line.startswith(("spectral_radius=", "ipr=")))
        self.assertAlmostEqual(float(baseline["spectral_radius"]),
                               float(scaled["spectral_radius"]), places=9)
        self.assertAlmostEqual(float(baseline["ipr"]),
                               float(scaled["ipr"]), places=9)

    def test_noncanonical_inputs_rejected(self):
        good = encode_graph(2, 2, complete_graph(2, 2))
        bad = (
            good + b"extraneous\n",
            good.replace(b"variables=2", b"variables=02"),
            good.replace(b"edges=4", b"edges=+4"),
            good.replace(b"1,1\n1,2", b"1,1\n1,1"),
            good.replace(b"2,1\n2,2", b"2,2\n2,1"),
            good.replace(b"1,1", b"0,1"),
            good.replace(b"1,1", b"1,0"),
            good.replace(b"1,1", b"1,1,1"),
            good.replace(b"QECADA-TANNER-EDGES-V1", b"TANNER-v2"),
        )
        for raw in bad:
            with self.subTest(raw=raw[:50]):
                p = execute_raw(raw)
                self.assertNotEqual(0, p.returncode, raw)
                self.assertIn("ERROR:", p.stderr)


if __name__ == "__main__":
    unittest.main()
