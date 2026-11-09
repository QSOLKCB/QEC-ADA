# SPECTRAL / Tanner graph observation

Native graph source: `qec_tanner.ads`, `qec_tanner.adb`.
No external libraries, floating-point eigenvalues or dense spectral
operators. The implementation counts exact degree, four-cycle and
non-backtracking fourth-moment information.
See [scope and evidence](../docs/PHASE1C_TANNER_SPECTRAL.md).

## Phase 1D — Sparse SCC-aware NB mode

`qec_nb_spectral.ads/.adb` builds the non-backtracking transition
operator implicitly over directed Tanner edges, finds recurrent
strongly connected components, estimates Perron radii with lazy
`I+B` iterations and reports block-local IPR, EEEC and ranked edge
energies. It does not build a dense matrix or change decode/routing
decisions. See [technical contract](../docs/PHASE1D_SPARSE_SPECTRAL.md).

### Replayable export

`scripts/nb_spectral_export.py` creates a canonical source-bound
spectral receipt and validates it independently of the Ada executable.
The read-only adapter rejects altered model scores, SCCs, float
encoding and forged self-consistent JSON hashes. It is not a live
SPECTRAL/APP render recipe nor an authenticated physical measurement.

## Phase 1E — Larger sparse Tanner graphs

`qec_scaled_spectral.ads/.adb` uses bounded O(V+E) arrays for canonical
Tanner edge lists, sparse in/out adjacency, iterative SCC decomposition and
recurrent-block Perron modes up to 128+128 nodes and 2,048 edges.
`src/qec_scale.adb` is a separate, read-only native CLI.

It does not modify the existing small-graph `qec_nb_spectral`, GF(3)
decoder or SPECTRAL WAV/receipt engine. Analytical K(m,n) and long-cycle
fixtures are enforced by `tests/test_phase1e_scale.py`.
See [methods](../docs/PHASE1E_SCALED_SPECTRAL_BP.md).
