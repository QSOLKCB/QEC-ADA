--  SPDX-License-Identifier: MPL-2.0
--  Exact, bounded, fixed cyclic [[5,1,3]]_3 qutrit code.
--  Reference structure: QEC src/qec/decoder/qutrit/codes.py at
--  27bbc798c4e38138ca5b0fff70b15c3271a1917d.
--  This is NOT a general stabilizer-code decoder or a hardware result.
with QEC_GF3;
package QEC_Qutrit is
   subtype Site_Index is Positive range 1 .. 5;
   subtype Check_Index is Positive range 1 .. 4;

   type Pauli is record
      X : QEC_GF3.Trit_Vector (Site_Index) := (others => 0);
      Z : QEC_GF3.Trit_Vector (Site_Index) := (others => 0);
   end record;

   type Syndrome_Vector is array (Check_Index) of QEC_GF3.Trit;
   type Lookup_Result is record
      Found      : Boolean := False;
      Correction : Pauli;
   end record;
   type Decode_Result is record
      Syndrome   : Syndrome_Vector;
      Found      : Boolean;
      Correction : Pauli;
      Residual   : Pauli;
      Success    : Boolean;
   end record;

   function Zero return Pauli;
   function Check_X (Row : Check_Index; Site : Site_Index)
     return QEC_GF3.Trit;
   function Check_Z (Row : Check_Index; Site : Site_Index)
     return QEC_GF3.Trit;
   function Scalar_Syndrome (Error : Pauli) return Syndrome_Vector;
   function OPT_Syndrome (Error : Pauli) return Syndrome_Vector;
   function Inverse (Error : Pauli) return Pauli;
   function Compose (Left, Right : Pauli) return Pauli;
   function Is_Stabilizer (Error : Pauli) return Boolean;
   function Lookup (Syndrome : Syndrome_Vector) return Lookup_Result;
   function Correct (Error : Pauli) return Decode_Result;
   function Leader_Count return Natural;
   function Exhaustive_Parity return Boolean;
end QEC_Qutrit;
