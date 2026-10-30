# Task 15: evaluation preparation

Tooling is ready for offline comparisons. No participant data has been collected.
Human evaluation and final research findings remain blocked by HG-01/HG-02/HG-03.

## Offline paired comparison

Create one JSONL record per held-out educational passage. Fields:

- `sample_id`: unique comparison identifier.
- `document_id`: document/source group, preserved from the frozen test split.
- `original`: full original passage.
- `uniform_simplification`: actual whole-passage baseline output.
- `generic_accessibility`: exactly the original text; display settings differ.
- `targeted`: full passage with the actual local adaptation and any explanation.

Never invent outputs or use the demo lexicon as a reviewed research resource.
Record model, dataset, generator and verification versions in your experiment
documentation. Use the same original passage in all conditions. A missing output
is an error, not an unchanged passage. Store participant information separately.

    python -m ML.evaluation --comparisons DATA/comparisons_v1.jsonl --out ARTIFACTS/evaluation/v1

The command saves hashed provenance, per-passage checks, paired edit-budget
differences and a summary. It refuses overwriting an existing evaluation.
The default semantic model checks are unavailable unless scorers are passed to
the Python API; unavailable scores stay null. Outputs are marked unvalidated,
not research-valid, regardless of an automated pass. Readability can be supplied
as a callback; document its scale and direction. SARI is not computed without
task-matched human references. An explanatory addition need not be entailed by
the passage alone: review it against its cited source separately.

## Human evaluation preparation (before recruitment)

1. Submit the study protocol, consent wording, material licences, privacy plan
   and recruitment criteria to the appropriate institutional process (HG-02).
2. Predeclare the primary outcome, comprehension-question scoring, secondary
   outcomes, exclusion rules, sample-size rationale and statistical analysis.
3. Use original, uniform simplification, generic accessibility and targeted
   support as four separate conditions. Keep presentation settings matched
   between linguistic conditions unless explicitly testing presentation.
4. Counterbalance order and passage-to-condition assignments. Do not show the
   same learner the same passage in every condition: memory would affect scores.
5. Have educators review passages, explanations and equivalent comprehension
   questions before collecting responses. Separate questions that test original
   facts from questions requiring genuinely new explanatory content.
6. Collect only approved fields: pseudonymous participant ID, passage ID,
   condition, question score, reading time, difficulty rating and helpfulness.
   Health status is not inferred from interaction logs.
7. Distinguish participants from passages as analysis units. Account for repeated
   measurements and document/participant clustering. Do not treat every span as
   an independent participant. Select tests based on the final approved design.
8. Report uncertainty, exclusions and missing outcomes. General-student results
   do not establish effectiveness specifically for dyslexic readers.

These steps prepare a reviewable study. They do not constitute institutional
approval or authorize recruitment. No synthetic participant rows are provided.
