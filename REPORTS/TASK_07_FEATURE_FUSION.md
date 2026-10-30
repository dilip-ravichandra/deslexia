# Task Report — 07 Feature Fusion
## Objective
Fuse linguistic features with the transformer and ablate against a matched transformer-only control.
## Files
ML/features.py (10 text-only span/sentence features), ML/context.py (new), ML/fusion.py (new), ML/distilbert_trainer.py (`arch`: hf_head | fusion_off | fusion_on), ML/ablation.py (new), TESTS/test_fusion.py.
## Design
- FusionClassifier: CLS vector + projected, train-standardised features -> dropout -> linear. `fusion_off` uses the same head without the feature branch, so the ablation changes one thing. (The Task 06 `hf_head` arch is not a matched control because its head has an extra layer.)
- Features contain no visual/presentation settings (tested).
- Ablation runs both arms over a seed list, reports mean/std and paired differences, and labels itself descriptive; fewer than 5 seeds adds a warning; no significance test is performed.
- Saved fusion models reload from config + weights without any download (tested), including the training max length (a bug found by a backend test: inference had used a hard-coded length).
## Tests
6 new tests; full suite 101 passed.
## Results
None. Only synthetic fixtures were run; no ablation conclusion exists.
## Limitations
Features are simple counts; unknown whether they help. Real ablation needs gold data (HG-01) and pretrained weights; at least 5 seeds recommended.
## Next
Run `python -m ML.ablation --csv gold.csv --manifest DATA/split_manifest.json` on Colab once data and weights exist.
