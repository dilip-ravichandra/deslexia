# Task Report — 14 Experiment Runner
## Files
ML/experiment_runner.py, EXPERIMENTS/config.yaml (extended), TESTS/test_experiment_runner.py (7 tests); Research Lab/back-end sections for experiments.
## What it does
`python -m ML.experiment_runner --config EXPERIMENTS/config.yaml --csv <data>` validates the config, validates the data, freezes the split, runs baselines, DistilBERT per seed, the fusion ablation, error analysis and figures (confusion matrices, per-class F1, confidence histograms, training curves), then writes `run_manifest.json`.
- experiment_id = hash(config, dataset sha256, code sha256, mode); identical completed experiments are reused; `verify_experiment` recomputes output hashes and detects tampering.
- Non-research data needs `--allow-fixture`/`--smoke` and everything is stamped non-research.
- Each step records ok / failed / unavailable with the reason. Missing pretrained weights give `unavailable` and a `partial` experiment; a failed split stops dependent steps and the failure is recorded.
- `valid_for_scientific_claims` is true only if research-valid data, frozen split and every required step (real weights included) completed. `--plan` shows steps without running.
## Verification
Smoke experiment end to end (all steps ok, stamped non-research, hashes verify), idempotent re-run, tamper detection, id sensitivity to config/data/code/mode, unavailable-weights path, failed-step path.
## Results
None. No research-valid experiment has been run.
## Limitations
Windows/Colab not exercised. Hashing large model files is slow. Figures are for inspection; they are watermarked when non-research.
