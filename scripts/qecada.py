#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline QEC-ADA reference explorer and immutable snapshot checker."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import webbrowser
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "fixtures" / "qec_reference_manifest.json"


def inventory() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def reference_path(manifest: dict, name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("invalid reference path")
    return ROOT / manifest["mirror_root"] / Path(*path.parts)


def blob_sha1(contents: bytes) -> str:
    """Exact Git blob identity, including size prefix and NUL byte."""
    return hashlib.sha1(b"blob " + str(len(contents)).encode("ascii") + b"\x00" + contents).hexdigest()


def verify(manifest: dict) -> int:
    errors = []
    for item in manifest["files"]:
        try:
            path = reference_path(manifest, item["path"])
            if path.is_symlink() or not path.is_file():
                errors.append(f"{item['path']}: missing, symlink or not regular")
                continue
            raw = path.read_bytes()
            if len(raw) != item["size_bytes"] or blob_sha1(raw) != item["git_blob_sha1"]:
                errors.append(f"{item['path']}: size / Git blob identity mismatch")
        except (OSError, ValueError) as exc:
            errors.append(f"{item['path']}: {exc}")
    if errors:
        for error in errors:
            print("FAIL", error, file=sys.stderr)
        return 1
    print(f"PASS {len(manifest['files'])} source-identical files; "
          f"{len(manifest['excluded'])} recorded exclusions "
          f"({manifest['source_commit']})")
    return 0


def docs(manifest: dict, action: str, query: list[str], json_mode: bool) -> int:
    records = manifest["files"]
    if action == "show":
        if len(query) != 1:
            print("docs show requires one exact source-relative path", file=sys.stderr)
            return 2
        selected = next((x for x in records if x["path"] == query[0]), None)
        if selected is None:
            print("unknown source-relative document path", file=sys.stderr)
            return 2
        path = reference_path(manifest, selected["path"])
        if path.is_symlink() or not path.is_file():
            print("missing or non-regular document", file=sys.stderr)
            return 1
        raw = path.read_bytes()
        if blob_sha1(raw) != selected["git_blob_sha1"]:
            print("document identity mismatch", file=sys.stderr)
            return 1
        sys.stdout.buffer.write(raw)
        return 0
    terms = [part.lower() for part in query]
    if action == "search" and not terms:
        print("docs search requires at least one term", file=sys.stderr)
        return 2
    matching = [x for x in records if all(term in x["path"].lower() for term in terms)]
    if json_mode:
        print(json.dumps(matching, indent=2, sort_keys=True))
    else:
        for item in matching:
            print(item["path"])
        print(f"{len(matching)} document(s)", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline QEC-ADA CLI and docs tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="verify copied bytes against original Git blobs")
    sub.add_parser("status", help="show truthful implementation and reference status")
    docs_p = sub.add_parser("docs", help="list/search/read pinned QEC documents")
    docs_p.add_argument("action", choices=("list", "search", "show"))
    docs_p.add_argument("query", nargs="*")
    docs_p.add_argument("--json", action="store_true", help="machine-readable list/search")
    gui_p = sub.add_parser("gui", help="open universal offline browser GUI")
    gui_p.add_argument("--no-open", action="store_true", help="only print file URI")
    args = parser.parse_args()
    manifest = inventory()
    if args.command == "verify":
        return verify(manifest)
    if args.command == "docs":
        return docs(manifest, args.action, args.query, args.json)
    if args.command == "status":
        print(json.dumps({"project": "QEC-ADA", "stage": "GF3_PILOT",
                          "source_commit": manifest["source_commit"],
                          "mirrored_reference_files": len(manifest["files"]),
                          "excluded_reference_files": len(manifest["excluded"]),
                          "gnatprove_status": "NOT_RUN",
                          "python_decoder_equivalence": "NOT_TESTED",
                          "quantum_hardware_validation": "NOT_TESTED"},
                         indent=2, sort_keys=True))
        return 0
    if args.command == "gui":
        url = (ROOT / "gui" / "index.html").resolve().as_uri()
        print(url)
        if not args.no_open and not webbrowser.open(url):
            print("Browser was not opened; paste the URI into a browser.", file=sys.stderr)
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
