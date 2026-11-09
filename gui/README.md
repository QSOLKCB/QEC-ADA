# QEC-ADA offline research desk

Open `index.html` directly in a modern browser, or run
`uv run --no-project python scripts/qecada.py gui`.

No server, network, Node, framework, CDN, telemetry or account is needed.
The GUI has a restrictive CSP including `connect-src 'none'`.

The 103-entry catalogue is statically embedded so it works under `file://`.
For the four archived HTML and JavaScript source files, `archived-text.js`
contains their exact source as inert string data. The interface displays it
only with `textContent`, not in an iframe, through `innerHTML`, or via a
direct navigable document link. All other archive entries remain linked as
local documents.

**The source files still exist in `docs/reference/qec/`.** A user who manually
opens an HTML path in a browser leaves this viewer's safety model. Review
imported reference HTML/JS before any future snapshot refresh.

The GF(3) workbench is educational JavaScript, not native Ada execution,
SPARK proof, or general quantum error-correction validation. The native CLI
and independent pinned donor validation are available without a GUI.

See `docs/REFERENCE.md` for the trust model and known restrictions.
