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
