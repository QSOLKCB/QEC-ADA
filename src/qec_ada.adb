--  SPDX-License-Identifier: MPL-2.0
--  Narrow first native CLI; no Python runtime or external package.
with Ada.Command_Line;
with Ada.Strings;
with Ada.Strings.Fixed;
with Ada.Text_IO;
with QEC_Decode;
with QEC_GF3;
with QEC_Invariants;

procedure QEC_ADA is
   use Ada.Command_Line;
   use Ada.Text_IO;

   function Parse_Trit (Position : Positive) return QEC_GF3.Trit is
      Text : constant String := Argument (Position);
   begin
      if Text'Length /= 1
        or else Text (Text'First) not in '0' .. '2'
      then
         raise Constraint_Error;
      end if;
      return QEC_GF3.Trit
        (Character'Pos (Text (Text'First)) - Character'Pos ('0'));
   end Parse_Trit;

   procedure Put_Result (Value : QEC_GF3.Trit) is
   begin
      Put_Line
        (Ada.Strings.Fixed.Trim
           (Integer'Image (Integer (Value)), Ada.Strings.Both));
   end Put_Result;

   procedure Check_Field is
   begin
      for A in QEC_GF3.Trit loop
         if not QEC_Invariants.Additive_Inverse (A) then
            raise Program_Error;
         end if;
         for B in QEC_GF3.Trit loop
            if not QEC_Invariants.Addition_Commutative (A, B)
              or else not QEC_Invariants.Multiplication_Commutative (A, B)
            then
               raise Program_Error;
            end if;
         end loop;
      end loop;
      Put_Line ("PASS GF(3) small-domain identities");
   end Check_Field;

   procedure Usage is
   begin
      Put_Line ("QEC-ADA - independent native GF(3) pilot");
      Put_Line ("Usage:");
      Put_Line ("  qec_ada --help");
      Put_Line ("  qec_ada --version");
      Put_Line ("  qec_ada selftest");
      Put_Line ("  qec_ada gf3 add TRIT TRIT");
      Put_Line ("  qec_ada gf3 mul TRIT TRIT");
      Put_Line ("  qec_ada gf3 neg TRIT");
      Put_Line ("  qec_ada syndrome C1 C2 C3 E1 E2 E3");
      Put_Line ("TRIT must be exactly one digit: 0, 1, or 2.");
      Put_Line ("Only a three-term GF(3) single-check demo is implemented.");
   end Usage;

begin
   if Argument_Count = 0 then
      Usage;
   elsif Argument (1) = "--help" then
      Usage;
   elsif Argument (1) = "--version" then
      Put_Line ("QEC-ADA 0.1.0-dev");
   elsif Argument_Count = 1
     and then Argument (1) = "selftest"
   then
      Check_Field;
   elsif Argument_Count = 4
     and then Argument (1) = "gf3"
     and then Argument (2) = "add"
   then
      Put_Result (QEC_GF3.Add (Parse_Trit (3), Parse_Trit (4)));
   elsif Argument_Count = 4
     and then Argument (1) = "gf3"
     and then Argument (2) = "mul"
   then
      Put_Result (QEC_GF3.Multiply (Parse_Trit (3), Parse_Trit (4)));
   elsif Argument_Count = 3
     and then Argument (1) = "gf3"
     and then Argument (2) = "neg"
   then
      Put_Result (QEC_GF3.Negate (Parse_Trit (3)));
   elsif Argument_Count = 7
     and then Argument (1) = "syndrome"
   then
      declare
         Coefficients : constant QEC_GF3.Trit_Vector (1 .. 3) :=
           (Parse_Trit (2), Parse_Trit (3), Parse_Trit (4));
         Errors : constant QEC_GF3.Trit_Vector (1 .. 3) :=
           (Parse_Trit (5), Parse_Trit (6), Parse_Trit (7));
      begin
         Put_Result
           (QEC_Decode.Single_Check_Syndrome (Coefficients, Errors));
      end;
   else
      Put_Line (Standard_Error, "ERROR: unknown command or argument count");
      Usage;
      Set_Exit_Status (Failure);
   end if;
exception
   when Constraint_Error =>
      Put_Line (Standard_Error, "ERROR: trits must be single digits 0, 1, or 2");
      Set_Exit_Status (Failure);
   when Program_Error =>
      Put_Line (Standard_Error, "FAIL: GF(3) field identity check");
      Set_Exit_Status (Failure);
end QEC_ADA;
