# Document release verification

This release passed 89 checks: 63 backend/document/profile/access checks; 6 checks using actual pretrained text weights; 20 real Chromium browser-flow checks. Repeated descriptive pilot scores and small synthetic visual tests are not independent research validation.

The backend tests exercised real RapidOCR and PDFium, including a scanned PDF, embedded PDF text, OCR override, UTF-8 import, invalid files, page bounds, upload/pixel limits, private admin access and actual prototype summary. Visual feedback checks verified profile ownership, idempotent final decisions, learned style preferences and deletion. Existing text retraining/profile/intervention checks passed with generation disabled to isolate their behavior.

The six neural checks used actual MiniLM, Qwen text and NLI weights. They exercised the pretrained encoder, contradictions, student API generation, contextual word senses, prompt-instruction filtering, classifier behavior and number-list checking. The earlier skipped invocation was replaced by an explicitly enabled real-model run: all six passed.

Chromium flows checked image upload → OCR → editable text → reader → word support; mobile width with no horizontal overflow; actual evidence and candidate reports; PDF page 1 embedded extraction and page 2 chart OCR; keyboard crop; visual question → real Qwen multimodal inference → saved notebook → feedback → lab counts → deletion; dataset disagreement inspection; recorded confusion matrix navigation; and successful train-lab load status. No browser JavaScript exceptions occurred. A caught legacy dashboard render error was found in visual inspection and fixed by separating prototype reports from the historical registry; final checks assert an empty error banner.

Two original synthetic visual fixtures were also inspected with real weights: chart A=2, B=4, C=6 and Sun → Plant → Food. The model correctly described the chart values and diagram relationships. These two cases do not measure broad accuracy. Initial full-resolution calls were slow (326 seconds for chart, 164 seconds for diagram). Final browser inference downsizes the model input to at most 640 pixels per side; the chart question completed in 70.1 seconds on this CPU and identified C=6 compared with B=4 and A=2. Performance depends on hardware and input. The original page preview stays at its own rendered resolution.

Pinned text assets and the final vision assets were SHA256-verified. OCR engine warmup passed. Python package dependency checking passed. Document and neural runtime wheels downloaded successfully for CPython 3.12 on win_amd64. The batch launcher itself was not executed on a native Windows host.

Actual pilot labels remain AI weak labels. No student study, clinical validation or accessibility certification was performed. Visual explanations have no semantic truth verifier; they are visibly marked unverified. The original Qwen vision license is non-commercial research/evaluation, despite a conflicting quantizer card. Original license/notice are retained.

See DOCUMENT_RELEASE_QA.json for browser checks and exact generated outputs. TESTS/fixtures/documents contains the synthetic inputs. Browser scripts are in TESTS/browser and are optional; install BACKEND/requirements-test.txt and Playwright Chromium to run them. Model weights must be set up first.
