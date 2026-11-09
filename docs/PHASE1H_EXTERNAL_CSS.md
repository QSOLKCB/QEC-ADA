# Phase 1H — Independently sourced CSS Tanner matrices

**Scope:** read-only source admission, independent GF(2) CSS checks,
native sparse spectral observation and controlled classical BP traces.
The native Ada GF(3) decoder, SPARK proof pilot, Phase 1D–1G protocols,
Strowger routing, SPECTRAL audio and historical QEC mirror are unchanged.

## External data provenance and reuse conditions

Phase 1G demonstrated independent *execution* of a QEC-owned CSS
generator, but its graphs still came from QSOLKCB/QEC. Phase 1H
instead admits **published matrix files from two public source
repositories neither maintained by QSOLKCB/QEC**.

| Provider | Immutable source | Rights / provenance | Admitted pairs |
| --- | --- | --- | --- |
| Simula UiB, **NISQEC** | `Simula-UiB/nisqec`, commit `913e0f26b07919ab73d7052159196599d34a2969` | **CC BY 4.0**; E. Durazo Rocha, O. Å. Mostad, H.-Y. Lin and E. Rosnes, *NISQEC v1.0.0* (2026), DOI `10.5281/zenodo.23378284` | 2 quantum Tanner Hₓ/Hᵤ pairs (n=10 and n=45) |
| Wang *et al.*, **Explicit QLDPC Database** | `lilyxy/Check-weight-constrained-quantum-codes`, commit `0e6c3e281fe044315286fbdcf5295cb16f47f90d` | **No repository licence identified**; Lily Wang, Andy Zeyi Liu, Ray Li, Aleksander Kubica and Shouzhen Gu, *Check-weight-constrained quantum codes: Bounds and examples* (public 2026 matrix collection; formal paper identifier not supplied in repository) | 7 HGP, bivariate-bicycle and lifted-product Hₓ/Hᵤ pairs (n=10, 41, 58, 72, 75, 108, 125) |

The source catalog in
[`fixtures/phase1h_external_css_sources.json`](../fixtures/phase1h_external_css_sources.json)
pins **18 individual matrix Git blobs**, their relative paths,
the complete source commits, declared licensing and prespecified
study rules. The *source bytes themselves are never committed,
vendored or uploaded in the research artifact*. The explicit
QLDPC repository has **no stated source redistribution licence**:
QEC-ADA does **not** assert a right to copy/relicense its matrices.
Anyone planning redistribution should obtain appropriate permission.
The Phase 1H artifact retains **derived** spectra, decoder outputs
and hashes only, not the original raw matrices.

These are two **independently maintained repositories**, but
their code families are still structurally related within each
publisher. They are not an unbiased population sample of QLDPC
codes, nor evidence from a physical quantum computer.

## Admission gates: exact binary CSS source evidence

`scripts/phase1h_external_css.py` reads the nine matrix pairs
only from two **separately checked-out, commit-pinned local Git
repositories**. The importer executes no code from either matrix
provider. Every matrix is admitted only after:

1. Verifying source repository HEAD equals the exact pinned commit,
   source blob SHA-1 equals the committed expected Git object, checked-
   out file Git object equals that blob, and path resolves to a
   regular non-symlink file inside its checkout.
2. Requiring ASCII LF input, strict binary symbols and exact dimensions.
   Simula's dense whitespace-separated `0/1` format and the explicit
   database's Matrix Market `coordinate integer general` triples are
   parsed independently. Unknown formats, malformed rows,
   duplicate/out-of-range COO coordinates and wrong entry counts
   are **rejected**, not auto-repaired.
3. Enforcing the existing native limits: at most 128 variable nodes,
   128 check nodes and 2,048 support edges per matrix.
4. Independently checking CSS commutation
   `H_X × H_Z^T = 0 (mod 2)` with exact Python integer bitsets,
   and computing GF(2) row ranks with XOR elimination rather than
   floating-point NumPy matrix rank.
5. Assigning SHA-256 identities to both original file byte streams
   and the canonical sorted Tanner support, failing closed on any
   repeated H_Z topology in the nine-code cohort.
6. Recomputing all observational sparse SCC/Hashimoto `rho`, IPR,
   EEEC and top-edge energies with QEC-ADA's **unchanged** native
   `qec_scale` and independent Python finite-graph reference oracle.

This is *source admission*, not proof of QEC code distance, nor a
port of the authors' joint quantum decoder. The original H_X/H_Z
binary symbols are never silently transformed to make checks commute.

## Frozen predictor and decoder experiment

| Dimension | Preregistered condition |
| --- | --- |
| Source unit | One canonical external H_X/H_Z pair |
| Dataset sizes | 2 Simula + 7 explicit-database pairs |
| Training/source baseline | **Simula UiB** (two graphs) |
| Publisher holdout | **Explicit QLDPC Database** (seven graphs) |
| Classical tested component | H_Z Tanner check matrix, X-bit errors, all-zero transmitted word |
| Noise | Deterministic BSC at 4%, **8% primary**, 12% |
| Per graph / noise | 4 integer min-sum BP trials |
| Total integer min-sum trials | **108**, complete iteration traces |
| Actual source-pinned QEC `bp_decode` | Two same-input comparisons per graph at 8% = **18** |
| Numeric spectral features | Recurrent-block IPR, rho, EEEC and edge density |
| Primary hypothesis | Higher IPR predicts more binary frame failure |
| Original threshold preserved | Heldout IPR AUROC ≥0.65 **and** ≥0.05 over density |
| Graph-cluster bootstrap | 256 deterministic full-heldout-graph resamples/noise |
| Required interpretation | Descriptive/exploratory only, no learned heldout thresholds |

No prediction threshold was trained from the heldout publisher.
The "train" publisher has only **two** graph samples and is included
as a source baseline, **not** as adequate model training data.
The families have large differences in n, m and graph density.
Publisher membership is therefore confounded with construction
family, code length and other properties. No causal attribution to
IPR or generalization claim follows from a high score.

BP is the established deterministic, bounded integer min-sum
**classical GF(2)** reference introduced in Phase 1E. The 18
same-input comparisons execute **QEC's actual pinned floating-point
`bp_decode`** (`mode=min_sum`, flooding, no postprocessing).
QEC's executable reference is a separate dependency enabled only
with `--execute-pinned-qec`, commit
`27bbc798c4e38138ca5b0fff70b15c3271a1917d`,
source Git blob `266dc35c7162adf6a895eb796760e2bc6724eff4`.
NumPy is used only for this opt-in QEC reference, never for native
Ada or the external matrix parsers.

**Decoder agreement means frame-failure-label agreement on matched
Phase 1H trials**, not identical correction words or identical BP
update equations. No experiment here applies correlated Pauli
X/Z noise or measures a logical quantum error rate.

## Executed results — negative primary test

Full source admission, native Ada math, both BP implementations,
replay and dedicated tests passed on PR #10
[GitHub Actions run 42613372613](https://github.com/QSOLKCB/QEC-ADA/actions/runs/42613372613),
implementation commit `908c56625c47b57618c86202af9f213e4ef5a878`.

- **Nine** CSS pairs from two unrelated source repositories
  admitted, with no duplicate H_Z graph or GF(2) CSS failure.
- **108** actual integer min-sum BP trials, with every source-bound
  flipped site, iteration decision and failure label retained.
- **18/18** exact same-input *frame-failure labels* matched between
  the integer BP trial and pinned QEC floating min-sum decoder.
  No claim of correction-word parity.
- Full source/backend/BP reexecution succeeded, including the
  self-consistently rehashed evidence-forgery rejection test.

| BSC error rate | Heldout failures | IPR AUROC | Density AUROC | QEC same-input label agreement |
| --- | ---: | ---: | ---: | ---: |
| 4% | 8/28 | 0.675000 | 0.225000 | Not evaluated |
| **8% primary** | **11/28** | **0.510695** | **0.371658** | **18/18** |
| 12% | 22/28 | 0.515152 | 0.287879 | Not evaluated |

**Predeclared finding: NO_PRE_REGISTERED_ADVANTAGE_DETECTED.**
At the primary 8% level, IPR AUROC was ~0.511, below 0.65.
The 4% secondary figure exceeds 0.65 but **does not** override
the fixed primary test or validate an IPR predictor. These graph
collections are small and heterogeneous; no statistical significance,
external generalization, physical quantum threshold or proof of
a spectral-localization failure mechanism is established.

Canonical complete receipt digest (SHA-256):
`d81f1bff2e29fa846e972320d6aca6a2d62ac65655ac8fbaf013e87d9023315a`.
This **is not** the GitHub artifact ZIP's SHA-256.
[Retained derived-only source-bound corpus](https://github.com/QSOLKCB/QEC-ADA/actions/runs/42613372613/artifacts/13670449914)
(30 days). Original matrix bytes remain exclusively at their
separately attributed publishers.

The Phase 1E 720-trial, Phase 1F 1,440-trial and Phase 1G
source-generated cohorts remain unchanged; none is replaced or
post-hoc reclassified by Phase 1H.

## Offline reproduction

Prepare three **separate** exact-commit source checkouts:
`Simula-UiB/nisqec` at the commit above,
`lilyxy/Check-weight-constrained-quantum-codes` at its commit,
and QSOLKCB/QEC at its Phase 1F pinned reference commit.
The files are downloaded from source publishers once; no ongoing
network or hosted runtime is required afterwards.

~~~sh
gprbuild -p -P qec_ada.gpr

uv run --no-project --with numpy==1.26.4 python   scripts/phase1h_external_css.py create   /tmp/qecada-phase1h.json   --simula /path/to/nisqec   --explicit /path/to/explicit-qldpc   --qec /path/to/pinned/QEC   --execute-pinned-qec

uv run --no-project --with numpy==1.26.4 python   scripts/phase1h_external_css.py verify   /tmp/qecada-phase1h.json   --simula /path/to/nisqec   --explicit /path/to/explicit-qldpc   --qec /path/to/pinned/QEC   --execute-pinned-qec
~~~

The verifier rejects a validly rehashed but semantically altered
receipt and must regenerate all matrices from exact source checkouts.
Numerical results are conditioned on the declared Python, NumPy,
Ada compiler and host environment; portable bitwise equivalence
across untested architectures is **not** claimed.

## Next independently useful gate

For Phase 1I, acquire **explicitly licensed, separately published**
additional matrices across larger and more independent code families;
increase heldout source/sample count and separate code length,
density and check-weight factors. Then add a **genuinely distinct
quantum CSS syndrome/depolarizing-channel decoder** and logical
failure measurement under a source-pinned protocol. Any new claim
must have a separately frozen hypothesis, reference manifest and
outcome-blind evaluation plan. No release of a universal IPR
predictor is justified by these results.
