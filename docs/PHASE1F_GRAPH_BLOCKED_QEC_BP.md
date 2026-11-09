# Phase 1F — Held-out topology uncertainty and pinned QEC BP comparison

**Status:** additional empirical validity checks on the existing, frozen
Phase 1E baseline. The native Ada GF(3) decoder, matrix-free spectral
observatory, Strowger receipts and historical QEC mirror are untouched.

## Research question and fixed prior evidence

Phase 1E found that native Tanner-graph IPR did **not** meet the
prespecified predictive threshold for classical binary BP failures.
The 20-graph, 720-trial evidence remains fixed:

- Parent schema: `qec-ada.phase1e-bp-spectral-evidence.v1`
- Parent experiment SHA-256:
  `ee0dc4ea5868386b3e60bbdef20c9d5c2c8e4b43e5ae160847f0bb5069a69738`
- IPR held-out AUROC: 0.595238 at 8% BSC error probability.
- Edge-density held-out AUROC: 0.383598.
- **Pre-registered outcome: predictive advantage NOT established.**

The four held-out Tanner graphs (IDs 0, 5, 10, 15) contain multiple
correlated noise trials. Treating those 48 trials as 48 independent
topology observations would be pseudoreplication.

## A. Graph-blocked bootstrap and permutation

`scripts/phase1f_blocked_inference.py` replays the **entire original
Phase 1E corpus** using the existing exact source-bound verifier,
and estimates *exploratory* numerical stability across held-out
Tanner graph clusters:

- Resampling unit: **one complete held-out graph**, retaining every
  original BP trial and failure label with each draw.
- Deterministic SHA-256 counter-derived draws; no global PRNG or
  time-dependent seed.
- The same drawn clusters are used for paired IPR and edge-density
  AUROCs and for their difference.
- Each bootstrap replicate with only one outcome class is recorded
  as **undefined**, not counted as AUROC=1, AUROC=0 or AP=1.
- Report conditional 2.5/97.5 percentile ranges over defined replicates,
  count all undefined draws, and preserve the original Phase 1E result.
- Exact two-sided Spearman **graph-label** permutation on graph-level
  failure rates, with complete enumeration for at most eight clusters.
  Only four clusters are available here; permutation p values are very
  coarse and do not establish significance.
- Independent replay derives the entire inference report afresh from
  the immutable parent (rather than simply accepting a valid hash).

**Executed preliminary observation**, Phase 1F PR #8, Actions
`42587318495`: at 8% noise, 512 graph-cluster resamples produced
a conditional IPR AUROC range of approximately **0.401645–0.677391**,
with **0 undefined replicates** for this specific run. This broad
exploratory range is not a confidence-certified prediction bound and
does not overturn the negative Phase 1E finding.

The inferential method is fixed independently of the held-out
outcomes: larger IPR predicts greater failure risk; edge density is
the Phase 1E baseline. No new classifier, feature selection, threshold
tuning or claimed external validation is introduced.

Reproduce using a locally regenerated Phase 1E parent:

~~~sh
uv run --no-project python scripts/phase1e_experiment.py run \
  /tmp/qecada-phase1e.json --graphs 20 --trials 12 \
  --variables 32 --checks 24 --seed qecada-phase1e-001 \
  --noise-bps 400,800,1200

uv run --no-project python scripts/phase1f_blocked_inference.py create \
  /tmp/qecada-phase1e.json /tmp/qecada-phase1f-blocked.json \
  --resamples 512

uv run --no-project python scripts/phase1f_blocked_inference.py verify \
  /tmp/qecada-phase1e.json /tmp/qecada-phase1f-blocked.json
~~~

The output is canonical UTF-8 JSON with a separate SHA-256 identity,
the parent file and receipt digests, every per-noise observed statistic,
paired resample ranges and missing-class counts.

## A2. Prespecified independent-seed replication (40 graphs)

This additional Phase 1F cohort was specified **before inspecting any
cohort output**. It uses the unchanged Phase 1E data generator and
pre-registered risk/evaluation logic with these distinct, fixed inputs:

| Field | Prespecified value |
| --- | --- |
| Seed | `qecada-phase1f-cohort40-001` |
| Variables/checks per graph | 32 / 24 |
| Graphs | 40 distinct synthetic source identities |
| Training / held-out graph counts | 32 / 8 |
| Held-out IDs | 0, 5, 10, 15, 20, 25, 30, 35 |
| Error rates | 4%, **8% primary**, 12% |
| Noise trials per graph/rate | 12 |
| Total classical BP evaluations | **1,440** |
| Primary feature | IPR, larger predicts more failures |
| Baseline | Graph edge density |
| Frozen signal threshold | Held-out AUROC ≥ 0.65 and ≥0.05 above density |
| Cluster resampling | 512 deterministic draws of whole held-out graphs |
| Graph permutations | Exact 8! permutations (if graph rates vary) |

The source graph generator and fixed four structural families are the
same as Phase 1E; the seed and graph identifiers are new. This is a
**distinct deterministic synthetic cohort**, not independently sourced
physical/QLDPC data. The original 20-graph 720-trial evidence and its
negative outcome remain immutable. Even eight held-out graphs do not
provide a generalizable performance guarantee or valid quantum threshold.

CI records `evidence/phase1f/cohort40.json` and
`evidence/phase1f/cohort40-inference.json` as separate 30-day
artifacts after **complete offline replay of both records**. The
Phase 1F output must retain negative or null results without modifying
thresholds in response.

## B. Actual pinned QEC BP decoder comparison

QEC has its **own genuine** frozen `bp_decode` reference in
`src/qec_qldpc_codes.py`. It is not the same algorithm as Phase 1E:

| Property | Phase 1E pilot | Pinned QEC reference |
| --- | --- | --- |
| Model | Classical GF(2) Tanner parity checks | Same binary H input, QEC `bp_decode` |
| Channel | Shared deterministic BSC flip sites | Same flip sites, mapped to channel log-likelihoods |
| Check update | Integer-clipped min-sum | QEC floating-point `mode="min_sum"` |
| Schedule | Synchronous flooding | QEC `schedule="flooding"` |
| Posterior | Integer fixed prior 6 | Floating LLR magnitude `log((1-p)/p)` |
| Target | All-zero transmitted word | All-zero target syndrome |
| Postprocessor | None | Explicitly none |
| Output | Full per-round classical BP trace | QEC decoded word, iterations and parity validation |

The study selects the first **two** trials per held-out graph/noise:
4 held-out graphs × 3 noise rates × 2 trials = **24 shared inputs**.
Each comparison calls QEC's actual imported reference, records exact
binary decoded word, iterations, parity status, frame failure and
agreement with the Phase 1E frame-failure label. Different outcomes
are preserved, not normalized away.

This does **not** compare identical update equations or assert
bitwise/algorithmic BP parity. It is a first controlled **same-input
cross-decoder observation**, not a quantum CSS code validation.

### Provenance, execution consent and dependencies

- QEC repository: `QSOLKCB/QEC`.
- Exact commit:
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`.
- Exact `src/qec_qldpc_codes.py` Git blob ID:
  `266dc35c7162adf6a895eb796760e2bc6724eff4`.
- The adapter verifies checkout HEAD, Git tree blob ID, checked-out
  file Git blob ID, regular file type and resolved containment before
  importing and executing source code.
- **Executing third-party/reference source is not reading inert
  data**. It is disabled by default and requires explicit
  `--execute-pinned-donor`. QEC itself is owned by the same research
  organisation but remains a separately pinned source boundary.
- NumPy is an opt-in CI-only reference dependency; no new Ada runtime
  package, Docker, Node.js or cloud service is required locally.
- Comparison receipt records NumPy/Python versions and donor file
  SHA-256; exact repeatability is relative to that environment.
- Validation reexecutes the same pinned donor and compares the *full*
  output record, rejecting altered decoded words even if all hashes
  are recomputed. It is not a standalone no-source verification claim.

**Executed preliminary result**, CI `42587318495`: actual pinned
QEC BP ran successfully on all 24 matched held-out inputs and agreed
with the Phase 1E **frame-failure labels on 23/24 cases**. That is
outcome-label agreement on one small set, not decoder equivalence or
an accuracy certification. The subsequent test fixture failure was
a missing test call argument, not a failure of those actual QEC BP
executions; acceptance requires a later fully green CI run.

Run with a **separately checked-out pinned donor**:

~~~sh
uv run --no-project --with numpy==1.26.4 python \
  scripts/phase1f_qec_bp_bridge.py create \
  /tmp/qecada-phase1e.json /tmp/qecada-phase1f-qec.json \
  --donor /path/to/pinned/QEC --trials-per-graph 2 \
  --execute-pinned-donor

uv run --no-project --with numpy==1.26.4 python \
  scripts/phase1f_qec_bp_bridge.py verify \
  /tmp/qecada-phase1e.json /tmp/qecada-phase1f-qec.json \
  --donor /path/to/pinned/QEC --execute-pinned-donor
~~~

Use `uv --with` for isolated execution if desired; normal
`uv run --no-project` Phase 1F uncertainty and Phase 1E native tools
need no third-party Python packages. The CI lane installs Ubuntu's
`python3-numpy` package and records its actual version.

## Acceptance and remaining limitations

- Frozen Phase 1E negative finding and exact 720-trial receipt SHA;
  full canonical source, noise and BP replay before any inference.
- Graph-level blocking, missing-class handling, forgery tests,
  deterministic resampling and direct numerical replay.
- Cross-QEC source pin, explicit opt-in, actual QEC algorithm
  invocation, source-hash binding, same-input comparison and exact
  independent rerun before accepting a comparison receipt.
- Both Phase 1F JSON artifacts uploaded with 30-day GitHub
  Actions retention. Historical artifacts and CI source hashes
  remain distinguishable; no silent overwrite.
- All existing GF(3) decoder, 2,048-edge spectral, Strowger,
  SPECTRAL WAV and proof-scope checks unchanged.

Phase 1F does **not** establish spectral localization as a general
predictor, statistical significance, a rigorous bootstrap coverage
guarantee, equivalence of BP update equations, QLDPC quantum decoding,
a physical threshold, or proof of the native eigenmode solver.

Future research should use **additional externally sourced Tanner
topologies** and multiple controlled noise/decoder regimes, with more
independent held-out graphs and separately pre-registered features
before stronger statistical conclusions are attempted.
