# Fixtures and provenance

- `qec_reference_manifest.json`: pinned source path/size/Git SHA-1 identity
  of copied QEC documentation and explicit exclusions.
- `gf3_vectors.json`: small, independently reviewable finite-field vectors.

Fixture changes require explicit rationale and versioning; never rewrite
historical QEC receipts to match new Ada code. Verify the docs snapshot via
`uv run --no-project python scripts/qecada.py verify`.
