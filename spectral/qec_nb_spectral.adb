--  SPDX-License-Identifier: MPL-2.0
with QEC_Tanner;
package body QEC_NB_Spectral is
   use type QEC_Configurable.Trit;

   subtype Index is Edge_Index;
   type Directed_Edge is record
      Source : Natural := 0;
      Target : Natural := 0;
   end record;
   type Directed_Array is array (Index) of Directed_Edge;
   type Membership is array (Index) of Boolean;
   type Queue_Array is array (Index) of Natural;
   type Weight_Vector is array (Index) of Long_Float;

   Max_Iterations : constant Positive := 4_000;
   Relative_Tolerance : constant Long_Float := 1.0E-11;
   Tie_Tolerance : constant Long_Float := 1.0E-9;

   function Allowed
     (E : Directed_Array; I, J : Index) return Boolean is
   begin
      return E (I).Target = E (J).Source
        and then E (I).Source /= E (J).Target;
   end Allowed;

   function Reachable
     (E : Directed_Array; Count : Natural; Start : Index;
      Is_Reverse : Boolean) return Membership is
      Seen : Membership := (others => False);
      Queue : Queue_Array := (others => 0);
      Head : Natural := 1;
      Tail : Natural := 1;
   begin
      Seen (Start) := True;
      Queue (1) := Natural (Start);
      while Head <= Tail loop
         declare
            Current : constant Index := Index (Queue (Index (Head)));
         begin
            for J in 1 .. Count loop
               if not Seen (Index (J)) then
                  if (not Is_Reverse and then Allowed (E, Current, Index (J)))
                    or else
                     (Is_Reverse and then Allowed (E, Index (J), Current))
                  then
                     Seen (Index (J)) := True;
                     Tail := Tail + 1;
                     Queue (Index (Tail)) := J;
                  end if;
               end if;
            end loop;
         end;
         Head := Head + 1;
      end loop;
      return Seen;
   end Reachable;

   type Candidate_Mode is record
      Valid : Boolean := False;
      Root : Natural := 0;
      Count : Natural := 0;
      Iterations : Natural := 0;
      Rho : Long_Float := 0.0;
      Lower : Long_Float := 0.0;
      Upper : Long_Float := 0.0;
      Residual : Long_Float := 0.0;
      IPR : Long_Float := 0.0;
      Energy : Edge_Weight := (others => 0.0);
   end record;

   function Solve
     (E : Directed_Array; Count : Natural; Members : Membership;
      Root : Index; Size : Natural) return Candidate_Mode is
      V : Weight_Vector := (others => 0.0);
      W : Weight_Vector := (others => 0.0);
      Result : Candidate_Mode;
      Sum : Long_Float;
      Total : Long_Float;
      Lower : Long_Float := 0.0;
      Upper : Long_Float := 0.0;
      Rho : Long_Float;
      Norm2 : Long_Float := 0.0;
      Difference : Long_Float := 0.0;
   begin
      Result.Root := Natural (Root);
      Result.Count := Size;
      --  Strict positive normalized start (no hidden randomness or seed).
      for I in 1 .. Count loop
         if Members (Index (I)) then
            V (Index (I)) := 1.0 / Long_Float (Size);
         end if;
      end loop;

      for Step in 1 .. Max_Iterations loop
         Total := 0.0;
         Lower := Long_Float'Last;
         Upper := 0.0;
         for I in 1 .. Count loop
            if Members (Index (I)) then
               Sum := 0.0;
               for J in 1 .. Count loop
                  if Members (Index (J))
                    and then Allowed (E, Index (I), Index (J))
                  then
                     Sum := Sum + V (Index (J));
                  end if;
               end loop;
               --  Perron bounds on the recurrent block only.
               Rho := Sum / V (Index (I));
               if Rho < Lower then
                  Lower := Rho;
               end if;
               if Rho > Upper then
                  Upper := Rho;
               end if;
               --  Lazy iteration I+B breaks the period of bipartite or
               --  directed-cycle components while retaining eigenvectors.
               W (Index (I)) := V (Index (I)) + Sum;
               Total := Total + W (Index (I));
            end if;
         end loop;
         Result.Iterations := Step;
         if Upper - Lower <= Relative_Tolerance *
           Long_Float'Max (1.0, Upper)
         then
            Result.Valid := True;
            exit;
         end if;
         if Total <= 0.0 then
            return Result;
         end if;
         for I in 1 .. Count loop
            if Members (Index (I)) then
               V (Index (I)) := W (Index (I)) / Total;
            end if;
         end loop;
      end loop;
      if not Result.Valid then
         return Result;
      end if;

      Rho := (Lower + Upper) / 2.0;
      Result.Rho := Rho;
      Result.Lower := Lower;
      Result.Upper := Upper;
      for I in 1 .. Count loop
         if Members (Index (I)) then
            Norm2 := Norm2 + V (Index (I)) * V (Index (I));
         end if;
      end loop;
      for I in 1 .. Count loop
         if Members (Index (I)) then
            Result.Energy (Index (I)) :=
              V (Index (I)) * V (Index (I)) / Norm2;
            Result.IPR := Result.IPR +
              Result.Energy (Index (I)) * Result.Energy (Index (I));
            Sum := 0.0;
            for J in 1 .. Count loop
               if Members (Index (J))
                 and then Allowed (E, Index (I), Index (J))
               then
                  Sum := Sum + V (Index (J));
               end if;
            end loop;
            Difference := Difference + abs (Sum - Rho * V (Index (I)));
         end if;
      end loop;
      --  V has L1 norm exactly 1 up to floating arithmetic.
      Result.Residual := Difference;
      return Result;
   end Solve;

   function Observe
     (Definition : QEC_Configurable.Code_Definition) return Spectrum is
      --  Reuse independent Phase 1C exact-graph validation and invariants.
      Graph : constant QEC_Tanner.Graph_Observation :=
        QEC_Tanner.Observe (Definition);
      E : Directed_Array := (others => (Source => 0, Target => 0));
      Assigned : Membership := (others => False);
      Members : Membership;
      Forward : Membership;
      Backward : Membership;
      Candidate : Candidate_Mode;
      Best : Candidate_Mode;
      Count : Natural := 0;
      Size : Natural;
      Result : Spectrum;
      Chosen : Membership := (others => False);
      Remaining : Membership := (others => False);
      Top : Natural := 0;
      Best_Edge : Natural;
      Best_Weight : Long_Float;
   begin
      for Row in 1 .. Definition.Rows loop
         for Site in 1 .. Definition.Sites loop
            if Definition.X (Row) (Site) /= 0
              or else Definition.Z (Row) (Site) /= 0
            then
               Count := Count + 1;
               E (Index (Count)) :=
                 (Source => Natural (Site),
                  Target => Natural (Definition.Sites) + Natural (Row));
               Count := Count + 1;
               E (Index (Count)) :=
                 (Source => Natural (Definition.Sites) + Natural (Row),
                  Target => Natural (Site));
            end if;
         end loop;
      end loop;
      if Count /= 2 * Graph.Edges then
         raise Program_Error with "Tanner/Hashimoto topology mismatch";
      end if;
      Result.Directed_Edges := Count;
      if Count = 0 then
         return Result;
      end if;
      Result.Status := Acyclic;

      --  Sparse SCC decomposition: forward/reverse graph traversal over
      --  directed edge IDs. No O(E**2) Hashimoto matrix allocation.
      for Root in 1 .. Count loop
         if not Assigned (Index (Root)) then
            Result.SCC_Count := Result.SCC_Count + 1;
            Forward := Reachable (E, Count, Index (Root), False);
            Backward := Reachable (E, Count, Index (Root), True);
            Members := (others => False);
            Size := 0;
            for J in 1 .. Count loop
               if Forward (Index (J)) and then Backward (Index (J)) then
                  Members (Index (J)) := True;
                  Assigned (Index (J)) := True;
                  Size := Size + 1;
               end if;
            end loop;
            --  No directed-edge self loops are possible in simple Tanner
            --  graphs. Singletons are transient and have eigenvalue 0.
            if Size > 1 then
               Result.Cyclic_SCC_Count := Result.Cyclic_SCC_Count + 1;
               Candidate := Solve (E, Count, Members, Index (Root), Size);
               if not Candidate.Valid then
                  Result.Status := Not_Converged;
                  Result.Spectral_Radius := 0.0;
                  Result.Ranking_Count := 0;
                  Result.Energy := (others => 0.0);
                  return Result;
               end if;
               if Result.Status = Acyclic
                 or else Candidate.Rho >
                   Best.Rho + Tie_Tolerance
               then
                  Best := Candidate;
                  Chosen := Members;
                  Result.Dominant_Tie_Count := 1;
                  Result.Status := Converged_Numeric;
               elsif abs (Candidate.Rho - Best.Rho) <= Tie_Tolerance then
                  --  Exact canonical tie rule: earlier minimum edge index
                  --  remains selected (SCC roots are scanned ascending).
                  Result.Dominant_Tie_Count :=
                    Result.Dominant_Tie_Count + 1;
               end if;
            end if;
         end if;
      end loop;
      if Result.Status /= Converged_Numeric then
         return Result;
      end if;

      Result.Root_Edge := Best.Root;
      Result.Mode_Edge_Count := Best.Count;
      Result.Iterations := Best.Iterations;
      Result.Spectral_Radius := Best.Rho;
      Result.Collatz_Lower := Best.Lower;
      Result.Collatz_Upper := Best.Upper;
      Result.Residual_L1 := Best.Residual;
      Result.IPR := Best.IPR;
      Result.Energy := Best.Energy;

      --  Score ranking stable on exact source edge IDs, ties resolved
      --  by ascending index. EEEC uses ceil(sqrt(active_mode_edges)).
      Top := 1;
      while Top * Top < Best.Count loop
         Top := Top + 1;
      end loop;
      Result.Ranking_Count := Best.Count;
      for Rank in 1 .. Best.Count loop
         Best_Edge := 0;
         Best_Weight := -1.0;
         for I in 1 .. Count loop
            if Chosen (Index (I)) and then not Remaining (Index (I))
              and then Best.Energy (Index (I)) > Best_Weight
            then
               Best_Edge := I;
               Best_Weight := Best.Energy (Index (I));
            end if;
         end loop;
         if Best_Edge = 0 then
            raise Program_Error with "missing spectral ranking edge";
         end if;
         Remaining (Index (Best_Edge)) := True;
         Result.Ranking (Index (Rank)) := Best_Edge;
         if Rank <= Top then
            Result.EEEC := Result.EEEC + Best_Weight;
         end if;
      end loop;
      return Result;
   end Observe;
end QEC_NB_Spectral;
