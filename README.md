# QEC-ADA

**Independent native Ada/SPARK implementation of selected, deterministic QEC kernels.**

QEC-ADA is a new project, not a fork of QSOLKCB/QEC and not a declaration that the
Python research programme has been ported. The initial deliverable contains a
small GF(3) mathematical kernel, a three-term syndrome demo, frozen reference
documents, a reproducible documentation catalogue and a local browser UI.

- **Reference:** [QSOLKCB/QEC](https://github.com/QSOLKCB/QEC) at pinned commit
  `27bbc798c4e38138ca5b0fff70b15c3271a1917d`.
- **Documentation:** [docs/README.md](docs/README.md), including the verbatim
  mirror in [docs/reference/qec/](docs/reference/qec/).
- **Source layout:** `codes/` finite fields; `decode/` syndrome boundary;
  `invariants/` verification contracts; `research/` proposed experiments.
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

On Windows use `build\bin\qec_ada.exe`. The syndrome demo accepts a
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
