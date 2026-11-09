# SPDX-License-Identifier: MPL-2.0
"""Independent bounded Tanner/Hashimoto and Strowger CLI oracles."""
import itertools
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build/bin" / ("qec_research.exe" if os.name == "nt" else "qec_research")


def run(*args):
    return subprocess.run([str(BIN), *map(str, args)], capture_output=True,
                          text=True, timeout=20, check=False)


def fields(out):
    values = {}
    for line in out.splitlines():
        if "=" in line and not line.startswith("event=") and not line.startswith("edge="):
            a, b = line.split("=", 1)
            if a in values:
                raise AssertionError("duplicate result field " + a)
            values[a] = b
    return values


def reference_graph(n, rows):
    """Independent support graph and exact nonbacktracking trace(B**4)."""
    directed = []
    check_degrees = [0] * len(rows)
    var_degrees = [0] * n
    edge_sites = []
    for ci, row in enumerate(rows):
        for vi in range(n):
            if row[vi] != "0" or row[n + vi] != "0":
                check_degrees[ci] += 1
                var_degrees[vi] += 1
                edge_sites.append((ci, vi))
                directed.extend(((vi, n + ci), (n + ci, vi)))
    cycles = 0
    heat = [0] * n
    for a in range(len(rows)):
        for b in range(a + 1, len(rows)):
            shared = [v for v in range(n) if (a, v) in edge_sites
                      and (b, v) in edge_sites]
            for u, v in itertools.combinations(shared, 2):
                cycles += 1
                heat[u] += 1
                heat[v] += 1
    # Independent explicit Hashimoto matrix multiplication over integers.
    size = len(directed)
    B = [[int(directed[i][1] == directed[j][0] and
              directed[i][0] != directed[j][1])
          for j in range(size)] for i in range(size)]
    # For every basis vector, multiply by B four times and inspect the diagonal.
    trace = 0
    for src in range(size):
        vector = [int(i == src) for i in range(size)]
        for _ in range(4):
            vector = [sum(vector[i] * B[i][j] for i in range(size))
                      for j in range(size)]
        trace += vector[src]
    return {
        "edges": len(edge_sites), "four_cycles": cycles, "nb_trace4": trace,
        "var_degrees": var_degrees, "check_degrees": check_degrees,
        "heat": heat, "edge_sites": edge_sites,
    }


@unittest.skipUnless(BIN.is_file(), "native Ada research CLI not built")
class TannerTests(unittest.TestCase):
    def check_graph(self, n, rows):
        p = run("tanner", n, *rows)
        self.assertEqual(0, p.returncode, p.stderr)
        data = fields(p.stdout)
        expected = reference_graph(n, rows)
        self.assertEqual("qec-ada.tanner-observation.v1", data["schema"])
        self.assertEqual(expected["edges"], int(data["edges"]))
        self.assertEqual(expected["four_cycles"], int(data["four_cycles"]))
        self.assertEqual(expected["nb_trace4"], int(data["nb_trace4"]))
        self.assertEqual(8 * expected["four_cycles"], expected["nb_trace4"])
        for j in range(n):
            self.assertEqual(expected["var_degrees"][j],
                             int(data["variable_degree_" + str(j + 1)]))
            self.assertEqual(expected["heat"][j],
                             int(data["variable_cycle_heat_" + str(j + 1)]))
        for j in range(len(rows)):
            self.assertEqual(expected["check_degrees"][j],
                             int(data["check_degree_" + str(j + 1)]))
        edge_lines = [line.removeprefix("edge=") for line in p.stdout.splitlines()
                      if line.startswith("edge=")]
        actual = [tuple(map(int, line.split(","))) for line in edge_lines]
        self.assertEqual(expected["edge_sites"],
                         [(c - 1, v - 1) for c, v, _, _ in actual])
        return p.stdout

    def test_exact_four_cycle_and_trace(self):
        x = self.check_graph(2, ("1100", "0012"))
        self.assertIn("four_cycles=1", x)
        self.assertIn("nb_trace4=8", x)
        self.assertEqual(x, self.check_graph(2, ("1100", "0012")))

    def test_pure_mixed_support(self):
        x = self.check_graph(1, ("11",))
        self.assertIn("mixed_edges=1", x)
        self.assertIn("x_edges=1", x)
        self.assertIn("z_edges=1", x)

    def test_independent_all_bipartite_patterns_two_by_three(self):
        for pattern in range(64):
            rows = []
            for c in range(2):
                bitstring = "".join(str((pattern >> (c * 3 + v)) & 1)
                                    for v in range(3))
                rows.append("000" + bitstring)
            self.check_graph(3, tuple(rows))

    def test_observation_accepts_noncommuting_support(self):
        p = self.check_graph(3, ("111000", "000111"))
        self.assertIn("four_cycles=3", p)
        self.assertIn("nb_trace4=24", p)

    def test_graph_input_rejections(self):
        for args in (
            ("tanner", "0", "01"),
            ("tanner", "6", "000000000000"),
            ("tanner", "2", "010"),
            ("tanner", "2", "0009"),
            ("tanner", "1"),
        ):
            self.assertNotEqual(0, run(*args).returncode, args)


@unittest.skipUnless(BIN.is_file(), "native Ada research CLI not built")
class StrowgerTests(unittest.TestCase):
    GOOD = ("strowger", "1020", "3333", "1100", "0100", "0010", "none")

    def test_route_event_order_replay_repeat(self):
        p = run(*self.GOOD)
        self.assertEqual(0, p.returncode, p.stderr)
        data = fields(p.stdout)
        self.assertEqual("ROUTED", data["status"])
        self.assertEqual(("1", "2", "3"), (data["linefinder"],
                                          data["selector_a"], data["selector_b"]))
        self.assertEqual("qec-ada.strowger-event-stream.v1", data["schema"])
        ev = [line.removeprefix("event=").split(",") for line in
              p.stdout.splitlines() if line.startswith("event=")]
        self.assertEqual(int(data["count"]), len(ev))
        self.assertEqual(list(range(len(ev))), [int(e[0]) for e in ev])
        self.assertEqual(list(range(len(ev))), [int(e[1]) for e in ev])
        self.assertEqual(9, sum(e[2] == "PULSE_RECEIVED" for e in ev))
        self.assertEqual("RESOURCES_RELEASED", ev[-1][2])
        self.assertEqual(p.stdout, run(*self.GOOD).stdout)
        for i in range(1, 4):
            self.assertEqual(data["tone_expected_" + str(i)],
                             data["tone_observed_" + str(i)])

    def test_fail_closed_with_faults_and_contact_masks(self):
        cases = (
            (("0000", "0100", "0010", "none"), "NO_LINEFINDER"),
            (("1100", "0000", "0010", "none"), "NO_FIRST_TRUNK"),
            (("1100", "0100", "0000", "none"), "NO_SECOND_TRUNK"),
            (("Q000", "0100", "0010", "none"), "NO_LINEFINDER"),
            (("1100", "0100", "0010", "miss1"), "PULSE_MISMATCH"),
            (("1100", "0100", "0010", "dup2"), "PULSE_MISMATCH"),
            (("1100", "0100", "0010", "stuck1"), "SELECTOR_STUCK"),
            (("1100", "0100", "0010", "route"), "TONE_MISMATCH"),
            (("1100", "0100", "0010", "check"), "TONE_MISMATCH"),
            (("1100", "0100", "0010", "dark"), "TONE_MISMATCH"),
        )
        for (l, a, b, f), reason in cases:
            with self.subTest(case=(l,a,b,f)):
                p = run("strowger", "1020", "3333", l, a, b, f)
                self.assertNotEqual(0, p.returncode)
                data = fields(p.stdout)
                self.assertEqual(reason, data["status"])
                self.assertEqual("0", data["linefinder"])
                self.assertEqual("0", data["selector_a"])
                self.assertEqual("0", data["selector_b"])
                self.assertNotIn("ROUTE_COMMITTED", p.stdout)
                self.assertIn("ROUTE_REJECTED", p.stdout)

    def test_mixed_radices_and_zero_pulse_train(self):
        for digits, radices in (("1020", "3498"), ("0000", "2345"),
                                ("2222", "3456")):
            p = run("strowger", digits, radices, "1111", "1111", "1111", "none")
            self.assertEqual(0, p.returncode, (digits, radices, p.stderr))
            count = sum(int(r) if int(d) == 0 else int(d)
                        for d, r in zip(digits, radices))
            self.assertEqual(count, p.stdout.count("PULSE_RECEIVED"))

    def test_invalid_route_input(self):
        for args in (("9000", "3333", "1111", "1111", "1111", "none"),
                     ("0000", "3333", "1111", "1111", "1111", "stuck3"),
                     ("0000", "3333", "1111", "1111", "1111", "bad"),
                     ("0000", "3333", "1111", "1111", "111", "none"),
                     ("0000", "3333", "1111", "1111", "1111", "miss9")):
            self.assertNotEqual(0, run("strowger", *args).returncode, args)


if __name__ == "__main__":
    unittest.main()
