# Task Report

## Task
05_BASELINES

## Objective
Majority, TF-IDF Logistic Regression and Linear SVM; save metrics, predictions, confusion matrices and model metadata.

## Files changed
ML/baselines.py (new), ML/train_baselines.py (now a thin CLI), TESTS/test_baselines.py (new), PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q` -> 46 passed, 0 failed.

## Results (implementation only; no scientific results)
- Models: majority-class, TF-IDF(1-2gram)+LogReg, TF-IDF+LinearSVC, class-balanced. C is chosen on the validation split by macro-F1; the test split is scored once afterwards (the selection function has no test argument).
- Outputs per run: results.json (accuracy, macro-F1, per-class P/R/F1, labelled confusion matrix for validation and test), predictions.csv (model, split, span_id, true, pred), joblib models, metadata.json (seed, dataset SHA-256, split manifest hash, library versions, command, C grid).
- Guard: a run is `research` only if the CSV passes research-mode validation AND a frozen split manifest is supplied. Otherwise it is refused unless `--allow-fixture`, which stamps outputs `fixture_not_research`. Running on the repo seed file is refused.
- Run: `python -m ML.train_baselines --csv <gold.csv> --manifest DATA/split_manifest.json`.
- Non-primary labels (OTHER_UNCERTAIN) are excluded from training/eval and the count is recorded.

## Limitations
- No real data, so NO baseline performance numbers exist for this project. The fixture is synthetic with label-revealing marker words; its scores prove nothing.
- The research gate is structural. It cannot tell genuinely human-annotated data from a synthetic file given plausible annotator ids (one test does exactly this to exercise the code path); provenance integrity still depends on HG-01/HG-03 and the manifest/hash trail.
- Only C is tuned; no feature ablations or cross-validation yet. With few documents, validation-based selection is noisy.

## Next task
06_DISTILBERT. Code can be written and unit-tested, but weights cannot be downloaded here (huggingface.co is blocked), and real training needs HG-01 data.
