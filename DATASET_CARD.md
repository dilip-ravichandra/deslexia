# Dataset Card — DyslexiAdapt span-support annotations

> **RELEASE STATUS: PENDING — DO NOT REDISTRIBUTE.** The source-text licence decision (ADR-009) is unconfirmed. Do not publish or share any passage pool, annotated file or derived text until the source licence and release conditions are verified (see `DATA/LICENSE_ANALYSIS.md`).

## Dataset status
**NO GOLD DATASET EXISTS.** No human annotations have been collected (HG-01). `DATA/seed_examples.csv` holds three smoke-test rows (annotator `seed`) that are rejected by research-mode validation.

## Intended use
Research on computational support-category routing for selected educational text spans.

## Not intended for
- dyslexia diagnosis
- medical decision making
- inferring learner health status
- clinical efficacy claims

## Labels
| Label | Meaning (guidelines v1) |
|---|---|
| VOCABULARY | a word or short phrase is the barrier |
| SYNTACTIC | sentence structure is the barrier |
| CONCEPTUAL | the idea itself needs support |
| OTHER_UNCERTAIN | not trainable; routed to adjudication, excluded from training |

Full definitions: `DATA/annotation_guidelines_v1.md`.

## Schema
Required columns: source_id, document_id, span_id, text, context_before, context_after, category. Research mode also requires: annotator_id, guideline_version, confidence, rationale, source_license, created_at. Validation: `python -m ML.data_validation --csv <file> --mode research`.

## Annotation process
Double annotation by distinct human annotators (AI/seed ids are rejected). Gold = unanimous human label or a named human adjudicator's decision; disagreements are never auto-resolved. Use `human-review.html` and `HUMAN_REVIEW_GUIDE.md`; the lab preserves raw exports and unresolved decisions.

## Required reporting — current status
| Item | Status |
|---|---|
| Source provenance and licences | PENDING (ADR-009) |
| Annotator count | NOT AVAILABLE |
| Guideline version | v1 (`DATA/annotation_guidelines_v1.md`) |
| Agreement | NOT AVAILABLE (no annotations) |
| Adjudication | NOT AVAILABLE |
| Class distribution | NOT AVAILABLE |
| Document-level split | NOT AVAILABLE |

## Candidate source and its consequences
Candidate: Simple English Wikipedia text (CC BY-SA, version unconfirmed) — attribution and ShareAlike apply to text and likely to files that combine text with labels. Source text, excerpts, annotations, metadata and model artefacts carry different obligations; see `DATA/LICENSE_ANALYSIS.md`. This is an engineering summary, not legal advice.

## Known biases and limits
Simple Wikipedia is already simplified, so hard spans may be under-represented. Annotator count and background will bound label validity. Label categories are an operational scheme, not a theory of reading difficulty.
