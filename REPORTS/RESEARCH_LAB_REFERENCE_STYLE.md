# Reference-driven admin visual redesign

The admin Research Lab now follows the supplied dark research/dashboard reference: a compact navigation sidebar, teal/violet paired accents, dark and light themes, alternate accent palettes, readiness cards, recorded training curves, comparison tables and a side evidence inspector.

The learner reading room was not modified. Research theme preferences have a separate storage key. Navigation controls connect to actual dataset, run, experiment, error, feedback, training and report views. The inspector calls the existing admin-gated artifact endpoint and renders content as literal text.

No scores or training curves were invented. The dashboard shows empty states without real recorded results. The self-contained RESEARCH_PREVIEW.html is a snapshot of the current actual artifact state; live evidence and artifact loading require the backend. The image is used as a style reference, not as project data.

Backend access remains local/admin-token restricted. A full account/role login system was not implemented by this visual change. Automatic retraining remains disabled.

Verification is automated DOM/API and static auditing. Actual browser rendering and assistive-technology behaviour remain unverified.

Verification: 28 interface checks passed in the targeted runner; the 11-check Python interface/audit selection passed. Static QA: 43 pass, no warnings/failures. Standalone actual-state preview verified in jsdom.
