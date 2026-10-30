# DyslexiAdapt reading workspace

Serve via the existing FastAPI app: `python -m uvicorn BACKEND.app:app --port 8000`.
Open http://127.0.0.1:8000. See `RUN_NEW_INTERFACE.md` for Windows setup.

`index.html` contains the learner application and API integration; `workspace.css` contains the responsive design system. `PREVIEW.html` is a self-contained copy for inspecting the interface without a server. It does not provide offline model support. Regenerate it after changing the main HTML/CSS with `python FRONTEND/build_preview.py`.

## Learner views
- Reading room: exact selected-span assistance, original/adapted comparison, accept/reject/regenerate, undo, plain-text import/export, paragraph focus, browser read aloud, manual read marker.
- Library: explicit browser-local passage saving, search, reopen/delete and original practice passages.
- Notebook: write/save/delete personal notes, capture actual support responses and export notes as text.
- Reading comfort: colour, contrast, size, line/letter spacing, system-font family, reading column, paragraph focus and pointer reading guide. Preferences are presentation only and never sent to classification.
- How it works: introductory guide, storage explanation and actual implementation status.

## Research tools
`research.html` still reads actual backend artifacts and displays empty states when results do not exist. `adjudication.html` remains the browser-local human conflict review tool. `research-shell.css` applies consistent presentation to both.

No new paid APIs or remote font dependencies. Browser speech availability and whether voices use the network depend on the browser/OS. The demo helper is explicitly labelled; no trained classifier, research scores or independent annotations have been invented.

## Verification
The jsdom/API suite covers exact selection, repeated sentences, long-document request offsets, stale responses, visual preference independence, saved passage lifecycle, notebook injection safety, comfortable settings, speech fallback, and existing research tools. This is functional DOM/API verification; actual browser layout, assistive technology and speech engines need separate checks.

## Adaptive continuation
`adaptive-controls.js` adds opt-in support style persistence. `learning.html` provides actual admin review, candidate training, validation, activation and rollback. Contextual supplementary explanations are separate from in-place rewrites. See RUN_ADAPTIVE.md.
