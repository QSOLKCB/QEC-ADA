# QEC-ADA repository rules

## Scope

This is a new Ada/SPARK project, not the Python QEC repository. Make scoped
changes on a branch and draft PR; do not merge, tag, publish or deploy without
owner approval. Prefer local/offline execution, no Docker, npm or cloud runtime.

## Source of truth

- `codes/`, `decode/`, `invariants/`: authoritative native source.
- `research/`: prospective work and non-executable design notes.
- `fixtures/`: checked test vectors and pinned source inventory.
- `docs/`: QEC-ADA working documentation.
- `docs/reference/qec/`: **verbatim historical QEC docs; do not edit**.
- `gui/`: offline browse/search and educational finite-field demos only.
- `scripts/qecada.py`: Python-stdlib documentation and integrity tooling.

Do not edit files in the verbatim mirror, even to fix links or references. New
Ada interpretations and corrections go in `docs/` and `research/`.

## Evidence gates

- A SPARK pragma or contract is NOT a discharged proof.
- A JavaScript/GF(3) browser result is NOT an authoritative decoder result.
- Every parity or behavioural equivalence claim needs pinned fixtures and
  independent implementation comparisons.
- Preserve original ordered bytes, fixture identities, source SHAs, invalid
  input handling and deterministic ordering.
- Never mutate or claim to replace the frozen QEC decoder baseline.
- Keep build, runtime, test, benchmark, proof and GUI evidence distinct.

## Validation

~~~sh
uv run --no-project python scripts/qecada.py verify
uv run --no-project python -m unittest discover -s tests -v
gprbuild -p -P qec_ada.gpr
./build/bin/qec_ada gf3 add 1 2
./build/bin/qec_ada syndrome 1 2 1 2 0 1
~~~

GNATprove, if installed, is a separate proof gate. Report success, failures
and environment restrictions precisely; never imply proof or GPU execution
when only static or Python checks have run.

## Provenance and archive-content review

Protect changes to the reference manifest, SHA-256 inventory, the two
verification scripts, imported reference files, the GUI source viewer and
GitHub workflows. CI checks a separate QEC donor checkout at a fixed commit;
its result is stronger than local manifest consistency, but a malicious
workflow edit can bypass either check without enforced owner review.
Use CODEOWNERS and branch protection requiring owner approvals.

Never link archived HTML/JS as runnable pages from the GUI. Render copies as
inert escaped text, with a restrictive CSP and no outbound connections.

## Phase 1B extra boundary

The configurable decoder (`codes/qec_configurable.*`) must validate
commuting, independent stabilizers before constructing radius-one
representatives. Preserve QEC's deterministic first-representative ordering
and accept collisions only for stabilizer-equivalent errors. Each OPT plan
must be bound to a full immutable code definition; do not add global caches
or hash-only identity. Keep the Phase 1A implementation as an oracle and do
not weaken pinned-donor provenance checks.

A GNATprove proof applies only to the actual declarations it analyzes.
Do not report the configurable decoder as formally proved unless its own
obligations have been discharged and independently checked.

## Phase 1C observational SPECTRAL and receipt boundaries

Never feed Tanner cycle heat or NB moments into decoder correction
authority. Never rename an exact non-backtracking fourth moment as a
spectral radius/eigenpair or attribute a graph sonification to hardware.
The original WAV renderer is 48kHz signed 24-bit linear PCM.

The Strowger receipt validator must reconstruct route and events from
complete request inputs instead of blessing a self-consistently rehashed
forgery. Its Python implementation is a separate validation boundary;
the original QEC Strowger schema is not compatible by default.

## Phase 1D sparse NB invariants

The spectral observer is read-only: no decoder mutation, hidden RNG,
dense production NB matrix, arbitrary eigenvector from a nilpotent
operator, or elevated physical-QEC claims. Verify strongly connected
components and periodic cycles before treating a power estimate as a
dominant radius. Record numerical convergence and local recurrent
mode support. A low-order moment is not an eigenvalue; a component
eigenvector may not be a full reducible-operator eigenvector.
Independent tiny-graph oracles must remain separate and CI-enforced.

## Phase 1E evidence and inference limits

Keep the `qec_scale` sparse observer and the classical GF(2) min-sum BP
reference strictly separate from the protected native GF(3) decoder.
Maintain exact Phase 1A–1D small fixtures. Never infer full-graph
eigenvectors from a selected recurrent SCC, or promote numerical Collatz
estimates to rigorous enclosures.

Hold out **whole graphs**, not random trials. Predeclare predictor
direction, train-only thresholds and evaluation criteria, and preserve
negative findings and missing-class metrics as null. Do not tune
thresholds or graph families against held-out labels.

For any Phase 1E evidence claim, retain the full canonical corpus,
its SHA-256, exact source commit, independent Ada/reference parity and
offline replay. Never call this a QEC BP parity result or hardware
fault-tolerance validation.
