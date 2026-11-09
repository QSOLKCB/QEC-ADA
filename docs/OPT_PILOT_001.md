# OPT-PILOT-001 — QEC-ADA fixed-qutrit syndrome reuse

**Status:** observational benchmark / exact parity confirmed. **Not** a general
QEC decoder speedup certification.

## Source identities

- Tested QEC-ADA commit: `f2f0b0086eebd719a630dd72a3da6ae42e148fdc`.
- CI run: `42551742636` (`validate` job, successful).
- Original QEC mathematical source pinned to commit
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`.
- OPT donor catalog at commit
  `7556dd36acd53ed3ed538fd03b1db44e5c1ec869`;
  patterns: OPT-INV-001 and OPT-REDUCE-001.
- Adaptation: independent Ada; no OPT source copied.

## Exactness preconditions

- Fixed cyclic [[5,1,3]]₃ stabilizer matrix, hard-coded and immutable.
- Every one of the **3^10 = 59,049** possible Pauli errors has the same
  scalar and optimized four-trit syndrome, executed in the native binary.
- All 40 weight-one errors correct; table contains 41 entries total
  (identity + 40 distinct errors) across 81 syndrome values.
- Benchmark path checksum equals **33457** for both execution paths;
  same ordered 59,049 inputs and reduction.

## Execution environment

GitHub-hosted Ubuntu 24.04 (x86_64), Linux
`7.0.0-1017-azure`, Python 3.12.3, GNAT 13.3 with GPRbuild, CI job
`128948625966`. Measurement includes process creation, initialization
and the entire fixed workload. No GPU is used.

- Warmups per path: 2.
- Repetitions: 7 per path.
- Alternating per-pair execution order.
- Clock: Python `time.perf_counter_ns`.
- No timeout or performance threshold changed based on observations.

## Raw observations (nanoseconds)

| Trial | Scalar | OPT |
| ---: | ---: | ---: |
| 1 | 13,257,789 | 7,861,430 |
| 2 | 13,180,424 | 7,804,141 |
| 3 | 13,307,116 | 7,969,008 |
| 4 | 13,187,680 | 8,011,361 |
| 5 | 13,233,825 | 7,830,134 |
| 6 | 13,011,050 | 7,771,928 |
| 7 | 13,069,642 | 7,819,851 |
| **Median** | **13,187,680** | **7,830,134** |

Observed scalar/OPT median ratio: **1.684221×**, for the
specified CI runner and tiny bounded workload only.

The observed difference is not a portable performance guarantee; the
baseline includes process startup, the compiler flags are not tuned,
multiple hardware populations have not been measured, and a short
workload does not establish end-to-end QEC gains.

## Repeat locally

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_ada selftest qutrit
uv run --no-project python scripts/bench_qutrit.py --trials 7 --warmups 2
~~~

The harness revalidates the output checksum before accepting every sample.
Do not silently promote the OPT path to a general code-definition cache:
changing the stabilizer checks invalidates the constant contribution plan.
A future generalized implementation needs a full code-definition identity
and a scalar equivalence fallback for every new code.
