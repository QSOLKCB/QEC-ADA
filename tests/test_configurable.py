# SPDX-License-Identifier: MPL-2.0
"""Independent finite-domain oracle for QEC-ADA configurable GF(3) decoder.

All arithmetic uses Python integers modulo 3. No source from QEC or Ada is
imported. This validates native behavior and rejection across distinct codes.
"""
from __future__ import annotations

import itertools
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build/bin" / ("qec_ada.exe" if os.name == "nt" else "qec_ada")


def run(mode, n, x, z, *rows):
    return subprocess.run(
        [str(BIN), "config", mode, str(n), x, z, *rows],
        text=True, capture_output=True, check=False, timeout=15,
    )


def lines(text):
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def rows_cyclic():
    result = []
    for shift in range(4):
        x = [0] * 5
        z = [0] * 5
        for site in (0, 3):
            x[(site + shift) % 5] = 1
        for site in (1, 2):
            z[(site + shift) % 5] = 1
        result.append("".join(map(str, x + z)))
    return tuple(result)


def syndrome(n, rows, x, z):
    return tuple(
        (sum(int(row[i]) * z[i] for i in range(n)) -
         sum(int(row[n + i]) * x[i] for i in range(n))) % 3
        for row in rows
    )


def add(a, b):
    return tuple((x + y) % 3 for x, y in zip(a, b))


def neg(a):
    return tuple(-x % 3 for x in a)


def stabilizers(n, rows):
    """Independent exhaustive reference set for a small bounded code."""
    answer = set()
    for powers in itertools.product(range(3), repeat=len(rows)):
        data = [0] * (2 * n)
        for factor, row in zip(powers, rows):
            data = [(value + factor * int(symbol)) % 3
                    for value, symbol in zip(data, row)]
        answer.add(tuple(data))
    return answer


def representatives(n, rows):
    span = stabilizers(n, rows)
    zero = (0,) * n
    table = {syndrome(n, rows, zero, zero): (zero, zero)}
    for site in range(n):
        for x in range(3):
            for z in range(3):
                if x == 0 and z == 0:
                    continue
                ex, ez = [0] * n, [0] * n
                ex[site], ez[site] = x, z
                pair = (tuple(ex), tuple(ez))
                s = syndrome(n, rows, pair[0], pair[1])
                if s in table:
                    old_x, old_z = table[s]
                    difference = add(pair[0] + pair[1],
                                     neg(old_x + old_z))
                    if difference not in span:
                        return None
                else:
                    table[s] = pair
    return table


def encode(values):
    return "".join(map(str, values))


@unittest.skipUnless(BIN.is_file(), "GNAT binary not built")
class ConfiguredDecoderTests(unittest.TestCase):
    def test_cyclic_matches_original_40_errors(self):
        rows = rows_cyclic()
        table = representatives(5, rows)
        assert table and len(table) == 41
        for site in range(5):
            for x in range(3):
                for z in range(3):
                    if (x, z) == (0, 0):
                        continue
                    ex, ez = [0] * 5, [0] * 5
                    ex[site], ez[site] = x, z
                    p = run("decode", 5, encode(ex), encode(ez), *rows)
                    self.assertEqual(0, p.returncode, (site, x, z, p.stderr))
                    data = lines(p.stdout)
                    self.assertEqual("CORRECTED", data.get("status"))
                    self.assertEqual("41", data.get("leaders"))
                    self.assertEqual(encode(syndrome(5, rows, ex, ez)),
                                     data.get("syndrome"))
                    self.assertEqual(data["syndrome"], data["opt_syndrome"])
                    self.assertEqual("00000", data.get("residual_x"))
                    self.assertEqual("00000", data.get("residual_z"))
                    self.assertEqual(encode(neg(tuple(ex))), data.get("correction_x"))
                    self.assertEqual(encode(neg(tuple(ez))), data.get("correction_z"))

    def test_product_state_all_81_error_vectors(self):
        rows = ("0010", "0001")  # n=2; independent commuting Z stabilizers
        table = representatives(2, rows)
        self.assertEqual(9, len(table))
        for symbols in itertools.product(range(3), repeat=4):
            ex, ez = symbols[:2], symbols[2:]
            p = run("decode", 2, encode(ex), encode(ez), *rows)
            self.assertEqual(0, p.returncode, (symbols, p.stderr))
            data = lines(p.stdout)
            self.assertEqual("9", data["leaders"])
            self.assertEqual("CORRECTED", data["status"])
            self.assertEqual(encode(syndrome(2, rows, ex, ez)), data["syndrome"])
            self.assertEqual(data["syndrome"], data["opt_syndrome"])
            correction_x = tuple(map(int, data["correction_x"]))
            correction_z = tuple(map(int, data["correction_z"]))
            self.assertEqual(
                encode(neg(table[syndrome(2, rows, ex, ez)][0])), data["correction_x"])
            self.assertEqual(
                encode(neg(table[syndrome(2, rows, ex, ez)][1])), data["correction_z"])
            residual = add(ex + ez, correction_x + correction_z)
            self.assertIn(residual, stabilizers(2, rows))

    def test_single_qutrit_degenerate_stabilizer(self):
        rows = ("01",)
        table = representatives(1, rows)
        self.assertEqual(3, len(table))
        for x, z in itertools.product(range(3), repeat=2):
            p = run("decode", 1, str(x), str(z), *rows)
            self.assertEqual(0, p.returncode, (x, z, p.stderr))
            data = lines(p.stdout)
            self.assertEqual("3", data["leaders"])
            self.assertEqual("CORRECTED", data["status"])

    def test_invalid_generator_sets_fail_closed(self):
        cases = (
            # More generators than sites (no hidden truncation).
            (1, "0", "0", ("01", "01"), "TOO_MANY_GENERATORS"),
            # Independent noncommuting X_1 and Z_1.
            (2, "00", "00", ("1000", "0010"),
             "NONCOMMUTING_GENERATORS"),
            # Rank deficient.
            (2, "00", "00", ("0010", "0010"),
             "DEPENDENT_GENERATORS"),
            # Independent but insufficient quantum distance for radius 1.
            (2, "00", "00", ("0011",),
             "AMBIGUOUS_BOUNDED_SET"),
        )
        for n, x, z, rows, wanted in cases:
            with self.subTest(rows=rows):
                p = run("decode", n, x, z, *rows)
                self.assertNotEqual(0, p.returncode)
                self.assertEqual({"status": wanted}, lines(p.stdout))

    def test_bad_cli_lengths_and_symbols(self):
        for args in (
            ("config", "decode", "6", "0", "0", "01"),
            ("config", "decode", "2", "0", "00", "0010", "0001"),
            ("config", "decode", "2", "00", "00", "0090"),
            ("config", "decode", "2", "00", "00", "001"),
            ("config", "decode", "2", "00", "00"),
            ("config", "decode", "2", "00", "00", "0010", "0001",
             "0010", "0001", "0010"),
        ):
            with self.subTest(args=args):
                p = subprocess.run([str(BIN), *args], text=True,
                                   capture_output=True, timeout=15)
                self.assertNotEqual(0, p.returncode)

    def test_repeated_code_contexts_preserve_state(self):
        contexts = (
            (5, "10000", "00000", rows_cyclic()),
            (2, "10", "01", ("0010", "0001")),
            (1, "1", "2", ("01",)),
            (5, "10000", "00000", rows_cyclic()),
        )
        values = [lines(run("decode", n, x, z, *rows).stdout)
                  for n, x, z, rows in contexts]
        self.assertEqual(values[0], values[3])
        for value in values:
            self.assertEqual(value["syndrome"], value["opt_syndrome"])

    def test_config_selftest(self):
        p = subprocess.run([str(BIN), "selftest", "config"],
                           text=True, capture_output=True, timeout=15)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn("PASS CONFIGURABLE", p.stdout)


if __name__ == "__main__":
    unittest.main()
