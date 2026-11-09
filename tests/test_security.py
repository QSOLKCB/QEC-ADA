# SPDX-License-Identifier: MPL-2.0
"""Adversarial tests for local archive handling and configured CI trust."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import qecada


class SecurityTests(unittest.TestCase):
    def test_untrusted_manifest_cannot_redirect_mirror_root(self):
        manifest = qecada.inventory()
        for root in ("../../", "/etc", "docs/reference/qec/../../", "docs/reference"):
            altered = copy.deepcopy(manifest)
            altered["mirror_root"] = root
            with self.subTest(root=root), self.assertRaises(ValueError):
                qecada.reference_path(altered, "README.md")

    def test_paths_are_strictly_canonical(self):
        m = qecada.inventory()
        for name in ("../file", "dir/../file", "/etc/passwd", "foo//bar",
                     "foo/./bar", "foo\\bar", "", "foo\x00bar"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                qecada.reference_path(m, name)

    def test_symlinked_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            (root / "docs" / "reference").mkdir(parents=True)
            (root / "docs" / "reference" / "qec").symlink_to(real, target_is_directory=True)
            with patch.object(qecada, "ROOT", root), self.assertRaises(ValueError):
                qecada.reference_path(qecada.inventory(), "README.md")

    def test_pinned_metadata_and_checksums_are_complete(self):
        m = qecada.inventory()
        qecada.checked_headers(m)
        sums = qecada.digest_table(m)
        self.assertEqual(103, len(sums))
        self.assertEqual({x["path"] for x in m["files"]}, set(sums))
        self.assertEqual(0, qecada.verify(m))

    def test_missing_and_changed_sha256_are_rejected(self):
        m = qecada.inventory()
        sha = qecada.sha_inventory()
        sha["files"][0]["sha256"] = "0" * 64
        with patch.object(qecada, "sha_inventory", return_value=sha):
            self.assertEqual(1, qecada.verify(m))
        sha["files"].pop()
        with patch.object(qecada, "sha_inventory", return_value=sha):
            with self.assertRaises(ValueError):
                qecada.digest_table(m)

    def test_archive_browser_uses_inert_source(self):
        html = (ROOT / "gui/index.html").read_text(encoding="utf-8")
        app = (ROOT / "gui/app.js").read_text(encoding="utf-8")
        self.assertIn("connect-src 'none'", html)
        self.assertIn('src="archived-text.js"', html)
        self.assertIn(r"/\.(html|js)$/i.test(item.path)", app)
        self.assertIn("previewText.textContent = content", app)
        self.assertNotIn("innerHTML", app)
        self.assertNotIn("eval(", app)
        packed = (ROOT / "gui/archived-text.js").read_text(encoding="utf-8")
        header = "window.QEC_ADA_ARCHIVE_TEXT = Object.freeze("
        self.assertIn(header, packed)
        content = packed.split(header, 1)[1].rsplit(");", 1)[0]
        archive = json.loads(content)
        self.assertEqual({
            "labs/acoustic-evidence.html",
            "labs/acoustic-evidence.js",
            "labs/digital/index.html",
            "labs/packet/index.html",
        }, set(archive))
        for path, text in archive.items():
            self.assertEqual(
                (ROOT / "docs/reference/qec" / path).read_text(encoding="utf-8"),
                text,
            )

    def test_ci_pins_checkout_and_prevents_credential_persistence(self):
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertEqual(2, workflow.count(
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
        ))
        self.assertEqual(2, workflow.count("persist-credentials: false"))
        self.assertIn("scripts/verify_donor.py --donor .donor-qec", workflow)
        self.assertIn("timeout-minutes: 20", workflow)
        self.assertIn("ref: 27bbc798c4e38138ca5b0fff70b15c3271a1917d", workflow)


if __name__ == "__main__":
    unittest.main()
