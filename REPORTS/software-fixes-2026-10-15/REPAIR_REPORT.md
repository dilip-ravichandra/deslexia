**Software repair and verification — 15 October 2026**

The reproducible software defects from the local audit have been addressed. The missing independent human-review workflow and structured generation screening are now implemented locally. No genuine reviewer judgments, participant outcomes, routing results or historical model metrics were invented or replaced.

**Changes and their purpose**

| Area | Result |
|---|---|
| Selected concept/occurrence | The support API carries the selected sentence and occurrence into explanation generation. A nearby glossary entry cannot replace an unrelated selected concept. The second river-bank occurrence receives its river meaning. |
| Unicode selection | The browser explicitly sends UTF-16 offsets; the API converts to Python code points and rejects offsets inside a surrogate pair. Emoji before a selection no longer breaks it. |
| Windows files | Python source/data/report reads and writes explicitly use UTF-8. Hindi, Kannada and Tamil public-material endpoints work with normal Windows settings. |
| Personal evidence | Repeated identical span/category requests do not count toward the automatic-suggestion threshold. Client request IDs make retried help observations idempotent. Decision provenance distinguishes manual choice, survey, history, routing model and lexical model. |
| History deletion | Picture inference captures a consent generation before it starts. Persistence checks that same consent generation inside a database transaction. Deletion removes current and legacy history together; late picture/quality writes cannot recreate it. The browser discards pending support results on successful deletion. |
| Database lifecycle | Database context managers close connections explicitly, fixing Windows file locks and resource leakage. |
| Generation | Main local generation uses structured claims with literal evidence quotes, script/quantity/negation/finite condition screens, one retry, then withholding. The optional English local-model path also screens source claims. Failed drafts are not displayed. Screening metadata is attached only to still-existing consented routes. |
| Reader clarity | Source evidence is inspectable beside screened explanations. Results scroll into view. Missing models are distinguished from basic support. Manual help no longer depends on unrelated classifier inference. |
| Human review | New blank, independent review page supports all four languages, confidence 1–5, rationale, skip/uncertainty, browser restoration and separate JSON exports. No suggested routing label is shown. |
| Review merge | Admin-gated merge validates pool hash, exact source columns, reviewer/session metadata, declarations, timestamps and decisions. Raw exports, all rows, disagreements and incomplete reviews are retained. Agreement/kappa is reported per language/pair, with undefined values remaining null. Merge never trains or activates a model. |
| Research UI | The evidence lab links independent review and provides merge/download controls. `learning.html` is explicitly legacy GPT-pilot operations and explains that current reader feedback goes to the evidence lab. |
| Training/runtime | DistilBERT receives only supported tokenizer inputs. Background routing jobs share the API job gate and record startup failures. Existing human-data activation thresholds remain intact. |
| Setup | Research requirements now include the neural runtime requirements. Windows setup checks supported Python and dependency consistency before downloading assets. Service readiness reports missing files/packages and direct dependency mismatches. |
| Documentation/tests | Review confidence instructions agree with validation. README, status and generated cards distinguish current behavior, historical prototypes and supplementary lexical results. Tests use isolated fixtures instead of assuming an archived pilot is active. |

**Fresh results**

- Full Python test run: **229 passed, 10 skipped, 3 captured warnings**. See `tests-final.txt`. The pytest-asyncio configuration warning also printed at startup. The reported elapsed time includes the interruption/suspension of the working session; it is not a performance benchmark.
- The 10 skips comprise three OCR checks without the required runtime/assets, six explicitly opt-in real-model checks, and one legacy jsdom check without its node dependencies. These are not counted as passes.
- **10 browser checks passed**, with no JavaScript page exceptions. The checks cover actual browser → API → isolated SQLite → lab behavior, deletion, independent save/restore/export, admin merge/download, disagreement retention, Indic data endpoints and Kannada mobile layout. See `browser-checks.json` and screenshots. The intentionally different reviewer labels were engineering fixtures stored only under `.audit-tmp`, never genuine research submissions.
- All **74** backend, ML and test Python modules parsed. Changed JavaScript files passed Node syntax checks.
- Earlier incomplete verification attempts are documented in the audit/scratch logs. One browser harness initially used the wrong context API; another assumed exactly two events although changing passages legitimately adds session closure. The harness was corrected to check actual event types. The preserved `browser-previous-*.json` records that count-assumption failure.

The initially broader test run exposed additional real defects—unsupported DistilBERT token fields, Unicode report writes and unclosed database connections. Those were fixed in implementation. Historical tests expecting an active bundled GPT pilot or an empty artifacts directory were replaced with explicit temporary pilot fixtures and provenance checks. The QA metric regex now reports passages requiring review as warnings, because a numeric regex cannot establish that a source-backed or historical result is fabricated; structural provenance and source-hash failures remain failures.

**What this does not establish**

Finite source checks do not prove entailment, native fluency, instructional quality or comprehension benefit. They can both miss errors and reject valid paraphrases. No fresh live Qwen/vision/MMS/OCR-model quality evaluation was performed, because the large weights and some runtimes are absent. The supplied public routing pool remains blank; the main four-language routing experiment and participant study remain pending. Existing CompLex artifact values are unchanged.

No paid API or hosted service was introduced. Existing component licenses still apply: recorded speech/vision restrictions are not removed by downloading the models for free.

**Running locally**

For the complete pinned stack, install Python **3.12**, run `SETUP_RESEARCH_WINDOWS.bat`, then `START_DYSLEXIADAPT.bat`. The existing Python 3.13 installation cannot install the pinned RapidOCR 1.4.4 package. Model setup explicitly downloads several GB and verifies pinned hashes; it never substitutes simulated inference. See `RUN_RESEARCH.md`.

An isolated `.venv-check` was created for software verification using the existing Python 3.13 packages plus local compatible API/transformer packages. The shared Python installation was not modified. This verification environment can run the basic reader, but it is not the full research environment:

```powershell
.venv-check\Scripts\python -m uvicorn BACKEND.app:app --host 127.0.0.1 --port 8000
```

Reader: `/`; evidence/merge: `/learner-lab.html`; independent collection: `/human-review.html`. Follow `HUMAN_REVIEW_GUIDE.md` before actual annotation. Inspect `/api/model-status` for readiness rather than interpreting a successful health check as model availability.

Repeat the offline software suite in the verification environment:

```powershell
$env:USE_TF='0'
$env:USE_FLAX='0'
$env:HF_HUB_OFFLINE='1'
.venv-check\Scripts\python -m pytest TESTS -q -p no:cacheprovider
```

The standalone browser companion is `TESTS/browser/verify_current.py`. It requires installed Playwright/Chromium and uses isolated, clearly marked engineering fixtures. No actual review judgment should be copied from these fixtures into a dataset.

Implementation references: grammar-constrained generation follows the [llama-cpp-python grammar API](https://llama-cpp-python.readthedocs.io/en/latest/api-reference/); the Python compatibility limitation is recorded in [RapidOCR 1.4.4 package metadata](https://pypi.org/pypi/rapidocr-onnxruntime/1.4.4/json).
