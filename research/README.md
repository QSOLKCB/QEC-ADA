# Research

QEC-ADA research proposals live here, separate from implementation and
proof results. A proposal must identify its mathematical model, reference
fixtures, error conditions and validation method before activation.

Historical QEC research papers and plans are preserved unmodified at
`docs/reference/qec/research/`; they are **not** evidence that QEC-ADA
implements those experiments.

## Phase 1E controlled spectral prediction pilot

`scripts/phase1e_reference.py` contains an independently implemented
deterministic classical GF(2) min-sum BP experiment, source generator and
matrix-free eigenvalue reference. It does not import QEC's protected
decoder or alter native Ada correction decisions.

`scripts/phase1e_experiment.py` records all graph, noise, message
iteration and prediction outputs as a single canonical replayable corpus.
The initial result **did not** meet the preregistered IPR held-out
prediction criterion. The negative result and limitations are retained
in [Phase 1E](../docs/PHASE1E_SCALED_SPECTRAL_BP.md).

## Phase 1F independent inference and QEC reference lane

`scripts/phase1f_blocked_inference.py` reports **graph-cluster**
uncertainty for the frozen Phase 1E experiment, plus an exact
graph-label permutation check. These are exploratory bounds from only
four held-out topologies, not a revised post-hoc predictive result.

`scripts/phase1f_qec_bp_bridge.py` provides an opt-in real-QEC
source-pinned baseline comparison on explicitly matched classical
binary graph/channel inputs. It requires the verified original QEC
source and NumPy, and must not be confused with a parity reproduction
of its full joint quantum BP model.

The receipts and their limitations are documented in
[Phase 1F](../docs/PHASE1F_GRAPH_BLOCKED_QEC_BP.md).

## Phase 1G: source-verifiable CSS code family cohort

`scripts/phase1g_pinned_css.py` explicitly executes the pinned
QEC `create_code` for 24 bounded CSS instances, independently checks
binary GF(2) orthogonality and code provenance, then measures
read-only Tanner spectrum and classical BP errors.
`rate_0.75` is held out by entire family; training graphs are from
`rate_0.50` and `rate_0.60`. Multiple seeds from one generator
are not equivalent to independent external QLDPC datasets.

See [Phase 1G](../docs/PHASE1G_QEC_CSS_FAMILY.md) for
the complete experimental contract and claim limits.

## Phase 1H — externally published CSS parity-matrix cohort

`scripts/phase1h_external_css.py` reads nine CSS check pairs
from Simula UiB NISQEC and a separate explicit QLDPC matrix database.
All files are verified by exact source commit and Git blob; no data
provider code is executed. CSS orthogonality, GF(2) rank, duplicate
topology and native scale are checked before the read-only spectrum
and controlled classical BP study. Only the pre-existing opt-in
QSOLKCB/QEC reference `bp_decode` runs as a third-party executable.

The repository with unspecified licensing is never redistributed
as raw matrices. Source/publisher is the holdout boundary; the
small, heterogeneous cohort and negative IPR result cannot validate
a universal quantum-decoder failure predictor. See
[Phase 1H](../docs/PHASE1H_EXTERNAL_CSS.md).
