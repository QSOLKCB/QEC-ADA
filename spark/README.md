# SPARK proof pilot — GF(3) arithmetic only

The units in this directory form an **independently specified bounded integer
model**, with exact postconditions for GF(3) addition, multiplication, additive
inverse and one-site symplectic arithmetic. The `Verify_Identities` procedure
states concrete algebraic relationships over the 0–2 domain.

They are not a proof of the configurable decoder, stabilizer row-rank
elimination, coset-leader construction, OPT cache binding, or QEC routing.

To execute with a locally installed compatible GNATprove:

~~~sh
sh scripts/prove_spark.sh
~~~

The command uses `--mode=all`, `--checks-as-errors=on` and
`--warnings=error`. A nonzero status must fail the proof gate. Merely compiling
these units, or seeing `SPARK_Mode => On` in the source, is not a proof.
Record the exact GNATprove version, source commit, analyzed units and any
unproved obligations. The runtime CI job does not silently claim that this
separate toolchain is present.

GNATprove can be installed separately through Alire when desired; there is no
added production runtime dependency or automatic remote service.
