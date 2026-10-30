# Task Report — 13 Research Lab
## Files
FRONTEND/research.html, BACKEND/research.py.
## Behaviour
Private page (local-only or token-gated API) that reads real artifacts only: model status, frozen split manifest and leakage report, agreement reports, research-grade runs (metrics, per-class tables, confusion matrices, training curves, seeds, dataset hash, library versions, experiment ids), ablations (descriptive, with the interpretation guard), trace-log counts, summary JSON download. Smoke/fixture runs are listed separately under "NOT RESEARCH". Missing sections show an explicit empty state explaining what is needed; nothing is estimated.
## Tests
Backend tests for empty state, smoke separation, admin guard, path-traversal blocking; jsdom tests for empty states and for research vs non-research rendering (render fixture, labelled).
## Limitations
Not browser-tested beyond jsdom; no pagination for large trace logs; confusion heat-shading uses CSS color-mix (modern browsers).
