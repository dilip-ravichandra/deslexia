# Local software repair update — 15 October 2026

The audit in REPORTS/local-audit-2026-10-15 describes the pre-repair folder. The current code adds occurrence-aware support, explicit UTF-16 browser offsets, UTF-8 data loading, deduplicated routing evidence, consent-checked visual persistence and quality metadata that cannot restore deleted profiles. It also provides structured source-claim generation with screening/retry/withholding, and independent review/export/merge. These are software safeguards, not a guarantee of multilingual semantic correctness.

Use HUMAN_REVIEW_GUIDE.md for independent collection. No real human judgments or student outcomes were manufactured during implementation. The supplied routing pool remains blank, the main trained routing comparison remains pending, and the recorded CompLex results are unchanged.

Large model weights and some dependencies are absent on the audited Windows computer. Readiness is reported per service. The earlier Hindi error is now covered by authored finite-screen regression fixtures; a fresh live four-language model evaluation is still pending. Historical generation statements below are preserved as historical evidence and must not be read as current verification.

# Current implementation and evidence

## Implemented

- English, Hindi, Kannada and Tamil controls, native-script extraction, selected-span support, language-specific speech and explanation requests. Script estimation is user-correctable; Devanagari alone cannot distinguish Hindi from every other language.
- Consented initial survey, learner-specific online need/style parameters, presentation preferences, session history, recency and selected-word/text-shape relevance. Manual requests override suggestions. A single reported starting need can guide the first suggestion; repeated relevant observations can revise it.
- Dwell, rereading and returning to a tab are recorded without automatically assigning a difficulty label. Repeated requests for the same span/category in a session are counted once; retried event IDs are idempotent.
- Live private admin view with actual profiles/events, before/after need/style parameters, presentation changes and saved decision rationale. Profile deletion removes the new learner model and legacy stored feedback. No fake student records are included.
- Pinned public data, licenses, revisions and file hashes; explicit source roles. CompLex, ASSET, OneStopEnglish, CWID-hi and IndicQA remain separate tasks.
- Original TF-IDF → multilingual DistilBERT → multilingual DistilBERT plus fixed text-feature routing comparison, using identical frozen document splits. Import preserves unresolved rows. Completed genuine runs can be activated only after declared validation gates. No completed human routing run currently exists.
- Supplementary CompLex lexical-regression experiment using published human ratings and frozen partitions. This is NOT the main three-category routing task.
- 100 public-source spans with BLANK routing labels for a focused independent human-review starter. Published QA/complexity annotations are preserved separately. They are not silently mapped into support categories.
- OCR text is editable before reading. PDF/photo upload, region selection and optional local visual explanation remain available. Text and vision caches are mutually exclusive to reduce memory pressure.

## Observed software evidence

Backend/data invariants: 50 checks passed at the recorded check point. Browser flow: consented survey, Hindi upload/OCR, reader, actual pronunciation route, lab rendering, deletion and mobile width; no JavaScript exceptions. Four authored sentence images produced text in the requested scripts with Tesseract tessdata_best. All four pinned MMS voices produced nonempty 16-kHz WAV output in engineering tests. These results are not student outcomes or native pronunciation-quality ratings.

Public IndicQA source audit records answer-text/offset issues without altering raw files. The offset audit uses Python Unicode-codepoint indexing; the publisher's offset convention is unverified, so mismatches do not necessarily mean incorrect answers. Annotation-starter selection uses matching answer text and distinct passages.

## Still required for research claims

- Genuine four-language human-reviewed routing gold data and independent agreement analysis. Existing GPT review files remain AI pilot data even if they resemble human responses.
- Strong language-competent checks of explanations, visual understanding, OCR and speech across subjects and languages. A script guard cannot establish correctness.
- The four-condition dyslexia learner study and personalization ablations in RESEARCH/PROTOCOL_CURRENT.md. The implementation cannot establish comprehension improvement by itself.
- Formal calibration of learner evidence weights, routing thresholds and native semantic-preservation checks. Current engineering gates are not educational-effectiveness thresholds.

Large pretrained weights are downloaded by revision/hash, not embedded in the ZIP. The public source data and small trained experiment artifacts are included. Speech uses CC BY-NC 4.0 and the optional vision model uses the original Qwen research license; unrestricted commercial rights are not claimed.

Read RUN_RESEARCH.md to launch. Read REPORTS/current-build for inspectable software/source checks, and ARTIFACTS/human_lexical for actual training logs and results. Incomplete/interrupted runs are explicitly marked and must not be reported as completed comparisons.

Rendering QA caught missing Indic glyph coverage. The reader now bundles the original OFL-licensed Noto fonts locally; Hindi text has been visually rechecked. Normal native-script letter spacing preserves shaping. Optional helpfulness controls are collapsed; routine reading does not require feedback. Different-style requests remain observable actions.

## Completed public lexical run

Run e8c83d66789541ff965aa5344daf6e01 completed on 512 training / 308 validation / 887 test rows. Validation MAE: TF-IDF 0.1113, DistilBERT 0.1044, DistilBERT + features 0.1076. Test MAE: 0.0984, 0.1032, 0.1053 respectively. Selection used validation only; neither neural arm improved the held-out test result over TF-IDF. This is not routing F1 or evidence of dyslexia benefit.

Final native-generation checks were interrupted when the transient runtime ended. An inspected Hindi output introduced an unsupported high-temperature condition; the prompt was tightened, but the follow-up quality check is not confirmed complete. Kannada/Tamil broad explanation correctness is not signed off. Four-language OCR/speech software paths exist; a requested script alone does not establish a correct explanation. Do not present this package as fully validated multilingual teaching.
