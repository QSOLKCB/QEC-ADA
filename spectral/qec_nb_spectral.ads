--  SPDX-License-Identifier: MPL-2.0
--  Phase 1D: bounded non-backtracking *recurrent-block* observatory.
--  Sparse directed-edge transitions; no dense Hashimoto matrix, no RNG.
--  The mode belongs to the selected strongly connected block, not
--  necessarily an eigenvector of a reducible full-graph operator.
with QEC_Configurable;
package QEC_NB_Spectral is
   Max_Directed : constant Positive := 40;
   subtype Edge_Index is Positive range 1 .. Max_Directed;

   type Edge_Weight is array (Edge_Index) of Long_Float;
   type Edge_Indices is array (Edge_Index) of Natural;

   type Solve_Status is
     (No_Edges, Acyclic, Converged_Numeric, Not_Converged);
   type Spectrum is record
      Status              : Solve_Status := No_Edges;
      Directed_Edges      : Natural range 0 .. Max_Directed := 0;
      SCC_Count           : Natural range 0 .. Max_Directed := 0;
      Cyclic_SCC_Count    : Natural range 0 .. Max_Directed := 0;
      Dominant_Tie_Count  : Natural range 0 .. Max_Directed := 0;
      Root_Edge           : Natural range 0 .. Max_Directed := 0;
      Mode_Edge_Count     : Natural range 0 .. Max_Directed := 0;
      Iterations          : Natural := 0;
      Spectral_Radius     : Long_Float := 0.0;
      Collatz_Lower       : Long_Float := 0.0;
      Collatz_Upper       : Long_Float := 0.0;
      Residual_L1         : Long_Float := 0.0;
      IPR                 : Long_Float := 0.0;
      EEEC                : Long_Float := 0.0;
      Energy              : Edge_Weight := (others => 0.0);
      Ranking             : Edge_Indices := (others => 0);
      Ranking_Count       : Natural range 0 .. Max_Directed := 0;
   end record;

   --  Definition is read-only. For every n<=5,m<=4 matrix with canonical
   --  padding, compute an SCC-aware, deterministic positive mode of the
   --  sparse Hashimoto operator. If convergence cannot be established
   --  inside the declared iteration budget, return Not_Converged and
   --  do not publish speculative eigenvalue claims.
   function Observe
     (Definition : QEC_Configurable.Code_Definition) return Spectrum;
end QEC_NB_Spectral;
