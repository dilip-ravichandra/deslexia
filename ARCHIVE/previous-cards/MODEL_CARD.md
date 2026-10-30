# Model Card — DyslexiAdapt

> Status legend used across this project: **IMPLEMENTED** (code exists and is tested), **DEMO** (rule of thumb or placeholder resource), **SMOKE-TESTED** (pipeline runs on synthetic/tiny data), **VALIDATED** (supported by research-grade artifacts). Nothing below is VALIDATED unless a research-grade result is listed in the Evaluation section.

## Components
| Component | Status | Notes |
|---|---|---|
| TF-IDF + Logistic Regression / Linear SVM, majority baseline | IMPLEMENTED, SMOKE-TESTED | `ML/baselines.py` |
| DistilBERT span-support classifier | IMPLEMENTED, SMOKE-TESTED (tiny random-init model) | `ML/distilbert_trainer.py`; needs real pretrained weights |
| DistilBERT + linguistic-feature fusion and matched ablation | IMPLEMENTED, SMOKE-TESTED | `ML/fusion.py`, `ML/ablation.py` |
| Support-type suggestion in the app | DEMO | rule of thumb, no probability; replaced only by a registered research-grade model |
| Targeted interventions (word gloss/replace, sentence split/chunk, steps/scaffold) | IMPLEMENTED, DEMO lexicon | rule-based; lexicon (39 entries) unreviewed; conceptual support is scaffolding only |
| Semantic verification (numbers, negation, entities, modality; optional embedding/NLI) | IMPLEMENTED | thresholds uncalibrated; model-based scorers untested on real weights |

## Intended use
Research prototype for studying whether localized, learner-guided support (vs uniform simplification) helps readers while changing less text. A reading aid under the learner's control.

## Out of scope / must not be used for
Diagnosing dyslexia or any condition; inferring health or ability; clinical or educational placement decisions; claims of clinical effectiveness; automatic rewriting without the learner's choice.

## Training data
**NOT AVAILABLE.** No human-annotated gold dataset exists yet (HG-01). Seed examples in `DATA/seed_examples.csv` are three smoke-test rows, not gold data.

## Evaluation
**NO VALIDATED MODEL.** No research-grade result exists. Any score produced by `--smoke` or fixture runs only shows that the pipeline executes and must not be cited.


Smoke/fixture result files present in this checkout (not quoted): 0.

## Ethical considerations
No diagnosis or medical inference. The learner can reject any adaptation. Uncertainty is shown (demo mode is announced; automatic checks never claim to guarantee meaning). Minimal data: logging is off by default and stores no learner text unless explicitly enabled with consent (HG-02). Content licences must be verified before any data release (HG-03).

## Known limitations
See `LIMITATIONS.md`. Key points: no validated model; unreviewed lexicon; uncalibrated verifier; interface tested only with jsdom; no user study.

## How to reproduce
`python -m ML.experiment_runner --config EXPERIMENTS/config.yaml --csv <gold.csv>` (research data) — see `RUN_COLAB.md`. Every run writes a manifest with dataset, code and output hashes.
