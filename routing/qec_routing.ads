--  SPDX-License-Identifier: MPL-2.0
--  Deterministic, classical routing pilot derived from QEC Strowger
--  first-free selector ordering. No tones, pulses, persistence or receipts.
with QEC_GF3;
package QEC_Routing is
   subtype Slot is Positive range 1 .. 4;
   type Free_Map is array (Slot) of Boolean;
   type Digits is array (Positive range 1 .. 4) of QEC_GF3.Trit;
   type Outcome is (Committed, No_Linefinder, No_First_Trunk,
                    No_Second_Trunk);
   type Selection is record
      Status           : Outcome := No_Linefinder;
      Linefinder       : Natural := 0;
      First_Trunk      : Natural := 0;
      Second_Trunk     : Natural := 0;
      First_Level      : QEC_GF3.Trit := 0;
      Second_Level     : QEC_GF3.Trit := 0;
      Vertical         : QEC_GF3.Trit := 0;
      Rotary           : QEC_GF3.Trit := 0;
   end record;

   --  All capacity is passed as an immutable snapshot.
   --  No partial route or resource mutation is published on failure.
   function First_Free (Map : Free_Map) return Natural;
   function Route
     (Address : Digits;
      Linefinders, First_Bank, Second_Bank : Free_Map)
      return Selection;
end QEC_Routing;
