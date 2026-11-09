--  SPDX-License-Identifier: MPL-2.0
--  Mathematical GF(3) kernel. All operations are exact modulo three.
package QEC_GF3 with SPARK_Mode => On is
   type Trit is mod 3;
   type Trit_Vector is array (Positive range <>) of Trit;

   function Add (Left, Right : Trit) return Trit
     with Global => null,
          Post => Add'Result = Left + Right;

   function Multiply (Left, Right : Trit) return Trit
     with Global => null,
          Post => Multiply'Result = Left * Right;

   function Negate (Value : Trit) return Trit
     with Global => null,
          Post => Negate'Result + Value = 0;

   function Dot (Coefficients, Errors : Trit_Vector) return Trit
     with Global => null,
          Pre => Coefficients'First = Errors'First
            and then Coefficients'Last = Errors'Last;
end QEC_GF3;
