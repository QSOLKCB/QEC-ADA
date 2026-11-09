#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Offline QEC-ADA reference explorer and local byte-integrity checker.

Local manifest verification is NOT a donor trust anchor. The separate
verify_donor.py command checks a pinned independent Git checkout in CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import webbrowser
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "fixtures" / "qec_reference_manifest.json"
SHA256_PATH = ROOT / "fixtures" / "qec_reference_sha256.json"
SOURCE_COMMIT = "27bbc798c4e38138ca5b0fff70b15c3271a1917d"
SOURCE_TREE = "fbbe3123f79964a26176539f47a6c68c68280553"
MIRROR_ROOT = "docs/reference/qec"
EXCLUDED = frozenset({
    "releases/release_history.json",
    "roadmap/QEC_DETERMINISTIC_SWITCHING_MIND_MAP.jpg",
})


def inventory() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def sha_inventory() -> dict:
    return json.loads(SHA256_PATH.read_text(encoding="utf-8"))


def checked_parts(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("invalid reference path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or str(path) != name:
        raise ValueError("invalid reference path")
    return path.parts


def reference_root(manifest: dict) -> Path:
    if manifest.get("mirror_root") != MIRROR_ROOT:
        raise ValueError("mirror_root must be the pinned repository-local directory")
    repo = ROOT.resolve(strict=True)
    path = ROOT
    for part in ("docs", "reference", "qec"):
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink in mirror root")
    root = path.resolve(strict=True)
    if not root.is_dir() or not root.is_relative_to(repo):
        raise ValueError("mirror root escapes repository")
    return root


def reference_path(manifest: dict, name: str) -> Path:
    root = reference_root(manifest)
    current = root
    for component in checked_parts(name):
        current = current / component
        if current.is_symlink():
            raise ValueError("symlink in reference path")
    if not current.resolve(strict=False).is_relative_to(root):
        raise ValueError("reference path escapes mirror")
    return current


def blob_sha1(contents: bytes) -> str:
    """Exact Git blob identity, including size prefix and NUL byte."""
    return hashlib.sha1(
        b"blob " + str(len(contents)).encode("ascii") + b"\x00" + contents
    ).hexdigest()


def digest_table(manifest: dict) -> dict[str, str]:
    digest = sha_inventory()
    if (digest.get("schema_version") != 1
            or digest.get("algorithm") != "SHA-256"
            or digest.get("source_commit") != SOURCE_COMMIT
            or digest.get("mirror_root") != MIRROR_ROOT):
        raise ValueError("SHA-256 inventory header mismatch")
    records = digest.get("files")
    if not isinstance(records, list):
        raise ValueError("invalid SHA-256 records")
    table: dict[str, str] = {}
    for entry in records:
        path = entry["path"]
        value = entry["sha256"]
        checked_parts(path)
        if path in table or not isinstance(value, str) or len(value) != 64:
            raise ValueError("duplicate or invalid SHA-256 entry")
        if any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("invalid SHA-256 hex")
        table[path] = value
    paths = [item["path"] for item in manifest["files"]]
    if len(paths) != len(set(paths)) or set(table) != set(paths):
        raise ValueError("SHA-256 coverage / manifest membership mismatch")
    return table


def checked_headers(manifest: dict) -> None:
    if (manifest.get("schema_version") != 1
            or manifest.get("source_repository") != "QSOLKCB/QEC"
            or manifest.get("source_commit") != SOURCE_COMMIT
            or manifest.get("source_docs_tree") != SOURCE_TREE
            or manifest.get("mirror_root") != MIRROR_ROOT):
        raise ValueError("donor identity or mirror directory mismatch")
    files, exclusions = manifest.get("files"), manifest.get("excluded")
    if not isinstance(files, list) or not isinstance(exclusions, list):
        raise ValueError("invalid manifest arrays")
    if len(files) != 103 or len(exclusions) != 2:
        raise ValueError("unexpected manifest cardinality")
    paths = [item["path"] for item in files]
    if len(set(paths)) != 103:
        raise ValueError("duplicate manifest file")
    for path in paths:
        checked_parts(path)
    omitted = [item["path"] for item in exclusions]
    if len(set(omitted)) != 2 or set(omitted) != EXCLUDED:
        raise ValueError("unexpected excluded paths")
    for path in omitted:
        checked_parts(path)


def verify(manifest: dict) -> int:
    """Self-consistency only. Independent donor verification is separate."""
    try:
        checked_headers(manifest)
        root = reference_root(manifest)
        digests = digest_table(manifest)
        actual = set()
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"symlink within mirror: {path}")
            if path.is_file():
                actual.add(path.relative_to(root).as_posix())
        expected = {entry["path"] for entry in manifest["files"]}
        if actual != expected:
            raise ValueError(f"mirror membership differs: missing={sorted(expected - actual)}, "
                             f"extra={sorted(actual - expected)}")
        for item in manifest["files"]:
            path = reference_path(manifest, item["path"])
            if not path.is_file():
                raise ValueError(f"nonregular reference: {item['path']}")
            raw = path.read_bytes()
            if len(raw) != item["size_bytes"] or blob_sha1(raw) != item["git_blob_sha1"]:
                raise ValueError(f"Git blob mismatch: {item['path']}")
            if hashlib.sha256(raw).hexdigest() != digests[item["path"]]:
                raise ValueError(f"SHA-256 mismatch: {item['path']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {len(manifest['files'])} local SHA-1/SHA-256 checks "
          f"({len(manifest['excluded'])} excluded); donor independence NOT checked")
    return 0


def docs(manifest: dict, action: str, query: list[str], json_mode: bool) -> int:
    records = manifest["files"]
    if action == "show":
        if len(query) != 1:
            print("docs show requires one exact source-relative path", file=sys.stderr)
            return 2
        selected = next((item for item in records if item["path"] == query[0]), None)
        if selected is None:
            print("unknown source-relative document path", file=sys.stderr)
            return 2
        try:
            checked_headers(manifest)
            table = digest_table(manifest)
            path = reference_path(manifest, selected["path"])
            if not path.is_file() or path.is_symlink():
                raise ValueError("missing or nonregular document")
            raw = path.read_bytes()
            if (len(raw) != selected["size_bytes"]
                    or blob_sha1(raw) != selected["git_blob_sha1"]
                    or hashlib.sha256(raw).hexdigest() != table[selected["path"]]):
                raise ValueError("document identity mismatch")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        sys.stdout.buffer.write(raw)
        return 0
    terms = [part.lower() for part in query]
    if action == "search" and not terms:
        print("docs search requires at least one term", file=sys.stderr)
        return 2
    matching = [item for item in records if all(term in item["path"].lower() for term in terms)]
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
    sub.add_parser("verify", help="check local mirror against two manifests")
    sub.add_parser("status", help="show implementation and reference status")
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
                          "source_commit": SOURCE_COMMIT,
                          "mirrored_reference_files": len(manifest["files"]),
                          "excluded_reference_files": len(manifest["excluded"]),
                          "local_digest_verification": "AVAILABLE",
                          "independent_donor_verification": "CI_ONLY",
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
