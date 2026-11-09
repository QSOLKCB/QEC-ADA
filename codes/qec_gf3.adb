--  SPDX-License-Identifier: MPL-2.0
package body QEC_GF3 with SPARK_Mode => On is

   function Add (Left, Right : Trit) return Trit is
     (Left + Right);

   function Multiply (Left, Right : Trit) return Trit is
     (Left * Right);

   function Negate (Value : Trit) return Trit is
     (0 - Value);

   function Dot (Coefficients, Errors : Trit_Vector) return Trit is
      Accumulator : Trit := 0;
   begin
      for Index in Coefficients'Range loop
         Accumulator := Add
           (Accumulator, Multiply (Coefficients (Index), Errors (Index)));
      end loop;
      return Accumulator;
   end Dot;

end QEC_GF3;
