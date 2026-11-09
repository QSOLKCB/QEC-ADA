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
