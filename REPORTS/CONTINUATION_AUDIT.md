# Progress ZIP audit and continuation

## Verified scope

Inspected the supplied progress ZIP's state, task reports, data schema and
annotation workflow, group splitting, baseline/transformer/fusion training,
experiment runner, error analysis, interventions, semantic checks, FastAPI,
learner/adjudication/research pages, tests, QA and generated cards. The research
idea was read from the two supplied PDFs earlier in this session.

The supplied state called tasks 00-14/17/18 complete. That means implementation
tooling, not scientific completion: the archive contains no gold corpus, actual
agreement, trained research checkpoint, validated semantic thresholds or human
study results. The 39-entry vocabulary lexicon is a demo resource. Conceptual
support is scaffolding, not an actual domain explanation. The app accepts pasted
text; PDF/TXT ingestion proposed in the platform document is still absent.

## Architecture and strengths

- Learner selection and text context feed either a demo rule or a registered
  classifier, then rule-based intervention, verification, comparison and feedback.
- Presentation preferences are excluded from text classification inputs.
- Training uses document/source grouping, validation-only model selection,
  train-only feature scaling and explicit smoke/research labels.
- DistilBERT training is now genuine training code, unlike the first master ZIP.
  Feature fusion has a matched no-feature control.
- Experiment artifacts carry hashes, dataset/code versions and explicit failures.
- The Research Lab reads artifacts and shows empty sections when none exist.
- Research APIs are admin-gated; learner text logging is off by default.

## Defects reproduced and repaired

| Finding | Consequence | Repair |
|---|---|---|
| Blank/null human IDs and fractional confidence passed research validation | Invalid metadata could reach training | Reject blank/disguised non-human IDs, padded unknown licences and noninteger confidence; reject empty datasets |
| Returned fractional confidence was truncated | Annotation confidence changed silently | Require integer confidence before conversion |
| Duplicate votes could be passed directly to resolution | One person's repeated label could look like two votes | Require distinct votes; reject fewer than two annotators |
| Batch IDs could contain path separators; zero copies accepted | Bad filenames or empty assignments | Validate batch IDs/copy count and unique span IDs |
| Context strips collapsed `The catalyst speeds` to `Thecatalystspeeds` in features | Training/inference representations disagreed | Preserve whitespace at selection boundaries |
| First-occurrence replacement ignored selected duplicate word/sentence | Wrong occurrence adapted/accepted | Replace at the selected local offset and preserve sentence offset through the UI |
| Numbered conceptual steps introduced numbers | Quantity-preservation check rejected presentation numbering | Use bullets without inventing quantities |
| Average token length counted spaces/punctuation | Linguistic feature was misnamed | Compute average from actual token lengths |
| Artifact path check used string prefixes | A sibling folder such as DATA_private could pass | Use resolved path containment |
| Frozen manifest loads trusted unchecked assignments | Edited manifests could leak groups or omit rows | Verify nonoverlap, full coverage, span assignments and duplicate context |
| Runner reused modified outputs and allowed force overwrite | Recorded evidence could be silently altered | Verify artifact hashes on reuse; refuse recorded experiment overwrite |
| Node's default reporter changed test output format | All 12 JS tests passed but Python wrapper failed | Request TAP explicitly |

Changing the context/token-length implementation changes model inputs/features.
Any models trained with the older code should be versioned and retrained for
the new feature definitions. This supplied archive contains none to migrate.

## Continued work

1. Added runnable annotation batching and resolution commands with agreement,
   adjudication queue, provenance, unresolved-span tracking and versioned outputs.
2. Implemented Task 15's offline four-condition comparison tooling and a human
   study preparation protocol. Participant evaluation is not performed.
3. Implemented Task 16's table exporter. It requires a verified complete real
   run, uses held-out test metrics, checks them against confusion counts and
   writes provenance. No real paper tables were generated.
4. Added regression and fixture tests for these changes and a practical
   `CONTINUE_HERE.md` guide. Fixtures never appear as project results.

## Remaining material limits

- HG-01: humans must supply independent labels and resolve ambiguity.
- HG-03: the source/licence decision remains pending; no source corpus fetched.
- HG-02: participant approval/consent is still needed before collection.
- Pretrained classifier/embedding/NLI runs and verifier calibration need real data
  and available weights. No pretrained weights were downloaded in this work.
- Semantic `pass` only means no automatic flag; entity checks are heuristic.
  Full-passage similarity can hide local factual errors; added explanations need
  their own source-backed factual review.
- Generic conceptual scaffolding cannot establish successful conceptual support.
- The classifier's routing label is not a diagnosis or a learner's medical cause.
- No PDF upload, automatic localization, multilingual support or robust learner
  history personalization is provided by this continuation.
- jsdom checks are not real-browser/screen-reader accessibility evidence.
- Structural metadata checks cannot prove human authorship or licence validity.

## Verification

The initial existing suite had 128 Python tests pass and one wrapper failure:
the underlying 12 JS UI tests all passed; its expected reporter format differed.
The wrapper was repaired. Final suite/audit results are recorded in
`PROJECT_STATE.json` and `REPORTS/QA_AUDIT.md` after verification.

Final verification: 152 passed in 66.03s (0:01:06). Automated audit: {'pass': 44, 'warn': 0, 'fail': 0}. The Python suite includes 13 jsdom/live-backend checks. No synthetic scores were saved as research results.
