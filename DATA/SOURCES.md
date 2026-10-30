# Candidate free sources (checked via the Hugging Face connector, 2026-10-09)

Nothing here is downloaded into the repo. The Claude sandbox cannot resolve huggingface.co; the
connector returns metadata and short previews only. Licence tags on Hub re-uploads are
uploader-declared and must be checked against the original source before release (HG-03).

## Text corpus (unlabelled source passages)
| Dataset | Licence tag | Notes |
|---|---|---|
| juno-labs/simple_wikipedia | CC-BY-SA-3.0 | 276K English Simple Wikipedia pages, dump 2026-03-01. Recommended for the pool. Caveat: text is already simplified, so many spans will be easy; the study may need harder source text. |
| cahya/simple-wikipedia | CC-BY-SA-3.0 | Single `text` column, no page ids -> weaker provenance. Not preferred. |

**ShareAlike consequence (needs your decision):** CC BY-SA 3.0 requires attribution and that adapted
material (including an annotated dataset built from these passages) be released under the same or a
compatible licence. That is fine for an open academic dataset, not for a closed one.

## Not used
- H-Huang/complex_word_identification (CC-BY-4.0 tag): Dataset Viewer fails to load it, provenance unverified, and its labels are word-level complexity, not our support categories.
- hasankursun/age-specific-text-simplification (Apache-2.0 tag): provenance of the simplifications is unclear and was not inspected. Do not use as gold.
- WikiLarge re-uploads: licence tags inconsistent across uploaders; unverified.

## Models (free, Apache-2.0 per Hub metadata)
| Use | Repo |
|---|---|
| Classifier backbone (Task 06) | distilbert/distilbert-base-uncased |
| Embedding similarity (Task 10) | sentence-transformers/all-MiniLM-L6-v2 |
| NLI verification (Task 10) | cross-encoder/nli-deberta-v3-small |

## What no free dataset gives us
None of these contain VOCABULARY / SYNTACTIC / CONCEPTUAL support labels. Those must come from
human annotators (HG-01). Models or LLMs must not label them.

## Build the pool (on your machine)
    pip install datasets
    python -m ML.source_pool --n-articles 200 --out DATA/source_pool.csv
