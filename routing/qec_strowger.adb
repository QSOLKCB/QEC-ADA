--  SPDX-License-Identifier: MPL-2.0
package body QEC_Strowger is

   function First_Free (Source : Bank) return Natural is
   begin
      for Slot in Slot_Index loop
         if Source (Slot) = Free then
            return Natural (Slot);
         end if;
      end loop;
      return 0;
   end First_Free;

   procedure Append
     (Result : in out Trace; Action : Event_Action;
      Stage : Natural; Value : Natural) is
   begin
      if Result.Count = Max_Events or else Stage > 4 then
         raise Program_Error with "bounded Strowger event capacity";
      end if;
      Result.Count := Result.Count + 1;
      Result.Events (Result.Count) :=
        (Sequence => Result.Count - 1,
         Tick => Result.Count - 1,
         Action => Action, Stage => Stage, Value => Value);
   end Append;

   procedure Reject
     (Result : in out Trace; Why : Route_Outcome) is
   begin
      Result.Status := Why;
      Append (Result, Route_Rejected, 0, Route_Outcome'Pos (Why));
      if Result.Linefinder /= 0 then
         Append (Result, Resources_Released, 0, Result.Linefinder);
      end if;
      --  No partial successful allocation is ever returned.
      Result.Linefinder := 0;
      Result.First_Trunk := 0;
      Result.Second_Trunk := 0;
   end Reject;

   function Expected
     (Input : Route_Request; R : Trace) return Tone_Vector is
      Weighted : Natural := 0;
   begin
      for I in Stage_Index loop
         Weighted := Weighted + Natural (I) * 17 * Input.Address (I);
      end loop;
      return
        (1 => 320 + Weighted + 3 * R.Linefinder
             + 5 * R.First_Trunk + 7 * R.Second_Trunk,
         2 => 600 + (Weighted + 11 * R.Linefinder
             + 13 * R.First_Trunk + 17 * R.Second_Trunk) mod 127,
         3 => 90);
   end Expected;

   function Execute (Input : Route_Request) return Trace is
      Result : Trace;
      Expected_Pulses : Natural;
      Actual_Pulses : Natural;
      Chosen : Natural;
   begin
      for I in Stage_Index loop
         if Input.Address (I) >= Natural (Input.Radices (I)) then
            Reject (Result, Invalid_Request);
            return Result;
         end if;
      end loop;
      if Input.Fault.Mode = Stuck_Selector
        and then Input.Fault.Stage > 2
      then
         Reject (Result, Invalid_Request);
         return Result;
      end if;

      Result.Linefinder := First_Free (Input.Linefinders);
      if Result.Linefinder = 0 then
         Reject (Result, No_Linefinder);
         return Result;
      end if;
      Append (Result, Linefinder_Selected, 0, Result.Linefinder);

      for I in Stage_Index loop
         --  In a mixed-radix pulse stream a zero is a full-radix train.
         Expected_Pulses :=
           (if Input.Address (I) = 0 then Natural (Input.Radices (I))
            else Input.Address (I));
         Actual_Pulses := 0;
         for Pulse in 1 .. Expected_Pulses loop
            if Input.Fault.Mode = Miss_Pulse
              and then Input.Fault.Stage = I and then Pulse = 1
            then
               Append (Result, Pulse_Missed, Natural (I), Pulse);
            else
               Append (Result, Pulse_Received, Natural (I), Pulse);
               Actual_Pulses := Actual_Pulses + 1;
               if Input.Fault.Mode = Duplicate_Pulse
                 and then Input.Fault.Stage = I and then Pulse = 1
               then
                  Append (Result, Pulse_Duplicated, Natural (I), Pulse);
                  Actual_Pulses := Actual_Pulses + 1;
               end if;
            end if;
         end loop;
         if Actual_Pulses /= Expected_Pulses then
            Reject (Result, Pulse_Mismatch);
            return Result;
         end if;
         if I <= 2 then
            if Input.Fault.Mode = Stuck_Selector
              and then Input.Fault.Stage = I
            then
               Reject (Result, Selector_Stuck);
               return Result;
            end if;
            if I = 1 then
               Chosen := First_Free (Input.First_Bank);
               if Chosen = 0 then
                  Reject (Result, No_First_Trunk);
                  return Result;
               end if;
               Result.First_Trunk := Chosen;
            else
               Chosen := First_Free (Input.Second_Bank);
               if Chosen = 0 then
                  Reject (Result, No_Second_Trunk);
                  return Result;
               end if;
               Result.Second_Trunk := Chosen;
            end if;
            Append (Result, Trunk_Selected, Natural (I), Chosen);
         else
            Append (Result, Connector_Selected, Natural (I),
                    Input.Address (I));
         end if;
      end loop;

      Result.Expected_Tones := Expected (Input, Result);
      Result.Observed_Tones := Result.Expected_Tones;
      case Input.Fault.Mode is
         when Route_Tone_Fault =>
            Result.Observed_Tones (1) := Result.Observed_Tones (1) + 1;
         when Check_Tone_Fault =>
            Result.Observed_Tones (2) := Result.Observed_Tones (2) + 1;
         when Dark_Tone_Fault =>
            Result.Observed_Tones (3) := Result.Observed_Tones (3) + 1;
         when others => null;
      end case;
      for I in Result.Expected_Tones'Range loop
         Append (Result, Tone_Expected, I, Result.Expected_Tones (I));
         Append (Result, Tone_Observed, I, Result.Observed_Tones (I));
      end loop;
      if Result.Expected_Tones /= Result.Observed_Tones then
         Reject (Result, Tone_Mismatch);
         return Result;
      end if;
      Result.Status := Routed;
      Append (Result, Route_Committed, 0, 1);
      Append (Result, Resources_Released, 0, Result.Linefinder);
      return Result;
   end Execute;
end QEC_Strowger;
