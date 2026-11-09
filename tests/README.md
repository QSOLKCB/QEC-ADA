# Test policy

Run `uv run --no-project python -m unittest discover -s tests -v` to
verify the Python-stdlib catalogue, byte identity, arithmetic fixture
expectations, source layout and (when built) native Ada CLI outputs.

Native build:
`gprbuild -p -P qec_ada.gpr`

Optional native smoke:
`build/bin/qec_ada selftest` and
`build/bin/qec_ada syndrome 1 2 1 2 0 1`.

Tests of a three-trit demo do not establish general decoder parity or
scientific quantum-error-correction performance. Formal SPARK proofs require
their own separately executed GNATprove gate.

## Phase 1F evidence acceptance

`test_phase1f_inference.py` tests graph-blocking, one-class bootstrap
replicates, deterministic inference and hash-forgery rejection.
`test_phase1f_qec_bp.py` adds explicit pinned-source opt-in tests;
genuine QEC BP execution and replay are exercised only in a separate
CI lane with verified `.donor-qec-bp` and optional NumPy. They never
change the core Ada regression tests.

## Phase 1G source admission acceptance

`test_phase1g.py` covers integer-GF(2) CSS commutation, exact row
rank, source pin/admission failure, opt-in gating and whole-family
split/missing-class behavior. CI additionally executes actual
QEC-generated CSS matrices and both BP implementations, then
independently **reexecutes** the exact-source-bound cohort. These
integration tests activate only with a separately pinned QEC checkout,
NumPy and a completed receipt, without modifying core Ada regression
results.

## Phase 1H external CSS admission gates

`test_phase1h.py` exercises strict dense binary and Matrix Market
COO parsing, CSS GF(2) orthogonality and rank, exact source
manifests, one-class metrics, and execution opt-in. In the pinned
reference CI lane it also verifies all nine external H_X/H_Z
matrix pairs, whole-publisher leakage separation, complete BP
traces and the **full source-reexecution** of the receipt.
The raw third-party matrices are never committed or uploaded;
the derived-only artifact is not a redistribution grant for
unlicensed source data.
