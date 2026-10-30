# Task 15 preparation

Objective: implement offline targeted-versus-uniform comparisons and prepare
the human-evaluation workflow without collecting participants.

Files: `ML/evaluation.py`, `RESEARCH/EVALUATION_WORKFLOW.md`, continuation tests.
Metrics include passage intervention rate, token additions/deletions/replacements,
source-token retention, sentence changes, edit budget and verification flags.
Paired outputs use the same passage; generic accessibility preserves text.
Unavailable scorers remain null, and all outputs are descriptive/unvalidated.
Input hashes and per-passage checks are saved; overwriting is refused.

Tests: identity/layout-only/addition/substitution cases, four-condition matching,
missing/duplicate inputs, honest missing scores and versioned output behavior.
Final verification: `REPORTS/QA_AUDIT.md`.

Limit: human study remains blocked (HG-02); real outcomes/semantic calibration
remain unavailable. Task 15 is prepared, not scientifically completed.
Next: reviewed dataset, actual paired outputs and approved human evaluation.
