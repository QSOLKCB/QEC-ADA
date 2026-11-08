# Command-line interfaces

Two separate entry points serve different purposes:

- **Native Ada execution:** `build/bin/qec_ada` (or `.exe` on Windows)
  after `gprbuild -p -P qec_ada.gpr`. Commands: `--help`,
  `--version`, `selftest`, `gf3 add`, `gf3 mul`, `gf3 neg`,
  `syndrome C1 C2 C3 E1 E2 E3`. Mathematical results go to stdout;
  invalid commands/trits return non-zero status. No machine JSON protocol yet.
- **Python standard-library companion:** `scripts/qecada.py`.
  Commands: `docs list [--json]`, `docs search TERM [--json]`,
  `docs show SOURCE_RELATIVE_PATH`, `verify`, `status`, `gui`.

For automation, prefer `docs list --json` to parsing formatted text, and
`verify` for exact reference byte identity.

These are separate binaries: the Python companion does not interpret Ada
results, and the GUI does not execute native Ada code.
