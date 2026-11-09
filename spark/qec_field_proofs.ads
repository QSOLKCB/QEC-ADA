--  SPDX-License-Identifier: MPL-2.0
--  Standalone, precisely scoped SPARK proof target.
--  Independent integer model of GF(3); not a proof of the full QEC decoder.
package QEC_Field_Proofs with SPARK_Mode => On is
   subtype Trit is Integer range 0 .. 2;

   function Add (A, B : Trit) return Trit
     with Global => null,
          Post => Add'Result = (A + B) mod 3;

   function Multiply (A, B : Trit) return Trit
     with Global => null,
          Post => Multiply'Result = (A * B) mod 3;

   function Negate (A : Trit) return Trit
     with Global => null,
          Post => Negate'Result = (-A) mod 3;

   --  One-site (check_x * error_z - check_z * error_x) mod 3.
   function Symplectic
     (Check_X, Check_Z, Error_X, Error_Z : Trit) return Trit
     with Global => null,
          Post => Symplectic'Result =
            ((Check_X * Error_Z - Check_Z * Error_X) mod 3);

   procedure Verify_Identities with Global => null;
end QEC_Field_Proofs;
