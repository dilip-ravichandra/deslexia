# Task Report

## Task
06_DISTILBERT (plus licence review requested for ADR-009)

## Objective
Real DistilBERT training pipeline for VOCABULARY / SYNTACTIC / CONCEPTUAL with grouped split, validation-only selection, reproducibility and saved artifacts; honest handling of unavailable weights.

## Files changed
ML/distilbert_trainer.py (new), ML/train_distilbert.py (CLI, replaces skeleton), TESTS/test_distilbert.py (new), DATA/LICENSE_ANALYSIS.md (new), RUN_COLAB.md (new), DECISIONS.md, BLOCKED.md, PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q` -> 54 passed. Environment: torch 2.14.1 (CPU use), transformers 5.19.0, no GPU.

## What the pipeline does
- Research mode requires research-valid human data (provenance, human annotator ids, licences) AND a frozen split manifest AND pretrained weights loaded. Otherwise it refuses.
- Plain PyTorch loop (AdamW, linear warmup/decay, class-weighted loss from TRAIN counts only, gradient clipping, early stopping on validation macro-F1). The test split is scored once, after the best-validation checkpoint is restored.
- Saves: model + tokenizer + config, per-epoch training_log.jsonl, results.json (accuracy, macro-F1, per-class P/R/F1, confusion matrix for validation and test), predictions.csv with class probabilities, metadata.json (seed, hyperparameters, dataset and manifest SHA-256, library versions, platform, device, command).
- Seeds set for python, numpy and torch; same seed reproduced identical predictions in tests.
- Label checks: empty splits and a missing train class are errors; classes with <10 train examples produce warnings.
- Weight download failure is a hard error: writes DOWNLOAD_FAILED.json with the error and practical alternatives and trains nothing. It never falls back to random weights.
- Smoke mode uses a tiny locally initialised DistilBERT and a locally trained tokenizer; outputs carry `smoke: true`, `weights: random_init_tiny_local`, `valid_for_scientific_claims: false`.
- Tests also show that permuting the labels of the test documents changes neither the selected epoch nor validation metrics nor test predictions (selection cannot see test labels).

## Results
None scientific. No pretrained DistilBERT run has completed, and no human-labelled dataset exists. Smoke-test scores are not reported or meaningful.

## Licence review (ADR-009 stays PENDING)
See DATA/LICENSE_ANALYSIS.md. Summary: provenance of the Hub copy is documented by the uploader (Wikimedia dump with SHA-1) but not independently verified; the governing CC BY-SA version is unconfirmed; source text, excerpts, annotations, metadata and model artefacts carry different obligations; five alternatives compared; recommendation is provisional and the owner must answer three questions.

## Limitations
- Not run on real weights or real data. Windows/Colab commands are documented but only the Linux sandbox was tested.
- Hyperparameters are defaults; no search was done. With few annotated documents, validation-based epoch selection is noisy.
- The research gate is structural; it cannot prove annotators are human (HG-01).
- Licence analysis is not legal advice.

## Next task
07_FEATURE_FUSION and other tasks not blocked by the licence decision or gold labels (09 interventions, 10 semantic verification, 11-13).
