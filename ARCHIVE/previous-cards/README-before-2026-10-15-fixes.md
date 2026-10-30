# DyslexiAdapt multilingual research build

Start with [RUN_RESEARCH.md](RUN_RESEARCH.md). Current implementation status and limitations are in [CURRENT_RESEARCH_STATUS.md](CURRENT_RESEARCH_STATUS.md).

English, Hindi, Kannada and Tamil document extraction, supplementary support and speech; consented survey and session evidence; live learner evidence lab; public human lexical comparison; original three-category comparison tooling requiring genuinely human-reviewed routing labels.

Earlier prototype documentation below is historical and does not describe the current active routing model. GPT pilot annotations and old prototype artifacts are archived, never presented as human gold.

# Latest build: document uploads, OCR, visual help and connected lab

Start with **RUN_DOCUMENTS.md** and **START_WINDOWS.bat**. The document release supersedes older setup/status descriptions below. It includes actual PDF/OCR extraction and Qwen multimodal inference, with recorded prototype evidence in the lab. Human dyslexia evaluation is still pending.

# Real-model continuation

Start with **RUN_NEURAL.md** and **START_WINDOWS.bat**. This build uses a validation-gated pretrained-feature classifier, native local Qwen generation and pretrained NLI. First launch downloads 1.54 GB of pinned public weights automatically. No manual model API configuration is needed.

# DyslexiAdapt

A research prototype of a learner-guided reading aid: select a hard word or sentence, get targeted support, check that meaning markers survived, accept or reject. It does **not** diagnose dyslexia. **A trained GPT-weak-label prototype is now bundled. No gold dataset or validated research result exists.** Start with `RUN_ADAPTIVE.md`.

## Quick start
    pip install -r BACKEND/requirements.txt
    python -m uvicorn BACKEND.app:app --port 8000      # learner app at /, Research Lab at /research.html
    python -m pytest -q                                # full suite

## Where things are
| Folder / file | What |
|---|---|
| `ML/` | data validation, annotation, agreement, grouped split, baselines, DistilBERT, fusion, ablation, interventions, verifier, error analysis, experiment runner, cards |
| `BACKEND/`, `FRONTEND/` | API and pages (learner app, Research Lab, adjudication tool) |
| `QA/audit.py` | automated QA audit; report in `REPORTS/QA_AUDIT.md` |
| `REPORTS/STATUS_AND_NEXT_STEPS.md`, `BLOCKED.md`, `PROJECT_STATE.json` | current state, blockers, task status |
| `MODEL_CARD.md`, `DATASET_CARD.md` | generated from artifacts: `python -m ML.cards` |
| `DEFENSE_GUIDE.md`, `LIMITATIONS.md` | what to say and not claim |
| `RUN_PRODUCT.md`, `RUN_COLAB.md` | run guides (product; training on Windows/Colab) |
| `DATA/LICENSE_ANALYSIS.md`, `DECISIONS.md` | licence analysis, ADR-009 (PENDING) |

## Real experiments (after human annotation and licence decision)
    python -m ML.experiment_runner --config EXPERIMENTS/config.yaml --csv DATA/gold.csv
Every run writes a manifest with dataset, code and output hashes; `verify_experiment` re-checks them.

## Latest continuation
Read `CONTINUE_HERE.md` for annotation commands, offline adaptation evaluation
and verified paper-table export. See `REPORTS/CONTINUATION_AUDIT.md` for the
in-depth review and fixes. Real human data and research findings remain pending.

## Adaptive prototype continuation
See `RUN_ADAPTIVE.md` for persistent learner profiles, contextual explanations, feedback review, evaluated retraining, activation and rollback. Open `/learning.html` for prototype operations. The existing research registry still rejects weak-label artifacts.
