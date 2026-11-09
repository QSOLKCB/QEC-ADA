--  SPDX-License-Identifier: MPL-2.0
--  Independent native GF(3), fixed cyclic qutrit decode and classical
--  first-free routing. Not the historical QEC Strowger receipt protocol.
with Ada.Command_Line;
with Ada.Strings;
with Ada.Strings.Fixed;
with Ada.Text_IO;
with QEC_Decode;
with QEC_Configurable;
with QEC_GF3;
with QEC_Invariants;
with QEC_Qutrit;
with QEC_Routing;

procedure QEC_ADA is
   use Ada.Command_Line;
   use Ada.Text_IO;
   use type QEC_GF3.Trit;
   use type QEC_Configurable.Preparation_Status;
   use type QEC_Configurable.Syndrome_Vector;
   use type QEC_Routing.Outcome;
   Invalid_Input : exception;

   function Number_String (Value : Natural) return String is
     (Ada.Strings.Fixed.Trim (Natural'Image (Value), Ada.Strings.Both));

   function One_Trit (C : Character) return QEC_GF3.Trit is
   begin
      if C not in '0' .. '2' then
         raise Invalid_Input;
      end if;
      return QEC_GF3.Trit (Character'Pos (C) - Character'Pos ('0'));
   end One_Trit;

   function Parse_Trit (Position : Positive) return QEC_GF3.Trit is
      Text : constant String := Argument (Position);
   begin
      if Text'Length /= 1 then
         raise Invalid_Input;
      end if;
      return One_Trit (Text (Text'First));
   end Parse_Trit;

   function Trit_String (Value : QEC_GF3.Trit) return String is
     (1 => Character'Val (Character'Pos ('0') + Integer (Value)));

   function Vector_String (Values : QEC_GF3.Trit_Vector) return String is
      Result : String (1 .. Values'Length);
      Index : Positive := 1;
   begin
      for Position in Values'Range loop
         Result (Index) := Trit_String (Values (Position)) (1);
         Index := Index + 1;
      end loop;
      return Result;
   end Vector_String;

   function Syndrome_String
     (Values : QEC_Qutrit.Syndrome_Vector) return String is
      Result : String (1 .. 4);
   begin
      for Position in QEC_Qutrit.Check_Index loop
         Result (Position) := Trit_String (Values (Position)) (1);
      end loop;
      return Result;
   end Syndrome_String;

   function Parse_Pauli
     (X_Arg, Z_Arg : Positive) return QEC_Qutrit.Pauli is
      X_Text : constant String := Argument (X_Arg);
      Z_Text : constant String := Argument (Z_Arg);
      Result : QEC_Qutrit.Pauli := QEC_Qutrit.Zero;
   begin
      if X_Text'Length /= 5 or else Z_Text'Length /= 5 then
         raise Invalid_Input;
      end if;
      for Site in QEC_Qutrit.Site_Index loop
         Result.X (Site) := One_Trit (X_Text (Site));
         Result.Z (Site) := One_Trit (Z_Text (Site));
      end loop;
      return Result;
   end Parse_Pauli;

   function Parse_Syndrome
     (Position : Positive) return QEC_Qutrit.Syndrome_Vector is
      Value : constant String := Argument (Position);
      Result : QEC_Qutrit.Syndrome_Vector := (others => 0);
   begin
      if Value'Length /= 4 then
         raise Invalid_Input;
      end if;
      for Row in QEC_Qutrit.Check_Index loop
         Result (Row) := One_Trit (Value (Row));
      end loop;
      return Result;
   end Parse_Syndrome;

   function Parse_Mask (Position : Positive) return QEC_Routing.Free_Map is
      Value : constant String := Argument (Position);
      Result : QEC_Routing.Free_Map := (others => False);
   begin
      if Value'Length /= 4 then
         raise Invalid_Input;
      end if;
      for Slot in QEC_Routing.Slot loop
         if Value (Slot) = '1' then
            Result (Slot) := True;
         elsif Value (Slot) /= '0' then
            raise Invalid_Input;
         end if;
      end loop;
      return Result;
   end Parse_Mask;

   procedure Put_Result (Value : QEC_GF3.Trit) is
   begin
      Put_Line (Trit_String (Value));
   end Put_Result;

   procedure Check_Field is
   begin
      for A in QEC_GF3.Trit loop
         if not QEC_Invariants.Additive_Inverse (A) then
            raise Program_Error with "additive inverse";
         end if;
         for B in QEC_GF3.Trit loop
            if not QEC_Invariants.Addition_Commutative (A, B)
              or else not QEC_Invariants.Multiplication_Commutative (A, B)
            then
               raise Program_Error with "GF3 commutativity";
            end if;
         end loop;
      end loop;
      Put_Line ("PASS GF(3) small-domain identities");
   end Check_Field;

   procedure Check_Qutrit is
   begin
      if not QEC_Qutrit.Exhaustive_Parity then
         raise Program_Error with "scalar/OPT syndrome equivalence";
      end if;
      Put_Line ("PASS QUTRIT 59049 scalar/OPT parity + 40 corrections");
   end Check_Qutrit;

   procedure Check_Routing is
      Zero : constant QEC_Routing.Free_Map := (others => False);
      All_Free : constant QEC_Routing.Free_Map := (others => True);
      Address_Word : constant QEC_Routing.Address_Word := (1, 2, 0, 1);
   begin
      if QEC_Routing.Route (Address_Word, Zero, All_Free, All_Free).Status
           /= QEC_Routing.No_Linefinder
        or else QEC_Routing.Route (Address_Word, All_Free, Zero, All_Free).Status
           /= QEC_Routing.No_First_Trunk
        or else QEC_Routing.Route (Address_Word, All_Free, All_Free, Zero).Status
           /= QEC_Routing.No_Second_Trunk
        or else QEC_Routing.Route
          (Address_Word, All_Free, All_Free, All_Free).Linefinder /= 1
      then
         raise Program_Error with "routing first-free and fail-closed";
      end if;
      Put_Line ("PASS classical first-free routing");
   end Check_Routing;

   procedure Put_Route (R : QEC_Routing.Selection) is
   begin
      case R.Status is
         when QEC_Routing.Committed =>
            Put_Line ("status=ROUTED");
            Put_Line ("linefinder=" & Number_String (R.Linefinder));
            Put_Line ("selector_a=" & Number_String (R.First_Trunk));
            Put_Line ("selector_b=" & Number_String (R.Second_Trunk));
            Put_Line ("selector_levels=" &
                      Trit_String (R.First_Level) & Trit_String (R.Second_Level));
            Put_Line ("connector=" &
                      Trit_String (R.Vertical) & Trit_String (R.Rotary));
         when QEC_Routing.No_Linefinder =>
            Put_Line ("status=NO_LINEFINDER");
            Set_Exit_Status (Failure);
         when QEC_Routing.No_First_Trunk =>
            Put_Line ("status=NO_FIRST_TRUNK");
            Set_Exit_Status (Failure);
         when QEC_Routing.No_Second_Trunk =>
            Put_Line ("status=NO_SECOND_TRUNK");
            Set_Exit_Status (Failure);
      end case;
   end Put_Route;

   procedure Put_Qutrit_Lookup (S : QEC_Qutrit.Syndrome_Vector) is
      Answer : constant QEC_Qutrit.Lookup_Result := QEC_Qutrit.Lookup (S);
   begin
      if not Answer.Found then
         Put_Line ("status=NO_REPRESENTATIVE");
         Set_Exit_Status (Failure);
      else
         Put_Line ("status=FOUND");
         Put_Line ("correction_x=" & Vector_String (Answer.Correction.X));
         Put_Line ("correction_z=" & Vector_String (Answer.Correction.Z));
      end if;
   end Put_Qutrit_Lookup;

   procedure Put_Qutrit_Decode (Error : QEC_Qutrit.Pauli) is
      Answer : constant QEC_Qutrit.Decode_Result := QEC_Qutrit.Correct (Error);
   begin
      Put_Line ("syndrome=" & Syndrome_String (Answer.Syndrome));
      if not Answer.Found then
         Put_Line ("status=NO_REPRESENTATIVE");
         Set_Exit_Status (Failure);
      else
         Put_Line ("correction_x=" & Vector_String (Answer.Correction.X));
         Put_Line ("correction_z=" & Vector_String (Answer.Correction.Z));
         Put_Line ("residual_x=" & Vector_String (Answer.Residual.X));
         Put_Line ("residual_z=" & Vector_String (Answer.Residual.Z));
         if Answer.Success then
            Put_Line ("status=CORRECTED");
         else
            Put_Line ("status=DETECTED_UNCORRECTED");
            Set_Exit_Status (Failure);
         end if;
      end if;
   end Put_Qutrit_Decode;

   procedure Usage is
   begin
      Put_Line ("QEC-ADA - native GF3 + fixed [[5,1,3]]_3 qutrit pilot");
      Put_Line ("  qec_ada --help | --version");
      Put_Line ("  qec_ada selftest [qutrit|route]");
      Put_Line ("  qec_ada gf3 add|mul TRIT TRIT");
      Put_Line ("  qec_ada gf3 neg TRIT");
      Put_Line ("  qec_ada syndrome C1 C2 C3 E1 E2 E3");
      Put_Line ("  qec_ada qutrit syndrome XXXXX ZZZZZ");
      Put_Line ("  qec_ada qutrit decode XXXXX ZZZZZ");
      Put_Line ("  qec_ada qutrit lookup SSSS");
      Put_Line ("  qec_ada route D1 D2 D3 D4 LLLL AAAA BBBB");
      Put_Line ("  qec_ada benchmark qutrit scalar|opt");
      Put_Line ("TRIT and D1..D4 are 0/1/2; masks use 1=free, 0=busy.");
   end Usage;

begin
   if Argument_Count = 0 then
      Usage;
   elsif Argument_Count = 1 and then Argument (1) = "--help" then
      Usage;
   elsif Argument_Count = 1 and then Argument (1) = "--version" then
      Put_Line ("QEC-ADA 0.2.0-dev");
   elsif Argument_Count = 1 and then Argument (1) = "selftest" then
      Check_Field;
   elsif Argument_Count = 2
     and then Argument (1) = "selftest"
     and then Argument (2) = "qutrit"
   then
      Check_Qutrit;
   elsif Argument_Count = 2
     and then Argument (1) = "selftest"
     and then Argument (2) = "route"
   then
      Check_Routing;
   elsif Argument_Count = 3
     and then Argument (1) = "benchmark"
     and then Argument (2) = "qutrit"
     and then (Argument (3) = "scalar" or else Argument (3) = "opt")
   then
      declare
         Use_OPT : constant Boolean := Argument (3) = "opt";
         Checksum : constant Natural := QEC_Qutrit.Workload_Checksum (Use_OPT);
      begin
         Put_Line ("workload=59049");
         Put_Line ("path=" & (if Use_OPT then "opt" else "scalar"));
         Put_Line ("checksum=" & Number_String (Checksum));
      end;
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
         Put_Result (QEC_Decode.Single_Check_Syndrome (Coefficients, Errors));
      end;
   elsif Argument_Count = 4
     and then Argument (1) = "qutrit"
     and then Argument (2) = "syndrome"
   then
      Put_Line (Syndrome_String
        (QEC_Qutrit.Scalar_Syndrome (Parse_Pauli (3, 4))));
   elsif Argument_Count = 4
     and then Argument (1) = "qutrit"
     and then Argument (2) = "decode"
   then
      Put_Qutrit_Decode (Parse_Pauli (3, 4));
   elsif Argument_Count = 3
     and then Argument (1) = "qutrit"
     and then Argument (2) = "lookup"
   then
      Put_Qutrit_Lookup (Parse_Syndrome (3));
   elsif Argument_Count = 8
     and then Argument (1) = "route"
   then
      declare
         Address : constant QEC_Routing.Address_Word :=
           (Parse_Trit (2), Parse_Trit (3),
            Parse_Trit (4), Parse_Trit (5));
         Linefinders : constant QEC_Routing.Free_Map := Parse_Mask (6);
         First_Bank : constant QEC_Routing.Free_Map := Parse_Mask (7);
         Second_Bank : constant QEC_Routing.Free_Map := Parse_Mask (8);
      begin
         Put_Route (QEC_Routing.Route
           (Address, Linefinders, First_Bank, Second_Bank));
      end;
   else
      Put_Line (Standard_Error, "ERROR: unknown command or argument count");
      Usage;
      Set_Exit_Status (Failure);
   end if;
exception
   when Invalid_Input =>
      Put_Line (Standard_Error,
        "ERROR: exact trits 0/1/2, 5-trit Pauli halves, 4-trit syndrome, "
        & "or four-bit 0/1 masks required");
      Set_Exit_Status (Failure);
   when Program_Error =>
      Put_Line (Standard_Error, "FAIL: mathematical or routing invariant");
      Set_Exit_Status (Failure);
end QEC_ADA;
