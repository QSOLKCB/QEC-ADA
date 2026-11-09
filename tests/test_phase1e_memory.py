# SPDX-License-Identifier: MPL-2.0
"""Regression: Linux native VmHWM must exclude Python parent's memory.

The conventional wait4/getrusage RUSAGE_CHILDREN peak is deliberately NOT
used: it inherits the parent's pre-exec high-water mark on Linux.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase1e_memory as measurement
from phase1e_reference import canonical_graph

BIN = ROOT / "build/bin/qec_scale"


@unittest.skipUnless(sys.platform == "linux" and BIN.is_file(),
                     "native Linux Ada executable is required")
class NativeRSSMeasurementTests(unittest.TestCase):
    def test_default_protocol_remains_unchanged_and_opt_in_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.txt"
            path.write_bytes(canonical_graph(
                2, 2, [(1, 1), (1, 2), (2, 1), (2, 2)]))
            plain = subprocess.run(
                [str(BIN), "inspect", str(path)], text=True,
                capture_output=True, timeout=10, check=True)
            measured = subprocess.run(
                [str(BIN), "inspect", str(path), "--native-rss"],
                text=True, capture_output=True, timeout=10, check=True)
            self.assertNotIn("native_post_exec_peak_rss_kib_linux=", plain.stdout)
            lines = measured.stdout.splitlines()
            values = [line for line in lines
                      if line.startswith("native_post_exec_peak_rss_kib_linux=")]
            self.assertEqual(1, len(values))
            self.assertEqual(plain.stdout.splitlines(), [
                line for line in lines if not line.startswith(
                    "native_post_exec_peak_rss_kib_linux=")])
            self.assertGreater(int(values[0].split("=", 1)[1]), 0)

    def test_memory_report_is_executable_owned_and_v2(self):
        report = measurement.run(2, 2)
        self.assertEqual("qec-ada.phase1e.memory-observation.v2",
                         report["schema"])
        self.assertEqual(
            "linux_proc_self_status_VmHWM_read_inside_Ada_after_exec",
            report["rss_measurement_source"])
        self.assertNotIn("native_peak_rss_kib_linux", report)
        self.assertGreater(report["native_post_exec_peak_rss_kib_linux"], 0)
        self.assertEqual(8, report["directed_edges"])
        self.assertAlmostEqual(1.0, report["observed_rho"], places=9)

    def test_large_python_parent_rss_does_not_inflate_native_peak(self):
        before = measurement.run(2, 2)[
            "native_post_exec_peak_rss_kib_linux"]
        # Touch every page to guarantee that 80 MiB enters parent RSS.
        pressure = bytearray(80 * 1024 * 1024)
        for offset in range(0, len(pressure), 4096):
            pressure[offset] = 1
        try:
            after = measurement.run(2, 2)[
                "native_post_exec_peak_rss_kib_linux"]
        finally:
            del pressure
        # Runtime/linker fluctuations are allowed, an inherited 80 MiB
        # parent footprint is not. This checks the exact reviewer concern.
        self.assertLess(after, before + 16 * 1024)
        self.assertLess(after, 80 * 1024)

    def test_missing_native_metric_fails_closed(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="status=CONVERGED_NUMERIC\nspectral_radius=1.0\n"
                   "directed_edges=8\n",
            stderr="",
        )
        with patch.object(measurement.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(ValueError, "post-exec VmHWM"):
                measurement.run(2, 2)

    def test_invalid_report_flag_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.txt"
            path.write_bytes(canonical_graph(
                2, 2, [(1, 1), (1, 2), (2, 1), (2, 2)]))
            result = subprocess.run(
                [str(BIN), "inspect", str(path), "--native-rss-invalid"],
                text=True, capture_output=True, timeout=10,
            )
            self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
