--  SPDX-License-Identifier: MPL-2.0
package body QEC_Tanner is
   use type QEC_Configurable.Trit;

   Max_Edges : constant Positive := 20;
   Max_Directed : constant Positive := 2 * Max_Edges;
   subtype Edge_Index is Positive range 1 .. Max_Directed;

   type Directed_Edge is record
      Source : Natural := 0;
      Target : Natural := 0;
   end record;
   type Directed_Array is array (Edge_Index) of Directed_Edge;
   type Walk_Counts is array (Edge_Index) of Natural;

   function Present
     (D : QEC_Configurable.Code_Definition;
      Row : Check; Site : Variable) return Boolean is
   begin
      return D.X (Row) (Site) /= 0 or else D.Z (Row) (Site) /= 0;
   end Present;

   function Observe
     (Definition : QEC_Configurable.Code_Definition)
      return Graph_Observation is
      D : constant QEC_Configurable.Code_Definition := Definition;
      R : Graph_Observation;
      E : Directed_Array := (others => (Source => 0, Target => 0));
      Count : Natural := 0;
      Current : Walk_Counts;
      Next_Walk : Walk_Counts;
      Total : Natural := 0;
   begin
      --  This is an observational graph, not a quantum decoder.
      --  Enforce exact explicit padding without imposing stabilizer
      --  commutation or any correction-radius assumptions.
      for Row in QEC_Configurable.Check_Index loop
         for Site in QEC_Configurable.Site_Index loop
            if (Row > D.Rows or else Site > D.Sites)
              and then (D.X (Row) (Site) /= 0
                         or else D.Z (Row) (Site) /= 0)
            then
               raise Constraint_Error with "noncanonical Tanner padding";
            end if;
         end loop;
      end loop;
      R.Sites := Natural (D.Sites);
      R.Checks := Natural (D.Rows);
      --  Canonical edge iteration is check-major, then variable-major.
      --  X/Z support is a SIMPLE undirected bipartite graph, not a
      --  multigraph with two edges when both X and Z are nonzero.
      for Row in 1 .. D.Rows loop
         for Site in 1 .. D.Sites loop
            if Present (D, Row, Site) then
               R.Edges := R.Edges + 1;
               R.Variable_Degree (Site) := R.Variable_Degree (Site) + 1;
               R.Check_Degree (Row) := R.Check_Degree (Row) + 1;
               if D.X (Row) (Site) /= 0 then
                  R.X_Edges := R.X_Edges + 1;
               end if;
               if D.Z (Row) (Site) /= 0 then
                  R.Z_Edges := R.Z_Edges + 1;
               end if;
               if D.X (Row) (Site) /= 0
                 and then D.Z (Row) (Site) /= 0
               then
                  R.Mixed_Edges := R.Mixed_Edges + 1;
               end if;

               Count := Count + 1;
               E (Edge_Index (Count)) :=
                 (Source => Natural (Site),
                  Target => Natural (D.Sites) + Natural (Row));
               Count := Count + 1;
               E (Edge_Index (Count)) :=
                 (Source => Natural (D.Sites) + Natural (Row),
                  Target => Natural (Site));
            end if;
         end loop;
      end loop;

      --  Exact 4-cycles: two checks share an unordered pair of sites.
      --  Heat counts one participation per variable per cycle.
      for First_Row in 1 .. D.Rows loop
         for Other_Row in First_Row + 1 .. D.Rows loop
            for A in 1 .. D.Sites loop
               if Present (D, First_Row, A)
                 and then Present (D, Other_Row, A)
               then
                  for B in A + 1 .. D.Sites loop
                     if Present (D, First_Row, B)
                       and then Present (D, Other_Row, B)
                     then
                        R.Four_Cycles := R.Four_Cycles + 1;
                        R.Variable_Cycle_Heat (A) :=
                          R.Variable_Cycle_Heat (A) + 1;
                        R.Variable_Cycle_Heat (B) :=
                          R.Variable_Cycle_Heat (B) + 1;
                     end if;
                  end loop;
               end if;
            end loop;
         end loop;
      end loop;

      --  The directed-edge Hashimoto non-backtracking matrix has
      --  B(e,f)=1 when target(e)=source(f) and f is not the reverse e.
      --  Compute trace(B^4) by four exact sparse logical steps from
      --  every directed basis vector; never build a dense B matrix.
      for Start in 1 .. Count loop
         Current := (others => 0);
         Current (Edge_Index (Start)) := 1;
         for Depth in 1 .. 4 loop
            Next_Walk := (others => 0);
            for I in 1 .. Count loop
               if Current (Edge_Index (I)) /= 0 then
                  for J in 1 .. Count loop
                     if E (Edge_Index (I)).Target =
                         E (Edge_Index (J)).Source
                       and then E (Edge_Index (I)).Source /=
                         E (Edge_Index (J)).Target
                     then
                        Next_Walk (Edge_Index (J)) :=
                          Next_Walk (Edge_Index (J)) +
                          Current (Edge_Index (I));
                     end if;
                  end loop;
               end if;
            end loop;
            Current := Next_Walk;
         end loop;
         Total := Total + Current (Edge_Index (Start));
      end loop;
      R.NB_Trace_4 := Total;

      if R.NB_Trace_4 /= 8 * R.Four_Cycles then
         raise Program_Error with "Tanner/NB fourth-moment identity";
      end if;
      return R;
   end Observe;
end QEC_Tanner;
