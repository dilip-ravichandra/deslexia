# Reading workspace redesign

The learner interface has been replaced with a responsive sage-and-cream workspace. The reading area remains the focal point; additional tools live in separate library, notebook, comfort and guide views.

## Implemented
- Original practice passages; custom paste and .txt import; current-text export.
- Exact span support through the existing API; suggestions, original/adapted comparison, accept/reject/regenerate and undo.
- Request revision/selection guards prevent an old response appearing after the selection changes.
- API window offsets are translated back to the full passage before accepting a change.
- Repeated-word selection updates the occurrence, with first/last keyboard selection controls.
- Explicit browser-local passage saving, library search/open/delete.
- Browser-local notes, response capture, delete and text export; untrusted content is rendered as text.
- Seven reading colours, three contrasts, four system font families; size, line spacing, letter spacing and reading width.
- Paragraph focus with pointer and keyboard activation; optional pointer reading guide.
- Browser speech with pause/resume/stop/rate and unavailable/error states.
- Responsive navigation, keyboard focus, skip link, live announcements, reduced motion and print styles.
- Styled Research Lab and existing adjudication tool; no placeholder scientific scores.
- Self-contained visual preview, preview rebuild utility, Windows launcher and user-facing setup guide.
- Earlier annotation starter included under EXTRAS.

## Design and state
Plain HTML/CSS/JavaScript extends the existing FastAPI-served application, avoiding a new framework or build dependency. No chart is needed because there are no real quantitative learner results to plot. Neutral warm surfaces, a sage focal accent and explicit selected/focus states keep the reading task clear. Mobile uses a compact navigation row and stacks support below the text. Reading presentation preferences persist locally; passage/note content persists only when explicitly saved. URL hashes represent the selected workspace view.

## Verification limits
Automated DOM/API checks validate behaviour and text-colour contrast combinations; static checks verify IDs, labels, script syntax and preview embedding. Actual browser layout, speech voices, touch selection, screen readers and participant comfort were not tested in this environment. This is not a WCAG certification or a dyslexia user-study result.

The backend remains in practice mode until a validated research model is available. Conceptual support remains a guiding-question scaffold. This frontend change does not provide gold labels or model results.

## Final checks
152 Python-suite tests passed in 120.13 seconds, including the runner for 22 jsdom/API interface checks. QA audit: 43 pass, zero warnings and zero failures. JavaScript syntax verified for both the actual application and standalone preview. UI test startup now waits for real application readiness instead of a fixed delay.
