# Task Report

## Task
02_ANNOTATION_SYSTEM

## Objective
Annotation import/export, double annotation support, adjudication queue/UI.

## Files changed
ML/annotation.py (new), FRONTEND/adjudication.html (new), TESTS/test_annotation.py (new), PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q TESTS/test_annotation.py` -> 6 passed. Full suite: see PROJECT_STATE.json (only known D1 failure). The adjudication page's CSV parser was checked with node on quoted commas and escaped quotes; the page itself was not browser-tested.

## Results
- `make_batches`: each span goes to `copies` distinct annotators (default 2), balanced load, seeded, label-free output files; AI/seed annotator ids rejected.
- `import_annotations`: one human annotator per file, labels/confidence/span_ids validated, unfinished files rejected.
- `resolve`: gold only from unanimous human labels or a named human adjudicator; disagreements, OTHER_UNCERTAIN and under-annotated spans go to the queue. No majority vote, no model labels.
- `adjudication_sheet` + `FRONTEND/adjudication.html`: offline browser tool that shows span in context and exports adjudications.

## Limitations
All tests use synthetic fixtures labelled as such; no real annotations exist (HG-01). The UI needs a manual browser pass with a real sheet. Three-or-more-annotator policies beyond "unanimous or adjudicate" are a scientific choice left to the protocol.

## Next task
03_AGREEMENT (Cohen's kappa, Krippendorff's alpha, per-class agreement, conflict report).
