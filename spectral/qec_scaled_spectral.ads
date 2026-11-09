--  SPDX-License-Identifier: MPL-2.0
--  Phase 1E: bounded, sparse, native Ada non-backtracking observatory.
--  Supports arbitrary binary Tanner support graphs, independently of
--  the GF(3) decoder and the existing small-graph Phase 1D implementation.
package QEC_Scaled_Spectral is
   Max_Variables : constant Positive := 128;
   Max_Checks : constant Positive := 128;
   Max_Edges : constant Positive := 2_048;
   Max_Directed : constant Positive := 2 * Max_Edges;
   Max_Nodes : constant Positive := Max_Variables + Max_Checks;
   Max_Iterations : constant Positive := 2_000;

   subtype Variable_Index is Positive range 1 .. Max_Variables;
   subtype Check_Index is Positive range 1 .. Max_Checks;
   subtype Edge_Index is Positive range 1 .. Max_Directed;

   type Graph is private;

   type Solve_Status is (No_Edges, Acyclic, Converged_Numeric,
                         Not_Converged);
   type Ranked_Edge is record
      Directed_Id : Natural := 0;
      Energy : Long_Float := 0.0;
   end record;
   type Top_Ten is array (Positive range 1 .. 10) of Ranked_Edge;
   type Observation is record
      Status : Solve_Status := No_Edges;
      Variables : Natural := 0;
      Checks : Natural := 0;
      Edges : Natural := 0;
      Directed_Edges : Natural := 0;
      SCC_Count : Natural := 0;
      Cyclic_SCC_Count : Natural := 0;
      Dominant_Tie_Count : Natural := 0;
      Mode_Root_Edge : Natural := 0;
      Mode_Edge_Count : Natural := 0;
      Iterations : Natural := 0;
      Spectral_Radius : Long_Float := 0.0;
      Collatz_Lower : Long_Float := 0.0;
      Collatz_Upper : Long_Float := 0.0;
      Residual_L1 : Long_Float := 0.0;
      IPR : Long_Float := 0.0;
      EEEC : Long_Float := 0.0;
      Top_Count : Natural range 0 .. 10 := 0;
      Top : Top_Ten := (others => (others => <>));
   end record;

   --  Edges are supplied in exact ascending (check, variable) order.
   --  Duplicate edges, out-of-range nodes and overflow raise Constraint_Error.
   function Create (Variables, Checks : Positive) return Graph;
   procedure Add_Edge
     (G : in out Graph; Check : Positive; Variable : Positive);
   function Edge_Count (G : Graph) return Natural;

   --  Sparse O(V+E) storage; no dense Hashimoto matrix is constructed.
   --  Estimates are bounded numerical results on a selected recurrent SCC.
   --  Fail closed if a cyclic SCC does not meet the convergence criterion.
   function Observe (G : Graph) return Observation;

private
   type Undirected_Edge is record
      C : Natural := 0;
      V : Natural := 0;
   end record;
   type Edge_List is array (Positive range 1 .. Max_Edges)
     of Undirected_Edge;

   type Graph is record
      Variables : Positive := 1;
      Checks : Positive := 1;
      Length : Natural range 0 .. Max_Edges := 0;
      Entries : Edge_List := (others => (others => <>));
   end record;
end QEC_Scaled_Spectral;
