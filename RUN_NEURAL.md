# Run the real-model build

> Legacy prototype guide. `START_WINDOWS.bat` now launches the current multilingual build. Use `RUN_WINDOWS.md` and `RUN_RESEARCH.md` for current setup and model status.

This continuation was exercised with downloaded pretrained weights. It is not the earlier connector-only prototype.

## Windows: easiest route

1. Install Python 3.12 (64-bit) with **Add Python to PATH** enabled.
2. Extract this project ZIP into a normal writable folder.
3. Double-click **START_WINDOWS.bat**.
4. The first launch installs dependencies and downloads about **1.54 GB** of pinned model files. Keep the terminal open and allow the download to finish.
5. Open http://127.0.0.1:8000 for the reader and http://127.0.0.1:8000/learning.html for admin improvement controls.

No paid API, API key or separate Ollama configuration is needed. After setup, inference runs on your computer. Subsequent launches verify and reuse downloaded files. At least 8 GB RAM is advisable; the build was tested on a 9.7 GB Linux CPU environment. Actual response time depends on your CPU.

The CPU wheel index has a Windows x64 wheel for the pinned llama-cpp-python version. The Windows launcher itself was not executed on Windows during this build; Linux runtime, model inference and API/interface flows were tested.

## Manual setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r BACKEND/requirements.txt
.\.venv\Scripts\python.exe -m pip install --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r BACKEND/requirements-neural.txt
.\.venv\Scripts\python.exe -m ML.model_setup
.\.venv\Scripts\python.exe -m uvicorn BACKEND.app:app --host 127.0.0.1 --port 8000
```

Linux/macOS: use `.venv/bin/python` instead of the Windows Python path.

## What actually runs

- **Classifier:** a validation-selected probability ensemble of the original TF-IDF classifier and a classifier using pretrained MiniLM span/context embeddings plus linguistic features. All 45 unresolved examples retain both GPT pass labels and are excluded from consensus-target training.
- **Explanation model:** Qwen2.5-1.5B-Instruct Q4_K_M, executed directly through llama-cpp-python. It provides plain-language explanations for inputs outside the bundled glossary.
- **Meaning checks:** pretrained MiniLM NLI and sentence embeddings plus number/negation/entity checks. Additions are treated as supplementary explanations; candidate replacements use stricter verification.
- **Context disambiguation:** high-risk ambiguous words such as bank use explicit contextual definitions or a clarifying question. The model is not allowed to blend unrelated word senses in that path.
- **Safety fallback:** rejected generated explanations are not shown as accepted model answers. The original passage remains intact and grounded support is retained. A rejection is not hidden in the logs or claimed as a successful generation.
- **Personalization:** opt-in helpfulness feedback updates support-style preferences; it does not automatically label difficulty or update global model weights.
- **Admin learning:** review selected feedback, train a candidate, inspect validation metrics, activate an eligible version and roll back. Candidate selection and promotion never use test metrics.

## Try it

Select `denominator` in: “In the fraction 3/8, the denominator is 8 and indicates the number of equal parts in the whole.” Choose **Explain a word**.

Select `ecosystem` in: “An ecosystem includes living organisms and the nonliving surroundings with which they interact.” Choose **Explore an idea**. The response is generated locally; if automatic checks reject it, the interface retains grounded support and reports the rejection.

Select `bank` in “After crossing the river, she rested on the bank.” The contextual dictionary should identify the river meaning. With only “She went to the bank,” it should ask which meaning is intended.

For immediate adaptation, enable **Remember which support helps me**, request **Step by step**, mark two separate responses helpful, then choose **Follow what helps me**. The next support request for that category should prefer steps. Turning memory off deletes stored profile feedback and reviews; existing weights are not automatically unlearned.

## Measured classification results

Same 140 synthetic examples and frozen document partitions as before: 60 agreed training rows, 19 validation rows, 16 test rows. The remaining 45 rows preserve disagreement.

| Metric | Earlier baseline | Selected upgrade |
| --- | ---: | ---: |
| Validation macro-F1 | 0.430 | 0.829 |
| Descriptive frozen-test macro-F1 | 0.286 | 0.661 |

The upgraded model was selected on validation only and passed the existing non-regression gate for supported-class recall. This is a repeated descriptive evaluation on the same small pilot test, not a new independent benchmark. The labels are GPT-generated; these results do not show human agreement or improvement for students with dyslexia.

The abstention threshold is selected on validation to balance accepted examples and provisional-label agreement. Raw probabilities are not calibrated clinical or learner-difficulty confidence. When unsure, the reader asks the learner to choose help rather than force a category.

## Model provenance and licences

Exact repository revisions, file sizes and SHA-256 hashes are in MODELS/manifest.json. Setup refuses hash mismatches. Model cards and licences are downloaded alongside their weights.

- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF — upstream Apache-2.0.
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 — upstream Apache-2.0.
- https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768 — upstream Apache-2.0.

These model licences do not turn the synthetic annotation pilot into a human-validated or dyslexia-specific dataset. No public dataset licence is invented for the user’s annotation files.

## Verification and limits

ARTIFACTS/real_generation_evaluation.json contains actual model outputs, latency and verification outcomes for 12 technical cases. This includes genuinely new concepts, word senses, quantities, exceptions, negation, ambiguity and instruction-like text. Rejected outputs and dictionary/clarification routes remain labelled honestly.

Pretrained NLI can make false-positive and false-negative decisions. Its thresholds are not calibrated against a human review set. Generated facts and analogies can still be wrong; no “perfect answer” guarantee is made. The known instruction-filter test is not proof against every prompt injection.

Human comprehension, accessibility, actual-browser/screen-reader behaviour and dyslexia benefit remain unvalidated. The technical implementation is now using real models; a learner study is a separate evidence step, not a missing model connector.
