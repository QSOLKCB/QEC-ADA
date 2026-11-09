--  SPDX-License-Identifier: MPL-2.0
--  QEC-ADA observational research CLI; separate from native decoder entry.
with Ada.Command_Line;
with Ada.Strings;
with Ada.Strings.Fixed;
with Ada.Text_IO;
with QEC_Configurable;
with QEC_Strowger;
with QEC_Tanner;

procedure QEC_Research is
   use Ada.Command_Line;
   use Ada.Text_IO;
   use type QEC_Configurable.Trit;
   use type QEC_Strowger.Route_Outcome;
   Invalid : exception;

   function Number (Value : Natural) return String is
     (Ada.Strings.Fixed.Trim (Natural'Image (Value), Ada.Strings.Both));

   function Trit_Of (Value : Character)
     return QEC_Configurable.Trit is
   begin
      if Value not in '0' .. '2' then
         raise Invalid;
      end if;
      return QEC_Configurable.Trit
        (Character'Pos (Value) - Character'Pos ('0'));
   end Trit_Of;

   function Site_Count (Text : String)
      return QEC_Configurable.Site_Index is
   begin
      if Text'Length /= 1 or else Text (Text'First) not in '1' .. '5' then
         raise Invalid;
      end if;
      return QEC_Configurable.Site_Index
        (Character'Pos (Text (Text'First)) - Character'Pos ('0'));
   end Site_Count;

   function Parse_Tanner return QEC_Configurable.Code_Definition is
      D : QEC_Configurable.Code_Definition;
      Row_Count : Natural;
   begin
      if Argument_Count < 3 or else Argument_Count > 6 then
         raise Invalid;
      end if;
      D.Sites := Site_Count (Argument (2));
      Row_Count := Argument_Count - 2;
      D.Rows := QEC_Configurable.Check_Index (Row_Count);
      for Row in 1 .. D.Rows loop
         declare
            Text : constant String := Argument (Natural (Row) + 2);
         begin
            if Text'Length /= 2 * Natural (D.Sites) then
               raise Invalid;
            end if;
            for Site in 1 .. D.Sites loop
               D.X (Row) (Site) := Trit_Of (Text (Natural (Site)));
               D.Z (Row) (Site) :=
                 Trit_Of (Text (Natural (D.Sites) + Natural (Site)));
            end loop;
         end;
      end loop;
      return D;
   end Parse_Tanner;

   procedure Show_Tanner is
      D : constant QEC_Configurable.Code_Definition := Parse_Tanner;
      R : constant QEC_Tanner.Graph_Observation := QEC_Tanner.Observe (D);
   begin
      Put_Line ("schema=qec-ada.tanner-observation.v1");
      Put_Line ("variables=" & Number (R.Sites));
      Put_Line ("checks=" & Number (R.Checks));
      Put_Line ("edges=" & Number (R.Edges));
      Put_Line ("x_edges=" & Number (R.X_Edges));
      Put_Line ("z_edges=" & Number (R.Z_Edges));
      Put_Line ("mixed_edges=" & Number (R.Mixed_Edges));
      Put_Line ("four_cycles=" & Number (R.Four_Cycles));
      Put_Line ("nb_trace4=" & Number (R.NB_Trace_4));
      for Site in 1 .. D.Sites loop
         Put_Line ("variable_degree_" & Number (Natural (Site)) &
                   "=" & Number (R.Variable_Degree (Site)));
         Put_Line ("variable_cycle_heat_" & Number (Natural (Site)) &
                   "=" & Number (R.Variable_Cycle_Heat (Site)));
      end loop;
      for Row in 1 .. D.Rows loop
         Put_Line ("check_degree_" & Number (Natural (Row)) &
                   "=" & Number (R.Check_Degree (Row)));
      end loop;
      --  Canonical, check-major and then variable-major edge identity.
      for Row in 1 .. D.Rows loop
         for Site in 1 .. D.Sites loop
            if D.X (Row) (Site) /= 0 or else D.Z (Row) (Site) /= 0 then
               Put_Line ("edge=" & Number (Natural (Row)) & "," &
                         Number (Natural (Site)) & "," &
                         Number (Natural (D.X (Row) (Site))) & "," &
                         Number (Natural (D.Z (Row) (Site))));
            end if;
         end loop;
      end loop;
   end Show_Tanner;

   function Four_Characters
     (Index : Positive) return String is
      Text : constant String := Argument (Index);
   begin
      if Text'Length /= 4 then
         raise Invalid;
      end if;
      return Text;
   end Four_Characters;

   function Decode_Bank (Index : Positive)
     return QEC_Strowger.Bank is
      Text : constant String := Four_Characters (Index);
      R : QEC_Strowger.Bank := (others => QEC_Strowger.Busy);
   begin
      for I in QEC_Strowger.Slot_Index loop
         case Text (I) is
            when '1' => R (I) := QEC_Strowger.Free;
            when '0' => R (I) := QEC_Strowger.Busy;
            when 'Q' => R (I) := QEC_Strowger.Quarantined;
            when others => raise Invalid;
         end case;
      end loop;
      return R;
   end Decode_Bank;

   function Decode_Fault (Value : String)
      return QEC_Strowger.Fault_Plan is
      R : QEC_Strowger.Fault_Plan;
   begin
      if Value = "none" then
         return R;
      elsif Value = "route" then
         R.Mode := QEC_Strowger.Route_Tone_Fault;
      elsif Value = "check" then
         R.Mode := QEC_Strowger.Check_Tone_Fault;
      elsif Value = "dark" then
         R.Mode := QEC_Strowger.Dark_Tone_Fault;
      elsif Value'Length = 5
        and then Value (Value'First .. Value'First + 3) = "miss"
      then
         R.Mode := QEC_Strowger.Miss_Pulse;
         if Value (Value'Last) not in '1' .. '4' then
            raise Invalid;
         end if;
         R.Stage := QEC_Strowger.Stage_Index
           (Character'Pos (Value (Value'Last)) - Character'Pos ('0'));
      elsif Value'Length = 4
        and then Value (Value'First .. Value'First + 2) = "dup"
      then
         R.Mode := QEC_Strowger.Duplicate_Pulse;
         if Value (Value'Last) not in '1' .. '4' then
            raise Invalid;
         end if;
         R.Stage := QEC_Strowger.Stage_Index
           (Character'Pos (Value (Value'Last)) - Character'Pos ('0'));
      elsif Value'Length = 6
        and then Value (Value'First .. Value'First + 4) = "stuck"
      then
         R.Mode := QEC_Strowger.Stuck_Selector;
         if Value (Value'Last) not in '1' .. '2' then
            raise Invalid;
         end if;
         R.Stage := QEC_Strowger.Stage_Index
           (Character'Pos (Value (Value'Last)) - Character'Pos ('0'));
      else
         raise Invalid;
      end if;
      return R;
   end Decode_Fault;

   function Parse_Route return QEC_Strowger.Route_Request is
      R : QEC_Strowger.Route_Request;
      Digit_Text : constant String := Four_Characters (2);
      Radix_Text : constant String := Four_Characters (3);
   begin
      if Argument_Count /= 7 then
         raise Invalid;
      end if;
      for I in QEC_Strowger.Stage_Index loop
         if Digit_Text (I) not in '0' .. '9'
           or else Radix_Text (I) not in '2' .. '9'
         then
            raise Invalid;
         end if;
         R.Address (I) := QEC_Strowger.Digit
           (Character'Pos (Digit_Text (I)) - Character'Pos ('0'));
         R.Radices (I) := QEC_Strowger.Radix
           (Character'Pos (Radix_Text (I)) - Character'Pos ('0'));
      end loop;
      R.Linefinders := Decode_Bank (4);
      R.First_Bank := Decode_Bank (5);
      R.Second_Bank := Decode_Bank (6);
      R.Fault := Decode_Fault (Argument (7));
      return R;
   end Parse_Route;

   procedure Show_Route is
      Input : constant QEC_Strowger.Route_Request := Parse_Route;
      R : constant QEC_Strowger.Trace := QEC_Strowger.Execute (Input);
   begin
      Put_Line ("schema=qec-ada.strowger-event-stream.v1");
      Put_Line ("status=" & QEC_Strowger.Route_Outcome'Image (R.Status));
      Put_Line ("linefinder=" & Number (R.Linefinder));
      Put_Line ("selector_a=" & Number (R.First_Trunk));
      Put_Line ("selector_b=" & Number (R.Second_Trunk));
      for I in R.Expected_Tones'Range loop
         Put_Line ("tone_expected_" & Number (I) &
                   "=" & Number (R.Expected_Tones (I)));
         Put_Line ("tone_observed_" & Number (I) &
                   "=" & Number (R.Observed_Tones (I)));
      end loop;
      Put_Line ("count=" & Number (R.Count));
      for I in 1 .. R.Count loop
         declare
            E : constant QEC_Strowger.Event := R.Events (I);
         begin
            Put_Line ("event=" & Number (E.Sequence) & "," &
              Number (E.Tick) & "," &
              QEC_Strowger.Event_Action'Image (E.Action) & "," &
              Number (E.Stage) & "," & Number (E.Value));
         end;
      end loop;
      if R.Status /= QEC_Strowger.Routed then
         Set_Exit_Status (Failure);
      end if;
   end Show_Route;

   procedure Usage is
   begin
      Put_Line ("QEC-ADA research: exact bounded graph diagnostics and switching");
      Put_Line ("  qec_research tanner N ROW1 [ROW2 ... ROW4]");
      Put_Line ("  qec_research strowger DDDD RRRR LLLL AAAA BBBB FAULT");
      Put_Line ("Masks use 1=free, 0=busy, Q=quarantined; fault:");
      Put_Line ("  none | miss1..4 | dup1..4 | stuck1..2 | route | check | dark");
      Put_Line ("Neither spectral moments nor route tones prove quantum correction.");
   end Usage;

begin
   if Argument_Count = 1 and then Argument (1) = "--help" then
      Usage;
   elsif Argument_Count >= 3 and then Argument_Count <= 6
     and then Argument (1) = "tanner"
   then
      Show_Tanner;
   elsif Argument_Count = 7 and then Argument (1) = "strowger" then
      Show_Route;
   else
      Usage;
      Set_Exit_Status (Failure);
   end if;
exception
   when Invalid | Constraint_Error =>
      Put_Line (Standard_Error, "ERROR: INVALID_INPUT");
      Set_Exit_Status (Failure);
end QEC_Research;
