--  SPDX-License-Identifier: MPL-2.0
with QEC_GF3;
package QEC_Decode with SPARK_Mode => On is

   --  One parity-check row only; NOT a full quantum decoder.
   function Single_Check_Syndrome
     (Check : QEC_GF3.Trit_Vector;
      Error : QEC_GF3.Trit_Vector) return QEC_GF3.Trit
     with Global => null,
          Pre => Check'First = Error'First
            and then Check'Last = Error'Last;

end QEC_Decode;
