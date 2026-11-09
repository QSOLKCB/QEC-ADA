# QEC-ADA SPARK-GF3-001 — Independently executed proof record

**Scope:** isolated `QEC_Field_Proofs` integer model under
`spark/qec_field_proofs.ad[sb]`. This does **not** constitute proof of
`QEC_Configurable`, the fixed decoder, Strowger routing, physical QEC
or the entire QEC-ADA repository.

## Reproducible execution

| Field | Evidence |
| --- | --- |
| GitHub Actions run | `42554134425` |
| Job | `128955965063` — prove-field-arithmetic-only |
| Source commit | `4f5db29752989cf6302a8150f8e08713ee0cc3a3` |
| Runner | GitHub-hosted `ubuntu-24.04` |
| Alire | 2.1.1, checksum-verified binary |
| GNATprove | 16.1.0, pinned through Alire (CI-only) |
| Why3 | 1.8.2+git |
| Solver suite | Alt-Ergo 2.6.1; cvc5 1.3.2; Z3 4.15.4 |
| Analysis | `--mode=all --level=2 --report=all -f` |
| Enforcement | `--checks-as-errors=on --warnings=error` |
| Result | **Success: all checks proved (28 checks)** |

Run link: https://github.com/QSOLKCB/QEC-ADA/actions/runs/42554134425

The run showed proved postconditions, termination/data-flow claims,
division checks and explicit algebraic assertions. The proof target covers:

- GF(3) addition and multiplication modulo three;
- additive inverse;
- one-site exact symplectic product
  `(check_x*error_z - check_z*error_x) mod 3`;
- commutativity/associativity/distributivity assertions in
  `Verify_Identities`.

It does **not** analyze the private code-snapshot implementation,
Gaussian-elimination rank validation, collision checks, stabilizer-span
enumeration, correction table or OPT contribution reuse. Those are covered
by executed bounded tests rather than formal proof in this phase.

The prover and compiler are CI-only dependencies; no added runtime stack
is necessary for the Ada command line or offline GUI.

To repeat locally with a matching toolchain:

~~~sh
sh scripts/prove_spark.sh
~~~

Nonzero exit is mandatory for warnings or unproved obligations. Record
the complete source SHA and prover version for any subsequent proof run.
