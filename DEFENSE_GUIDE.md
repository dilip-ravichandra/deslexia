# Defense guide — what to say, show and not claim

## One-minute summary
DyslexiAdapt is a research prototype of a *learner-guided reading aid*. The learner selects the part that is hard; the system suggests (or the learner picks) a kind of support — word, sentence structure, or idea — applies a small targeted change instead of rewriting everything, checks that obvious meaning markers survived, and lets the learner accept or reject it. Visual comfort settings are a separate layer and never influence the language analysis. The research question is whether this localized approach changes less text and preserves more content than uniform simplification. **The question is not answered yet**: no human labels or trained model exist.

## What exists, honestly
| Part | State |
|---|---|
| Data schema, validation, annotation batches, agreement (kappa, alpha), adjudication UI, grouped split with leakage report | IMPLEMENTED, tested on synthetic fixtures |
| Baselines, DistilBERT trainer, feature-fusion + matched ablation, experiment runner with hashes, error analysis (clustered bootstrap, calibration) | IMPLEMENTED, SMOKE-TESTED |
| Rule-based interventions + demo lexicon | IMPLEMENTED, DEMO |
| Meaning checks | IMPLEMENTED, uncalibrated |
| Backend + learner UI + Research Lab | IMPLEMENTED; practice mode; jsdom-tested |
| Any trained model, metric, agreement value or user finding | **none exist** |

## Method safeguards worth pointing out
- Document-grouped, frozen splits with a leakage report; model selection on validation only; test scored once.
- Matched control for the fusion ablation (same head, only the features removed); multiple seeds; descriptive reporting; document-clustered bootstrap CIs.
- Research gates: seed/AI/synthetic annotators and unknown licences are rejected; every output is stamped research vs non-research; the app refuses research mode without a validated registered model.
- Honest failure: missing pretrained weights produce a recorded `unavailable` step, never random weights.
- Privacy: logging off by default, no learner text unless consented; visual settings cannot be sent to the classifier (API rejects extra fields).

## Anticipated questions
- *"What accuracy does it get?"* None measured. Say so, then explain the protocol that will measure it and why synthetic scores were not reported.
- *"Isn't the demo suggestion a classifier?"* No — a rule of thumb, labelled as such; the learner can always choose.
- *"Can it detect dyslexia?"* No. It never diagnoses; the scope is support for selected text.
- *"Do the colours/fonts help?"* Unknown; they are user-controlled comfort settings, with no claim of benefit.
- *"Is the meaning preserved?"* The checks catch changed numbers, negation and dropped names; they cannot guarantee meaning, and thresholds are uncalibrated.
- *"Can you release the dataset?"* Not yet; licence decision pending (see `DATA/LICENSE_ANALYSIS.md`).
- *"Why rules instead of an LLM?"* Free-only constraint and verifiability; a generator plugin hook exists, and any generator's output must pass verification.

## Demo script (3 minutes)
1. Start: `python -m uvicorn BACKEND.app:app --port 8000`; open `/`. Point out the practice-mode banner.
2. Use "Try a short sample"; select *catalyst* → gloss, highlighted changes, verification note, accept/undo.
3. Select the *Although…* sentence → split version; show "Try another way" (chunks).
4. Choose "Help with the idea" → scaffold, no invented explanation.
5. Change colours/size/focus mode; show the request in dev tools has only text fields.
6. Open `/research.html` → empty states; explain what unlocks each section.

## Do not claim
Diagnosis; clinical benefit; model accuracy; "validated"; "meaning-preserving"; that any font/colour helps; that the dataset is publishable.
