# Independent QEC-ADA porting plan

## Phase 0 — Bootstrap (this PR)

- Byte-exact pinned QEC documentation mirror; explicit binary/data exclusions.
- Stable offline docs CLI, manifest verifier, machine-readable list.
- Minimal native GF(3) ring arithmetic, bounded syndrome demonstration.
- Separate GUI for document browsing and educational computation.
- CI compile/test baseline; no automatic web publication.

## Phase 1A — Fixed qutrit decoding and routing pilot (additive)

- Independently implement the cyclic [[5,1,3]]₃ stabilizer code and
  deterministic weight-one bounded syndrome lookup in native Ada.
- Preserve the scalar syndrome path; add immutable OPT one-site contributions
  with exhaustive 3^10 exact-equality gating, never heuristic equivalence.
- Introduce a bounded classical first-free selector pilot based on QEC's
  Strowger ordering without claiming its receipt or pulse protocol.
- Run independent oracle and native executable tests on CI.
- [Implementation scope and limitations](PHASE1A_DECODER_ROUTING.md).

## Phase 1B — Configurable code definitions and exact OPT binding

- Bound 1–5 qutrit sites, 1–4 commuting independent generators and an exact
  radius-one syndrome table to an immutable code snapshot.
- Reject duplicate/linearly dependent or noncommuting checks and ambiguous
  bounded error sets rather than inventing representative choices.
- Prove scalar and precomputed path parity across every effective Pauli input.
- Introduce and execute a separate, narrow SPARK GF(3) mathematical proof
  harness (28 checks proved; configurable decoder not proved).
- [Phase 1B contract](PHASE1B_CONFIGURABLE.md).

## Phase 1 — Algebraic correctness

Specify and independently implement GF(2), GF(3), GF(4) algebra.
The fixed GF(3) qutrit slice is an additive pilot; standalone GF(2) and
GF(4) implementations remain pending. GF(4)
requires an irreducible polynomial and must **not** be implemented as
integers modulo four. Compare exhaustive small cases with an independently
generated mathematical oracle.

## Phase 2 — Frozen decoder parity

Pin a specific source commit, identify narrow interfaces and immutable QEC
fixtures. Port one small decoder operation at a time. Validate syndrome,
representative selection, invalid-input rejection and byte-level outputs.
No incidental mutation of QEC's frozen baseline.

## Phase 1C — Classical Strowger replay (proposed)

- Use explicit immutable topology and source-bound initial state.
- Add canonical event streams, deterministic pulses, no hidden work,
  route/dark/check tone verification and independent receipt replay.
- See [Phase 1C proposal](PHASE1C_STROWGER_PLAN.md).
- No physical quantum-routing claim or automatic decoder replacement.

## Phase 1D — Sparse Spectral Observatory

- Native read-only Tanner directed-edge Hashimoto operator, SCC-aware
  recurrent-mode computation, IPR, EEEC and stable edge rankings.
- Exact finite graph/trace regression preserved and independent known
  eigenvalue fixtures added, including periodic/disconnected cases.
- Strict convergence reporting and no claim of universal floating-point
  bit identity or a full reducible-graph eigenvector.
- [Phase 1D implementation and limitations](PHASE1D_SPARSE_SPECTRAL.md).

## Phase 1E — Scaled spectral diagnosis and controlled BP failure tests

- Native read-only sparse observatory beyond the five-qutrit pilot;
  128×128 nodes and 2,048 edges with independent analytic eigenvalues.
- Controlled deterministic classical GF(2) min-sum decoding trials
  separate from the protected native GF(3) decoder.
- Prespecified graph-blocked holdout and honest AUROC/AP/negative outcomes;
  full source-bound trial corpus and offline replay.
- [Phase 1E methods, results and limitations](PHASE1E_SCALED_SPECTRAL_BP.md).

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
