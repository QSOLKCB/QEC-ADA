--  SPDX-License-Identifier: MPL-2.0
--  Bounded observational Tanner-graph and exact NB spectral moments.
--  No mutation of the decoder, code definition or correction outputs.
with QEC_Configurable;
package QEC_Tanner is
   subtype Variable is QEC_Configurable.Site_Index;
   subtype Check is QEC_Configurable.Check_Index;
   type Variable_Vector is array (Variable) of Natural;
   type Check_Vector is array (Check) of Natural;
   type Graph_Observation is record
      Sites         : Natural := 0;
      Checks        : Natural := 0;
      Edges         : Natural := 0;
      X_Edges       : Natural := 0;
      Z_Edges       : Natural := 0;
      Mixed_Edges   : Natural := 0;
      Four_Cycles   : Natural := 0;
      NB_Trace_4    : Natural := 0;
      Variable_Degree : Variable_Vector := (others => 0);
      Check_Degree    : Check_Vector := (others => 0);
      Variable_Cycle_Heat : Variable_Vector := (others => 0);
   end record;
   --  Accept raw parity-check support separately from decoder validity.
   --  A graph does not have to be correctable to be observable.
   --  These metrics are EXACT finite graph counts, NOT eigenvalues.
   function Observe
     (Definition : QEC_Configurable.Code_Definition)
      return Graph_Observation;
end QEC_Tanner;
