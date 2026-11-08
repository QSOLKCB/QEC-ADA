# Decode

Native decoding layers consume exact symbols from `codes/`.
Keep contracts pure and deterministic; do not import GUI or benchmark
layers into decoding.

Current scope: a three-term single parity-check syndrome demonstration,
with explicit trit input validation in the CLI. General QEC decoding and
equivalence to historical Python decoders remain future work.
