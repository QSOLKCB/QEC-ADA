# Universal offline GUI

**Chosen approach:** plain HTML, CSS and JavaScript served directly from
`gui/index.html` via `file://` without CDN, framework, Node, account,
installer or network. A current browser is the only GUI dependency.

The static interface supports:
- indexed browsing/filtering of the mirrored QEC documentation;
- links to the local historical files;
- an explicitly labelled three-term GF(3) syndrome **demo**.

It does **not** execute Ada code, modify research artifacts, prove programs,
or make any network requests. The Ada CLI is the authoritative executable
candidate, and GNATprove is a separate proof authority. A later optional
loopback service (bound to 127.0.0.1, no public listen, no network by default)
could mediate CLI invocations after explicit design and security review.

This avoids committing to GTK/Qt GUI installations, WebView-specific runtimes,
or the deprecated Ada Web Server package. Use a browser for universal
presentation; keep computation native and independently validated.
