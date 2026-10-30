# DyslexiAdapt — Architecture Map (Task 00 audit)

Pipeline per CLAUDE.md: span selection -> context builder -> support classifier -> intervention -> semantic verification -> comparison -> accept/reject -> logging -> artifacts.

| Stage | Module | State (verified by inspection/tests) |
|---|---|---|
| Data schema/validation | DATA/schema.json, ML/data_validation.py | Partial. No provenance/license/version checks; schema.json is informal, not enforced. |
| Seed data | DATA/seed_examples.csv | 3 smoke rows (annotator "seed"), NOT gold. Quoting bug fixed in audit; span_id collisions remain. |
| Annotation + agreement | none | Missing (Tasks 02, 03). Gated by HG-01 for real labels. |
| Grouped split | ML/group_split.py | Works for large inputs; fails on small group counts; no manifest, no leakage report, no label-aware handling. |
| Baselines | ML/train_baselines.py | Logistic regression + LinearSVC only. No majority baseline, no validation use, no per-sample predictions, no confusion matrix, no metadata/hashes. Imports `from group_split` so it only runs as a script from ML/. |
| DistilBERT | ML/train_distilbert.py | Skeleton only: guard + writes metadata; no training. |
| Feature fusion | ML/features.py, ML/feature_fusion.md | 7 hand-crafted features; no fusion model. |
| Interventions | ML/interventions.py | Stub: returns text unchanged, status IMPLEMENT_REAL_INTERVENTION. |
| Semantic verification | ML/semantic_verifier.py | Lexical SequenceMatcher + number check only. Entity/NLI/embedding = None. Lexical ratio must not be reported as semantic similarity. |
| Backend | BACKEND/app.py | 3 endpoints, all NOT_CONNECTED/demo. No feedback, experiment metadata, or logging. |
| Learner UI | FRONTEND/index.html | Static prototype: 4 colour presets, text size, line spacing. No span selection, no API call (button is an alert), no letter spacing/font/focus mode, no comparison/accept/reject. |
| Research Lab | none | Missing (Task 13). |
| Experiment runner | EXPERIMENTS/config.yaml | Config only. No runner. |
| Paper | PAPER/*.md | Structure + template with NOT_AVAILABLE cells. Correct. |
| Tests | TESTS/ | 2 original + 6 audit guards. |

## Governance consistency
CLAUDE.md, HUMAN_GATES.md, DECISIONS.md (ADR-001..008), ethics.md, dataset_card.md agree: no diagnosis, no fabricated results, human gold labels only. Preserve as-is.
