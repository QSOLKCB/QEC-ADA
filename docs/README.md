# QEC-ADA documentation index

This directory separates **current implementation guidance** from **archived
QEC reference material**. The original QEC documents have not been rewritten.

| Start here | Purpose |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Native design, execution and proof boundaries |
| [PORTING.md](PORTING.md) | Incremental QEC-to-Ada migration sequence |
| [PHASE1A_DECODER_ROUTING.md](PHASE1A_DECODER_ROUTING.md) | Fixed qutrit decoder, OPT reuse and classical deterministic routing |
| [PHASE1B_CONFIGURABLE.md](PHASE1B_CONFIGURABLE.md) | Configurable GF(3) stabilizer validation, OPT binding and tests |
| [PHASE1C_TANNER_SPECTRAL.md](PHASE1C_TANNER_SPECTRAL.md) | Native Tanner/SPECTRAL observations, sonification and Strowger replay |
| [PHASE1D_SPARSE_SPECTRAL.md](PHASE1D_SPARSE_SPECTRAL.md) | SCC-aware recurrent-block spectral modes, IPR and edge energy |
| [PHASE1E_SCALED_SPECTRAL_BP.md](PHASE1E_SCALED_SPECTRAL_BP.md) | Scaled sparse observatory, classical BP failures and retained negative result |
| [PHASE1F_GRAPH_BLOCKED_QEC_BP.md](PHASE1F_GRAPH_BLOCKED_QEC_BP.md) | Topology-blocked uncertainty and actual pinned QEC BP comparison |
| [PHASE1G_QEC_CSS_FAMILY.md](PHASE1G_QEC_CSS_FAMILY.md) | Source-pinned CSS/QLDPC Tanner admission and family-blocked BP |
| [GUI.md](GUI.md) | Universal offline browser UI and its limits |
| [REFERENCE.md](REFERENCE.md) | Donor source, exact-copy policy and omissions |
| [reference/qec/](reference/qec/) | Verbatim QEC documentation and labs |
| [../research/](../research/) | New research proposals |
| [../codes/](../codes/) | GF(3) finite-field source |
| [../decode/](../decode/) | Native decoder boundary |
| [../invariants/](../invariants/) | SPARK-oriented invariant contracts |
| [../fixtures/](../fixtures/) | Manifest and reference vectors |

## CLI discovery

~~~sh
uv run --no-project python scripts/qecada.py docs list --json
uv run --no-project python scripts/qecada.py docs search decoder
uv run --no-project python scripts/qecada.py docs show architecture/INVARIANTS.md
~~~

The CLI returns paths relative to `docs/reference/qec`, so tooling can use
them as stable IDs independently of working directory. No network required.

## Current scope

Only the initial bounded GF(3) arithmetic and demo syndrome calculation are
native implementation candidates. All other documentation is source context
until separately ported, tested and verified.

