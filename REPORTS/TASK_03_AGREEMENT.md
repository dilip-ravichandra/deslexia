# Task Report

## Task
03_AGREEMENT

## Objective
Inter-annotator agreement, class-wise agreement, conflict reports, adjudication tracking.

## Files changed
ML/agreement.py (new), TESTS/test_agreement.py (new), PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q TESTS/test_agreement.py` -> 8 passed. Full suite: 34 passed, 1 known failure (D1, Task 04).

## Results
- `cohen_kappa` (pairwise) verified against scikit-learn; `krippendorff_alpha_nominal` (any number of annotators, missing data) verified against Krippendorff's published 4-observer example (alpha = 0.743).
- `agreement_report`: Krippendorff alpha, raw % agreement, pairwise kappa with n, one-vs-rest alpha per class, label distribution, conflict-pair counts, adjudication counts (queued/adjudicated/pending). `conflict_report` lists disagreeing spans.
- Undefined cases (single observed label, <2 labels) return None, never 1.0. Fewer than 30 multi-annotated spans emits an "unstable" warning.
- CLI: `python -m ML.agreement --annotations <long.csv> --out artifacts/agreement.json`.

## Limitations
No real annotations exist, so no agreement value has been computed on project data; the only numbers above are test fixtures and a published reference example. The 30-span warning threshold is a pragmatic guard, not a statistical power analysis. Nominal alpha treats OTHER_UNCERTAIN as an ordinary category.

## Next task
04_GROUP_SPLIT (also fixes known failing test D1).
