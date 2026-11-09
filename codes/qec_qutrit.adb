--  SPDX-License-Identifier: MPL-2.0
--  OPT-INV-001: all site contributions depend ONLY on the one fixed
--  immutable 5-qutrit code. Precompute once, no mutable cross-code cache.
--  Scalar_Syndrome is the independent in-module equivalence oracle.
with QEC_GF3;
package body QEC_Qutrit is
   use type QEC_GF3.Trit;
   subtype Trit is QEC_GF3.Trit;

   function Zero return Pauli is
   begin
      return (X => (others => 0), Z => (others => 0));
   end Zero;

   function Check_X (Row : Check_Index; Site : Site_Index)
     return QEC_GF3.Trit is
      Offset : constant Natural :=
        (Natural (Site) - Natural (Row) + 5) mod 5;
   begin
      if Offset = 0 or else Offset = 3 then
         return 1;
      end if;
      return 0;
   end Check_X;

   function Check_Z (Row : Check_Index; Site : Site_Index)
     return QEC_GF3.Trit is
      Offset : constant Natural :=
        (Natural (Site) - Natural (Row) + 5) mod 5;
   begin
      if Offset = 1 or else Offset = 2 then
         return 1;
      end if;
      return 0;
   end Check_Z;

   function Scalar_Syndrome (Error : Pauli) return Syndrome_Vector is
      Result : Syndrome_Vector := (others => 0);
   begin
      for Row in Check_Index loop
         for Site in Site_Index loop
            Result (Row) := Result (Row)
              + Check_X (Row, Site) * Error.Z (Site)
              - Check_Z (Row, Site) * Error.X (Site);
         end loop;
      end loop;
      return Result;
   end Scalar_Syndrome;

   subtype Local_Operator is Natural range 0 .. 8;
   type Contribution_Plan is array
     (Site_Index, Local_Operator, Check_Index) of Trit;

   function Build_Contributions return Contribution_Plan is
      Plan : Contribution_Plan := (others => (others => (others => 0)));
   begin
      for Site in Site_Index loop
         for X in Trit loop
            for Z in Trit loop
               for Row in Check_Index loop
                  Plan (Site, Natural (X) * 3 + Natural (Z), Row) :=
                    Check_X (Row, Site) * Z - Check_Z (Row, Site) * X;
               end loop;
            end loop;
         end loop;
      end loop;
      return Plan;
   end Build_Contributions;

   --  Fully bound to a static code definition; no invalidation is needed.
   Contributions : constant Contribution_Plan := Build_Contributions;

   function OPT_Syndrome (Error : Pauli) return Syndrome_Vector is
      Result : Syndrome_Vector := (others => 0);
      Operator : Local_Operator;
   begin
      for Site in Site_Index loop
         --  OPT-REDUCE-001: skip identity sites without altering arithmetic.
         if Error.X (Site) /= 0 or else Error.Z (Site) /= 0 then
            Operator := Natural (Error.X (Site)) * 3
              + Natural (Error.Z (Site));
            for Row in Check_Index loop
               Result (Row) := Result (Row)
                 + Contributions (Site, Operator, Row);
            end loop;
         end if;
      end loop;
      return Result;
   end OPT_Syndrome;

   function Inverse (Error : Pauli) return Pauli is
      Result : Pauli := Zero;
   begin
      for Site in Site_Index loop
         Result.X (Site) := -Error.X (Site);
         Result.Z (Site) := -Error.Z (Site);
      end loop;
      return Result;
   end Inverse;

   function Compose (Left, Right : Pauli) return Pauli is
      Result : Pauli := Zero;
   begin
      for Site in Site_Index loop
         Result.X (Site) := Left.X (Site) + Right.X (Site);
         Result.Z (Site) := Left.Z (Site) + Right.Z (Site);
      end loop;
      return Result;
   end Compose;

   function Is_Stabilizer (Error : Pauli) return Boolean is
      --  Independently enumerate all 3**4 stabilizer combinations;
      --  this is exact and avoids floating-point elimination/rank.
      Trial : Pauli;
      Address_Word : Natural;
      Coefficient : Trit;
   begin
      for Combination in 0 .. 80 loop
         Trial := Zero;
         Address_Word := Combination;
         for Row in Check_Index loop
            Coefficient := Trit (Address_Word mod 3);
            Address_Word := Address_Word / 3;
            for Site in Site_Index loop
               Trial.X (Site) := Trial.X (Site)
                 + Coefficient * Check_X (Row, Site);
               Trial.Z (Site) := Trial.Z (Site)
                 + Coefficient * Check_Z (Row, Site);
            end loop;
         end loop;
         if Trial = Error then
            return True;
         end if;
      end loop;
      return False;
   end Is_Stabilizer;

   subtype Syndrome_Key is Natural range 0 .. 80;
   function Key_Of (Syndrome : Syndrome_Vector) return Syndrome_Key is
      Result : Natural := 0;
   begin
      for Row in Check_Index loop
         Result := 3 * Result + Natural (Syndrome (Row));
      end loop;
      return Syndrome_Key (Result);
   end Key_Of;

   type Leader is record
      Present : Boolean := False;
      Error   : Pauli;
   end record;
   type Leader_Table is array (Syndrome_Key) of Leader;

   function Build_Table return Leader_Table is
      Table : Leader_Table := (others => (Present => False, Error => Zero));
      Candidate : Pauli;
      Index : Syndrome_Key;
   begin
      --  The first representative wins, exactly like the QEC bounded
      --  enumerator: identity, increasing support, local (X,Z) lexicographic.
      Table (0) := (Present => True, Error => Zero);
      for Site in Site_Index loop
         for X in Trit loop
            for Z in Trit loop
               if X /= 0 or else Z /= 0 then
                  Candidate := Zero;
                  Candidate.X (Site) := X;
                  Candidate.Z (Site) := Z;
                  Index := Key_Of (OPT_Syndrome (Candidate));
                  if Table (Index).Present then
                     --  For this fixed distance-three code, no weight-one
                     --  collision is admissible; reject construction.
                     raise Program_Error with "qutrit syndrome collision";
                  end if;
                  Table (Index) := (Present => True, Error => Candidate);
               end if;
            end loop;
         end loop;
      end loop;
      return Table;
   end Build_Table;

   Leaders : constant Leader_Table := Build_Table;

   function Lookup (Syndrome : Syndrome_Vector) return Lookup_Result is
      Stored : constant Leader := Leaders (Key_Of (Syndrome));
   begin
      return
        (Found      => Stored.Present,
         Correction => (if Stored.Present then Inverse (Stored.Error)
                        else Zero));
   end Lookup;

   function Correct (Error : Pauli) return Decode_Result is
      S : constant Syndrome_Vector := Scalar_Syndrome (Error);
      Candidate : constant Lookup_Result := Lookup (S);
      Residual : constant Pauli :=
        (if Candidate.Found then Compose (Error, Candidate.Correction)
         else Error);
   begin
      return (Syndrome   => S,
              Found      => Candidate.Found,
              Correction => Candidate.Correction,
              Residual   => Residual,
              Success    => Candidate.Found and then Is_Stabilizer (Residual));
   end Correct;

   function Leader_Count return Natural is
      Count : Natural := 0;
   begin
      for Index in Syndrome_Key loop
         if Leaders (Index).Present then
            Count := Count + 1;
         end if;
      end loop;
      return Count;
   end Leader_Count;

   function Exhaustive_Parity return Boolean is
      --  Compare scalar and precomputed paths for every one of the 3**10
      --  possible X/Z error vectors of the fixed five-qutrit code.
      Trial : Pauli;
      Digit_Stream : Natural;
   begin
      if Leader_Count /= 41 then
         return False;
      end if;
      for Number in 0 .. 59_048 loop
         Trial := Zero;
         Digit_Stream := Number;
         for Site in Site_Index loop
            Trial.X (Site) := Trit (Digit_Stream mod 3);
            Digit_Stream := Digit_Stream / 3;
         end loop;
         for Site in Site_Index loop
            Trial.Z (Site) := Trit (Digit_Stream mod 3);
            Digit_Stream := Digit_Stream / 3;
         end loop;
         if Scalar_Syndrome (Trial) /= OPT_Syndrome (Trial) then
            return False;
         end if;
      end loop;
      --  Every weight-one error must decode to a stabilizer residual.
      for Site in Site_Index loop
         for X in Trit loop
            for Z in Trit loop
               if X /= 0 or else Z /= 0 then
                  Trial := Zero;
                  Trial.X (Site) := X;
                  Trial.Z (Site) := Z;
                  if not Correct (Trial).Success then
                     return False;
                  end if;
               end if;
            end loop;
         end loop;
      end loop;
      return Correct (Zero).Success;
   end Exhaustive_Parity;

   function Workload_Checksum (Optimized : Boolean) return Natural is
      --  Exact fixed workload for external timing: no clocks or output inside
      --  the pure math loop. Same order and checksum for both paths.
      Trial : Pauli;
      Counter : Natural;
      S : Syndrome_Vector;
      Result : Natural := 0;
   begin
      for Number in 0 .. 59_048 loop
         Trial := Zero;
         Counter := Number;
         for Site in Site_Index loop
            Trial.X (Site) := Trit (Counter mod 3);
            Counter := Counter / 3;
         end loop;
         for Site in Site_Index loop
            Trial.Z (Site) := Trit (Counter mod 3);
            Counter := Counter / 3;
         end loop;
         if Optimized then
            S := OPT_Syndrome (Trial);
         else
            S := Scalar_Syndrome (Trial);
         end if;
         for Row in Check_Index loop
            Result := (Result * 3 + Natural (S (Row))) mod 65_521;
         end loop;
      end loop;
      return Result;
   end Workload_Checksum;

end QEC_Qutrit;
