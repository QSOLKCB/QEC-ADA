# Phase 1A — Native exact qutrit decoder + deterministic routing pilot

## Implemented scope

The first genuine decoder in QEC-ADA targets the **fixed cyclic [[5,1,3]]₃
stabilizer code** from QSOLKCB/QEC. It represents an n=5 Pauli as 5 X trits
and 5 Z trits; its four checks use the exact GF(3) symplectic form

`sigma = check_x * error_z - check_z * error_x (mod 3)`.

The generator rows follow the original cyclic construction, shifting the
X supports (0,3) and Z supports (1,2) by 0,1,2,3 sites. Identity is stored
first; 40 weight-one non-identity errors are enumerated in ascending site
order, then local (X,Z) lexicographic order, retaining the first
representative per syndrome. There are 41 reachable syndrome representatives
of 81 possible syndrome words. Other syndromes fail closed. For reachable
syndromes, the correction is the additive inverse of the stored representative.
Success is checked independently by exhaustive stabilizer-span membership,
not just by testing whether the syndrome is zero.

**Donor identity:**
- QSOLKCB/QEC source commit:
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`;
- `src/qec/decoder/qutrit/gf3.py`, `stabilizer.py`, `codes.py`, `exact.py`;
- `docs/QUTRIT_HARMONIC_QEC.md`.

The QEC decoder source remains unchanged and frozen; QEC-ADA is independently
implemented in Ada, with Python-stdlib mathematical oracle tests. This
is a narrow parity target, not a claim that all historical QEC decoders exist
or that quantum hardware has been tested.

## OPT adaptation

**OPT-INV-001** and **OPT-REDUCE-001**, from QSOLKCB/OPT:

- Precompute each of 5 sites × 9 local (X,Z) operators × 4 check rows
  in a **constant**, per-code contribution table at program elaboration.
- The table's validity is bound to the exact hard-coded stabilizer definition.
  No mutable cache, cross-code reuse, hidden equivalence heuristic, async work
  or invalidation is needed for this fixed code.
- Accumulate only nonzero Pauli sites; identity sites contribute exactly zero.
- Keep `Scalar_Syndrome` as an independent, unoptimized oracle and test
  **all 3^10 = 59,049** possible error vectors for exact syndrome equality.
- Never prune the error search using heuristic approximations, change insertion
  order, skip collision checks or reuse output across different code instances.

The equivalence test is the **rollback gate**: if parity fails, disable the
precomputed path before shipping. No throughput claim is made in this PR
without bounded comparative measurements; fewer arithmetic operations is not
automatically an end-to-end performance improvement.

**OPT source:** QSOLKCB/OPT, `OPT-INV-001` and `OPT-REDUCE-001`
(catalogue Apache-2.0); the adaptation is independently written Ada under
QEC-ADA MPL-2.0. No OPT donor source is copied.

## Routing semantics

The `QEC_Routing` package follows the *principle* of QEC's deterministic
Strowger switching: choose first free (minimum index) linefinder, then first
free in each of two independent selector banks. A 4-trit address supplies
two selector levels and vertical/rotary connector digits.

The three four-position free/busy maps are immutable invocation snapshots.
A missing resource emits an explicit no-route outcome with **no partially
published reservation**, no hidden resource mutation and no retry choice
based on timing. `qec_ada route` is a pure route-selection preview, not a
real multi-request reservation engine.

**Not yet implemented:** mixed-radix pulse codecs, multiple dynamic selector
stages, first-free capacity reservation or release, deterministic event
streams, canonical JSON/SHA-256 hash-chained receipts, tone verification,
fault injection, operator permissions, packet networks and cross-era routing.

**Donor:** QSOLKCB/QEC `src/qec/routing/strowger/exchange.py`,
`model.py` and `docs/STROWGER_SYNDROME_EXCHANGE.md`.
No historical Strowger receipt compatibility is asserted.

## CLI

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_ada selftest qutrit
./build/bin/qec_ada selftest route
./build/bin/qec_ada qutrit syndrome 10000 00000
./build/bin/qec_ada qutrit decode 10000 00000
./build/bin/qec_ada qutrit lookup 0002
./build/bin/qec_ada route 1 2 0 1 0101 0011 1010
~~~

`qutrit decode` returns `status=CORRECTED` only when the resulting error
belongs to the stabilizer; it returns nonzero exit status on missing
representatives or detected uncorrected errors. Routing uses `1=free`,
`0=busy`. Failures are nonzero exit statuses and never claim a partial route.

## Executed/required acceptance

- Compile with GNAT/GPRbuild and run unit+native CLI tests.
- Independent Python oracle: all 81 syndrome words, all 40 weight-one
  errors, invalid inputs, and deterministic routing outcomes.
- Native exhaustive scalar/OPT parity across all 59,049 error vectors.
- Preserve older CLI and reference provenance checks.
- Formal GNATprove proofs and performance characterization are separate
  future gates. Until those run, no proof-discharge or speedup claim.

## Follow-up roadmap

Complete general GF(2)/GF(4) field kernels and multiple independent
code definitions, then support configurable stabilizer tables with explicit
identity binding. Add native receipt schema and deterministic event replay
only once their full input and rejection contracts are specified.

## OPT observational benchmark

Two native entry points run exactly the same ordered workload of 59,049
five-qutrit error vectors and fold every four-trit syndrome into a bounded
checksum. `benchmark qutrit scalar` calls the original scalar path;
`benchmark qutrit opt` uses the immutable contribution plan. Both must
produce **checksum 33457**. This benchmark checksum is a coverage witness,
**not** a cryptographic receipt.

~~~sh
./build/bin/qec_ada benchmark qutrit scalar
./build/bin/qec_ada benchmark qutrit opt
uv run --no-project python scripts/bench_qutrit.py --trials 7
~~~

The stdlib harness runs warmups and paired, alternating measurements and
reports raw end-to-end process durations, environment and medians as JSON.
Those observations include process startup and are valid only for the stated
runner/toolchain; they do not establish a universal native speedup or end-to-end
QEC throughput improvement. Correctness parity is required independently
before considering any performance result.
