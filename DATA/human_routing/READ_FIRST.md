# 100 public-source examples ready for human review

These are real published English CompLex contexts and Hindi/Kannada/Tamil IndicQA contexts. Their routing labels are BLANK. The original public task and its annotation are kept in separate columns. A public complexity rating or QA answer is not a vocabulary/syntax/concept label.

Use `/human-review.html` for independent collection, then merge JSON exports in `/learner-lab.html`. See `HUMAN_REVIEW_GUIDE.md`. Two reviewers should work independently. Read the selected text together with its context. Propose the most appropriate type of support: VOCABULARY (word meaning), SYNTACTIC (sentence relationships), CONCEPTUAL (idea/background) or OTHER_UNCERTAIN (unclear or genuinely multiple). This is a support-routing judgment, not a diagnosis or proof that a particular student has this difficulty. If the reader's intended difficulty is unknown, say so in rationale and preserve uncertainty.

Fill category, your annotator_id, confidence (integer 1 to 5), rationale, created_at (ISO date/time), and annotation_type = HUMAN_REVIEWED only after you personally review the row. Keep the provenance/source columns unchanged. Do not turn model-generated annotations into human annotations merely by renaming the reviewer.

Retain both independent files. Preserve disagreements in the review archive; agreement/adjudication must be recorded separately. Unresolved examples remain OTHER_UNCERTAIN and are excluded only from the three-class supervised fit, not discarded from the research record.

These 100 rows are a focused annotation starter, not a sufficient or balanced final routing benchmark. Selecting QA answers as spans can bias support type and cannot replace sampling authentic learner-selected difficulties. Group train/validation/test by original document, including all language variants/related passages when applicable. Do not reuse a held-out test set as new training data without versioning the benchmark.
