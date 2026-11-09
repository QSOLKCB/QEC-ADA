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
