# QEC-ADA architecture

## Principles

QEC-ADA develops native, bounded kernels against independently specified,
versioned test vectors. Decoding, observation and governance retain separate
trust boundaries. No reference documentation implies feature completeness.

~~~text
  pinned QEC documents / fixtures
                   |
                   v
        mathematical contracts
                   |
           +-------+-------+
           |               |
       codes/GF(3)     invariants/SPARK
           |               |
           v               v
       decode/native --> independent verification
           |
           v
     native CLI (Ada)          gui/ (read-only docs + demo)
           |                            |
           +--- canonical future receipts <--+
~~~

The current CLI performs a bounded three-term GF(3) syndrome demo, not
general QEC. The GUI contains a separate JavaScript demonstration and
documentation browser. Neither one assumes authority over the other.

## Intended layers

1. `codes/` — exact algebraic types and field operations.
2. `decode/` — syndrome operators and future stable decoder contracts.
3. `invariants/` — executable and formally dischargeable properties.
4. `fixtures/` — immutable reference vectors and checked source identity.
5. `research/` — candidate experiments, no automatic promotion.
6. `src/` — CLI front-end without mathematical state hidden in the UI.
7. `gui/` — optional offline presentation, never proof authority.

Keep source metadata and baseline hashes immutable. No wall-clock or ambient
randomness in mathematics. Optional benchmarks must identify hardware,
compiler, and measurement limitations.

## Bounded native decoder + immutable routing extension

- `codes/qec_qutrit.*` contains the cyclic five-qutrit stabilizer checks,
  scalar and OPT-equivalent syndrome calculations, a fixed coset-leader
  table and independent stabilizer-span membership.
- `routing/qec_routing.*` implements first-free selection from explicit
  availability snapshots. It does not update state or create QEC receipts.
- Scalar parity, exhaustive optimization equivalence and negative-case
  checks are part of CI; reference identity is tied to the pinned QEC donor.
- The CLI is the only composition boundary. The offline GUI remains an
  educational document and GF(3) demonstration, not a native Ada decoder UI.

See [Phase 1A](PHASE1A_DECODER_ROUTING.md).
