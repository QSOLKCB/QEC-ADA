# Independent QEC-ADA porting plan

## Phase 0 — Bootstrap (this PR)

- Byte-exact pinned QEC documentation mirror; explicit binary/data exclusions.
- Stable offline docs CLI, manifest verifier, machine-readable list.
- Minimal native GF(3) ring arithmetic, bounded syndrome demonstration.
- Separate GUI for document browsing and educational computation.
- CI compile/test baseline; no automatic web publication.

## Phase 1 — Algebraic correctness

Specify and independently implement GF(2), GF(3), GF(4) algebra. GF(4)
requires an irreducible polynomial and must **not** be implemented as
integers modulo four. Compare exhaustive small cases with an independently
generated mathematical oracle.

## Phase 2 — Frozen decoder parity

Pin a specific source commit, identify narrow interfaces and immutable QEC
fixtures. Port one small decoder operation at a time. Validate syndrome,
representative selection, invalid-input rejection and byte-level outputs.
No incidental mutation of QEC's frozen baseline.

## Phase 3 — Formal proofs

Use GNATprove on explicit SPARK proof obligations for finite ranges,
bounds, totality, determinism and relevant algebraic identities. Publish
tool versions, proof results and remaining unproved obligations.
**Annotations alone do not count as proof.**

## Phase 4 — Evidence and CLI

Version canonical schema, rejection paths, SHA-256 receipts and provenance
separately. Cross-language outputs must agree under an explicit equivalence
definition; differences must be accounted for, not erased by normalisation.

## Phase 5 — Cross-platform packaging

Package Ada CLI and optional offline GUI separately for Linux, Windows and
macOS. All functionality must remain available from a terminal without GUI.
No container or hosted service needed.

## Out of scope at bootstrap

Quantum hardware thresholds, physical protection, scientific benchmarks,
feature completeness, official replication and verified production-grade
decoders are not claimed.
