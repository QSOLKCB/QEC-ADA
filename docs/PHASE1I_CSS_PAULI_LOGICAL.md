# Phase 1I — Ideal-syndrome CSS Pauli and logical-frame experiment

## Scope and prior evidence

Phase 1H established source-verified CSS parity matrices from two
public matrix providers, yet its BP work evaluated only a classical
binary H_Z / X-error slice. Phase 1I adds a **distinct mathematical
CSS Pauli decoding experiment** rather than another IPR seed search.
The source datasets, initial native spectral observatory, protected
Ada GF(3) decoder, SPARK proof scope, SPECTRAL sound, Strowger
receipts and Phase 1E/F/G/H negative IPR findings remain unchanged.

Phase 1I implements an **ideal, noiseless-syndrome CSS Pauli-frame
decoder** using separate X/Z syndrome-only integer min-sum channels.
The underlying mathematical correction is genuine Pauli/CSS
syndrome and stabilizer-coset reasoning, but the decoder is
**not a joint optimal BP, fault-tolerant circuit implementation
or physical quantum hardware experiment**.

## Algebra and classification contract

For binary CSS check matrices H_X (X stabilizers) and H_Z
(Z stabilizers), enforce exactly

`H_X H_Z^T = 0 (mod 2)`.

For physical Pauli bitmasks `e_X`, `e_Z`, using a Y error to set
**both** component bits at its qubit, ideal measured syndromes are:

`s_Z = H_Z e_X`, `s_X = H_X e_Z`.

The two correction engines receive ONLY `s_Z`, `s_X`,
the corresponding check topology, a fixed uniform prior of 6,
and an iteration bound. They do **not** receive `e_X`, `e_Z`
or planted error sites. They run deterministic integer flooding
min-sum with a bounded message magnitude of 48. If the syndrome
cannot be satisfied within 14 rounds, a fixed canonical **weight-one
syndrome leader** is attempted. If no such leader exists, the
component's failure is **unresolved**, not silently accepted.

For the resulting corrections `c_X,c_Z`, compute residuals:

`r_X = e_X XOR c_X`; `r_Z = e_Z XOR c_Z`.

Classification is **exact GF(2)**, not based solely on a zero
residual syndrome:

- **STABILIZER_EQUIVALENT_SUCCESS** iff `H_Z r_X=0`,
  `H_X r_Z=0`, AND `r_X` lies in the row span of `H_X`,
  AND `r_Z` lies in the row span of `H_Z`.
- **NONTRIVIAL_LOGICAL** iff both residual syndromes vanish, but
  at least one residual component is outside its stabilizer span.
  The separate X and Z logical flags preserve both possibilities,
  including both flags for a Y-component logical residual.
- **DETECTED_UNRESOLVED** if either residual syndrome remains
  nonzero after correction. Its measured logical flags are
  `null`: the unresolved syndrome is not falsely counted as
  an established nontrivial logical Pauli.

This distinction is essential: a nonzero stabilizer Pauli may
still be a correct result, and a zero-syndrome non-stabilizer
Pauli may encode a logical fault. Pure GF(2) integer elimination
computes row span, rank and `k=n-rank(H_X)-rank(H_Z)`
without floating-point matrix rank or arbitrary representative choices.

## Phenomenological channel and source protocol

The channel uses deterministic, separately domain-labelled SHA-256
draws for each source ID, probability, trial and qubit. At a declared
depolarizing probability p, each qubit has an independent chance p
to experience a nonidentity Pauli, then chooses X/Y/Z equiprobably.
In particular, a Y introduces **correlated X and Z components**,
unlike a pair of independently sampled bit-flip channels.

| Parameter | Frozen Phase 1I protocol |
| --- | --- |
| Original external source manifest | Phase 1H `fixtures/phase1h_external_css_sources.json` |
| Sources | Simula UiB NISQEC CC BY 4.0 (2 CSS pairs); explicit QLDPC source with unspecified licence (7 CSS pairs) |
| Matrix admission | Exact Git HEAD/blob/on-disk identity, path containment, binary syntax, CSS commutation and bounded sparse dimensions |
| Source-specific trial unit | One original H_X/H_Z CSS code pair |
| Source grouping | Simula = source baseline; external explicit database = descriptive heldout publisher |
| Physical channel probabilities | 4%, 8%, 12% Pauli depolarizing |
| Trials per CSS pair/noise | 8 |
| Total phase-space trials | **216** (9 × 3 × 8) |
| Decoder | Separate syndrome-only X/Z integer min-sum, plus canonical radius-one leader |
| Iteration maximum | 14 per component, with explicit trace |
| Correctness endpoint | Exact stabilizer-equivalent success / nontrivial logical residual / detected-unresolved |
| Original feature predictor | No new confirmatory IPR threshold; any resolved-only AUROC is descriptive and subject to selection bias |
| Seed | `qecada-phase1i-css-pauli-001` |
| Primary report rate | 8% (4% and 12% preserved as sensitivity checks) |

The initial Phase 1H unlicensed external matrix collection is never
redistributed in this PR. CI reads it from a separately verified,
commit-pinned, **credentialless external checkout**. The Phase 1I
research receipt includes **source hashes, ranks, derived spectral
metrics, Pauli error tapes, correction traces and logical outcomes**,
but **not raw H_X/H_Z parity matrices or edge lists**.
Only the Phase 1H admission code accesses source matrix bytes;
provider code is not imported or executed.

These nine external CSS examples do not form a representative
sample of physical QLDPC implementations. The per-publisher baseline
has only two Simula examples, and construction family, n, check
weight and density remain confounded. No statistical generalization
or learned predictive model is claimed.

## Executable evidence and independent tests

- `scripts/phase1i_css_pauli.py`: standalone stdlib syndrome-only
  decoding, exact stabilizer membership, Pauli channel and per-trial
  classification. This code does not call the protected Ada decoder.
- `scripts/phase1i_experiment.py`: verifies every original Phase 1H
  source Git blob and source matrices, native Ada SCC/Hashimoto metrics,
  then runs the Pauli channel experiment and reports per-source
  and per-noise categories without conflating unresolved and logical.
- `tests/test_phase1i.py`: exhaustive small GF(2) stabilizer-span
  oracle, degenerate stabilizer successes, the zero-syndrome
  nontrivial logical counterexample, correlated Pauli Y, identical
  syndrome/identical decoder decision despite different planted
  errors, explicit unresolved checks and rehashed evidence forgery.
- Canonical UTF-8, sorted-key JSON `qec-ada.phase1i.css-pauli-logical-evidence.v1`,
  with outer SHA-256 and complete local source reexecution. A
  correctly recomputed SHA-256 over a forged outcome cannot validate
  the artifact; full semantic replay is required.

No cryptographic key signs this self-consistency receipt, so it is
not independently authenticated external evidence. The numeric
native spectral estimates do not become formal SPARK proof
obligations. The exact GF(2) membership checks are executed tests,
not a machine-checked theorem about the whole software system.

### Reproduction

After compiling QEC-ADA with `gprbuild -p -P qec_ada.gpr`
and separately checking out the Phase 1H sources at their
exact pinned Git commits:

~~~sh
uv run --no-project python scripts/phase1i_experiment.py create \
  /tmp/qecada-phase1i.json \
  --simula /path/to/pinned/nisqec \
  --explicit /path/to/pinned/explicit-qldpc

uv run --no-project python scripts/phase1i_experiment.py verify \
  /tmp/qecada-phase1i.json \
  --simula /path/to/pinned/nisqec \
  --explicit /path/to/pinned/explicit-qldpc
~~~

Phase 1I uses no new runtime Python dependencies, network service,
Docker, Kubernetes or Node.js. It does not execute QEC's optional
NumPy BP donor; Phase 1F–1H already preserve that separate baseline.

## Boundaries for Phase 1J

The next independent gates include **syndrome extraction noise,
repeated measurement rounds, spatially correlated Pauli channels,
paired X/Z-aware joint CSS decoding**, and external code families
with explicitly licensed redistributable matrices. Classical
readout and circuit noise must not be added and still called the
same ideal-syndrome experiment.

New fault-tolerance claims require stronger external evidence
and appropriate independent mathematical or hardware validation.
