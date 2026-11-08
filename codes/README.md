# Codes and finite-field arithmetic

Native Ada source for finite fields and code structures belongs here.

Initial scope: GF(3) addition, multiplication, negation, dot product and a
small independent syndrome test. This is a finite arithmetic kernel, not a
full stabilizer-code decoder. See `../fixtures/gf3_vectors.json`.

Future field work must handle GF(4) polynomial arithmetic explicitly.
