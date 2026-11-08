# SPDX-License-Identifier: MPL-2.0
"""Python stdlib checks; Ada executable is tested in CI after GNAT build."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import qecada


class ReferenceTests(unittest.TestCase):
    def test_manifest_paths_are_unique(self):
        m = qecada.inventory()
        paths = [item["path"] for item in m["files"]]
        self.assertEqual(103, len(paths))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(2, len(m["excluded"]))

    def test_archive_has_exact_git_blob_identity(self):
        self.assertEqual(0, qecada.verify(qecada.inventory()))

    def test_no_path_traversal(self):
        with self.assertRaises(ValueError):
            qecada.reference_path(qecada.inventory(), "../../etc/passwd")

    def test_known_gf3_vectors(self):
        fixture = json.loads((ROOT / "fixtures" / "gf3_vectors.json").read_text())
        for row in fixture["add"]:
            self.assertEqual(row["out"], (row["a"] + row["b"]) % 3)
        for row in fixture["multiply"]:
            self.assertEqual(row["out"], (row["a"] * row["b"]) % 3)
        for row in fixture["dot"]:
            self.assertEqual(row["out"], sum(a * b for a, b in zip(row["a"], row["b"])) % 3)

    def test_gui_is_self_contained(self):
        html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("catalog.js", html)
        self.assertIn("app.js", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    @unittest.skipUnless((ROOT / "build/bin/qec_ada").exists() or
                         (ROOT / "build/bin/qec_ada.exe").exists(), "GNAT binary not built")
    def test_compiled_native_cli_vectors(self):
        binary = ROOT / "build/bin" / ("qec_ada.exe" if os.name == "nt" else "qec_ada")
        vectors = json.loads((ROOT / "fixtures/gf3_vectors.json").read_text())
        for row in vectors["add"]:
            p = subprocess.run([str(binary), "gf3", "add", str(row["a"]), str(row["b"])],
                               check=True, text=True, capture_output=True)
            self.assertEqual(str(row["out"]), p.stdout.strip())
        for row in vectors["multiply"]:
            p = subprocess.run([str(binary), "gf3", "mul", str(row["a"]), str(row["b"])],
                               check=True, text=True, capture_output=True)
            self.assertEqual(str(row["out"]), p.stdout.strip())
        for row in vectors["dot"]:
            p = subprocess.run([str(binary), "syndrome", *map(str, row["a"] + row["b"])],
                               check=True, text=True, capture_output=True)
            self.assertEqual(str(row["out"]), p.stdout.strip())


if __name__ == "__main__":
    unittest.main()
