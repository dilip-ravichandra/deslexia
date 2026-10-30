# Continue DyslexiAdapt

The code foundation is substantial. No real gold dataset, trained research model
or participant finding is bundled. This continuation adds annotation commands,
offline adaptation evaluation and verified classification table export, and
repairs research-data validation, context boundaries and artifact handling.

## 1. Prepare human annotation

Confirm the source licensing choice described in `DATA/LICENSE_ANALYSIS.md`.
Prepare `DATA/span_pool.csv` from approved educational sources. It must contain
`source_id,document_id,span_id,text,context_before,context_after,source_license`.
Use globally unique span IDs. Here `text` is the selected span; context preserves
the surrounding words. Record source URLs/attribution as extra columns.
`ML.source_pool` produces whole passages, not selected spans: do not feed its
output directly into the span annotation workflow.

    python -m ML.annotation batches --pool DATA/span_pool.csv --annotators ann1 ann2 --out DATA/annotations/batches_v1

Share the blank files and `DATA/annotation_guidelines_v1.md` with the actual
annotators yourself. No files are sent automatically. Each person fills their
own category, integer confidence (1-5) and rationale independently.

    python -m ML.annotation resolve --pool DATA/span_pool.csv --annotations DATA/annotations/returned_ann1.csv DATA/annotations/returned_ann2.csv --guideline guideline_v1 --out ARTIFACTS/annotation/v1

Outputs: long-format annotations, agreement before adjudication, resolved gold
rows, unresolved queue and a hashed manifest. Unreturned spans remain queued.
The resolved subset is not a finished dataset while any queue remains.
Load the queue in `/adjudication.html`, have a human adjudicator decide, export
their file, then run `resolve` again with `--adjudications <file>` and a NEW
output directory. Review licences, agreement and label distribution before
freezing. These structural checks cannot prove who supplied the labels.

## 2. Real training, after reviewed gold data exists

    python -m ML.data_validation --csv ARTIFACTS/annotation/v2/gold_resolved.csv --mode research
    python -m ML.experiment_runner --config EXPERIMENTS/config.yaml --csv ARTIFACTS/annotation/v2/gold_resolved.csv

Use a machine/Colab with pretrained-weight access. Synthetic fixtures and tiny
random-init training only test code; they do not establish model performance.
Recorded experiments cannot be overwritten with `--force`. Use a new output
root/version for any intentional new run. Tampered artifacts are not reused.

## 3. Adaptation evaluation (Task 15 tooling)

Read `RESEARCH/EVALUATION_WORKFLOW.md`. Supply actual paired outputs:

    python -m ML.evaluation --comparisons DATA/comparisons_v1.jsonl --out ARTIFACTS/evaluation/v1

This measures source-token changes, added/deleted tokens, sentence changes,
edit budget and verification flags. Missing semantic/readability models remain
unavailable. Evaluation outputs are descriptive and unvalidated; they do not
claim comprehension improvement. Participant collection requires HG-02.

## 4. Paper table generation (Task 16 tooling)

After a complete, verified real experiment exists:

    python -m ML.paper_tables --experiment ARTIFACTS/experiments/<experiment_id> --out PAPER/generated/v1

Exports held-out classification tables and provenance. Rejects incomplete,
tampered, smoke or fixture experiments by default; rechecks displayed metrics
against confusion counts. Does not write inside a frozen experiment, overwrite
tables, invent results, or write a conclusion. `--allow-fixture` is TEST ONLY.

## Verification

    pip install -r BACKEND/requirements.txt
    pip install pytest matplotlib pyyaml
    cd TESTS/ui
    npm ci
    cd ../..
    python -m pytest -q
    python -m QA.audit

UI checks use jsdom; real-browser, phone and screen-reader QA are still needed.
See `REPORTS/CONTINUATION_AUDIT.md` and `REPORTS/QA_AUDIT.md` for the latest run.
