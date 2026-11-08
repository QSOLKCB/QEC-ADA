--  SPDX-License-Identifier: MPL-2.0
with QEC_GF3;
package QEC_Invariants with SPARK_Mode => On is
   use type QEC_GF3.Trit;

   --  Reviewable mathematical claims; GNATprove execution is a separate gate.
   function Addition_Commutative
     (A, B : QEC_GF3.Trit) return Boolean is
     (QEC_GF3.Add (A, B) = QEC_GF3.Add (B, A));

   function Multiplication_Commutative
     (A, B : QEC_GF3.Trit) return Boolean is
     (QEC_GF3.Multiply (A, B) = QEC_GF3.Multiply (B, A));

   function Additive_Inverse
     (A : QEC_GF3.Trit) return Boolean is
     (QEC_GF3.Add (A, QEC_GF3.Negate (A)) = 0);

end QEC_Invariants;
