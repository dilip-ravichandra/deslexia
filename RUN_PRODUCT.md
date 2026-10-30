# Running DyslexiAdapt (learner app + Research Lab)

## Start (Windows PowerShell / Linux / macOS / Colab terminal)
    pip install -r BACKEND/requirements.txt
    python -m uvicorn BACKEND.app:app --port 8000
Open http://127.0.0.1:8000/ (learner app) and http://127.0.0.1:8000/research.html (private Research Lab).

Without a validated research model the app runs in **practice (demo) mode**: category suggestions come from a
simple rule of thumb and every trace is labelled demo. Learners can always pick the support type themselves.

## Environment variables
| Variable | Default | Meaning |
|---|---|---|
| DYSLEXIADAPT_ADMIN_TOKEN | unset | If set, research endpoints need header `x-admin-token`. If unset they are local-only (127.0.0.1) |
| DYSLEXIADAPT_LOG | off | `1` writes minimal trace/feedback events to ARTIFACTS/traces/traces.jsonl (no learner text) |
| DYSLEXIADAPT_LOG_TEXT | off | `1` also logs the selected span/sentence. Only with participant consent (HG-02) |
| DYSLEXIADAPT_SEMANTIC_MODELS | off | `1` loads MiniLM + NLI models for extra meaning checks (needs weights/network) |

## Plugging in a real research model (after real training)
1. Train on research-valid data with a frozen split (see RUN_COLAB.md).
2. Create `ARTIFACTS/research_model/registry.json`:
   `{"kind": "fusion", "path": "../<run folder>"}`  (or `{"kind":"sklearn","path":"../baselines","model_file":"tfidf_logreg.joblib"}`)
3. The backend accepts it only if that run's results.json has data_status = "research" (and
   valid_for_scientific_claims for transformers). Smoke/fixture runs are rejected with a reason.

## Tests
    python -m pytest -q                       # Python suite (includes the browser-level checks if node+jsdom exist)
    cd TESTS/ui && npm install                # one-time, enables the jsdom UI tests
