# Open your new DyslexiAdapt interface

1. Extract this ZIP into a NEW folder. Do not mix it with the older project.
2. Open the folder that contains BACKEND, FRONTEND, and this guide in VS Code.
3. Choose Terminal > New Terminal.
4. If your virtual environment already exists in this new folder, skip setup below. A virtual environment in the old extracted folder does not carry over automatically.

## First-time setup (Windows PowerShell)
Run one command at a time:

    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r BACKEND\requirements.txt

## Start the actual app

    .\.venv\Scripts\python.exe -m uvicorn BACKEND.app:app --port 8000

Open http://127.0.0.1:8000 in your browser.
If you still see the old design, stop the server in the old folder with Ctrl+C, start from this folder, and refresh with Ctrl+F5. If port 8000 is already in use, stop the old server or use --port 8001 and open http://127.0.0.1:8001.

After setup, you can also double-click START_DYSLEXIADAPT.bat. It starts the app and opens the browser when the local server is ready.

## Just look at the design, without setup
Double-click FRONTEND/PREVIEW.html. This self-contained preview includes styles and local interface features. The support helper and Research Lab require the running backend; they do not work in a standalone file preview.

## Your new interface
- Reading room: paste text, import a .txt file, select difficult text, choose support, compare suggestions, accept/reject/regenerate, undo, and export the current text.
- Library: explicitly save passages, search, reopen, delete, and open three original practice passages.
- Notebook: write notes, save actual support results, delete notes, and export a plain text notebook.
- Reading comfort: seven page colours, three contrast levels, four system-font choices, size, line and letter spacing, paragraph focus, pointer reading guide, and reading column width.
- Read aloud: uses your browser's available speech voices, with pause/resume, stop and speed controls. Some browsers/platforms may use network-backed voices. The app does not call a paid speech API.
- How it works: short instructions and direct access to the research and annotation-review tools.
- Responsive layout and keyboard controls; reduced-motion and print styles.

No paid model, endpoint, font subscription, or API has been added. System fonts are used. Notes and passages stay in this browser unless you export them. Reading preferences are saved locally. Selected text and nearby context go to the local support backend when you request help.

## What is still practice mode?
This frontend does not create a trained classifier or research results. The existing backend still uses demo rules and a small demonstration lexicon unless you load a validated trained model. Conceptual support currently offers guiding questions rather than generated explanations. Meaning checks are fallible.

The DOM/API regression checks passed. Actual browser rendering, browser speech voices and assistive-technology behaviour were not verified in this environment. No dyslexia user study has been conducted.

The earlier five-example annotation starter is included in EXTRAS/DyslexiAdapt_Annotation_Starter.zip. Its AI-suggested practice labels are not a gold dataset.

Research Lab upgrade: open http://127.0.0.1:8000/research.html for evaluation evidence, local training command preparation, research-note export, and the controlled learning guide. Automatic retraining is not enabled. Read RESEARCH/CONTROLLED_LEARNING.md before collecting feedback or selecting a new model.

The admin Research Lab now has the requested dark teal/violet dashboard style. For an offline look, open FRONTEND/RESEARCH_PREVIEW.html. Its snapshot reflects the current empty research artifacts; use research.html through the backend for live data.
