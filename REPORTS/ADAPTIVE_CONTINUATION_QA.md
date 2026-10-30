# Adaptive continuation verification

53 backend checks passed: persistent preferences, profile isolation, final-decision idempotency, opt-out deletion, GPT prototype provenance, uncertainty routing, local-provider fallback, generated-negation rejection, admin access gates, reviewed training, held-out overlap rejection, evaluated promotion, stale-validation hash guard and rollback.

28 existing UI checks passed in the no-model fallback configuration. 4 adaptive interface checks passed with the bundled prototype: status/opt-in controls, contextual explanations and saved notes, next-request preference adaptation and deletion, admin candidate training/activation/rollback. These used jsdom against a live FastAPI server; they are not real-browser layout or assistive-technology certification.

4 legacy neural/research checks were excluded because optional torch/transformers dependencies were absent. No pretrained transformer or local generative-model weights were exercised. Optional local generation was tested with controlled mock responses.

The shipped baseline is the original weak-label training run. Temporary UI-test candidate runs and learner databases are not shipped. Its validation macro-F1 is 0.430357; its one-time test macro-F1 is 0.285714. Test data were not used for candidate selection or activation.

Windows launcher syntax is supplied; the Windows runtime was not exercised on this Linux build host. See RUN_ADAPTIVE.md for setup and limitations. No study with students with dyslexia has been conducted.
