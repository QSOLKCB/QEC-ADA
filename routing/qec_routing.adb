--  SPDX-License-Identifier: MPL-2.0
--  Explicit minimum-index selection is the observable tie policy.
package body QEC_Routing is

   function First_Free (Map : Free_Map) return Natural is
   begin
      for Index in Slot loop
         if Map (Index) then
            return Natural (Index);
         end if;
      end loop;
      return 0;
   end First_Free;

   function Route
     (Address : Digits;
      Linefinders, First_Bank, Second_Bank : Free_Map)
      return Selection is
      L : constant Natural := First_Free (Linefinders);
      A : constant Natural := First_Free (First_Bank);
      B : constant Natural := First_Free (Second_Bank);
   begin
      if L = 0 then
         return (Status => No_Linefinder, others => <>);
      elsif A = 0 then
         return (Status => No_First_Trunk, others => <>);
      elsif B = 0 then
         return (Status => No_Second_Trunk, others => <>);
      end if;

      return (Status       => Committed,
              Linefinder   => L,
              First_Trunk  => A,
              Second_Trunk => B,
              First_Level  => Address (1),
              Second_Level => Address (2),
              Vertical     => Address (3),
              Rotary       => Address (4));
   end Route;

end QEC_Routing;
