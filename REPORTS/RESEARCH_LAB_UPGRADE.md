# Research workspace upgrade

The private Research Lab now separates evaluation evidence, preparation of a training run, and explanation of controlled model improvement. Readiness comes from the actual existing summary. Missing artifacts remain unavailable.

Added a relative-path and version-validated local command builder for data validation, frozen document splitting, baselines and DistilBERT. It does not launch shell commands or paid jobs. Known recorded output versions are rejected. JSON export is retained; Markdown documentation export includes actual research runs and provenance while excluding smoke metrics.

No learner collection, retraining job, model registration or experimental result was created. The protocol and remaining limitations are described in RESEARCH/CONTROLLED_LEARNING.md. Existing local/admin API restrictions are retained.

Automated tests cover the command contract, rejection of shell injection/parent paths, evidence-preserving tab changes and no fabricated research-report scores. Actual browser rendering and participant usability remain unverified.

Verification: 31 targeted Python checks passed, including the runner for 26 interface checks. Final interface recheck passed after the recorded-run collision guard. Audit: 43 pass, zero warnings/failures. The preceding full suite passed 152 tests; the backend/ML code was not changed in this update.
