# QEC-ADA Phase 1C — Native Tanner/SPECTRAL and Strowger baseline

## Current bounded implementation

A separate native executable `qec_research` provides two observational
subsystems. The existing `qec_ada` decoder, Phase 1A/1B equivalence tests,
formal proof scope and pinned historical reference are unchanged.

### 1. Exact Tanner graph + non-backtracking fourth moment

`qec_research tanner N ROW1 [ROW2 ... ROW4]`

- `N` is 1–5 variables; 1–4 GF(3) parity-check support rows.
- Each row has exactly 2*N ternary symbols, X then Z.
- A single undirected Tanner edge (check, variable) is present whenever
  either corresponding X or Z symbol is nonzero.
- The output retains separate counts for X, Z and mixed-support edges;
  a mixed X/Z support is **one** graph edge, not two.
- Edges and printed output use stable check-major, variable-major ordering.
- Exact variable/check degrees, 4-cycle counts and variable 4-cycle
  participation (“cycle heat”) are computed over integers.
- The 4th non-backtracking spectral moment is calculated as
  `trace(B^4)` by **sparse directed-edge transitions**, not a
  dense matrix nor eigensolver.
- A graph identity checks `trace(B^4) == 8 × number_of_4_cycles`
  for this simple undirected graph. This is an exact low-order moment,
  **not** a dominant eigenvalue, spectral radius, IPR, trapping-set
  detector, phase diagram, or proof of decoder failure.
- Graph observation accepts any well-formed bounded matrix, even where
  checks do not commute or a radius-one decoder cannot be constructed.
  No corrective action or control authority exists in this layer.

This implements a small but meaningful native foundation for
deterministic Tanner graph analysis. The more advanced non-backtracking
dominant eigenpair, IPR, edge energy, NB localization and instability
estimation remain separately scoped research work.

### 2. Native classical Strowger baseline

`qec_research strowger DDDD RRRR LLLL AAAA BBBB FAULT`

- Four digits each in the corresponding radix 2–9, zero encoded as
  a full-radix pulse train.
- Explicit four-slot linefinder and two selector banks;
  contact map: `1=free`, `0=busy`, `Q=quarantined`.
- First-free selection; deterministic pulse/event order and monotonic
  logical ticks. No host clock, random number, network or global state.
- Faults: `none`, `miss1..4`, `dup1..4`, `stuck1..2`,
  `route`, `check`, `dark`.
- Three deterministic integer tone witnesses; mismatch fails closed.
  All outcomes emit structured events; rejected outcomes have no
  partially successful resource selection.
- Capacity is fixed to 64 trace events, with checked overflow.
- This is a **single-invocation preview**; it does not establish
  concurrent reservations, real electromechanical operation, operator
  authorization, physical quantum routing, or interoperability with
  the historical QEC Strowger receipt schema.

This native output is the source for an independent Python-stdlib
receipt builder and replay validator; receipt construction and validation
must use the same explicit input and independently recompute all
events, not merely compare checksums.

## SPECTRAL integration

SPECTRAL repository: `QSOLKCB/SPECTRAL`, pinned source
`49401fa010ed673e3d3977ccd5e06d66b0d65096`, in particular `QEC/APP/README.md`.

SPECTRAL QEC Sonification Laboratory accepts
`cycle,qubit,error,syndrome,correction,residual` event datasets.
A separate interoperability adapter will export *actual* native decoder
results in that format. Tanner observations remain **separate** graph
datasets, never disguised as measured quantum errors or sonification
evidence.

SPECTRAL itself is MIT-licensed, the original `fusion-qec`
architecture is CC BY 4.0, and QEC-ADA is MPL-2.0. This phase is
independently written Ada/Python, with source attribution; no donor
code has been copied or relicensed.

## Source and research boundaries

- QEC-ADA Phase 1B baseline:
  `9d42f6677884e0167c1aa32d5c053d96b9529d10`.
- `multimodalas/fusion-qec` at
  `a390f57d3da2647ef8d835a7407ad0eb03d03093`:
  deterministic traversal, canonical tie-breaking, Tanner export,
  and strict decoder/analysis separation.
- `QSOLKCB/QEC` pinned Strowger donor:
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`.
- `QSOLKCB/SPECTRAL`: deterministic sonification and observation
  contracts, not physical QEC validation.

## Validation

The Python standard-library test oracle reconstructs Tanner graphs
independently, computes the directed-edge nonbacktracking matrix and
checks its 4th trace. It also tests repeated output, a complete
2-check/3-variable support-pattern sweep, 4-cycle participation and
fail-closed Strowger faults.

The existing native Ada correctness, independently checked historical
QEC provenance, benchmark and isolated SPARK GF(3) proof suites remain
required. The existing **28 proved SPARK GF(3) checks** do not become
proof of the new Tanner or switching modules.
