# Phase 1G — Source-pinned CSS Tanner admission and family-blocked BP

**Status:** bounded research implementation; proof and result scopes follow the
actual executed CI evidence, never prospective success claims.

## Why this phase exists

Phase 1E's 20-graph / 720-trial and Phase 1F's 40-graph / 1,440-trial
experiments failed to establish that a larger recurrent-block
non-backtracking IPR predicts classical BP decoder failures.
Both cohorts came from *one hand-authored synthetic Tanner graph
generator* with four structural variants. Repeated seeds do not supply
an independently sourced class of graphs.

Phase 1G generates code/check matrices using an **existing, pinned,
separately implemented source** from QSOLKCB/QEC rather than the
Phase 1E synthetic graph generator. This improves implementation and
topological diversity, but the generating code comes from the same
QSOL research ecosystem; it is **not independent external QLDPC evidence**.

The two negative baselines remain immutable, with no change in their
thresholds, classifier directions, source hashes or stated limitations.

## Exact executable source boundary

The source is QEC's original
`src/qec_qldpc_codes.py`, which exports `create_code` and
`bp_decode`, pinned by both:

- QEC Git HEAD: `27bbc798c4e38138ca5b0fff70b15c3271a1917d`
- Source Git blob: `266dc35c7162adf6a895eb796760e2bc6724eff4`

`scripts/phase1g_pinned_css.py` uses the Phase 1F provenance gate
to verify the donor checkout HEAD, source blob ID, on-disk byte
identity, real regular file and containment before importing it.
Importing the QEC module is **code execution**, not reading a safe data
file. The entry point fails unless `--execute-pinned-donor` is
explicitly supplied. NumPy is required **only** for this opt-in
reference lane; native Ada and ordinary Phase 1E/1F Python paths
remain offline-first and standard-library-only.

The reference source is not modified, vendored, copied into the Ada
decoder, or automatically updated from a moving QEC branch.

## Fixed CSS construction protocol

The Phase 1G protocol is not optimized against held-out labels:

| Dimension | Source-bound contract |
| --- | --- |
| QEC predefined code families | `rate_0.50`, `rate_0.60`, `rate_0.75` |
| GF source basis | QEC's GF(8) protographs, binary companion/circulant lifts |
| QEC construction seeds | 17, 29, 41, 53 |
| Lift sizes, rate 0.50 | 4, 5 |
| Lift sizes, rate 0.60 | 3, 4 |
| Lift sizes, rate 0.75 | 4, 5 |
| Prespecified source construction candidates | **24** (before duplicate admission) |
| Effective unique topology cohort | SHA-256-deduplicated before BP trials; every exclusion recorded |
| Train/heldout candidate configurations | 16 / 8 (admitted counts may differ) |
| Training families | `rate_0.50` and `rate_0.60` (16 instances) |
| Held-out family | **`rate_0.75`** (8 instances) |
| BSC error probabilities | 4%, **8% primary**, 12% |
| Integer min-sum BP trials/admitted topology/noise | 4 (at most **288** total) |
| Actual QEC BP trials/admitted heldout topology/noise | 2 (at most **48** total) |
| BP round bound | 14 |
| Graph-blocked bootstrap resamples/noise | 256 |
| Frozen primary hypothesis | Larger IPR predicts greater frame-failure risk |
| Fixed failure-prediction threshold | AUROC ≥ 0.65 and ≥0.05 over edge density |

For each source instance, QEC's genuine `create_code` produces both
`H_X` and `H_Z` binary parity-check matrices. The program
independently checks:

1. All binary symbols are exactly 0/1; dimensions and graph edge
   counts fit QEC-ADA's original bounded 128-node/2,048-edge model.
2. CSS orthogonality `H_X * H_Z^T == 0 (mod 2)` using integer bit
   intersections over GF(2), separately from QEC's own check.
3. Actual GF(2) binary row ranks using integer XOR elimination,
   explicitly **not** floating-point NumPy rank estimates.
4. Complete matrix/graph SHA-256 identities and canonical ascending
   check/variable edge ordering. All **24 predeclared candidate
   configurations** are inspected before any noise/BP outcome. Exact
   duplicates **within a family** are recorded with the original
   first-admitted topology ID in `duplicate_candidates` and receive
   no second set of trials or independent-graph weight.
5. Exact duplicates **between different families** (especially across
   train and heldout) are rejected outright before running trials.
   The fixed seed/lift list is never tuned to evade collisions.

**Evaluation uses only `H_Z` as a classical binary parity-check
matrix detecting X-channel bit flips.** `H_X` is retained to verify
source CSS orthogonality and source identity. This is not a full joint
X/Z QEC syndrome experiment, depolarizing channel, a quantum logical
failure rate, or a claim that individual generated codes meet a
physical threshold.

## Spectral and decoder comparability

The existing native `qec_scale` returns SCC-aware bounded
non-backtracking numerical radius, IPR, EEEC, exact edge density and
ranked top-edge energy for the source-derived `H_Z` Tanner graph.
All spectral outputs are checked against the independent Python
mathematical oracle retained in Phase 1E. The original Phase 1D
small graph/eigenvalue fixtures and Phase 1E 2,048-edge memory gates
remain unchanged.

For each BSC trial, the all-zero classical codeword is transmitted;
deterministic SHA-256-based errors are applied and **the original**
Phase 1E integer min-sum BP computes actual decisions, syndrome
weights and per-round traces. The at-most-48 selected held-out trials are
replayed through the **actual pinned QEC `bp_decode`**, also in
classical binary `mode=min_sum`, `schedule=flooding` without
postprocessing, on identical `H_Z`/flip inputs.

The message arithmetic, priors, rounding and stopping conditions
still differ between these implementations. Agreement in
frame-failure *labels* is reported as such; matching labels are
**not** identical recovered bitstrings, algorithmic equivalence or
fault tolerance.

The risk endpoint is the same prespecified `IPR` vs edge-density
comparison. The held-out set consists of a whole code family,
not graph trials randomly interleaved between train and test.
This introduces a substantial **rate and size domain shift**, so
any predictor finding cannot be attributed specifically to IPR
without separate controlled factorization.

AUROC and AP are `null` when either held-out class is absent;
conditional graph-blocked percentile ranges are
**exploratory**, not a calibrated external population interval.
No primary hypothesis or threshold will be changed in response
to CI outcomes.

## Complete evidence and trust boundaries

`qec-ada.phase1g-pinned-qec-css-cohort.v1` is a source-bound canonical
sorted-key UTF-8 JSON envelope containing the exact donor identity,
fixed predeclared parameters, both QEC CSS matrices' support,
independent GF(2) ranks and commutation, canonical graph identities,
native spectrum/independent-oracle equivalence, every error site,
integer min-sum BP trace, exact pinned QEC recovered words,
per-noise family-blocked evaluation, and a SHA-256 identity.

Unlike a hash-only check, **verification reexecutes the pinned QEC
source, regenerates every matrix, repeats the native graph analysis,
replays all BP trials and QEC decoder outcomes, and recomputes all
metrics and receipt bytes**. Verifying requires the matching binary
toolchain, NumPy environment, exact donor and explicit opt-in.
This is software provenance and reproducibility, not a signed
independent scientific witness.

The source receipt includes the 24 attempted constructions,
the effective number of unique Tanner topologies, and every
pretrial duplicate exclusion. Verification must regenerate
the exact same candidate order and exclusions.

The file is created without overwriting an existing output. CI
uploads the complete evidence for 30 days with the commit SHA
and experimental source IDs in the artifact metadata.

### Reproduction

With a separately checked-out QEC donor at the required exact commit
and native Ada binaries already compiled:

~~~sh
gprbuild -p -P qec_ada.gpr

uv run --no-project --with numpy==1.26.4 python \
  scripts/phase1g_pinned_css.py create \
  /tmp/qecada-phase1g-css.json \
  --donor /path/to/pinned/QEC --execute-pinned-donor

uv run --no-project --with numpy==1.26.4 python \
  scripts/phase1g_pinned_css.py verify \
  /tmp/qecada-phase1g-css.json \
  --donor /path/to/pinned/QEC --execute-pinned-donor
~~~

CI on Ubuntu 24.04 uses Ubuntu's `python3-numpy` package only for
the separately pinned reference lane, recording the actual version.
A new `uv` isolated run can use the documented exact version as
a starting environment; its evidence SHA might differ if it uses a
different Python/NumPy/compiler combination.

## Future independent gates

- Truly independently published Tanner/QLDPC topology datasets with
  explicit redistribution rights, original file hashes, code
  identifiers and experiment-source separation.
- Multiple genuine quantum CSS decoders and depolarizing/Puali error
  models, separately from the present classical bit-flip slice.
- Randomized code-family control studies that disentangle rate,
  check count, lift size and IPR.
- Independent held-out families from source **other than QEC**, with
  stronger statistical power and correction-aware metrics.
- Explicit SPARK verification of new native algorithms and portable
  floating-point numeric error enclosures.

**Do not promote** conditional synthetic/CSS-source predictor scores,
even above their preregistered exploratory threshold, to quantum
hardware/fault tolerance claims.
