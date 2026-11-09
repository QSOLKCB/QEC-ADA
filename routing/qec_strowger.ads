--  SPDX-License-Identifier: MPL-2.0
--  Deterministic bounded classical switching. No quantum routing.
package QEC_Strowger is
   subtype Stage_Index is Positive range 1 .. 4;
   subtype Slot_Index is Positive range 1 .. 4;
   subtype Digit is Natural range 0 .. 9;
   subtype Radix is Natural range 2 .. 9;
   type Address_Word is array (Stage_Index) of Digit;
   type Radix_Word is array (Stage_Index) of Radix;

   type Contact_State is (Free, Busy, Quarantined);
   type Bank is array (Slot_Index) of Contact_State;
   type Fault_Kind is
     (None, Miss_Pulse, Duplicate_Pulse, Stuck_Selector,
      Route_Tone_Fault, Check_Tone_Fault, Dark_Tone_Fault);
   type Fault_Plan is record
      Mode : Fault_Kind := None;
      Stage : Stage_Index := 1;
   end record;
   type Route_Outcome is
     (Routed, Invalid_Request, No_Linefinder, No_First_Trunk,
      No_Second_Trunk, Pulse_Mismatch, Selector_Stuck, Tone_Mismatch);

   type Event_Action is
     (Linefinder_Selected, Pulse_Received, Pulse_Missed, Pulse_Duplicated,
      Trunk_Selected, Connector_Selected, Tone_Expected, Tone_Observed,
      Route_Committed, Route_Rejected, Resources_Released);
   type Event is record
      Sequence : Natural := 0;
      Tick     : Natural := 0;
      Action   : Event_Action := Route_Rejected;
      Stage    : Natural range 0 .. 4 := 0;
      Value    : Natural := 0;
   end record;
   Max_Events : constant Positive := 64;
   type Events_Buffer is array (Positive range 1 .. Max_Events) of Event;
   type Tone_Vector is array (Positive range 1 .. 3) of Natural;

   type Route_Request is record
      Address : Address_Word := (others => 0);
      Radices : Radix_Word := (others => 3);
      Linefinders : Bank := (others => Free);
      First_Bank : Bank := (others => Free);
      Second_Bank : Bank := (others => Free);
      Fault : Fault_Plan;
   end record;

   type Trace is record
      Status : Route_Outcome := Invalid_Request;
      Count  : Natural range 0 .. Max_Events := 0;
      Events : Events_Buffer := (others => (others => <>));
      Linefinder : Natural := 0;
      First_Trunk : Natural := 0;
      Second_Trunk : Natural := 0;
      Expected_Tones : Tone_Vector := (others => 0);
      Observed_Tones : Tone_Vector := (others => 0);
   end record;

   --  Independent pure route-preview execution: no shared mutable state.
   function First_Free (Source : Bank) return Natural;
   function Execute (Input : Route_Request) return Trace;
end QEC_Strowger;
