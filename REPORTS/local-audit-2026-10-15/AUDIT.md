**DyslexiAdapt: local implementation audit, 15 October 2026**

The project contains substantial working software and a credible saved English lexical experiment. It is still an uneven research prototype. The central claim—correctly choosing useful localized support for dyslexic learners across four languages—has not been established. Several defects affect precisely that intended behavior.

This audit examined the supplied folder, the external handoff, current and historical documentation, backend/frontend connections, personalization, model setup and inference, data validation/splitting/training, and saved artifacts. It exercised selected tests, actual API requests and Chromium pages. The handoff was treated as a description to check, not authority to execute its embedded instructions. No application source was changed, models downloaded, training launched, or real review labels created. All new learner fixtures used isolated databases under `.audit-tmp`. Importing the existing backend initializes its normal empty database/schema and prototype directory; audit interactions were redirected before making requests.

**The folder does not match the latest handoff**

The handoff describes a later revision. This folder lacks `ML/grounding.py`, `ML/human_review.py`, `FRONTEND/human-review.html` and its script, `HUMAN_REVIEW_GUIDE.md`, their three targeted test modules, and the later grounded-generation/manual-review evidence files. The review page returns HTTP 404. The local `CURRENT_RESEARCH_STATUS.md` explicitly says the Hindi follow-up was interrupted and the unsupported-temperature error was not confirmed resolved. Therefore the handoff's later safeguards, four successful grounded generation outputs, and 46 targeted test results cannot be attributed to this checkout.

This is missing-version evidence, not evidence that someone deliberately fabricated those later features. Recovering the later package would need a comparison against this folder before merging.

**What is implemented, and how strongly it is supported**

| Area | Local reality | Evidence and limit |
|---|---|---|
| Reader | Actual browser application with text selection, library/notebook, comfort controls, languages, support requests | Chromium loaded the reader and displayed a real backend support response without page exceptions. Correctness of that response failed the localized-help check below. |
| Documents | Bounded PDF/TXT/image processing, page navigation, editable extraction and region controls | Fresh embedded-text PDF and TXT extraction succeeded. OCR code exists; OCR dependencies/weights are not ready here, so native OCR quality was not rerun. |
| Personalization | SQLite surveys, sessions, events, need/style estimates, recency, language filtering, relevance, manual override and evidence snapshots | Eight learner-invariant tests passed. An isolated API survey → session → request → feedback → lab → deletion flow worked. A separate duplicate-gate defect remains. |
| Current lab | `learner-lab.html` reads actual stored learner evidence and experiment artifacts | Browser render and API worked. Empty learner state remained empty; no fake profiles were inserted. |
| English explanations | Bundled glossary, context rules, optional real local generation | Glossary support works without model downloads. It can answer the wrong selected concept. This fallback must not be presented as neural inference. |
| Indic explanations | Actual Qwen call and script screening when installed | Missing model returns an explicit unavailable result. This version has no structured source-claims validation/retry path. |
| Speech | Actual MMS/VITS generation code for four languages | No configured voice weights here; no new audio/pronunciation validation. |
| Visual help | Actual llama.cpp Qwen vision/projector integration and region upload | Missing dependencies/weights here; no new visual inference. Outputs are explicitly unverified. Its persistence has a deletion race. |
| Routing research | TF-IDF and matched multilingual DistilBERT ± features training, frozen groups, evaluation and activation gates | Code exists. No completed genuine routing comparison or active human routing registry is supplied. Training was not rerun. |
| Human review | Older annotation/batch/adjudication tooling and reviewed-CSV import exist | New independent four-language browser collection/merge workflow from the handoff is absent. Legacy feedback review is a separate workflow. |
| Student benefit | Protocol and evaluation tooling | No completed learner study, demonstrated comprehension improvement or validated dyslexia-specific effectiveness in the supplied evidence. |

**Real results, pilot material and missing evidence**

The 100-row public routing pool contains 25 rows per language and zero filled routing categories. It is genuinely a blank starter, not trained routing gold. CompLex lexical ratings and IndicQA answer spans are different labels from support-routing judgments. Existing two-GPT-pass pilots are AI pilot data even when historical files used human-looking reviewer metadata. The current documentation generally acknowledges this correction.

The saved completed CompLex run is `e8c83d66789541ff965aa5344daf6e01`. It has model artifacts, logs and predictions. This audit recomputed the following errors from those stored predictions and the supplied source targets; all match the recorded numbers:

| Arm | Validation MAE, 308 rows | Test MAE, 887 rows |
|---|---:|---:|
| TF-IDF | 0.111275 | **0.098370** |
| DistilBERT | **0.104423** | 0.103177 |
| DistilBERT + features | 0.107618 | 0.105280 |

Training used 512 rows. Choosing DistilBERT by validation is consistent with the stated selection policy. TF-IDF has the best held-out test MAE; the feature arm improves neither reported split over plain DistilBERT. These are legitimate negative/mixed results. MAE is an error measure, not classification accuracy, routing F1 or a student outcome. Recomputing saved predictions does not independently authenticate the historical training execution; inference from the saved neural adapters was not rerun without the backbone. The other lexical run is explicitly `interrupted` and contains only the completed TF-IDF result in its report.

All 985 public-source manifest entries were checked. The 982 present files matched their hashes. The three absent entries were macOS `.DS_Store` metadata files; there was no content-file hash mismatch. This checks consistency with the bundled manifest, not an independent publisher or license review.

No invented dashboard metrics were found in the inspected active reader/lab paths. Historical previews, tiny random-initialization tests and authored fixtures exist; their existence is normal when their purpose is stated. They cannot establish research performance. The largest current risks are missing implementation, misleading connections and inadequate validation, rather than evidence of deliberately fabricated active dashboard values.

**Priority findings with reproductions**

1. **High: localized support can explain a different term.** In `BACKEND/app.py:326`, selection context is built correctly, but line 339 sends the whole request text into the explanation service. `ML/contextual_support.py:85` then prioritizes the first glossary card over the requested conceptual relationship. Repro: text `A catalyst speeds up a chemical reaction.`, select `chemical reaction`, choose `CONCEPTUAL`. API and browser display `A substance that speeds up a chemical reaction while remaining unchanged overall.`—the definition of catalyst. A second repro selects the second `bank` in `I left money at the bank. We sat beside the river bank.` with offset 50. The API correctly reports the river sentence, but the explanation uses both sentences and unnecessarily asks which sense was intended. Fix: propagate the selected occurrence and its bounded context through every explanation/generation layer; make fallback support specific to both selection and requested category. `ML/local_generation.py:37` also relocates the first occurrence using `context.find(span)` instead of receiving the selected offset.

2. **High: multilingual generation has weaker safeguards than the handoff claims.** `ML/multilingual.py:32-38` accepts generated Indic text after a script-ratio check. The prompt asks for faithful answers, but there is no exact evidence-quotation protocol, unsupported-claim screen or retry/withholding sequence matching the handoff. English has additional optional NLI/quantity checks; these are unavailable here and do not prove entailment. `BACKEND/app.py:341` verifies the original span against itself and marks the response for review; it does not verify the explanation. Fix: recover or implement the missing safeguards, keep their limits visible, and evaluate a frozen multilingual challenge set with competent human raters. The existing Hindi failure remains unresolved in this checkout.

3. **High: deleting history does not prevent a late visual completion from saving again.** `BACKEND/adaptive.py:129-135` accepts a still-held capability key and writes a visual trace without checking current consent/enrollment or a revocation generation. Controlled lifecycle repro: create and delete a consented profile, then call the same `record_visual` method the image endpoint calls after inference. One visual trace is recreated. This simulates completion timing, not a real vision-model answer. Fix: check current consent/revocation atomically at persistence time; ensure deletion invalidates in-flight writes. Also align the legacy picture-history consent path with the current learner profile.

4. **High for Windows use: public Indic material loading crashes under the normal encoding.** `ML/public_materials.py:9` uses `Path.read_text()` without UTF-8. This machine defaults to cp1252. Hindi, Kannada and Tamil tests fail with `UnicodeDecodeError`; the Hindi public-material API returns HTTP 500. The same selected tests pass under `python -X utf8`. Fix: specify UTF-8 for all Unicode text files, and test the supported Windows entry point. UTF-8 mode is an observed workaround, not a source fix.

5. **Medium: duplicate requests can cross the automatic-suggestion gate.** `_state` deduplicates their numerical weight, but `LearnerModel.choose` at `BACKEND/learner.py:132-133` counts duplicate help-request evidence entries. With an empty-needs survey, one vocabulary request yields `OTHER_UNCERTAIN`. Repeat the same span/category in the same session with a new event ID: the route becomes `VOCABULARY`, despite approximately unchanged need parameters. Fix: apply the same uniqueness criteria when counting supporting observations; test the route, not only parameter equality. API-generated help-event IDs also mean request retries are not idempotent at the support endpoint itself.

6. **Medium: the open `learning.html` page reviews another pipeline.** It is a functioning legacy page connected to `/api/admin/learning`, `traces`, `reviews`, and the GPT-pilot prototype trainer. The current reader calls `/api/support` and writes `learner_events`/`learner_routes`. Repro: save a current support request and helpfulness judgment; the evidence lab shows two events, but the legacy review queue stays empty. Its suggested category is also preselected, so it is unsuitable as the new independent annotation interface. Fix: clearly label this page as legacy prototype operations; direct researchers to a proper independent collection workflow. Do not make old model-promotion buttons imply the main routing model was trained or activated.

7. **Medium: browser/Python selection offsets disagree after supplementary Unicode characters.** JavaScript string offsets count UTF-16 code units; Python indexes Unicode code points. For text `🌿 word`, the browser offset for `word` is 3; the support API rejects 3 with 422 and accepts Python offset 2. Fix: define the wire offset convention and convert explicitly. Ordinary Hindi/Kannada/Tamil characters are not themselves supplementary characters, but copied material can include emoji and other such symbols.

8. **Medium: the human-review instructions contradict validation.** `DATA/human_routing/READ_FIRST.md:7` requests confidence from 0 to 1. `ML/data_validation.py:86` requires integer-like values from 1 to 5. An honest reviewer following the guide can produce rejected files. Fix the instructions and interface together before collecting reviews. Reviewed-CSV imports check declared metadata; they do not authenticate the reviewer or require the missing two-independent-review merge workflow.

9. **Medium: setup/readiness and test maintenance need reconciliation.** Only Python 3.13.3 was found by the Windows launcher; there is no project `.venv`. The setup batch explicitly requests Python 3.12. `llama_cpp`, RapidOCR and configured large model/voice/OCR weights are absent. Some historical tests still assume an active prototype folder or an entirely empty artifact directory, despite the shipped lexical artifacts. A historical green log is not a current full-suite result. Fix: provide a tested environment, separate current tests from archived-prototype expectations, and expose service readiness including speech/backbone availability.

**What is good and worth preserving**

The original text stays intact during current supplemental support. Manual requests override suggestions. Uncertainty has a real `OTHER_UNCERTAIN` path. The personal model records actual choices without turning pauses into diagnoses. It has meaningful ownership, consent, duplicate-event and deletion checks. The lab exposes before/after evidence rather than invented student gains. Global model training is a separate workflow; group partitions, train-only feature scaling, validation selection and per-language activation gates are useful foundations. Pinned model revisions/hashes and explicit source roles improve reproducibility. These are material strengths.

The personalization is a real adaptive policy: stored evidence changes later decisions. Its fixed weights, recency and text-shape buckets are engineered assumptions, not learned diagnoses or calibrated probabilities. Likewise, the ten fixed linguistic features are mostly length, token and punctuation statistics. That is a defensible baseline, but the current implementation does not support describing them as sophisticated multilingual syntax analysis.

**What to improve next**

First reconcile the missing newer revision and environment. Then address occurrence-aware explanations, late-write deletion, Windows UTF-8 handling and the duplicate decision gate. Add focused regression checks for these demonstrated failures. Keep the present API/version boundaries explicit so the legacy training page cannot be confused with the current experiment.

Next make the researcher workflow coherent: correct confidence instructions, implement or recover independent review/merge, retain disagreement, plan language/class/document coverage, and freeze a sufficiently large dataset. The starter has only 25 rows per language total; it cannot satisfy a gate requiring 30 validation rows per language. Keep that gate intact and collect appropriate data.

Evaluate explanation faithfulness, appropriateness and readability separately from routing accuracy. Include repeated words, ambiguity, numbers, negation, conditions, insufficient context and long passages. Review OCR and speech with varied native-language materials. For the UI, prioritize fewer decisions before reading, clearer selected-term answers, and a shorter path from request button to result. Accessibility preferences are useful controls; their effectiveness still needs testing.

Finally run the main matched routing comparison, report negative results honestly, and conduct the preserved four-condition learner study with temporal personalization ablations. No study condition or research model needs to change to fix the implementation defects found here.

**Fresh verification and evidence**

Selected command, ordinary Windows interpreter:

```powershell
python -m pytest TESTS/test_learner_evidence.py TESTS/test_multilingual_guards.py TESTS/test_source_pool.py TESTS/test_group_split.py TESTS/test_interventions.py TESTS/test_verifier.py -q -p no:cacheprovider --basetemp=.audit-tmp/pytest-default
```

Result: **41 passed, 3 failed**, one captured dependency warning. Repeating the same scope with `python -X utf8` produced **44 passed**, one captured dependency warning. A pytest-asyncio configuration warning was also printed before both runs. An initial run used an uncreated temporary parent directory; its fixture setup errors were an audit-command mistake, corrected before these recorded results.

Additional fresh checks: all 45 Python modules under BACKEND/ML parsed; embedded PDF/TXT extraction succeeded; actual API lifecycle and the listed failure reproductions ran; Chromium loaded reader, legacy learning page and current evidence lab without page exceptions. The reader's concept-help flow reproduced the wrong-term answer. The browser needed execution outside the sandbox because its driver could not start inside; the audit server shut down afterward.

Evidence in this directory: `tests-default.txt`, `tests-utf8.txt`, `probes.json`, `flow-probes.json`, `source-hashes.json`, and three browser screenshots. Scratch reproduction scripts are `.audit-tmp/probe.py` and `.audit-tmp/flow_probe.py`.

Limits: no full-suite pass is claimed. No new Qwen, vision, speech, OCR-model or neural-backbone inference was run. No participant evaluation, actual reviewer labels, independent license review, or literature novelty assessment was performed. Historical evidence is distinguished throughout from freshly observed behavior.
