# Run the adaptive prototype

This build implements a trained local baseline, opt-in persistent learner profiles, context-grounded explanations, feedback analysis, reviewed retraining, validation gates, activation and rollback. The bundled classifier is a prototype trained from GPT labels; it is not a validated research model.

## Windows / PowerShell

Use Python 3.11 or 3.12. Extract the ZIP and open a terminal in the folder containing this file.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r BACKEND/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn BACKEND.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the student reader. Open http://127.0.0.1:8000/learning.html for evaluated prototype training and feedback review. The older research lab remains at /research.html and retains its strict research-data gates.

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r BACKEND/requirements.txt
.venv/bin/python -m uvicorn BACKEND.app:app --host 127.0.0.1 --port 8000
```

## Try the adaptation loop

1. Paste a passage and select the part you want help with.
2. Choose Word, Sentence or Idea help when the prototype is unsure.
3. Choose a support style: short, steps or an example from your passage.
4. Enable **Remember which support helps me** only if you want the local helper to retain the selected text, passage and decisions for your profile and admin review.
5. Mark two separate step-by-step responses helpful. On a later request for the same support category, **Follow what helps me** should prefer steps.
6. Use **Forget my support history** to delete the local profile, stored traces and reviews. Deletion does not unlearn existing model weights; retrain after deletion to exclude reviewed records.

The browser keeps a random profile capability; it is not a login account. Different browser profiles have different histories. Keep this prototype on localhost. Existing admin access protection is preserved.

## Admin retraining

1. Inspect opt-in feedback in **Train & adapt**.
2. Read the passage and record a reviewed category, reason and reviewer code. Helpful feedback does not automatically become a training label.
3. Click **Train evaluated candidate**. Training happens in a background job.
4. Inspect validation precision, recall, F1 and support. The candidate must not reduce validation macro-F1 or recall for a supported category.
5. Activate an eligible candidate deliberately. Activation does not use the test score. The previous active version is retained for rollback.

The initial test result is recorded once in ARTIFACTS/prototype/initial_test.json. It is descriptive prototype evidence only. Repeated candidate selection against validation can also overfit; a later real study needs a fresh independent test set.

Feedback overlapping the bundled protected validation/test passages is rejected from retraining. This is text-overlap protection, not a universal semantic-duplicate detector. When importing new datasets, establish and inspect document identity before training.

## Contextual explanations

Without additional downloads, the reader combines the selected sentence, its context, explicit clause relationships and a bundled educational glossary. The original remains visible and unchanged; explanations are supplementary. The system says when no concrete example is present instead of inventing one.

For broader generated explanations, optionally run a **local** Ollama model. Install Ollama from https://ollama.com and choose a locally runnable model suitable for your RAM. Follow https://docs.ollama.com/quickstart to download and run it. The integration uses the official local /api/generate endpoint documented at https://docs.ollama.com/api/generate.

In the same PowerShell terminal before starting the app:

```powershell
$env:DYSLEXIADAPT_LOCAL_MODEL = "YOUR_DOWNLOADED_LOCAL_MODEL_NAME"
```

Linux/macOS:

```bash
export DYSLEXIADAPT_LOCAL_MODEL="YOUR_DOWNLOADED_LOCAL_MODEL_NAME"
```

The connection is fixed to http://127.0.0.1:11434. Use a locally downloaded model, not a cloud-only model. No external AI provider is configured by this app. If the local model is unavailable, the response falls back to the grounded support above. No generative weights are bundled, and real-model generation was not exercised in the build environment. Optional provider handling was tested with mocked local responses.

Generated explanations are marked as local-model output. Automated checks do not guarantee their truth or meaning preservation. They are supplemental notes, not automatic replacements of the source passage.

## Current evidence

- Two GPT passes on 140 synthetic examples: 95 matching labels, 45 unresolved.
- Agreed labels: 16 vocabulary, 19 syntactic, 27 conceptual, 33 other/uncertain.
- Training: 60 agreed rows; validation: 19; initial test: 16. All spans from a passage stay together.
- Baseline: TF-IDF + class-balanced logistic regression; C chosen on validation.
- Initial validation macro-F1: 0.430; test macro-F1: 0.286. These are weak results against provisional labels, not human comprehension results.
- Original reviewers' GPT labels and reasons remain in DATA/prototype_pilots.json; disagreements have no consensus category.

Human-review claims in earlier spreadsheets are superseded by the user's clarification that these were GPT passes. The canonical prototype dataset records TWO_GPT_PASSES. No synthetic material is promoted into the research registry.

## Remaining validation

This is an implementation prototype. It has not been evaluated with students with dyslexia. Broader lexical coverage, meaning-preservation calibration, real human annotations and comprehension/usability studies remain necessary. DistilBERT/fusion training scripts are retained but were not trained in this continuation. The classifier and presentation/feedback logic are separate.
