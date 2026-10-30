# Task Report — 12 Learner UI
## Files
FRONTEND/index.html (rewritten), TESTS/ui/ui_e2e.test.js + package.json, TESTS/test_ui_e2e.py.
## Features
Paste text, select a word/sentence (mouse, touch, or a typed fallback), choose support type or let the helper suggest, side-by-side original vs easier version with changed words highlighted, accept (replaces the sentence in the text, with undo), reject, try another way, optional comfort rating, plain-language verification notes, hidden unsafe output, calm wording, practice-mode notice, no-diagnosis disclaimer.
Visual settings (separate layer, saved only in the browser, never sent to the API): 7 backgrounds, 3 contrast levels, text size, line spacing, letter spacing, 4 font options, focus mode, reset. All 21 background x contrast combinations meet WCAG 4.5:1 (tested).
## Tests
10 jsdom end-to-end checks against a live backend (request contains only text fields after changing every visual setting; accept/undo; override; regenerate; typed fallback; labels/aria-live; Research Lab empty states).
## Limitations
Tested in jsdom only: not in real browsers, on phones, with a screen reader, or with dyslexic readers. Text selection with touch and keyboard, focus mode, and font choices need real-device checks. No claim is made that any setting or font helps; no user study has been run (HG-02).
