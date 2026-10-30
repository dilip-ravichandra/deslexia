# Implementation Gap List (Task 00)

## Defects found in existing code (reproduced)
| ID | Defect | Evidence | Planned fix |
|---|---|---|---|
| D1 | `test_group_split` fails | 10 rows / 5 docs: first split leaves 2 docs, second GroupShuffleSplit gets train_size=0.4999 -> empty train set ValueError | Task 04: deterministic group-level assignment with minimum-group checks and clear error |
| D2 | Seed CSV malformed | Unquoted comma gave 12 fields on row 3 | FIXED in audit (quoted field; content unchanged) |
| D3 | Seed validation fails | span_id "s1" duplicated across 3 documents; validator requires global uniqueness | Task 01: decide span_id policy (global unique) and update seeds |
| D4 | train_baselines not importable as module | `from group_split import split` | Task 05: package imports, add ML/__init__.py |
| D5 | Validator misses guards | No check of empty text, label whitespace/case, license, guideline_version, confidence range, annotator_id | Task 01 |

## Missing capabilities (by task)
01 schema/provenance/versioning; 02 annotation import/export, double-annotation, adjudication; 03 Cohen/Fleiss/Krippendorff + conflicts; 04 split manifest + leakage report; 05 majority baseline, predictions, confusion matrices, metadata; 06 real Trainer; 07 fusion model + ablation; 08 error analysis; 09 real interventions with change tracking; 10 embedding/NLI/entity verification with thresholds; 11 backend integration + safeguards + feedback; 12 learner UI; 13 Research Lab reading real artifacts; 14 experiment runner with hashes; 15 targeted-vs-uniform metrics + human eval workflow; 16 generated paper tables; 17 QA; 18 model/dataset cards.

## Environment
| Item | Status |
|---|---|
| Python 3.12.3, pandas, scikit-learn, scipy, matplotlib, joblib | present |
| pytest, fastapi, httpx, pydantic | installed during audit |
| torch | downloadable from PyPI (wheel ~555 MB), not yet installed |
| transformers, sentence-transformers, spacy, textstat | not installed; PyPI available |
| Hugging Face Hub (huggingface.co) | BLOCKED: HTTP 403 from sandbox egress. Pretrained weights (distilbert-base-uncased, NLI and embedding models) cannot be downloaded here. |
| GPU | none observed |

## Blockers and gates
- HG-01: no human-annotated gold data exists. Tasks 05-08, 14-16 cannot produce research results until it does.
- HG-03: source texts and licenses not yet chosen.
- HG-02: needed before any participant evaluation (Task 15).
- Resource: pretrained model weights unreachable; DistilBERT, NLI and embedding verification need either network access to huggingface.co or user-supplied local weights.

## Safe work order
Independent of gates: 01, 02, 03 (tooling, tested on synthetic fixtures clearly labelled as test data), 04, 09 (rule-based, labelled heuristic), 10 (entity/number parts; model parts pending weights), 11, 12, 13, 14 (runner code). Result-producing steps wait on HG-01.
