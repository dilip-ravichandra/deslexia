# Task Report — 11 Backend
## Files
BACKEND/app.py, BACKEND/pipeline.py, BACKEND/research.py, BACKEND/requirements.txt, TESTS/test_backend.py (19 tests), RUN_PRODUCT.md.
## Behaviour
- Pipeline: context builder -> category (learner choice, validated research model, or demo heuristic) -> intervention -> verification (at sentence level) -> trace.
- Endpoints: GET /api/health, /api/model-status, /api/disclaimer; POST /api/adapt, /api/feedback; admin/local-only GET /api/research/summary, /api/research/artifact, /api/research/traces; static serving of FRONTEND.
- Integrity gates: a trained model is used only if ARTIFACTS/research_model/registry.json points to a run with data_status "research" (and valid_for_scientific_claims for transformers); smoke/fixture runs are rejected with a reason. Requesting research mode without one returns 503. Demo suggestions have no probability or confidence and are labelled.
- Learner requests accept text fields only (extra fields such as colours or font size return 422), so visual settings cannot reach classification.
- Unsafe adaptations (verification `fail`) are marked not presentable and hidden by the UI.
- Logging is off by default; when on it stores minimal events without learner text unless explicitly enabled.
- Research endpoints require DYSLEXIADAPT_ADMIN_TOKEN if set, otherwise local-only.
## Limitations
No authentication or rate limiting for learners; in-memory trace summaries; the research-model gate is structural and cannot prove annotators were human (HG-01). Never run against a real validated model (none exists); the model-loading paths were exercised with smoke artifacts and a forged-flag plumbing test that is labelled as such.
