--  SPDX-License-Identifier: MPL-2.0
--  Configurable, value-bound GF(3) exact radius-one stabilizer decoder.
--  No global cache, timing, IO or mutable shared state.
package body QEC_Configurable is
   use type Trit;

   function Zero return Error_Vector is
   begin
      return (X => (others => 0), Z => (others => 0));
   end Zero;

   function Valid_Error
     (Definition : Code_Definition; Error : Error_Vector) return Boolean is
   begin
      for Site in Site_Index loop
         if Site > Definition.Sites
           and then (Error.X (Site) /= 0 or else Error.Z (Site) /= 0)
         then
            return False;
         end if;
      end loop;
      return True;
   end Valid_Error;

   function Validate_Padding
     (Definition : Code_Definition) return Boolean is
   begin
      for Row in Check_Index loop
         for Site in Site_Index loop
            if (Row > Definition.Rows or else Site > Definition.Sites)
              and then
                (Definition.X (Row) (Site) /= 0
                 or else Definition.Z (Row) (Site) /= 0)
            then
               return False;
            end if;
         end loop;
      end loop;
      return True;
   end Validate_Padding;

   function Independent
     (Definition : Code_Definition) return Boolean is
      --  Exact Gaussian elimination over GF(3), rank <= 4, width <= 10.
      type Work_Row is array (Positive range 1 .. 2 * Max_Sites) of Trit;
      type Work_Matrix is array (Check_Index) of Work_Row;
      Work : Work_Matrix := (others => (others => 0));
      Pivot_Rank : Natural := 0;
      Candidate : Natural;
      Temporary : Work_Row;
      Factor : Trit;
      Inverse_Pivot : Trit;
   begin
      for Row in 1 .. Definition.Rows loop
         for Site in 1 .. Definition.Sites loop
            Work (Row) (Natural (Site)) := Definition.X (Row) (Site);
            Work (Row) (Natural (Definition.Sites) + Natural (Site)) :=
              Definition.Z (Row) (Site);
         end loop;
      end loop;

      for Column in 1 .. 2 * Natural (Definition.Sites) loop
         exit when Pivot_Rank = Natural (Definition.Rows);
         Candidate := 0;
         for Row in Pivot_Rank + 1 .. Natural (Definition.Rows) loop
            if Work (Check_Index (Row)) (Column) /= 0 then
               Candidate := Row;
               exit;
            end if;
         end loop;
         if Candidate /= 0 then
            Pivot_Rank := Pivot_Rank + 1;
            if Candidate /= Pivot_Rank then
               Temporary := Work (Check_Index (Candidate));
               Work (Check_Index (Candidate)) :=
                 Work (Check_Index (Pivot_Rank));
               Work (Check_Index (Pivot_Rank)) := Temporary;
            end if;
            Inverse_Pivot :=
              (if Work (Check_Index (Pivot_Rank)) (Column) = 1
               then 1 else 2);
            for J in 1 .. 2 * Natural (Definition.Sites) loop
               Work (Check_Index (Pivot_Rank)) (J) :=
                 Work (Check_Index (Pivot_Rank)) (J) * Inverse_Pivot;
            end loop;
            for Row in 1 .. Definition.Rows loop
               if Natural (Row) /= Pivot_Rank then
                  Factor := Work (Row) (Column);
                  if Factor /= 0 then
                     for J in 1 .. 2 * Natural (Definition.Sites) loop
                        Work (Row) (J) := Work (Row) (J)
                          - Factor * Work (Check_Index (Pivot_Rank)) (J);
                     end loop;
                  end if;
               end if;
            end loop;
         end if;
      end loop;
      return Pivot_Rank = Natural (Definition.Rows);
   end Independent;

   function Commutes (Definition : Code_Definition) return Boolean is
      Sum : Trit;
   begin
      for A in 1 .. Definition.Rows loop
         for B in A .. Definition.Rows loop
            Sum := 0;
            for Site in 1 .. Definition.Sites loop
               Sum := Sum + Definition.X (A) (Site) *
                 Definition.Z (B) (Site)
                 - Definition.Z (A) (Site) * Definition.X (B) (Site);
            end loop;
            if Sum /= 0 then
               return False;
            end if;
         end loop;
      end loop;
      return True;
   end Commutes;

   function Validate
     (Definition : Code_Definition) return Preparation_Status is
   begin
      if not Validate_Padding (Definition) then
         return Noncanonical_Padding;
      elsif Natural (Definition.Rows) > Natural (Definition.Sites) then
         return Too_Many_Generators;
      elsif not Independent (Definition) then
         return Dependent_Generators;
      elsif not Commutes (Definition) then
         return Noncommuting_Generators;
      end if;
      return Ready;
   end Validate;

   function Build_Plan
     (Definition : Code_Definition) return Contribution_Plan is
      Result : Contribution_Plan :=
        (others => (others => (others => 0)));
   begin
      for Site in 1 .. Definition.Sites loop
         for X in Trit loop
            for Z in Trit loop
               for Row in 1 .. Definition.Rows loop
                  Result (Site, Natural (X) * 3 + Natural (Z), Row) :=
                    Definition.X (Row) (Site) * Z
                    - Definition.Z (Row) (Site) * X;
               end loop;
            end loop;
         end loop;
      end loop;
      return Result;
   end Build_Plan;

   function Scalar
     (Definition : Code_Definition; Error : Error_Vector)
      return Syndrome_Vector is
      Result : Syndrome_Vector := (others => 0);
   begin
      for Row in 1 .. Definition.Rows loop
         for Site in 1 .. Definition.Sites loop
            Result (Row) := Result (Row)
              + Definition.X (Row) (Site) * Error.Z (Site)
              - Definition.Z (Row) (Site) * Error.X (Site);
         end loop;
      end loop;
      return Result;
   end Scalar;

   function Fast
     (Definition : Code_Definition; Plan : Contribution_Plan;
      Error : Error_Vector) return Syndrome_Vector is
      Result : Syndrome_Vector := (others => 0);
      Operator : Local_Operator;
   begin
      for Site in 1 .. Definition.Sites loop
         if Error.X (Site) /= 0 or else Error.Z (Site) /= 0 then
            Operator := Natural (Error.X (Site)) * 3 +
              Natural (Error.Z (Site));
            for Row in 1 .. Definition.Rows loop
               Result (Row) := Result (Row) + Plan (Site, Operator, Row);
            end loop;
         end if;
      end loop;
      return Result;
   end Fast;

   function Minus (Error : Error_Vector) return Error_Vector is
      Result : Error_Vector := Zero;
   begin
      for Site in Site_Index loop
         Result.X (Site) := -Error.X (Site);
         Result.Z (Site) := -Error.Z (Site);
      end loop;
      return Result;
   end Minus;

   function Compose
     (Left, Right : Error_Vector) return Error_Vector is
      Result : Error_Vector := Zero;
   begin
      for Site in Site_Index loop
         Result.X (Site) := Left.X (Site) + Right.X (Site);
         Result.Z (Site) := Left.Z (Site) + Right.Z (Site);
      end loop;
      return Result;
   end Compose;

   function In_Span
     (Definition : Code_Definition; Error : Error_Vector)
      return Boolean is
      --  Enumerate all 3**Rows stabilizer products (at most 81).
      Limit : Natural := 1;
      Counter : Natural;
      Factor : Trit;
      Trial : Error_Vector;
   begin
      for Row in 1 .. Definition.Rows loop
         Limit := Limit * 3;
      end loop;
      for Combination in 0 .. Limit - 1 loop
         Trial := Zero;
         Counter := Combination;
         for Row in 1 .. Definition.Rows loop
            Factor := Trit (Counter mod 3);
            Counter := Counter / 3;
            for Site in 1 .. Definition.Sites loop
               Trial.X (Site) := Trial.X (Site)
                 + Factor * Definition.X (Row) (Site);
               Trial.Z (Site) := Trial.Z (Site)
                 + Factor * Definition.Z (Row) (Site);
            end loop;
         end loop;
         if Trial = Error then
            return True;
         end if;
      end loop;
      return False;
   end In_Span;

   function Key_Of
     (Definition : Code_Definition; Syndrome : Syndrome_Vector)
      return Syndrome_Key is
      Index : Natural := 0;
   begin
      for Row in 1 .. Definition.Rows loop
         Index := 3 * Index + Natural (Syndrome (Row));
      end loop;
      return Syndrome_Key (Index);
   end Key_Of;

   function Prepare (Definition : Code_Definition) return Prepared_Code is
      Model : Prepared_Code;
      Candidate : Error_Vector;
      Difference : Error_Vector;
      Index : Syndrome_Key;
   begin
      Model.Definition := Definition;
      Model.State := Validate (Definition);
      if Model.State /= Ready then
         return Model;
      end if;
      --  Snapshot and plan are returned in the same value. Reusing a plan
      --  against a different code is not an expressible API operation.
      Model.Plan := Build_Plan (Definition);
      Model.Leaders (0) := (Present => True, Error => Zero);
      for Site in 1 .. Definition.Sites loop
         for X in Trit loop
            for Z in Trit loop
               if X /= 0 or else Z /= 0 then
                  Candidate := Zero;
                  Candidate.X (Site) := X;
                  Candidate.Z (Site) := Z;
                  Index := Key_Of
                    (Definition, Fast (Definition, Model.Plan, Candidate));
                  if Model.Leaders (Index).Present then
                     Difference := Compose
                       (Candidate, Minus (Model.Leaders (Index).Error));
                     if not In_Span (Definition, Difference) then
                        Model.State := Ambiguous_Bounded_Set;
                        Model.Leaders :=
                          (others => (Present => False, Error => Zero));
                        return Model;
                     end if;
                  else
                     Model.Leaders (Index) :=
                       (Present => True, Error => Candidate);
                  end if;
               end if;
            end loop;
         end loop;
      end loop;
      return Model;
   end Prepare;

   function Status_Of
     (Model : Prepared_Code) return Preparation_Status is
   begin
      return Model.State;
   end Status_Of;

   function Definition_Of
     (Model : Prepared_Code) return Code_Definition is
   begin
      return Model.Definition;
   end Definition_Of;

   function Same_Definition
     (Left, Right : Prepared_Code) return Boolean is
   begin
      return Left.Definition = Right.Definition;
   end Same_Definition;

   procedure Require_Ready
     (Model : Prepared_Code) is
   begin
      if Model.State /= Ready then
         raise Constraint_Error with "invalid or ambiguous code";
      end if;
   end Require_Ready;

   function Scalar_Syndrome
     (Model : Prepared_Code; Error : Error_Vector)
      return Syndrome_Vector is
   begin
      Require_Ready (Model);
      if not Valid_Error (Model.Definition, Error) then
         raise Constraint_Error with "error outside code width";
      end if;
      return Scalar (Model.Definition, Error);
   end Scalar_Syndrome;

   function OPT_Syndrome
     (Model : Prepared_Code; Error : Error_Vector)
      return Syndrome_Vector is
   begin
      Require_Ready (Model);
      if not Valid_Error (Model.Definition, Error) then
         raise Constraint_Error with "error outside code width";
      end if;
      return Fast (Model.Definition, Model.Plan, Error);
   end OPT_Syndrome;

   function Lookup
     (Model : Prepared_Code; Syndrome : Syndrome_Vector)
      return Correction_Result is
      Index : Syndrome_Key;
   begin
      Require_Ready (Model);
      for Row in Check_Index loop
         if Row > Model.Definition.Rows and then Syndrome (Row) /= 0 then
            raise Constraint_Error with "noncanonical syndrome padding";
         end if;
      end loop;
      Index := Key_Of (Model.Definition, Syndrome);
      return (Found => Model.Leaders (Index).Present,
              Correction =>
                (if Model.Leaders (Index).Present
                 then Minus (Model.Leaders (Index).Error) else Zero));
   end Lookup;

   function Is_Stabilizer
     (Model : Prepared_Code; Error : Error_Vector) return Boolean is
   begin
      Require_Ready (Model);
      if not Valid_Error (Model.Definition, Error) then
         raise Constraint_Error with "error outside code width";
      end if;
      return In_Span (Model.Definition, Error);
   end Is_Stabilizer;

   function Correct
     (Model : Prepared_Code; Error : Error_Vector)
      return Decode_Result is
      Syndrome : constant Syndrome_Vector :=
        Scalar_Syndrome (Model, Error);
      Candidate : constant Correction_Result := Lookup (Model, Syndrome);
      Residual : constant Error_Vector :=
        (if Candidate.Found then Compose (Error, Candidate.Correction)
         else Error);
   begin
      return (Syndrome => Syndrome,
              Found => Candidate.Found,
              Correction => Candidate.Correction,
              Residual => Residual,
              Success => Candidate.Found
                and then In_Span (Model.Definition, Residual));
   end Correct;

   function Leader_Count (Model : Prepared_Code) return Natural is
      Count : Natural := 0;
   begin
      Require_Ready (Model);
      for Index in Syndrome_Key loop
         if Model.Leaders (Index).Present then
            Count := Count + 1;
         end if;
      end loop;
      return Count;
   end Leader_Count;

   function Exhaustive_Parity
     (Model : Prepared_Code) return Boolean is
      Error : Error_Vector;
      Counter : Natural;
      Limit : Natural := 1;
   begin
      Require_Ready (Model);
      for Site in 1 .. 2 * Natural (Model.Definition.Sites) loop
         Limit := Limit * 3;
      end loop;
      for Number in 0 .. Limit - 1 loop
         Error := Zero;
         Counter := Number;
         for Site in 1 .. Model.Definition.Sites loop
            Error.X (Site) := Trit (Counter mod 3);
            Counter := Counter / 3;
         end loop;
         for Site in 1 .. Model.Definition.Sites loop
            Error.Z (Site) := Trit (Counter mod 3);
            Counter := Counter / 3;
         end loop;
         if Scalar (Model.Definition, Error)
           /= Fast (Model.Definition, Model.Plan, Error)
         then
            return False;
         end if;
      end loop;
      return True;
   end Exhaustive_Parity;

end QEC_Configurable;
