# QEC-ADA Phase 1B — Configurable GF(3) Stabilizer Decoding

## Scope

This phase introduces a separately implemented, **bounded configurable decoder**
in `codes/qec_configurable.ads/.adb`. The original fixed-code Phase 1A
`QEC_Qutrit` API, its 41-entry table and its OPT timings remain unchanged.

**Declared limits:** 1–5 physical qutrit sites, 1–4 independent commuting
stabilizer rows, 0/1/2 symbols only, correction radius **exactly one**.
This is a finite software model; not a universal stabilizer-code decoder.

An input code is fully described by `Sites`, `Rows` and row-major
`X` and `Z` check matrices, with unused entries required to be zero.
Code creation rejects noncanonical padding, more checks than sites,
dependent generators and noncommuting generators before attempting a decoder.

For the first radius-one coset-leader table, candidates are enumerated
identity first, then site order, then local X/Z order. A syndrome collision
is accepted **only if the difference of the two errors is in the stabilizer
subspace** (quantum-degenerate equality). Otherwise, construction fails
`AMBIGUOUS_BOUNDED_SET`. The first valid representative retains precedence.

A decoder correction returns the inverse representative; the residual is
checked for membership in the full stabilizer span. A **zero syndrome is
not enough** to claim correction.

## OPT reuse is bound to the code definition

`QEC_Configurable.Prepare(Definition)` copies the *complete* code
definition and constructs a 5×9×4 lookup table of site contributions
inside a private `Prepared_Code` value. Neither the contribution plan nor
the code snapshot can be mutated through the public API.

The optimized function accepts **only the prepared value containing both
the source code definition and its plan**. It cannot be handed a plan
from one code and a separate definition from another. No process-wide cache,
fingerprint-only equality, heuristic key or cross-code reuse exists.

This adaptation follows OPT-INV-001 and OPT-REDUCE-001 but uses no imported
OPT source. The scalar path recomputes the symplectic product directly
from the frozen definition and provides an independent regression oracle.

For this bounded implementation, `Exhaustive_Parity` enumerates all
`3^(2n)` possible Pauli errors and requires exact scalar/optimized
syndrome equality. The maximum deployed domain is 59,049 errors.

## Examples

~~~sh
gprbuild -p -P qec_ada.gpr

# Existing fixed-code implementation remains available:
./build/bin/qec_ada qutrit decode 10000 00000

# Configurable n=2 product-state code. Two commuting generators:
# Row 1 = X:00 Z:10, Row 2 = X:00 Z:01.
./build/bin/qec_ada config decode 2 10 01 0010 0001

# n=1, one Z stabilizer; weight-one degeneracy is handled exactly:
./build/bin/qec_ada config decode 1 0 1 01

# Cyclic n=5, four rows generated independently from original QEC code:
./build/bin/qec_ada selftest config
~~~

`config syndrome|decode N X Z ROW1 ...` takes **1–4** rows; each
row has exactly `2*N` ternary characters and is ordered `X|Z`.
The correction table is valid only if the radius-one error set satisfies
the correctability condition. Missing syndrome representatives return
nonzero status. Input and code validation failures emit an explicit status.

## Test coverage and evidence

The independent Python standard-library oracle reconstructs each code
mathematically without importing the original QEC decoder or Ada sources.
It checks the 40 cyclic single-site errors, all 81 error vectors of a two-qutrit
product-state code, including radius-one rejection, all nine errors in a one-qutrit degenerate code,
ambiguous radius-one sets, noncommutation, rank deficiency, input
rejection and code-context switches.

The native `selftest config` also constructs code A → code B → code A
and runs exhaustive scalar/OPT parity checks, ensuring reusable
precomputation does not escape its immutable code snapshot.

**Completed initial proof pilot:** GNATprove 16.1.0 proved 28/28 checks
in the separate GF(3) arithmetic model at commit `4f5db297...`.
See [SPARK-GF3-001](PHASE1B_SPARK_PROOF.md) for executed tool versions and
scope. This is **not** formal proof of the configurable decoder or OPT
tables; those remain bounded-test validated.

## Attribution

Independent Ada implementation follows the algebra and ordering
defined by QSOLKCB/QEC source commit
`27bbc798c4e38138ca5b0fff70b15c3271a1917d`,
`src/qec/decoder/qutrit/{gf3,stabilizer,codes,exact}.py`.
Optimization patterns: QSOLKCB/OPT OPT-INV-001, OPT-REDUCE-001,
donor commit `7556dd36acd53ed3ed538fd03b1db44e5c1ec869`.
All copied historical QEC Markdown documents remain unchanged.

## Deliberately not yet implemented

- Configurable weight ≥2 decoding and larger stabilizer matrices.
- Binary/quaternary GF(2)/GF(4) decoders.
- Canonical SHA-256 decoder receipts and independent replay.
- Dynamic Strowger route reservation, pulse timing, tones and fault plans.
- End-to-end quantum hardware or fault-tolerance validation.

Those are separate phases with their own acceptance gates.
