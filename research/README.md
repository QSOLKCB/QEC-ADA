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
