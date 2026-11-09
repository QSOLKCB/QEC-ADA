--  SPDX-License-Identifier: MPL-2.0
with QEC_GF3;
package body QEC_Decode with SPARK_Mode => On is

   function Single_Check_Syndrome
     (Check : QEC_GF3.Trit_Vector;
      Error : QEC_GF3.Trit_Vector) return QEC_GF3.Trit is
   begin
      return QEC_GF3.Dot (Check, Error);
   end Single_Check_Syndrome;

end QEC_Decode;
