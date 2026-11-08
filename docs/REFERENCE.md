# Pinned QEC reference snapshot

- Donor: `QSOLKCB/QEC`
- Pinned source commit: `27bbc798c4e38138ca5b0fff70b15c3271a1917d`
- Docs tree: `fbbe3123f79964a26176539f47a6c68c68280553`
- Original roots: `docs/`
- Mirrored root: `docs/reference/qec/`
- Preserved: 103 files with exact matching Git blob SHA-1 values (92 Markdown and
  11 supporting text/lab/receipt files).
- Excluded: `releases/release_history.json` (2,866,122 bytes, large archival
  dataset) and `roadmap/QEC_DETERMINISTIC_SWITCHING_MIND_MAP.jpg` (binary JPEG).
  Both remain available from the pinned original repository; they have **not**
  been reconstructed, replaced or declared present.

The full inventory is in
[`fixtures/qec_reference_manifest.json`](../fixtures/qec_reference_manifest.json).
Every included file records its original path, byte size and Git blob SHA-1.
The `verify` command checks all copied bytes using Git's exact blob hashing.

### Important interpretation

The mirror is historical **reference data**, not an Ada/SPARK implementation.
Paths in mirrored Markdown may refer to the donor repository root, historical
CI, Python scripts or archived files. These links are not rewritten, because
doing so would break exact byte identity. Use the pinned original repository
to resolve any references not contained in this snapshot.

### Rebuild or audit

~~~sh
uv run --no-project python scripts/qecada.py verify
uv run --no-project python scripts/qecada.py docs list --json
~~~

Never silently update the mirror to a moving `main`. A future refresh must
identify a new donor commit and produce a new checked manifest.
