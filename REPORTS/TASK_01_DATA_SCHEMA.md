# Task Report

## Task
01_DATA_SCHEMA

## Objective
Dataset schema, validation, provenance fields, label definitions, versioning, data-quality checks.

## Files changed
ML/data_validation.py (rewritten, backward-compatible `validate()`), DATA/schema.json (now describes enforced rules), DATA/seed_examples.csv (unique span_ids), ML/__init__.py, BACKEND/__init__.py, TESTS/test_data_validation.py, PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q` -> 20 passed, 1 failed (known D1, assigned to Task 04).

## Results
- `smoke` mode validates seed fixtures; `research` mode rejects them (seed/AI annotators, unknown or synthetic licenses, missing provenance, bad confidence/timestamps, non-exact labels).
- `dataset_manifest()` records file SHA-256, validation result, label distribution, document/source counts for versioning.
- D3 and D5 from the gap list resolved.

## Limitations
Schema checks cannot establish that labels are correct or that a licence is genuine; that remains HG-01/HG-03. Dataset versioning is by content hash; a named version registry will be added with the experiment runner (Task 14).

## Next task
02_ANNOTATION_SYSTEM (tooling only; real labels remain HG-01).
