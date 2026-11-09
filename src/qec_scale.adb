--  SPDX-License-Identifier: MPL-2.0
--  Offline, read-only Phase 1E finite sparse Tanner observatory.
--  File format: exact ASCII, canonical check-major graph edge list.
with Ada.Command_Line;
with Ada.Directories;
with Ada.Exceptions;
with Ada.Strings;
with Ada.Strings.Fixed;
with Ada.Text_IO;
with QEC_Scaled_Spectral;

procedure QEC_Scale is
   use Ada.Command_Line;
   use Ada.Text_IO;
   use type Ada.Directories.File_Size;
   use type QEC_Scaled_Spectral.Solve_Status;
   Invalid_Input : exception;

   package Real_IO is new Ada.Text_IO.Float_IO (Long_Float);

   function Text (Value : Natural) return String is
     (Ada.Strings.Fixed.Trim (Natural'Image (Value), Ada.Strings.Both));

   function Decimal (Value : Long_Float) return String is
      Buffer : String (1 .. 48);
   begin
      Real_IO.Put (To => Buffer, Item => Value, Aft => 12, Exp => 0);
      return Ada.Strings.Fixed.Trim (Buffer, Ada.Strings.Both);
   end Decimal;

   function Exact_Positive (Source : String) return Natural is
      Value : Natural := 0;
   begin
      if Source'Length = 0 or else Source'Length > 6
        or else (Source'Length > 1
                 and then Source (Source'First) = '0')
      then
         raise Invalid_Input with "noncanonical decimal";
      end if;
      for C of Source loop
         if C not in '0' .. '9' then
            raise Invalid_Input with "nondecimal character";
         end if;
         Value := Value * 10 +
           Character'Pos (C) - Character'Pos ('0');
         if Value > 100_000 then
            raise Invalid_Input with "number exceeds input bound";
         end if;
      end loop;
      return Value;
   end Exact_Positive;

   function Header_Count
     (File : File_Type; Expected : String) return Natural is
      Line : constant String := Get_Line (File);
   begin
      if Line'Length <= Expected'Length
        or else Line (Line'First ..
          Line'First + Expected'Length - 1) /= Expected
      then
         raise Invalid_Input with "unexpected graph header";
      end if;
      return Exact_Positive
        (Line (Line'First + Expected'Length .. Line'Last));
   end Header_Count;

   procedure Inspect (Path : String) is
      Source : File_Type;
      Variables : Natural;
      Checks : Natural;
      Count : Natural;
   begin
      if Ada.Directories.Size (Path) > 131_072 then
         raise Invalid_Input with "oversize graph source";
      end if;
      Open (Source, In_File, Path);
      if Get_Line (Source) /= "QECADA-TANNER-EDGES-V1" then
         raise Invalid_Input with "unsupported Tanner schema";
      end if;
      Variables := Header_Count (Source, "variables=");
      Checks := Header_Count (Source, "checks=");
      Count := Header_Count (Source, "edges=");
      if Variables not in 1 .. QEC_Scaled_Spectral.Max_Variables
        or else Checks not in 1 .. QEC_Scaled_Spectral.Max_Checks
        or else Count > QEC_Scaled_Spectral.Max_Edges
      then
         raise Invalid_Input with "graph outside bounded capacities";
      end if;

      declare
         G : QEC_Scaled_Spectral.Graph :=
           QEC_Scaled_Spectral.Create (Variables, Checks);
      begin
         for I in 1 .. Count loop
            declare
               Line : constant String := Get_Line (Source);
               Comma : constant Natural :=
                 Ada.Strings.Fixed.Index (Line, ",");
            begin
               if Comma <= Line'First or else Comma >= Line'Last then
                  raise Invalid_Input with "invalid edge line";
               end if;
               QEC_Scaled_Spectral.Add_Edge
                 (G, Check => Exact_Positive
                   (Line (Line'First .. Comma - 1)),
                  Variable => Exact_Positive
                   (Line (Comma + 1 .. Line'Last)));
            end;
         end loop;
         if not End_Of_File (Source) then
            raise Invalid_Input with "unexpected trailing graph data";
         end if;
         Close (Source);

         declare
            R : constant QEC_Scaled_Spectral.Observation :=
              QEC_Scaled_Spectral.Observe (G);
         begin
            Put_Line ("schema=qec-ada.scaled-spectral.v1");
            Put_Line ("algorithm=bounded-sparse-scc-lazy-perron-v1");
            Put_Line ("mode_scope=selected-recurrent-block");
            Put_Line ("status=" &
              QEC_Scaled_Spectral.Solve_Status'Image (R.Status));
            Put_Line ("variables=" & Text (R.Variables));
            Put_Line ("checks=" & Text (R.Checks));
            Put_Line ("edges=" & Text (R.Edges));
            Put_Line ("directed_edges=" & Text (R.Directed_Edges));
            Put_Line ("scc_count=" & Text (R.SCC_Count));
            Put_Line ("cyclic_scc_count=" & Text (R.Cyclic_SCC_Count));
            Put_Line ("dominant_tie_count=" & Text (R.Dominant_Tie_Count));
            Put_Line ("mode_root_edge=" & Text (R.Mode_Root_Edge));
            Put_Line ("mode_edge_count=" & Text (R.Mode_Edge_Count));
            Put_Line ("iterations=" & Text (R.Iterations));
            Put_Line ("spectral_radius=" & Decimal (R.Spectral_Radius));
            Put_Line ("collatz_lower=" & Decimal (R.Collatz_Lower));
            Put_Line ("collatz_upper=" & Decimal (R.Collatz_Upper));
            Put_Line ("residual_l1=" & Decimal (R.Residual_L1));
            Put_Line ("ipr=" & Decimal (R.IPR));
            Put_Line ("eeec=" & Decimal (R.EEEC));
            Put_Line ("max_variables=" &
              Text (QEC_Scaled_Spectral.Max_Variables));
            Put_Line ("max_checks=" &
              Text (QEC_Scaled_Spectral.Max_Checks));
            Put_Line ("max_edges=" &
              Text (QEC_Scaled_Spectral.Max_Edges));
            Put_Line ("top_count=" & Text (R.Top_Count));
            for I in 1 .. R.Top_Count loop
               Put_Line ("top=" & Text (I) & "," &
                 Text (R.Top (I).Directed_Id) & "," &
                 Decimal (R.Top (I).Energy));
            end loop;
            if R.Status = QEC_Scaled_Spectral.Not_Converged then
               Set_Exit_Status (Failure);
            end if;
         end;
      end;
   end Inspect;

   --  Linux /proc/self/status belongs to the *already exec'd Ada process*.
   --  VmHWM is the kernel high-water mark for this process's current mm.
   --  Unlike wait4/ru_maxrss it excludes the Python launcher and the
   --  pre-exec inherited Python address space. Opt-in and Linux-only.
   function Native_Peak_RSS_KiB return Natural is
      Status_File : File_Type;
      Header : constant String := "VmHWM:";
   begin
      Open (Status_File, In_File, "/proc/self/status");
      while not End_Of_File (Status_File) loop
         declare
            Line : constant String := Get_Line (Status_File);
         begin
            if Line'Length > Header'Length
              and then Line (Line'First ..
                Line'First + Header'Length - 1) = Header
            then
               declare
                  Value : constant String := Ada.Strings.Fixed.Trim
                    (Line (Line'First + Header'Length .. Line'Last),
                     Ada.Strings.Both);
                  Separator : constant Natural :=
                    Ada.Strings.Fixed.Index (Value, " ");
               begin
                  if Separator <= Value'First
                    or else Value (Separator .. Value'Last) /= " kB"
                  then
                     raise Invalid_Input with
                       "unexpected /proc/self/status VmHWM unit";
                  end if;
                  declare
                     Peak : constant Natural := Natural'Value
                       (Value (Value'First .. Separator - 1));
                  begin
                     if Peak = 0 then
                        raise Invalid_Input with "zero VmHWM";
                     end if;
                     Close (Status_File);
                     return Peak;
                  end;
               end;
            end if;
         end;
      end loop;
      Close (Status_File);
      raise Invalid_Input with
        "native VmHWM unavailable; refusing inherited child rusage";
   end Native_Peak_RSS_KiB;

   procedure Usage is
   begin
      Put_Line ("QEC-ADA scaled spectral observatory (bounded, read-only)");
      Put_Line ("  qec_scale inspect <canonical-graph-file>");
      Put_Line ("  qec_scale inspect <canonical-graph-file> --native-rss");
      Put_Line ("  --native-rss reads Linux /proc/self/status VmHWM in Ada");
      Put_Line ("  QECADA-TANNER-EDGES-V1");
      Put_Line ("  variables=N");
      Put_Line ("  checks=M");
      Put_Line ("  edges=E");
      Put_Line ("  CHECK,VARIABLE  (sorted, unique, one per edge)");
      Put_Line ("  This is classical numerical graph research, not QEC proof.");
   end Usage;

begin
   if Argument_Count = 1 and then Argument (1) = "--help" then
      Usage;
   elsif Argument_Count = 2 and then Argument (1) = "inspect" then
      Inspect (Argument (2));
   elsif Argument_Count = 3
     and then Argument (1) = "inspect"
     and then Argument (3) = "--native-rss"
   then
      Inspect (Argument (2));
      Put_Line ("native_post_exec_peak_rss_kib_linux=" &
        Text (Native_Peak_RSS_KiB));
   else
      Usage;
      Set_Exit_Status (Failure);
   end if;
exception
   when E : others =>
      Put_Line (Standard_Error, "ERROR: " &
        Ada.Exceptions.Exception_Name (E) & ": " &
        Ada.Exceptions.Exception_Message (E));
      Set_Exit_Status (Failure);
end QEC_Scale;
