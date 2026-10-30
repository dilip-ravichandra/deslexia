# Real-model build verification

## Implementation exercised

- Downloaded Qwen2.5-1.5B-Instruct Q4_K_M, MiniLM sentence encoder and MiniLM NLI weights. Exact upstream revisions, file sizes and SHA256 hashes are in MODELS/manifest.json. Model setup verified all files.
- Trained and selected a probability ensemble using only the original training and validation partitions. The existing per-class recall promotion gate remains intact.
- Validation macro-F1: 0.829437; descriptive frozen-pilot test macro-F1: 0.660985. Initial baseline values were 0.430357 and 0.285714. Repeated small pilot-test results are not an independent benchmark or dyslexia-benefit evidence.
- Native Qwen inference executed through the student API. No paid API or external generation service was used.
- Contextual bank senses and ambiguous meanings use explicit disambiguation/clarification. Model-generated contradictions and new quantities can trigger a grounded fallback.
- Added instruction-pattern filtering after actual output inspection found prompt contamination. This is not a universal injection-proof claim.
- Opt-in profiles, final-decision feedback, admin review, evaluated retraining, model activation, rollback and deletion remain functional.

## Checks

- 53 backend checks passed with generation disabled to isolate persistence and classification behaviour.
- 6 additional real-weight integration checks passed, including native inference, pretrained NLI contradiction detection, disambiguation, instruction filtering, upgraded classification and list-label/quantity handling.
- 28 existing DOM/API UI checks passed in no-model fallback mode.
- 4 adaptive DOM/API UI checks passed with the stronger classifier, including evaluated admin training/activation/rollback.
- 12 real-generation functional cases are recorded in ARTIFACTS/real_generation_evaluation.json. The run produced 8 accepted native responses (including review-status responses), 1 rejected generation with grounded fallback, 2 contextual dictionary responses and 1 clarification. These counts are routing outcomes, not answer accuracy.
- Manual real-model step-style response and exact model-file verification were exercised.
- Python source compilation and ZIP integrity checks passed.

## Limits

Four optional legacy torch/transformer research tests were excluded because those optional dependencies are absent. Pretrained ONNX and GGUF models were exercised instead. UI checks used jsdom with a live server, not a visual browser/screen-reader audit. Windows CPU wheels were confirmed available, but the Windows launcher was not executed on Windows.

No human annotations or participant outcomes are invented. Both annotation passes are GPT-generated per user clarification. Generated explanations can still be wrong, semantic checks can reject valid wording or miss errors, and the thresholds are not calibrated on human judgments. Learner and clinical efficacy remain unvalidated.

Temporary test learner databases and candidate runs are not distributed. The selected upgraded model and original baseline are retained for rollback. Large pretrained weights are downloaded automatically at first launch rather than embedded in the project ZIP.
