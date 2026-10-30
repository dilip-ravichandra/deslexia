# Task Report — 08 Error Analysis
## Files
ML/error_analysis.py, TESTS/test_error_analysis.py (10 tests); backend/Lab sections for error analysis.
## What it does
From a real predictions file (and optionally the dataset CSV) it computes, per model and split: accuracy, macro-F1, per-class precision/recall/F1/support (absent classes are `n/a`, never 1.0), labelled confusion counts and row-normalised rates, ranked confusions, true vs predicted distribution, a document-clustered bootstrap 95% CI for macro-F1 (span-level fallback is labelled), confidence/calibration (histograms for correct vs incorrect, reliability table, ECE) when probabilities exist, slice tables (span length, source) flagged unreliable below n=20, and representative errors per confusion pair and per class (false positives / false negatives). Example selection is deterministic and stated (most confident errors first; span_id order without probabilities).
Outputs are stamped with the producing run's data_status; non-research analyses carry a NOT RESEARCH banner. A test-set caveat warns that tuning on test errors contaminates the test set.
## Verification
Metrics match scikit-learn on random data; seeded bootstrap is reproducible; clustered intervals are wider than naive ones under within-document correlation (a first test premise was wrong and was replaced); wrong labels/columns are rejected.
## Results
None. Only synthetic fixtures were analysed.
## Limitations
Bootstrap with few documents is unreliable (warned). Calibration needs probabilities and enough data. ECE is descriptive; softmax outputs are not calibrated.
