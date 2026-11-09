# QEC-ADA

**Independent native Ada/SPARK implementation of selected, deterministic QEC kernels.**

QEC-ADA is a new project, not a fork of QSOLKCB/QEC and not a declaration that the
Python research programme has been ported. The initial deliverable contains a GF(3) mathematical kernel, a three-term
syndrome demo, frozen reference documents, and a local browser UI. The next
native phase adds a **fixed cyclic [[5,1,3]]₃ bounded coset-leader decoder**
and an immutable-snapshot classical first-free routing pilot. These are bounded
research implementations, not general QEC or full Strowger switching.

- **Reference:** [QSOLKCB/QEC](https://github.com/QSOLKCB/QEC) at pinned commit
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`.
- **Documentation:** [docs/README.md](docs/README.md), including the verbatim
  mirror in [docs/reference/qec/](docs/reference/qec/).
- **Source layout:** `codes/` finite fields and fixed qutrit code; `decode/`
  syndrome boundary; `routing/` deterministic selection; `invariants/`
  verification contracts; `research/` proposed experiments.
- **Fixtures:** `fixtures/qec_reference_manifest.json` records Git blob
  hashes of 103 preserved reference files; two support assets are explicitly
  excluded (see [reference note](docs/REFERENCE.md)).
- **GUI:** open [gui/index.html](gui/index.html) locally in a modern desktop
  browser—no network requests, install, account, backend or build step.
- **Licensing:** MPL-2.0, with attribution in [NOTICE](NOTICE).

## Build the native CLI

Requires a GNAT Ada compiler and GPRbuild. No runtime libraries or package
manager are needed for the initial kernel.

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_ada --help
./build/bin/qec_ada gf3 add 1 2
./build/bin/qec_ada gf3 mul 2 2
./build/bin/qec_ada syndrome 1 2 1 2 0 1
~~~

For the fixed qutrit code and routing pilot:

~~~sh
./build/bin/qec_ada selftest qutrit
./build/bin/qec_ada qutrit decode 10000 00000
./build/bin/qec_ada qutrit lookup 0002
./build/bin/qec_ada route 1 2 0 1 0101 0011 1010
~~~

[Algorithm, OPT design and limits](docs/PHASE1A_DECODER_ROUTING.md).

On Windows use `build\bin\qec_ada.exe`. The original syndrome demo accepts a
three-term check vector followed by a three-term error vector; it does **not**
run a general quantum decoder.

## Portable docs CLI

Only the Python standard library is used. With uv:

~~~sh
uv run --no-project python scripts/qecada.py status
uv run --no-project python scripts/qecada.py docs search qutrit
uv run --no-project python scripts/qecada.py docs list --json
uv run --no-project python scripts/qecada.py docs show QUTRIT_HARMONIC_QEC.md
uv run --no-project python scripts/qecada.py verify
uv run --no-project python scripts/qecada.py gui
~~~

Or use `python3` in place of `uv run --no-project python`. Docs search is
offline, never fetches GitHub, and returns paths using stable source-relative
identifiers. The catalogue deliberately distinguishes **reference** from
**implemented** functionality.

## Validation status

The mirrored documents were compared by Git blob SHA-1 to their source at
import time. Ada compilation, GNATprove proof discharge and physical hardware
validation are separate gates; source code or a GUI demonstration alone is not
a formal proof. See [porting plan](docs/PORTING.md) and [CI policy](AGENTS.md).

## Project principles

1. Independently implement mathematics; preserve donor attribution and licence.
2. Use immutable, pinned source fixtures; never reinterpret old receipt bytes.
3. Reproduce defined behaviour before claiming equivalence or acceleration.
4. Keep execution and proof separate. SPARK annotations are not proof results.
5. Local-first, reproducible, no Docker, Node, CDN or cloud dependency.
6. Maintain reviewable PRs; no automatic release, merge or public GUI deployment.

## Phase 1B — Configurable stabilizer-code pilot

A separate bounded Ada decoder now accepts **1–5 qutrit sites and 1–4
independent, commuting stabilizer checks**. It validates finite-field
symplectic constraints, syndrome collision degeneracy, and radius-one
correctability. OPT contributions are immutable and held together with the
exact code-definition snapshot. A scalar path and independent Python tests
provide cross-code validation.

~~~sh
./build/bin/qec_ada selftest config
./build/bin/qec_ada config decode 2 10 01 0010 0001
~~~

[Phase 1B implementation and limits](docs/PHASE1B_CONFIGURABLE.md).

An isolated GNATprove 16.1.0 GF(3) arithmetic proof target completed
**28/28 checks**. See [proof receipt](docs/PHASE1B_SPARK_PROOF.md).
This does not certify the configurable decoder, OPT cache, or hardware QEC.

## Phase 1C — Observational SPECTRAL/Tanner + deterministic Strowger

The separately compiled `qec_research` CLI adds **exact bounded Tanner
graphs**, non-backtracking 4th-moment calculations, and a classical
Strowger event-stream pilot.

~~~sh
gprbuild -p -P qec_ada.gpr
./build/bin/qec_research tanner 2 1100 0012
./build/bin/qec_research strowger 1020 3333 1100 0100 0010 none
~~~

See [Phase 1C scope and evidence boundaries](docs/PHASE1C_TANNER_SPECTRAL.md).
Observational diagnostics do not alter decoder execution. No universal
eigensolver or physical QEC / audible physics claim is made.

### SPECTRAL export, 24-bit sonification and Strowger receipt replay

~~~sh
uv run --no-project python scripts/tanner_spectral_export.py \
  2 1100 0012 --output /tmp/qecada-tanner.json
uv run --no-project python scripts/tanner_sonify.py \
  2 1100 0012 --wav /tmp/qecada-tanner.wav \
  --manifest /tmp/qecada-tanner-audio.json

uv run --no-project python scripts/strowger_receipt.py create \
  /tmp/qecada-route.json 1020 3333 1100 0100 0010 none \
  --request-id demo-001
uv run --no-project python scripts/strowger_receipt.py verify \
  /tmp/qecada-route.json
~~~

The graph-to-audio demonstration produces **48 kHz signed 24-bit PCM**,
not 16-bit, and is deliberately distinct from SPECTRAL QEC/APP's separate
decoder event-import and render-receipt protocol. All receipt verification
remains offline with the Python standard library.

## Phase 1D — Sparse non-backtracking spectral observatory

A separate native Ada graph observer computes numerical dominant
**recurrent-component** non-backtracking spectral radii, IPR, top-energy
concentration and stable edge-sensitivity rankings. Sparse edge
transitions and deterministic SCC handling avoid a dense Hashimoto matrix
and periodicity-induced failure of naive power iteration.

~~~sh
./build/bin/qec_research spectral 2 1100 0012
./build/bin/qec_research spectral 3 111000 000111
~~~

The solver fails closed if numerical convergence is not reached. It does
not modify the decoder or produce hardware-QEC evidence. Its mode
vectors are local to the selected recurrent SCC, not necessarily global
eigenvectors on reducible graphs. See
[Phase 1D method and test contract](docs/PHASE1D_SPARSE_SPECTRAL.md).

### Auditable spectral observation

~~~sh
uv run --no-project python scripts/nb_spectral_export.py create \
  /tmp/qecada-nb-k23.json 3 111000 000111
uv run --no-project python scripts/nb_spectral_export.py verify \
  /tmp/qecada-nb-k23.json
~~~

This makes a canonical SHA-256 receipt binding source Tanner rows,
independently checked exact graph metrics and the native SCC-local
numerical spectrum. The verifier reconstructs the result from the
declared source using only Python's standard library, no Ada binary.
It is not a hardware-QEC certificate.

## Phase 1E — Scaled sparse spectral observatory and controlled BP validation

A separate native Ada executable, `qec_scale`, handles up to **128
variables, 128 check nodes and 2,048 canonical Tanner edges**. A
deterministic SCC-aware matrix-free non-backtracking solver reports
numerical recurrent-block spectral radii, IPR and edge-energy metrics.

A separate Python-standard-library experiment runs real **classical GF(2)
min-sum BP** on deterministic synthetic graph/noise ensembles and records
replayable per-iteration failures. Evaluation is **graph-blocked**: no
shared topology between training and held-out predictive testing.

The first 20-graph, 720-trial study **did not meet the preregistered
IPR predictive threshold**. At the primary 8% noise level, held-out
IPR AUROC was 0.595238 vs a 0.383598 edge-density baseline. This is
a negative experimental observation, not a physical quantum prediction.

~~~sh
gprbuild -p -P qec_ada.gpr
uv run --no-project python scripts/phase1e_experiment.py run \
  /tmp/qecada-phase1e.json --graphs 20 --trials 12 \
  --variables 32 --checks 24 --seed qecada-phase1e-001
uv run --no-project python scripts/phase1e_experiment.py verify \
  /tmp/qecada-phase1e.json
~~~

[Full Phase 1E methods, results, limits and evidence](docs/PHASE1E_SCALED_SPECTRAL_BP.md).
The earlier small-graph decoder, SPECTRAL sonification, Strowger receipts
and independent QEC donor provenance are preserved.

### Phase 1E measurement correction (post-exec RSS)

`scripts/phase1e_memory.py` now obtains Linux `VmHWM` **inside the
executing Ada binary**, not through a potentially contaminated
`RUSAGE_CHILDREN` high-water mark. Normal `qec_scale inspect`
output remains unchanged; the benchmark opts in with `--native-rss`.
Earlier CI readings obtained from the Python parent were **not isolated
native RSS measurements** and are superseded by v2 evidence. See the
[corrected measurements and limitations](docs/PHASE1E_SCALED_SPECTRAL_BP.md).

The same Phase 1E audit also makes average precision undefined (`null`)
when a held-out dataset contains only failures or only successes,
matching the AUROC missing-class policy.
