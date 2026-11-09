--  SPDX-License-Identifier: MPL-2.0
package body QEC_Field_Proofs with SPARK_Mode => On is

   function Add (A, B : Trit) return Trit is
     (Trit ((A + B) mod 3));

   function Multiply (A, B : Trit) return Trit is
     (Trit ((A * B) mod 3));

   function Negate (A : Trit) return Trit is
     (Trit ((-A) mod 3));

   function Symplectic
     (Check_X, Check_Z, Error_X, Error_Z : Trit) return Trit is
     (Trit ((Check_X * Error_Z - Check_Z * Error_X) mod 3));

   procedure Verify_Identities is
   begin
      for A in Trit loop
         pragma Assert (Add (A, 0) = A);
         pragma Assert (Add (A, Negate (A)) = 0);
         for B in Trit loop
            pragma Assert (Add (A, B) = Add (B, A));
            pragma Assert (Multiply (A, B) = Multiply (B, A));
            for C in Trit loop
               pragma Assert
                 (Add (Add (A, B), C) = Add (A, Add (B, C)));
               pragma Assert
                 (Multiply (A, Add (B, C)) =
                    Add (Multiply (A, B), Multiply (A, C)));
               pragma Assert
                 (Symplectic (A, B, C, 0) =
                    Add (0, Negate (Multiply (B, C))));
            end loop;
         end loop;
      end loop;
   end Verify_Identities;

end QEC_Field_Proofs;
