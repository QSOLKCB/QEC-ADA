# Pinned QEC reference snapshot

- Donor: `QSOLKCB/QEC`
- Pinned source commit: `27bbc798c4e38138ca5b0fff70b15c3271a1917d`
- Donor docs tree: `fbbe3123f79964a26176539f47a6c68c68280553`
- Original root: `docs/`
- Mirrored root: `docs/reference/qec/`
- Included: 103 byte-identical files (92 Markdown, 11 other text/lab files).
- Excluded (present in donor but **not** copied):
  `releases/release_history.json` (2,866,122 bytes) and
  `roadmap/QEC_DETERMINISTIC_SWITCHING_MIND_MAP.jpg` (12,524 bytes).

## Two different integrity checks

**Local self-consistency:**
`uv run --no-project python scripts/qecada.py verify`
checks the local SHA-1 Git blob IDs, independently recorded SHA-256 digests,
expected membership, paths and file types. This does **not** independently
establish source provenance because both inventories live in this repository.

**Pinned donor comparison (CI security gate):**
`uv run --no-project python scripts/verify_donor.py --donor .donor-qec`
compares against a separate checkout of the original QEC repository at the
hard-coded commit/tree shown above. It checks `git ls-tree` path/mode/size/blob
IDs for **all 105 donor files** (including the two exclusions), then compares
actual source bytes against mirrored bytes and their recorded SHA-256 digests
for **all 103 included files**. CI never executes donor files.

The combined check detects modifications to mirror + both manifests made
without modifying the independent donor source. It is **not** a guarantee
against an attacker who can alter the verifier/workflow and approve that
change. For meaningful protection, require owner review on critical paths
using `.github/CODEOWNERS` and configure branch protection to enforce
that policy. CODEOWNERS by itself does not enforce anything.

## Historical interpretation

Reference documents describe the original Python QEC project, **not**
functionality implemented in QEC-ADA. Their links and text remain byte-exact
to their donor origin; paths may refer outside this snapshot. Do not mutate
the mirror to fix old documentation. New interpretations go in `docs/`.

Historical HTML and JS labs are preserved as source but displayed as **inert
text** by the offline GUI. Opening their underlying files directly in a
browser is outside the GUI's safety boundary.

Never silently track moving donor `main`. A refreshed snapshot must pin a
new commit and pass both identity and source-byte comparisons.
