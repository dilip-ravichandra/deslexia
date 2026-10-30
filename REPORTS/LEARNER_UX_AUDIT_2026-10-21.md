# Learner experience audit — 21 October 2026

## Bottom line

The app has a functioning local account, saved learner state, document OCR, quick text help, optional local/online AI, picture explanation, and speech paths. It is **not yet a reliably fast or proven dyslexia-support product**. The most serious learner-facing problems are slow CPU inference, dependence on an installed browser voice or slow local speech model, unclear distinctions between OCR/opening text/speaking, and dense help/report screens. A `200 OK` only means an API request completed; it does not prove audible playback, OCR accuracy, a useful explanation, or successful learning.

This is a code and automated-browser heuristic audit, **not** a usability study with dyslexic learners. Dyslexia affects people differently; no one display setting or explanation style will suit everyone. The supplied screenshots and reported behavior were treated as evidence of confusion, but I did not access the user's signed-in browser, hear their speakers, or inspect their private account records.

## What I checked

| Flow | Evidence and result | Limit |
| --- | --- | --- |
| Sign up → profile setup → sign out/switch → sign back in | Real Chromium + FastAPI + **temporary isolated SQLite database**: passed. Two accounts had distinct profiles, and the first account's saved feedback influenced a later suggestion. | This does not prove the current browser is signed into the intended account. No live records were changed. |
| Saved report | Browser mock: signed-in username, immutable starting date, starting choices and current style render correctly after the wording change. | Screenshot's alias `h` and old date alone cannot establish a wrong account. |
| Reader speech | Browser mock: long text is chunked; browser voice error is shown and **does not silently start** slow local synthesis; explicit local-voice error path remains available. | Headless tests cannot prove sound reached the user's speakers. Actual browser/Windows voice availability varies. |
| OCR and picture help | Backend document tests and browser picture-help smoke passed. | Tests do not certify math OCR, multilingual OCR, biological diagrams, graph interpretation, or a specific uploaded file. |
| Research demo | Chromium desktop and 375 px mobile mocked-data smoke passed without horizontal overflow. | Mocked charts are not evidence of research-grade results or learner benefit. |
| Backend regressions | `.venv\Scripts\python.exe -m pytest TESTS\test_accounts.py TESTS\test_learner_evidence.py TESTS\test_documents.py TESTS\test_current_fixes.py -q --tb=short`: **63 passed**, 2 warnings. Earlier backend run: **20 passed**. | Not the full test suite or a clinical/educational evaluation. `.venv-check` lacks `onnxruntime`, so it is not a valid environment for the backend tests requiring that package. |

The warnings were a dependency deprecation warning and a deliberate oversized-image test warning. No real learner database was reset, migrated, or edited for this audit.

## Findings, from a learner's point of view

### 1. Read aloud can feel broken or frozen — critical

**Observed in code and tests:** The default browser voice previously fell back to local VITS after an error without asking. A prior measured English local synthesis of one short sentence took about **81 seconds** on this machine; a full passage could require multiple requests. The server's `POST /api/speech 200 OK` does not prove that the browser played the returned WAV. In addition, the main read-aloud status was far below the reading controls.

**Changed now:** Browser voice failures no longer silently switch to the slow model. The result appears next to `Read aloud`; a browser voice that never starts reports an error after 10 seconds, while a started long passage is allowed to finish. `Stop` can release a waiting browser-voice promise. Local voice is still selectable, visibly labeled slower. The browser smoke covers the failure path.

**Still needed:** Test audible English, Hindi, Kannada and Tamil playback on the actual Windows/browser setup, with speakers unmuted. Add a short audio test control and a visible play/pause state. Profile cold-start and per-language local TTS latency before promising it as an accessible fallback. If a browser voice is not installed for a language, say so in the interface rather than implying it will work.

### 2. The profile looks old, but the date is the starting baseline — high

**Observed in screenshot/code:** `Created 16/10/2026` and `Starting survey: Sentence structure; short` are saved, immutable setup choices. The report loads the signed-in account via `/api/account` and `/api/learner/report`; the screenshot alone does **not** demonstrate that another person's details leaked. The alias `h` is not necessarily the login username. Before this change, the page did not show the username or last activity above the fold, making a valid old baseline look stale.

**Changed now:** The report labels the creation date and survey as **starting** information, shows the signed-in username and latest recorded activity, and displays the current preferred language/style separately. The report continues to require explicit sign-in or legacy-key reconnect.

**Still needed:** On the user's machine, open `account.html`, verify the displayed username, then open `my-progress.html` and verify `Signed in as ...`. If wrong, use **Switch user**, not delete profile. Avoid posting recovery keys or account IDs in screenshots.

### 3. “Read this text” had the wrong action label — high

**Observed in code:** The OCR button only moves corrected text into the reading room. It does **not** speak. “Read page with OCR again” reruns extraction, not audio. This can reasonably be interpreted as a broken read-aloud feature.

**Changed now:** The controls say **Open text in reading room** and **Extract text again (OCR)**. The separate `Read aloud` button is in the reading room.

**Still needed:** Consider a direct **Speak corrected page** action next to OCR text, with Stop and visible progress, after validating the main speech path. Do not speak unreviewed OCR automatically; incorrect equations, labels and columns can change meaning.

### 4. Local AI and image explanations are not instant — high

**Observed in code/earlier local timing:** The Qwen text model is a 4B quantized model running locally on CPU; it may generate up to 650 tokens and retry once after failed source checks. Vision loads a separate model and processes images; an earlier picture request took roughly **60–80 seconds**. Local speech and generation share inference resources. Switching between text and vision models can add loading time. The UI has progress text but cannot make CPU inference immediate.

**Still needed:** Keep instant, clearly labeled passage/glossary help as the primary route. Make slower AI explicitly opt-in, cancellable, and timed. Benchmark cold and warm p50/p95 response times for each route and language on target hardware. Do not call a 60-second path “instant.” Online Groq is optional, needs its own consent and API setup, and sends selected content off-device; it should not be enabled silently.

### 5. Screens still demand too much scanning — high

**Observed in CSS/screenshots:** Several sidebar, help-choice, and helper labels use roughly 10–12 px at normal zoom; earlier screenshots showed browser zoom at 67%, making them smaller. The reader uses a sidebar, a support column, an overlay result, and long privacy/explanation text. A fixed result panel may cover context, and details such as source checks and model labels compete with the core answer.

**Recommended:** Put one primary action beside the selected text, keep the source and concise help visible together, move provenance/technical checks behind “More details,” and increase control/label size. Test at 100%, 200% zoom and 390 px width with keyboard only. Do not assume a special font or color universally helps; let learners keep individual settings.

### 6. Adaptation is evidence-based preference routing, not detected dyslexia — high

**Observed in code:** Starting survey, explicit help choices and optional feedback can change per-user category/style estimates. A deliberate request overrides history. Pauses and rereads are explicitly ambiguous, not proof of a difficulty. The report's percentages are internal suggestion weights, **not** reading-skill scores, model accuracy, or clinical measurements. Research charts can show recorded decisions but not educational outcomes without validated data.

**Still needed:** Keep the distinction visible in both reader and lab. For a research paper, collect consented human annotations and learner-centered outcomes, define comparison baselines, and evaluate whether personalized help improves comprehension/time/comfort without claiming diagnosis. Allow users to inspect/correct wrong assumptions.

### 7. OCR/diagram reliability needs separate validation — high

**Observed from supplied screenshots:** A textless shapes image correctly yielded an empty OCR field; OCR cannot explain pictures. Mathematical notation on a university slide was misread, including symbols and language detection. Vision descriptions can be helpful but may misidentify axes, labels, quantities or relations. A generic description of shapes does not demonstrate biology-diagram or physics-graph understanding.

**Still needed:** Build a labeled validation set of textbook pages, diagrams and graphs with expected labels/axes/units/relationships. Measure OCR character/word error and diagram-question correctness separately; show the original beside editable OCR text; require explicit learner review for formulas and graph values. Do not claim correct graph interpretation from a single geometric-shapes example.

### 8. Minor console noise — low

`GET /favicon.ico 404` is cosmetic. `200 OK` for `/api/support` and `/api/speech` confirms HTTP completion only. An old profile date and successful request logs are not proof of stale data or working audio, respectively.

## Safe manual test on the learner's computer

1. Restart the helper, use a private/incognito window if checking account separation, and set browser zoom to **100%**. Keep the original window/profile untouched.
2. Sign in. Confirm the username on `account.html` and the **Signed in as** line on `my-progress.html`. The “starting” date should remain old; the latest activity should update after consented interaction and report refresh.
3. Open a short English practice passage. Select **Fast browser voice** and press **Read aloud**. Check speaker volume and whether sound starts within a few seconds. Press **Stop** midway. If an error appears, note the exact text; do not infer success from server `200 OK`.
4. Explicitly choose **Local voice (slower)** for one short sentence only; time it. Repeat for each language you actually need. Stop if CPU load or latency is unacceptable.
5. Select one word; request quick help. Confirm the original sentence stays visible and the help concerns that exact selection. Try another support type and record whether the answer is useful; do not rely on a generic glossary answer as proof of understanding.
6. Upload a **copy** of a one-page image/PDF. Compare OCR with the original; correct errors before opening it in the reading room. For a diagram, ask a precise question about one region and cross-check labels/axes/units manually.
7. Refresh the report, then sign out and sign in to a *different test account*. Its private history should not show the first account's passages, feedback or report. Do not delete real profiles to test this.
8. Repeat the core flow at 200% zoom, 390 px width, keyboard-only Tab/Enter/Escape, and with a screen reader if one is available. Record where focus, reading position or status is lost.

Record each attempt as: action, browser/OS/language, expected result, actual result, elapsed seconds, screenshot/console error, and whether the response was useful. Use **at least several consenting dyslexic learners** with different preferences before claiming the UX works for that audience. Do not treat this heuristic audit as a substitute for their feedback.

## Reference basis

- [W3C WAI: Cognitive and learning](https://www.w3.org/WAI/people-use-web/abilities-barriers/cognitive/) describes variability, structured content, predictable controls, personalization and text-to-speech.
- [W3C WAI: Help users find what they need](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o2-find/) recommends making important actions easy to locate and using clear hierarchy and chunks. This is supplemental guidance, not a claim that this app meets WCAG.
- [British Dyslexia Association style guide](https://cdn.bdadyslexia.org.uk/uploads/documents/Advice/style-guide/BDA-Style-Guide-2023.pdf) informs the plain-language, layout and text-to-speech recommendations; individual learner choice still takes precedence.
