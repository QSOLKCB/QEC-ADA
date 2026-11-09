# Phase 1D — Sparse Non-Backtracking Spectral Observatory

**Scope:** Independent, bounded native Ada spectral diagnostics for Tanner
graphs. No modifications to the decoder, routing decisions, archived QEC
references, receipts, GUI or audio waveform generator.

## Implemented

Use the existing phase 1C graph input syntax:

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_research spectral 2 1100 0012
./build/bin/qec_research spectral 3 111000 000111
./build/bin/qec_research spectral 3 110000 011000 101000
~~~

`spectral N ROW...` supports at most five variables and four check rows;
rows encode X|Z powers over GF(3). Both nonzero X and Z at a check/site
produce a **single Tanner edge**. All graphs must have canonical zero
padding, but decoder independence/commutation are deliberately **not**
required: spectral observation is not a correction decision.

Each undirected edge becomes two directed edges, in check-major then
variable-major, forward followed by reverse order. The sparse
non-backtracking operator is defined over these directed edges by

`B[e,f] = 1 iff target(e)==source(f) and source(e)!=target(f)`.

The implementation does **not** allocate a dense B or use SciPy, C
bindings, BLAS, ARPACK, global RNG, network or cloud services.

### Why SCCs matter

A naive power iteration on B fails for periodic cycles, disconnected
graphs and the common bipartite `-rho` eigenvalue. In particular, a
single four-cycle has two independent directed-cycle SCCs. QEC-ADA
computes sparse graph reachability in forward/reverse directions,
enumerates all strongly connected components deterministically, and
solves each **cyclic recurrent block** independently.

Within each nontrivial SCC, nonnegative Perron iterations use
`(I+B)`, which breaks periodicity without changing that block's Perron
eigenvector. Every candidate starts from an explicit uniform positive
vector, is iterated at most 4,000 times and must satisfy a relative
Collatz–Wielandt ratio spread of `1e-11`. The largest converged block
radius is selected. Numerical ties within `1e-9` are broken by the
lowest canonical directed-edge ID, and `dominant_tie_count` reports
the degeneracy.

The per-edge **mode energy** `|v[e]|^2/sum|v|^2` and inverse
participation ratio `sum energy[e]^2` are defined for the selected
block. Stable rankings use decreasing energy, then increasing edge ID.
EEEC is the sum of the top `ceil(sqrt(mode_edge_count))` energies.

**Important distinction:** The padded selected recurrent-block mode
need not be a right eigenvector of the **full reducible B** when
transient states point into the selected block. Its reported IPR and
edge rankings are therefore *local to the selected recurrent block*.
The block's spectral radius is the dominant spectral radius of the full
finite B (SCC diagonal blocks determine eigenvalues). The schema names
the scope explicitly as `selected-recurrent-block`.

### Evidence and numerical limitations

The solver reports:
- `status`: NO_EDGES, ACYCLIC, CONVERGED_NUMERIC, NOT_CONVERGED;
- number of SCCs, cyclic SCCs and tied dominant recurrent blocks;
- selected block's canonical root, edge support and iterations;
- floating numerical spectral radius, estimated Collatz bounds,
  L1 eigen-residual, IPR, EEEC, edge energies and stable ranking;
- exact inherited Phase 1C four-cycle count and NB trace(B^4).

For a graph with **no non-backtracking cycle**, the spectral radius
is exactly zero and no arbitrary eigenmode, IPR or ranking is fabricated.
A graph may have no 4-cycles yet have a nonzero spectral radius:
the six-cycle acceptance fixture demonstrates this.

`CONVERGED_NUMERIC` means the finite-precision iteration met its
declared residual/ratio stopping test, **not** an interval-arithmetic
proof. Collatz bounds are floating estimates, not outward-rounded
rigorous enclosures. If a cyclic block does not converge, fail closed
with NOT_CONVERGED; do not silently return a guessed eigenpair.
Requested precision, computational budget and runtime representation
are local experimental contracts, not portable performance guarantees.

All report floats are formatted with twelve digits after the decimal
point. Output identity is reproducible under the declared executable,
compiler, architecture and math runtime; universal cross-platform
bitwise equality is **not** claimed.

### Independent correctness oracles

`tests/test_phase1d.py` constructs B independently as a dense **test
oracle only** for tiny graphs. The native implementation itself remains
matrix-free. The tests check exact fourth moments, known Perron radii
and eigenmode statistics for:

- isolated edges and trees: nilpotent B, radius zero, no mode;
- one 4-cycle: rho=1, two cyclic modes, IPR=1/4;
- a 6-cycle with **zero 4-cycles**: rho=1, IPR=1/6;
- K2,3: rho=sqrt(2);
- K3,3: rho=2, IPR=1/18, EEEC=5/18;
- disconnected 4-cycles: canonical tie winner and mode support;
- complete K4,5: bounded 40-directed-edge case;
- all 64 possible 2-check/3-variable support patterns;
- malformed input and X/Z-label changes that leave graph topology
  invariant.

Known analytical values are independent of the production Ada solver.
The existing pinned-donor verification, exact 59,049-vector GF(3) OPT
parity, Phase 1B decoder tests, Phase 1C Strowger receipts and 24-bit
WAV checks remain mandatory. The isolated GNATprove GF(3) proof
**does not** prove this numeric spectral module.

## Research lineage

- **QSOLKCB/QEC** at `27bbc798c4e38138ca5b0fff70b15c3271a1917d`
  (MPL-2.0), especially `src/qec/diagnostics/_spectral_utils.py`,
  `spectral_nb.py`, `tanner_spectral_analysis.py`: sparse directed
  edge operators, dominant-mode and IPR research.
- **multimodalas/fusion-qec** at
  `a390f57d3da2647ef8d835a7407ad0eb03d03093`
  (CC BY 4.0), architectural separation between decoder, diagnostics
  and deterministic graph export. Concepts only, no implementation
  copied.
- **QSOLKCB/SPECTRAL** at
  `49401fa010ed673e3d3977ccd5e06d66b0d65096`
  (MIT), canonical observation and data-to-sonification principles.
- **QSOLKCB/OPT** at
  `7556dd36acd53ed3ed538fd03b1db44e5c1ec869`
  (Apache-2.0), correctness-gated optimization and early sparse
  reduction. No donor source copied.

The native Ada algorithm, Python test oracle and any optional JSON
adapter in this phase are new MPL-2.0 implementations, not a copied
upstream dependency or a physical QEC result.

## Next gates, explicitly outside Phase 1D

- Independent full-graph eigenvectors and block-coupling analysis for
  reducible operators, beyond recurrent-block modes.
- Adaptive sparse storage and scale-up beyond the 5×4 bounded pilot.
- Bethe–Hessian/QLDPC spectral experiments, trapping-set predictions,
  held-out BP failure correlation and topology repair.
- SPARK/why3 proofs for the spectral implementation and machine-checked
  floating-point error enclosures.
- Live SPECTRAL browser observation and waveform integration; native
  audio still uses separately bounded Phase 1C graph metrics.
