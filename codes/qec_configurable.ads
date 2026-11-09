--  SPDX-License-Identifier: MPL-2.0
--  Bounded generic GF(3) stabilizer-code adapter. Not a complete QEC decoder.
--  An optimized contribution table is bundled with its immutable code snapshot.
with QEC_GF3;
package QEC_Configurable is
   subtype Trit is QEC_GF3.Trit;
   Max_Sites  : constant Positive := 5;
   Max_Checks : constant Positive := 4;
   subtype Site_Index is Positive range 1 .. Max_Sites;
   subtype Check_Index is Positive range 1 .. Max_Checks;
   type Trit_Row is array (Site_Index) of Trit;
   type Check_Matrix is array (Check_Index) of Trit_Row;
   type Error_Vector is record
      X : Trit_Row := (others => 0);
      Z : Trit_Row := (others => 0);
   end record;
   type Syndrome_Vector is array (Check_Index) of Trit;

   --  Values outside Sites/Rows must be zero; noncanonical padding is rejected.
   type Code_Definition is record
      Sites : Site_Index := 1;
      Rows  : Check_Index := 1;
      X     : Check_Matrix := (others => (others => 0));
      Z     : Check_Matrix := (others => (others => 0));
   end record;

   type Preparation_Status is
     (Ready, Noncanonical_Padding, Too_Many_Generators,
      Dependent_Generators, Noncommuting_Generators,
      Ambiguous_Bounded_Set);

   type Prepared_Code is private;
   type Correction_Result is record
      Found      : Boolean := False;
      Correction : Error_Vector;
   end record;
   type Decode_Result is record
      Syndrome   : Syndrome_Vector;
      Found      : Boolean;
      Correction : Error_Vector;
      Residual   : Error_Vector;
      Success    : Boolean;
   end record;

   function Zero return Error_Vector;
   function Prepare (Definition : Code_Definition) return Prepared_Code;
   function Status_Of (Model : Prepared_Code) return Preparation_Status;
   function Definition_Of (Model : Prepared_Code) return Code_Definition;
   function Same_Definition (Left, Right : Prepared_Code) return Boolean;
   function Valid_Error
     (Definition : Code_Definition; Error : Error_Vector) return Boolean;

   --  These functions raise Constraint_Error unless Model is ready and
   --  Error has zero symbols in every site outside the model's width.
   function Scalar_Syndrome
     (Model : Prepared_Code; Error : Error_Vector) return Syndrome_Vector;
   function OPT_Syndrome
     (Model : Prepared_Code; Error : Error_Vector) return Syndrome_Vector;
   function Lookup
     (Model : Prepared_Code; Syndrome : Syndrome_Vector)
     return Correction_Result;
   function Correct
     (Model : Prepared_Code; Error : Error_Vector) return Decode_Result;
   function Is_Stabilizer
     (Model : Prepared_Code; Error : Error_Vector) return Boolean;
   function Leader_Count (Model : Prepared_Code) return Natural;
   function Exhaustive_Parity (Model : Prepared_Code) return Boolean;

private
   subtype Local_Operator is Natural range 0 .. 8;
   type Contribution_Plan is array
     (Site_Index, Local_Operator, Check_Index) of Trit;
   subtype Syndrome_Key is Natural range 0 .. 80;
   type Leader is record
      Present : Boolean := False;
      Error : Error_Vector;
   end record;
   type Leader_Table is array (Syndrome_Key) of Leader;

   type Prepared_Code is record
      Definition : Code_Definition;
      State      : Preparation_Status := Noncanonical_Padding;
      Plan       : Contribution_Plan :=
        (others => (others => (others => 0)));
      Leaders    : Leader_Table := (others => (others => <>));
   end record;
end QEC_Configurable;
