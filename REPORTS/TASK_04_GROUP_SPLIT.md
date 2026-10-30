# Task Report

## Task
04_GROUP_SPLIT

## Objective
Document/source-grouped train/validation/test splitting, leakage report, frozen split manifest.

## Files changed
ML/group_split.py (rewritten, `split()` signature preserved), ML/train_baselines.py (import works as module or script; resolves D4), TESTS/test_group_split.py (+5 tests), PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q` -> 40 passed, 0 failed. Defect D1 (grouped split failing on small inputs) is fixed.

## Results
- Whole groups go to exactly one split; deterministic per seed; every split gets at least one group; clear errors for <3 groups, bad ratios, null group values.
- `leakage_report`: group overlap, duplicate (span text + context) overlap across splits, source overlap (informational), per-split label distribution, warnings for missing labels and splits under 30 rows.
- `freeze` writes `DATA/split_manifest.json` (seed, ratios, group and span_id lists, dataset SHA-256, leakage report), refuses to overwrite, and refuses to write if leakage is found. `load_frozen` returns the exact frozen splits and fails if the dataset changed.
- A planted leak and a planted duplicate are both detected in tests.

## Limitations
Splitting balances rows, not labels: with few documents a split can miss a class, which the report flags rather than hides. No manifest has been frozen for real data because none exists (HG-01); tests use synthetic fixtures only. Source-level (domain-held-out) splitting is available via `--group source_id` but is a protocol choice for the researcher.

## Next task
05_BASELINES (majority, logistic regression, SVM with real predictions and confusion matrices; runs on fixtures only until gold data exists).
