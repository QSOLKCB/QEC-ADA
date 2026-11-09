#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Independently validate QEC-ADA mirror against a pinned donor Git checkout.

The trusted donor *commit and tree* are constants in this implementation.
CI obtains those from QSOLKCB/QEC without executing donor code. Git ls-tree
and SHA-256 compare against donor bytes; modifying mirror+manifest cannot pass.
Integrity of this verifier/workflow still requires protected owner review.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import qecada


def git(repo: Path, *args: str) -> bytes:
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout


def source_entries(donor: Path) -> dict[str, tuple[str, int, str]]:
    result = {}
    for row in git(donor, "ls-tree", "-rlz", qecada.SOURCE_TREE).split(b"\x00"):
        if not row:
            continue
        details, filename = row.split(b"\t", 1)
        mode, kind, sha, size = details.decode("ascii").split()
        path = filename.decode("utf-8")
        qecada.checked_parts(path)
        if kind != "blob" or mode != "100644" or path in result:
            raise ValueError(f"unexpected donor entry mode/type/path: {path}")
        result[path] = (sha, int(size), mode)
    return result


def audit(donor: Path) -> None:
    manifest = qecada.inventory()
    qecada.checked_headers(manifest)
    if qecada.verify(manifest):
        raise ValueError("local mirror validation failed")

    donor = donor.resolve(strict=True)
    if git(donor, "rev-parse", "HEAD").decode("ascii").strip() != qecada.SOURCE_COMMIT:
        raise ValueError("donor HEAD does not match pinned commit")
    if git(donor, "rev-parse", "HEAD:docs").decode("ascii").strip() != qecada.SOURCE_TREE:
        raise ValueError("donor docs tree does not match pinned tree")

    source = source_entries(donor)
    if len(source) != 105:
        raise ValueError("unexpected donor file count")
    mirror_entries = manifest["files"]
    excluded_entries = manifest["excluded"]
    expected = {item["path"] for item in mirror_entries + excluded_entries}
    if set(source) != expected:
        raise ValueError("manifest+exclusions do not enumerate pinned donor tree")
    for item in mirror_entries + excluded_entries:
        sha, size, _ = source[item["path"]]
        if sha != item["git_blob_sha1"] or size != item["size_bytes"]:
            raise ValueError(f"donor Git identity mismatch: {item['path']}")

    hashes = qecada.digest_table(manifest)
    for item in mirror_entries:
        name = item["path"]
        source_path = donor / "docs" / name
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError(f"missing / unsafe donor file: {name}")
        donor_bytes = source_path.read_bytes()
        target_bytes = qecada.reference_path(manifest, name).read_bytes()
        original = hashlib.sha256(donor_bytes).hexdigest()
        if original != hashes[name] or target_bytes != donor_bytes:
            raise ValueError(f"SHA-256 / donor content mismatch: {name}")
    print(f"PASS independent donor tree and SHA-256 parity for "
          f"{len(mirror_entries)} mirrored files + {len(excluded_entries)} exclusions")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify against pinned donor checkout")
    parser.add_argument("--donor", required=True, type=Path)
    args = parser.parse_args()
    try:
        audit(args.donor)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL independent provenance check: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
