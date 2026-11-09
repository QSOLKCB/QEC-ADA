# SPDX-License-Identifier: MPL-2.0
"""Independent reference mathematics for the fixed cyclic [[5,1,3]]_3 pilot.

No donor code is imported or executed. The QEC source is pinned by commit
in docs/PHASE1A_DECODER_ROUTING.md; these tests independently reconstruct
the specified generators and bounded coset-leader enumeration in Python.
"""
from __future__ import annotations

import itertools
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "build/bin" / ("qec_ada.exe" if os.name == "nt" else "qec_ada")


def checks() -> tuple[tuple[int, ...], ...]:
    rows = []
    for shift in range(4):
        x, z = [0] * 5, [0] * 5
        for site in (0, 3):
            x[(site + shift) % 5] = 1
        for site in (1, 2):
            z[(site + shift) % 5] = 1
        rows.append(tuple(x + z))
    return tuple(rows)


def syndrome(x: tuple[int, ...], z: tuple[int, ...]) -> tuple[int, ...]:
    result = []
    for row in checks():
        result.append((sum(a * b for a, b in zip(row[:5], z)) -
                       sum(a * b for a, b in zip(row[5:], x))) % 3)
    return tuple(result)


def add(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    return tuple((x + y) % 3 for x, y in zip(a, b))


def inv(a: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(-x % 3 for x in a)


def leaders() -> dict[tuple[int, ...], tuple[tuple[int, ...], tuple[int, ...]]]:
    zero = (0,) * 5
    table = {syndrome(zero, zero): (zero, zero)}
    for site in range(5):
        for x in range(3):
            for z in range(3):
                if (x, z) == (0, 0):
                    continue
                xx, zz = [0] * 5, [0] * 5
                xx[site], zz[site] = x, z
                key = syndrome(tuple(xx), tuple(zz))
                if key in table:
                    raise AssertionError("reference generator collision")
                table[key] = (tuple(xx), tuple(zz))
    if len(table) != 41:
        raise AssertionError("unexpected reference table size")
    return table


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(BINARY), *map(str, args)], text=True, capture_output=True,
                          timeout=20, check=False)


def mapped(out: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


@unittest.skipUnless(BINARY.is_file(), "native Ada CLI not compiled")
class QutritParityTests(unittest.TestCase):
    def test_all_81_syndrome_representatives_or_rejections(self):
        table = leaders()
        for s in itertools.product(range(3), repeat=4):
            key = "".join(map(str, s))
            p = run("qutrit", "lookup", key)
            values = mapped(p.stdout)
            if s not in table:
                self.assertNotEqual(0, p.returncode, key)
                self.assertEqual("NO_REPRESENTATIVE", values.get("status"), key)
                continue
            self.assertEqual(0, p.returncode, (key, p.stderr))
            self.assertEqual("FOUND", values.get("status"), key)
            x, z = table[s]
            self.assertEqual("".join(map(str, inv(x))), values["correction_x"], key)
            self.assertEqual("".join(map(str, inv(z))), values["correction_z"], key)

    def test_all_40_weight_one_errors_correct(self):
        for site in range(5):
            for x in range(3):
                for z in range(3):
                    if (x, z) == (0, 0):
                        continue
                    xx, zz = [0] * 5, [0] * 5
                    xx[site], zz[site] = x, z
                    p = run("qutrit", "decode", "".join(map(str, xx)), "".join(map(str, zz)))
                    self.assertEqual(0, p.returncode, (site, x, z, p.stderr))
                    data = mapped(p.stdout)
                    self.assertEqual("".join(map(str, syndrome(tuple(xx), tuple(zz)))),
                                     data["syndrome"])
                    self.assertEqual("CORRECTED", data["status"])
                    self.assertEqual("00000", data["residual_x"])
                    self.assertEqual("00000", data["residual_z"])

    def test_scalar_opt_exhaustive_domain(self):
        p = run("selftest", "qutrit")
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn("59049 scalar/OPT parity", p.stdout)
        self.assertEqual(p.stdout, run("selftest", "qutrit").stdout)

    def test_failure_and_input_rejection(self):
        for cmd in (
            ("qutrit", "decode", "99999", "00000"),
            ("qutrit", "decode", "0000", "00000"),
            ("qutrit", "lookup", "000"),
            ("qutrit", "lookup", "100x"),
            ("route", "0", "1", "2", "0", "1234", "1111", "1111"),
            ("route", "0", "1", "2", "0", "1111", "1111", "111"),
            ("route", "0", "1", "9", "0", "1111", "1111", "1111"),
        ):
            with self.subTest(cmd=cmd):
                self.assertNotEqual(0, run(*cmd).returncode)

    def test_bench_paths_equal_independent_expected_checksum(self):
        outputs = []
        for path in ("scalar", "opt"):
            p = run("benchmark", "qutrit", path)
            self.assertEqual(0, p.returncode, p.stderr)
            self.assertEqual({
                "workload": "59049", "path": path, "checksum": "33457"
            }, mapped(p.stdout))
            outputs.append(mapped(p.stdout)["checksum"])
        self.assertEqual(outputs[0], outputs[1])

    def test_zero_error(self):
        p = run("qutrit", "decode", "00000", "00000")
        self.assertEqual(0, p.returncode)
        self.assertEqual("CORRECTED", mapped(p.stdout)["status"])
        self.assertEqual("0000", mapped(p.stdout)["syndrome"])


@unittest.skipUnless(BINARY.is_file(), "native Ada CLI not compiled")
class RoutingTests(unittest.TestCase):
    def test_first_free_ordering(self):
        p = run("route", "1", "2", "0", "1", "0101", "0011", "1010")
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertEqual({
            "status": "ROUTED", "linefinder": "2",
            "selector_a": "3", "selector_b": "1",
            "selector_levels": "12", "connector": "01",
        }, mapped(p.stdout))
        self.assertEqual(p.stdout, run("route", "1", "2", "0", "1",
                                       "0101", "0011", "1010").stdout)

    def test_fail_closed_no_partial_output(self):
        for masks, expected in (
            (("0000", "1111", "1111"), "NO_LINEFINDER"),
            (("0111", "0000", "1111"), "NO_FIRST_TRUNK"),
            (("1111", "1111", "0000"), "NO_SECOND_TRUNK"),
        ):
            p = run("route", "1", "2", "0", "1", *masks)
            self.assertNotEqual(0, p.returncode)
            self.assertEqual({"status": expected}, mapped(p.stdout))

    def test_router_selftest(self):
        p = run("selftest", "route")
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn("PASS classical first-free routing", p.stdout)

    def test_first_free_is_independent_of_destination(self):
        for digits in itertools.product("012", repeat=4):
            p = run("route", *digits, "0101", "0010", "0001")
            self.assertEqual(0, p.returncode, (digits, p.stderr))
            result = mapped(p.stdout)
            self.assertEqual(("2", "3", "4"),
                             (result["linefinder"], result["selector_a"],
                              result["selector_b"]))


if __name__ == "__main__":
    unittest.main()
