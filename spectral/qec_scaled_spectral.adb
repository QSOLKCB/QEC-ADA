--  SPDX-License-Identifier: MPL-2.0
--  Matrix-free, bounded memory non-backtracking spectral experiment.
--  Integer sparse adjacency and SCC decomposition are exact; Perron values
--  are explicitly labelled numerical approximations.
package body QEC_Scaled_Spectral is
   subtype Directed is Edge_Index;
   subtype Node_Index is Positive range 1 .. Max_Nodes;

   type Directed_Edge is record
      Source : Natural := 0;
      Target : Natural := 0;
   end record;
   type Directed_List is array (Directed) of Directed_Edge;
   type Index_List is array (Directed) of Natural;
   type Bool_List is array (Directed) of Boolean;
   type Real_List is array (Directed) of Long_Float;
   type Node_List is array (Node_Index) of Natural;
   type Offset_List is array (Positive range 1 .. Max_Nodes + 1)
     of Natural;
   type SCC_Metadata is array (Directed) of Natural;

   type Candidate is record
      Valid : Boolean := False;
      Root : Natural := 0;
      Size : Natural := 0;
      Iterations : Natural := 0;
      Rho : Long_Float := 0.0;
      Lower : Long_Float := 0.0;
      Upper : Long_Float := 0.0;
      Residual : Long_Float := 0.0;
      Energy : Real_List := (others => 0.0);
   end record;

   Tolerance : constant Long_Float := 1.0E-10;
   Tie_Tolerance : constant Long_Float := 1.0E-8;

   function Create (Variables, Checks : Positive) return Graph is
   begin
      if Variables > Max_Variables or else Checks > Max_Checks then
         raise Constraint_Error with "scaled Tanner graph exceeds capacity";
      end if;
      return (Variables => Variables, Checks => Checks, others => <>);
   end Create;

   procedure Add_Edge
     (G : in out Graph; Check : Positive; Variable : Positive) is
   begin
      if Check > G.Checks or else Variable > G.Variables
        or else G.Length >= Max_Edges
      then
         raise Constraint_Error with "scaled Tanner edge outside capacity";
      end if;
      if G.Length > 0 then
         declare
            Last : constant Undirected_Edge := G.Entries (G.Length);
         begin
            if Check < Last.C
              or else (Check = Last.C and then Variable <= Last.V)
            then
               raise Constraint_Error with "uncanonical or repeated edge";
            end if;
         end;
      end if;
      G.Length := G.Length + 1;
      G.Entries (G.Length) := (C => Check, V => Variable);
   end Add_Edge;

   function Edge_Count (G : Graph) return Natural is (G.Length);

   function Observe (G : Graph) return Observation is
      Result : Observation;
      D : constant Natural := 2 * G.Length;
      N : constant Natural := G.Variables + G.Checks;
      Edges : Directed_List := (others => (others => <>));
      Out_Degree : Node_List := (others => 0);
      In_Degree : Node_List := (others => 0);
      Out_Start : Offset_List := (others => 1);
      In_Start : Offset_List := (others => 1);
      Out_Cursor : Node_List := (others => 1);
      In_Cursor : Node_List := (others => 1);
      Out_Items : Index_List := (others => 0);
      In_Items : Index_List := (others => 0);

      Visited : Bool_List := (others => False);
      Stack_Node : Index_List := (others => 0);
      Stack_Position : Index_List := (others => 0);
      Finish : Index_List := (others => 0);
      Component_Of : SCC_Metadata := (others => 0);
      Component_Size : SCC_Metadata := (others => 0);
      Component_Root : SCC_Metadata := (others => 0);
      Finish_Count : Natural := 0;
      Top : Natural := 0;
      Component_Count : Natural := 0;
      Current_Edge : Natural;
      Following : Natural;
      Pos : Natural;
      Size : Natural;
      Best : Candidate;
      Trial : Candidate;
      Chosen : Natural := 0;
      Used : Bool_List := (others => False);
      First_Edge : Natural;
      First_Weight : Long_Float;
      Top_Limit : Natural := 1;

      function Solve_Component
        (Identifier, Span, Root : Positive) return Candidate is
         V : Real_List := (others => 0.0);
         W : Real_List := (others => 0.0);
         Output : Candidate;
         Total : Long_Float;
         Sum : Long_Float;
         Ratio : Long_Float;
         Min_Ratio : Long_Float;
         Max_Ratio : Long_Float;
         Norm2 : Long_Float := 0.0;
         Error_L1 : Long_Float := 0.0;
      begin
         Output.Root := Root;
         Output.Size := Span;
         for I in 1 .. D loop
            if Component_Of (Directed (I)) = Identifier then
               V (Directed (I)) := 1.0 / Long_Float (Span);
            end if;
         end loop;
         for Step in 1 .. Max_Iterations loop
            Total := 0.0;
            Min_Ratio := Long_Float'Last;
            Max_Ratio := 0.0;
            for I in 1 .. D loop
               if Component_Of (Directed (I)) = Identifier then
                  Sum := 0.0;
                  for K in Out_Start (Edges (Directed (I)).Target) ..
                    Out_Start (Edges (Directed (I)).Target + 1) - 1
                  loop
                     Following := Out_Items (Directed (K));
                     if Component_Of (Directed (Following)) = Identifier
                       and then
                         Edges (Directed (Following)).Target /=
                           Edges (Directed (I)).Source
                     then
                        Sum := Sum + V (Directed (Following));
                     end if;
                  end loop;
                  if V (Directed (I)) <= 0.0 then
                     return Output;
                  end if;
                  Ratio := Sum / V (Directed (I));
                  Min_Ratio := Long_Float'Min (Min_Ratio, Ratio);
                  Max_Ratio := Long_Float'Max (Max_Ratio, Ratio);
                  W (Directed (I)) := V (Directed (I)) + Sum;
                  Total := Total + W (Directed (I));
               end if;
            end loop;
            Output.Iterations := Step;
            if Max_Ratio - Min_Ratio <= Tolerance *
              Long_Float'Max (1.0, Max_Ratio)
            then
               Output.Valid := True;
               Output.Rho := (Min_Ratio + Max_Ratio) / 2.0;
               Output.Lower := Min_Ratio;
               Output.Upper := Max_Ratio;
               exit;
            end if;
            if Total <= 0.0 then
               return Output;
            end if;
            for I in 1 .. D loop
               if Component_Of (Directed (I)) = Identifier then
                  V (Directed (I)) := W (Directed (I)) / Total;
               end if;
            end loop;
         end loop;
         if not Output.Valid then
            return Output;
         end if;

         for I in 1 .. D loop
            if Component_Of (Directed (I)) = Identifier then
               Norm2 := Norm2 + V (Directed (I)) * V (Directed (I));
            end if;
         end loop;
         if Norm2 <= 0.0 then
            Output.Valid := False;
            return Output;
         end if;

         for I in 1 .. D loop
            if Component_Of (Directed (I)) = Identifier then
               Output.Energy (Directed (I)) :=
                 V (Directed (I)) * V (Directed (I)) / Norm2;
               Sum := 0.0;
               for K in Out_Start (Edges (Directed (I)).Target) ..
                 Out_Start (Edges (Directed (I)).Target + 1) - 1
               loop
                  Following := Out_Items (Directed (K));
                  if Component_Of (Directed (Following)) = Identifier
                    and then Edges (Directed (Following)).Target /=
                      Edges (Directed (I)).Source
                  then
                     Sum := Sum + V (Directed (Following));
                  end if;
               end loop;
               Error_L1 := Error_L1 +
                 abs (Sum - Output.Rho * V (Directed (I)));
            end if;
         end loop;
         Output.Residual := Error_L1;
         return Output;
      end Solve_Component;

   begin
      Result.Variables := G.Variables;
      Result.Checks := G.Checks;
      Result.Edges := G.Length;
      Result.Directed_Edges := D;
      if D = 0 then
         return Result;
      end if;

      --  Directed edges are enumerated in canonical input order:
      --  check/site forward followed by its reverse.
      for I in 1 .. G.Length loop
         declare
            V : constant Natural := G.Entries (I).V;
            C : constant Natural := G.Variables + G.Entries (I).C;
         begin
            Edges (Directed (2 * I - 1)) :=
              (Source => V, Target => C);
            Edges (Directed (2 * I)) :=
              (Source => C, Target => V);
         end;
      end loop;
      for I in 1 .. D loop
         Out_Degree (Edges (Directed (I)).Source) :=
           Out_Degree (Edges (Directed (I)).Source) + 1;
         In_Degree (Edges (Directed (I)).Target) :=
           In_Degree (Edges (Directed (I)).Target) + 1;
      end loop;
      for Node in 1 .. N loop
         Out_Start (Node + 1) := Out_Start (Node) + Out_Degree (Node);
         In_Start (Node + 1) := In_Start (Node) + In_Degree (Node);
         Out_Cursor (Node) := Out_Start (Node);
         In_Cursor (Node) := In_Start (Node);
      end loop;
      for I in 1 .. D loop
         declare
            Src : constant Natural := Edges (Directed (I)).Source;
            Dst : constant Natural := Edges (Directed (I)).Target;
         begin
            Out_Items (Directed (Out_Cursor (Src))) := I;
            Out_Cursor (Src) := Out_Cursor (Src) + 1;
            In_Items (Directed (In_Cursor (Dst))) := I;
            In_Cursor (Dst) := In_Cursor (Dst) + 1;
         end;
      end loop;

      --  Nonrecursive first Kosaraju pass. Each directed edge and its
      --  non-backtracking neighbours are visited once, no dense B.
      for Root in 1 .. D loop
         if not Visited (Directed (Root)) then
            Top := 1;
            Stack_Node (Directed (Top)) := Root;
            Stack_Position (Directed (Top)) :=
              Out_Start (Edges (Directed (Root)).Target);
            Visited (Directed (Root)) := True;
            while Top > 0 loop
               Current_Edge := Stack_Node (Directed (Top));
               Pos := Stack_Position (Directed (Top));
               if Pos <
                  Out_Start (Edges (Directed (Current_Edge)).Target + 1)
               then
                  Stack_Position (Directed (Top)) := Pos + 1;
                  Following := Out_Items (Directed (Pos));
                  if Edges (Directed (Following)).Target /=
                    Edges (Directed (Current_Edge)).Source
                    and then not Visited (Directed (Following))
                  then
                     Visited (Directed (Following)) := True;
                     Top := Top + 1;
                     Stack_Node (Directed (Top)) := Following;
                     Stack_Position (Directed (Top)) :=
                       Out_Start (Edges (Directed (Following)).Target);
                  end if;
               else
                  Finish_Count := Finish_Count + 1;
                  Finish (Directed (Finish_Count)) := Current_Edge;
                  Top := Top - 1;
               end if;
            end loop;
         end if;
      end loop;

      --  Reverse edges in descending finish order assign SCC membership.
      --  The explicit stack is bounded by D: vertices are assigned on push.
      for Rank in reverse 1 .. D loop
         declare
            Root : constant Natural := Finish (Directed (Rank));
         begin
            if Component_Of (Directed (Root)) = 0 then
               Component_Count := Component_Count + 1;
               Component_Root (Directed (Component_Count)) := Root;
               Component_Of (Directed (Root)) := Component_Count;
               Size := 1;
               Top := 1;
               Stack_Node (Directed (Top)) := Root;
               while Top > 0 loop
                  Current_Edge := Stack_Node (Directed (Top));
                  Top := Top - 1;
                  for K in In_Start (Edges (Directed (Current_Edge)).Source) ..
                    In_Start (Edges (Directed (Current_Edge)).Source + 1) - 1
                  loop
                     Following := In_Items (Directed (K));
                     if Edges (Directed (Following)).Source /=
                       Edges (Directed (Current_Edge)).Target
                       and then Component_Of (Directed (Following)) = 0
                     then
                        Component_Of (Directed (Following)) :=
                          Component_Count;
                        Size := Size + 1;
                        Top := Top + 1;
                        Stack_Node (Directed (Top)) := Following;
                        Component_Root (Directed (Component_Count)) :=
                          Natural'Min
                            (Component_Root (Directed (Component_Count)),
                             Following);
                     end if;
                  end loop;
               end loop;
               Component_Size (Directed (Component_Count)) := Size;
            end if;
         end;
      end loop;
      Result.SCC_Count := Component_Count;
      Result.Status := Acyclic;

      for Identifier in 1 .. Component_Count loop
         Size := Component_Size (Directed (Identifier));
         --  Self transitions are impossible in a simple bipartite Tanner
         --  Hashimoto graph. SCC singletons thus have eigenvalue zero.
         if Size > 1 then
            Result.Cyclic_SCC_Count := Result.Cyclic_SCC_Count + 1;
            Trial := Solve_Component
              (Identifier, Size,
               Component_Root (Directed (Identifier)));
            if not Trial.Valid then
               Result.Status := Not_Converged;
               Result.Spectral_Radius := 0.0;
               Result.Top_Count := 0;
               return Result;
            end if;
            if Chosen = 0
              or else Trial.Rho > Best.Rho + Tie_Tolerance
            then
               Best := Trial;
               Chosen := Identifier;
               Result.Dominant_Tie_Count := 1;
            elsif abs (Trial.Rho - Best.Rho) <= Tie_Tolerance then
               Result.Dominant_Tie_Count :=
                 Result.Dominant_Tie_Count + 1;
               if Trial.Root < Best.Root then
                  Best := Trial;
                  Chosen := Identifier;
               end if;
            end if;
         end if;
      end loop;
      if Chosen = 0 then
         return Result;
      end if;

      Result.Status := Converged_Numeric;
      Result.Mode_Root_Edge := Best.Root;
      Result.Mode_Edge_Count := Best.Size;
      Result.Iterations := Best.Iterations;
      Result.Spectral_Radius := Best.Rho;
      Result.Collatz_Lower := Best.Lower;
      Result.Collatz_Upper := Best.Upper;
      Result.Residual_L1 := Best.Residual;
      for I in 1 .. D loop
         if Component_Of (Directed (I)) = Chosen then
            Result.IPR := Result.IPR +
              Best.Energy (Directed (I)) * Best.Energy (Directed (I));
         end if;
      end loop;

      while Top_Limit * Top_Limit < Best.Size loop
         Top_Limit := Top_Limit + 1;
      end loop;
      Result.Top_Count := Natural'Min (10, Best.Size);
      --  Constant storage and canonical selection; the ranking is
      --  recalculated rather than retaining a dense sorting workspace.
      for Rank in 1 .. Best.Size loop
         First_Edge := 0;
         First_Weight := -1.0;
         for I in 1 .. D loop
            if Component_Of (Directed (I)) = Chosen
              and then not Used (Directed (I))
              and then Best.Energy (Directed (I)) > First_Weight
            then
               First_Edge := I;
               First_Weight := Best.Energy (Directed (I));
            end if;
         end loop;
         if First_Edge = 0 then
            raise Program_Error with "failed sparse edge ranking";
         end if;
         Used (Directed (First_Edge)) := True;
         if Rank <= Top_Limit then
            Result.EEEC := Result.EEEC + First_Weight;
         end if;
         if Rank <= Result.Top_Count then
            Result.Top (Rank) :=
              (Directed_Id => First_Edge, Energy => First_Weight);
         end if;
      end loop;
      return Result;
   end Observe;
end QEC_Scaled_Spectral;
