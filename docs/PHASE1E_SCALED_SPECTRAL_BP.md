# Phase 1E — Scaled Sparse Spectral Observatory + BP Predictive Validation

## Implemented boundary

Phase 1E is an **independent, read-only observational module**. It does not
modify QEC-ADA's GF(3) native stabilizer decoder, its OPT validation,
Strowger route semantics, previously proven SPARK GF(3) arithmetic
obligations, or historical QEC donor reference files.

**New native Ada executable:** `qec_scale`
- 1–128 variable nodes, 1–128 check nodes, up to 2,048 undirected Tanner
  edges (4,096 directed edges).
- Sparse outgoing/incoming adjacency using bounded arrays. The
  non-backtracking operator is evaluated by directed-edge transitions;
  the full dense Hashimoto matrix is never allocated.
- Nonrecursive, deterministic Kosaraju SCC decomposition; lazy `I+B`
  positive Perron mode on cyclic SCCs; no RNG.
- Explicit `NO_EDGES`, `ACYCLIC`, `CONVERGED_NUMERIC`, and
  `NOT_CONVERGED` outcomes. No unproved spectral radius is returned
  on nonconvergence.
- Canonical dominant recurrent-block selection and tie count,
  numerical rho, Collatz spread, L1 residual, IPR, EEEC and top-ten
  ranked edge energies.
- The mode is **local to the selected recurrent SCC**; the padded vector
  is not necessarily a right eigenvector of the whole reducible graph.
- All capacities are fixed statically. Storage is O(V+E) in the maximum
  capacities; operations are sparse edge-neighbour traversals, not an
  implicit promise that total runtime is linear.

### Input and reproducibility

Input is strict, canonical ASCII with exactly one line per edge:

~~~text
QECADA-TANNER-EDGES-V1
variables=3
checks=2
edges=6
1,1
1,2
1,3
2,1
2,2
2,3
~~~

Edges must be strictly ascending (check, variable), unique and within
the declared limits. Bad header, padding, extra data, duplicate edges,
oversized files and capacity overflows are rejected.

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_scale inspect path/to/graph.txt
~~~

The original small-graph `qec_research spectral` and `qec_ada`
executables remain available and unchanged.

## Independent eigenvalue and capacity checks

`tests/test_phase1e_scale.py` validates the native output using
**analytical spectra independent of the implementation**:

- Complete bipartite K(m,n): `rho(B)=sqrt((m-1)*(n-1))` for m,n ≥2;
- K₂,₂, K₂,₃, K₄,₅, K₈,₁₆, K₁₆,₂₄ and K₃₂,₆₄ (2,048-edge capacity);
- 64-variable/64-check simple long cycle: rho=1 and canonical two-way tie;
- 128-variable/127-check chain: nilpotent B, no fabricated eigenvector;
- two disconnected 4-cycles: stable canonical block tie;
- direct small K₂,₂ comparison with the existing Phase 1D solver;
- malformed and overcapacity input rejection.

`scripts/phase1e_reference.py` separately rebuilds directed Tanner
adjacency and computes SCC/Perron modes in Python's standard library
for each experiment graph. The experiment **fails** on disagreement
with native rho/IPR/EEEC, SCC identity or top ranked-energy constraints.

`scripts/phase1e_memory.py` now requests an **opt-in Ada-native,
post-exec VmHWM** via `qec_scale inspect GRAPH --native-rss`. The
already-executing Ada process reads Linux `/proc/self/status` and reports
`native_post_exec_peak_rss_kib_linux` (memory observation schema v2).
It includes the Ada executable, runtime and loader, but **not the
Python parent's inherited pre-exec address space**. Unlike
`resource.getrusage(RUSAGE_CHILDREN).ru_maxrss`, the reading is taken
inside the native program's own new Linux memory mapping.

The benchmark verifies the analytic K(m,n) spectral-radius formula.
These are *observational runner measurements*: runtime and RSS are not
portable deterministic fixtures. The hypothetical dense float64 B
comparison remains a storage-model calculation, **not** a measured
competitor implementation. The normal two-argument `qec_scale inspect`
output is unchanged; `--native-rss` is strictly opt-in and Linux-only.
Missing/malformed VmHWM fails closed instead of publishing an estimate.
`tests/test_phase1e_memory.py` explicitly tests this against an 80 MiB
Python-parent memory allocation.

## Executed sparse-memory observations — corrected native measurements

GitHub Actions run **`42582761067`** on Phase 1E PR #7, commit
`d31671910697e31a5120a212016c287933a7b05a`, executed the
new Linux in-process `VmHWM` measurement method and verified the
known K(m,n) non-backtracking spectral radius for each graph.

| Input | Edges / directed edges | Ada post-exec peak VmHWM | Hypothetical dense float64 B values | Process elapsed |
| --- | ---: | ---: | ---: | ---: |
| K₈,₁₆ | 128 / 256 | **4,920 KiB** | 0.5 MiB | 3.69 ms |
| K₁₆,₂₄ | 384 / 768 | **4,924 KiB** | 4.5 MiB | 15.24 ms |
| K₃₂,₆₄ | 2,048 / 4,096 | **4,928 KiB** | **128 MiB** | 296.53 ms |

The dense column is a **hypothetical** allocation for a dense float64
Hashimoto matrix's values alone (`8*(2*edges)^2` bytes). It is
not an executed dense baseline. VmHWM includes native loader/runtime
memory, fixed-capacity Ada arrays and everything else in the Ada
process since exec, so this table is *not* a pure algorithmic heap
allocation measurement or a demonstrated speedup against dense
solvers. RSS and runtime can vary across hosts, ASLR, compiler
versions, and system load. Graph/source identities remain in CI logs.

### Superseded measurement methodology

**The earlier numbers 17,964 / 17,968 / 18,416 KiB**, reported in
run `42568151303` at `ebbeb8f923c65fa4bac8101d25e40623b479cd3c`,
came from Linux `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss`.
Because that reading may include the Python launcher's memory footprint
before `execve`, **those figures were not isolated Ada executable
peak RSS and must not be cited as such**. They remain in the
historical CI logs, and the memory evidence schema was advanced
from v1 to v2 to distinguish the corrected measurements.

## Controlled BP experiment — precise scientific model

The separate Python `phase1e_reference.decode_min_sum` is a newly written,
deterministic **classical binary GF(2) min-sum belief-propagation**
experiment. It is **not** an executable port of QEC's Python BP family,
and it does not call the native QEC-ADA GF(3) stabilizer decoder.

- Transmitted codeword: all-zero classical parity-check codeword.
- Noise: reproducible synthetic BSC flips from SHA-256-derived integer
  draws, with explicit seed and per-graph/noise/trial/site inputs.
- Decoder: integer-valued sign/min updates, bounded messages,
  synchronous flooding, explicit iteration cap, parity checks and
  complete per-round decision/syndrome traces.
- Frame failure: recovered word differs from the known all-zero
  transmitted word, **including undetected valid but incorrect codewords**.
- No ambient clocks, global RNG, online services, hidden model state or
  learned weights. Graph generation and all noise draws are replayable.

### Prespecified evaluation

The baseline controlled experiment uses:

| Dimension | Value |
| --- | --- |
| Graphs | 20 distinct source-bound Tanner graphs |
| Graph sizes | 32 variables / 24 check nodes |
| Fixed graph families | 4 deterministic structural variants |
| Channel BSC rates | 4%, 8%, 12% |
| Trials per graph per noise | 12 |
| Total BP runs | **720** |
| Train graphs | 16 |
| Held-out graphs | 4 (graph ID divisible by 5) |
| Held-out trials at each noise | 48 |
| Primary endpoint | AUROC for higher IPR predicting BP frame failure at 8% noise |
| Comparison baseline | Edge density |
| Signal criterion (preregistered) | AUROC ≥ 0.65 and ≥0.05 above edge-density AUROC |

Model selection uses training-graph labels only. A balanced-accuracy
threshold is selected with a deterministic conservative tie policy;
the held-out graphs cannot be reused for tuning. The report includes
AUROC, average precision, graph-level Spearman correlation and
held-out confusion matrices. AUROC **and average precision (AP)**
are **null whenever either class is absent**, including the
all-positive case. In particular, one-class evaluation must never
publish AP=1.0 as though held-out discrimination were demonstrated.
Train-only thresholds and the negative preregistered finding remain
unchanged.

The comparison is observational and exploratory. BP trials within a
graph are dependent; there are only four held-out graphs. The report
does not establish statistically significant association, general
failure prediction, a causal role for spectral localization or
transfer to quantum QLDPC decoding.

## Executed Phase 1E research finding — negative result preserved

GitHub Actions at commit
`eef0f67cdf96ddf0e550705dfd694500f8796657`
performed the complete 20-graph/720-trial run and successfully replayed
its full corpus offline.

- GitHub run: `42567988090`.
- Complete evidence SHA-256:
  `ee0dc4ea5868386b3e60bbdef20c9d5c2c8e4b43e5ae160847f0bb5069a69738`.
- Corpus archived as GitHub Actions artifact under that run, with a
  30-day retention period.

| BSC rate | Holdout frame failures | IPR AUROC | IPR average precision | Edge-density AUROC |
| --- | ---: | ---: | ---: | ---: |
| 4% | 6/48 | 0.404762 | 0.118056 | 0.738095 |
| 8% (primary) | 21/48 | **0.595238** | 0.537698 | 0.383598 |
| 12% | 29/48 | 0.445554 | 0.625000 | 0.576225 |

The preregistered primary signal criterion **was not met**. The primary
IPR value exceeded edge density but remained below 0.65. There was
no threshold rerun, metric substitution or post-hoc graph split change.
This is a retained negative observation, not evidence that spectral
localization can never predict decoding failures.

### Reproduce and independently replay

~~~sh
gprbuild -p -P qec_ada.gpr

uv run --no-project python scripts/phase1e_experiment.py run \
  /tmp/qecada-phase1e.json \
  --graphs 20 --trials 12 --variables 32 --checks 24 \
  --seed qecada-phase1e-001 --noise-bps 400,800,1200

uv run --no-project python scripts/phase1e_experiment.py verify \
  /tmp/qecada-phase1e.json

uv run --no-project python scripts/phase1e_memory.py \
  --checks 32 --variables 64
~~~

The experiment JSON is canonical sorted-key UTF-8 with an outer
SHA-256 identity. It retains source graphs/identities, independent
spectra, all explicit error sites, every min-sum BP trace, graph-blocked
splits, evaluation metrics and scientific-claim boundaries.

The offline verifier needs **no Ada binary**: it regenerates every
graph and error pattern, independently validates the embedded numerical
spectrum, replays all integer BP steps and recalculates held-out
metrics and the claim boundary. Self-consistently rehashing altered
BP traces, metrics, graph splits or source bytes must not pass.
The SHA-256 receipt is an internal consistency record, **not** a
third-party authenticated scientific witness.

## Research lineage and licensing

Independently implemented Ada and Python under MPL-2.0.
Research design sources, not copied implementations:
- `QSOLKCB/QEC` commit
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`: spectral diagnostics
  and deterministic BP methodology.
- `multimodalas/fusion-qec` commit
  `a390f57d3da2647ef8d835a7407ad0eb03d03093`: graph/decoder
  separation and controlled spectral experiments (CC BY 4.0).
- `QSOLKCB/SPECTRAL` commit
  `49401fa010ed673e3d3977ccd5e06d66b0d65096`: source-bound
  spectral observation and sonification boundaries (MIT).
- `QSOLKCB/OPT` commit
  `7556dd36acd53ed3ed538fd03b1db44e5c1ec869`: correctness-gated
  optimization principles (Apache-2.0).

## Next independent scientific milestones

- Increase the number of **held-out topologies** and independently
  validate uncertainty intervals by graph-blocked bootstrap.
- Introduce multiple codes/decoders and actual QEC BP baseline traces,
  *without editing the existing protected decoder*.
- Test pre-registered trapping-set/localization hypotheses on
  independently sourced QLDPC topologies.
- Separate statistical prediction claims from causal experiments and
  physical quantum hardware validation.
- Extend native graph format and dynamic sparse allocation beyond the
  present bounded 2,048-edge instrument only with new memory tests.

No change in physical-QEC threshold or fault-tolerance performance is
claimed by Phase 1E.
