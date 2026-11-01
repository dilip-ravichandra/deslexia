# Run the multilingual research build

Use Python 3.11 or 3.12. Extract the ZIP before running commands. Open a terminal inside its project folder.

The pinned RapidOCR package requires Python below 3.13. If the launcher only lists Python 3.13, install Python 3.12 first. Keep this project in its own virtual environment. `BACKEND/requirements-research.txt` includes the neural runtime dependencies as well as document and API packages. Run `.venv\Scripts\python -m pip check` after installation. `/api/model-status` reports missing files/packages and direct dependency mismatches per service; it never initiates a download.

Independent manual review is at `/human-review.html`; collection and merge instructions are in `HUMAN_REVIEW_GUIDE.md`. The older `/learning.html` is explicitly legacy prototype operations.

## Windows

```powershell
py -3.12 -m venv .venv
```

On an NVIDIA Windows PC, install the CUDA-enabled PyTorch build so training can use the GPU:

```powershell
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
```

On a CPU-only Windows PC, use:

```powershell
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then continue with:

```powershell
.venv\Scripts\python -m pip install -r BACKEND/requirements-research.txt
.venv\Scripts\python -m ML.multilingual_setup --vision
.venv\Scripts\python launch_interface.py
```

`SETUP_RESEARCH_WINDOWS.bat` detects `nvidia-smi` and selects the CUDA 12.8
wheel automatically when an NVIDIA GPU is present. Verify the result with:

```powershell
.venv\Scripts\python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

For Windows with winget, install the verified community package with `winget install --id UB-Mannheim.TesseractOCR --exact --source winget`. Its package identifier and Apache-2.0 declaration are recorded in the Microsoft winget repository: https://github.com/microsoft/winget-pkgs/tree/master/manifests/u/UB-Mannheim/TesseractOCR . Install the native Tesseract executable and add its folder to PATH (or set TESSERACT_CMD to its full executable path). Language weights are downloaded and checked by multilingual_setup. Without the executable the app uses RapidOCR, which performed worse on the Indic engineering fixtures. Never accept extracted textbook text without checking it.

If llama-cpp-python tries compiling and you lack a compiler, use the maintainer's CPU wheel index:

```powershell
.venv\Scripts\python -m pip install llama-cpp-python==0.3.36 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r BACKEND/requirements-research.txt
.venv/bin/python -m ML.multilingual_setup --vision
.venv/bin/python launch_interface.py
```

Install Tesseract using your operating system's package manager. Open http://127.0.0.1:8000. Keep the terminal running. First-time model downloads require internet and several GB of disk space. Subsequent inference is local. CPU explanations can be slow; a four-language model-quality study is still required.

English **Help me understand** now shows quick passage/glossary help without loading Qwen. If the local model is installed, **Get deeper AI help (slower)** runs it on request; the quick answer remains visible while it works. The first AI request loads Qwen; source checks can require a second draft and meaning check. Hindi, Kannada and Tamil explanations still use the local model and may take longer. To disable all text generation, restart from PowerShell with `$env:DYSLEXIADAPT_GENERATION='off'; .\START_DYSLEXIADAPT.bat`. This also disables generated explanations in Hindi, Kannada and Tamil; speech and pronunciation buttons remain separate.

## Try the actual learner loop

On Windows, `START_WINDOWS.bat` opens `http://127.0.0.1:8000/account.html`. Choose **Sign in**, **Create account**, or **Read as guest**. New signup makes a separate account first; after saving the one-time recovery key, finish the separate profile-setup screen to choose a consented reading baseline. The next login reuses this saved profile. **Sign out** in the reader or **Switch account** on the account page ends the current session without deleting the profile. An older browser-only profile stays disconnected until you explicitly reconnect it. Opening the reader directly without signing in now takes you to the account page; guest reading requires an explicit choice.

1. After new signup, complete **Profile setup** and consent. Existing accounts sign in to their saved setup; guests can read without a saved profile.
2. Choose English, Hindi, Kannada or Tamil as the document language. Select the language you want explanations in.
3. Upload a PDF/photo or paste text. Check OCR text, then choose **Read this text**.
4. Select a word/phrase. Right-click for quick help, or use the side support choices for meaning, sentence, concept, pronunciation or reading comfort. Help opens in a closable panel without moving you away from the passage. Your current choice always overrides the history.
   **Untangle a sentence** uses the selected sentence's own clauses for quick help when it finds a safe split. A full sentence without a safe split is identified as complete; it is not sent through the word-meaning fallback. This quick view does not generate a paraphrase.
   **Read aloud** uses the browser voice by default for a faster start. If your browser voice is unavailable or does not support the selected language, choose **Local voice (slower)**; its first request may take about a minute on a CPU. **Stop** cancels reading.
5. Finish the session; open another passage and repeat. Repeated relevant support choices can influence the next suggestion. Pauses and rereading are recorded as ambiguous observations, never automatic difficulty labels.
6. Open **My progress and profile** to return to your saved survey and interaction report. The account page offers direct new-account creation; it shows a one-time recovery key to save privately. If you already have an older recovery-key profile, expand **Have an older profile or recovery key?** and choose to link it explicitly. Use **Switch account** before another person reads. After restarting the helper, sign in again. If you forget your password, use **Reset an account password** with your recovery key. There is no email recovery or internet account.
7. Open **Research lab** at http://127.0.0.1:8000/research-demo.html to watch a real learner's survey, choices, evidence update and next decision. It also shows request counts across all consented local readers and a visual path explaining the latest recommendation. Leave the reader open in another tab; the lab refreshes automatically. Open **Methods, installation status and advanced tools** for an on-demand check of installed models, dependencies and pinned public dataset files. File verification is not evidence that a model is accurate or trained for support routing. Interaction counts and preference estimates are not model accuracy or comprehension scores. **Advanced research tools** retain the separate human-data evaluations. The supplied paper's research-to-app plan is `RESEARCH/APP_AND_PAPER_PLAN.md`.

For a visible paragraph demo, paste a paragraph and click **Adapt this paragraph**. The original and supported view appear together. **Follow my profile** uses repeated saved requests for words or phrases in that paragraph, or a single starting survey need; otherwise it starts with sentence spacing. Change **Help type** or **Supported view style** to override the suggestion. Word notes come from the small English demo glossary; idea questions are reading prompts. This view keeps the original words and order and does not claim that a rewritten paragraph preserves meaning. Select source words in the supported view and click **Ask about selected words** for more specific help. Paragraph requests do not add learner evidence by themselves.

**Make an easier version** is a separate optional English-only action. It compares each original sentence with a conservative rule-based change, highlights every difference, and keeps the original visible. If a protected relationship word changes or an automatic check raises a flag, that sentence stays original. The currently bundled glossary is a demo resource, and the checks are uncalibrated; passing them does not prove semantic equivalence. Use **Back to original** at any time. Other languages currently keep their original wording.
The **Help type** controls which wording changes are attempted; **Supported view style** applies to the non-rewrite paragraph view.

To see a visible change, paste `The object accelerated. The result was approximately 10 units.`, select **Word help**, then click **Make an easier version**. The changed words are highlighted beside the original. Choose **Sentence help** for a conservative sentence split such as `The trial ran for three days; the result was clear.`

8. Use **Forget my support history** or **Delete this profile and its history** to remove the consented profile, session events and decisions.

Optional online explanations are off unless the helper process has `GROQ_API_KEY`. On Windows PowerShell, set `$env:GROQ_API_KEY='your-key'` in the same terminal before running `.\START_WINDOWS.bat`; never put it in frontend files or commit it. The reader then offers **Try online AI for this sentence** after quick help. Each click asks permission and sends only the selected span, its sentence (up to 1,200 characters), chosen help type/style, and target language—not the account name, full document, or interaction history. A failed source screen withholds the online draft and keeps local help. These finite checks do not prove correctness. Groq may apply rate limits and temporary reliability/abuse retention; read its [rate limits](https://console.groq.com/docs/rate-limits) and [data controls](https://console.groq.com/docs/your-data) before enabling the feature. Do not use online AI for private learner material without informed permission.

The profile, account, signed-in saved passages, and notebook entries are stored in `ARTIFACTS/learner_state.sqlite3` under this project folder; it is not uploaded or committed to Git. Stop the helper before copying that file to back up or move the project, and keep the private recovery key separately. Passwords protect encrypted recovery keys in the database; sessions expire after 12 hours and are cleared on server restart. Guest passages and notes remain in that browser only. Earlier account-scoped browser libraries are imported into SQLite on the next signed-in reader visit; use the account page's explicit import action for older unscoped browser libraries. `127.0.0.1` and `localhost` have different browser storage, so use the same address to import older browser data. A profile nickname is not an account password. Lost passwords cannot be reset without the original recovery key. These localhost accounts are not designed for public hosting or untrusted shared computers; the research/admin view can inspect consented local profiles.

## Real experiments

The included public data contain human lexical ratings, simplification references and reading-level texts. They do not supply the project's vocabulary/syntax/concept routing labels.

```bash
python -m ML.public_experiment --max-train 512 --epochs 2
```

This runs TF-IDF, actual multilingual DistilBERT with LoRA and the matched model with linguistic features on English **lexical regression**, with the same frozen source partitions. It is supplementary evidence, not a completed three-category routing comparison.

For the agreed routing comparison, import a genuinely human-reviewed CSV in Research lab, preserving unresolved rows. The lab validates, saves and hashes the original file, excludes unresolved rows only from supervised training, freezes document-group splits and runs the three agreed arms. Human provenance is reviewer-declared; the software cannot authenticate who wrote an annotation. No GPT pilot annotations are promoted to human gold.

The learner evidence model updates online after consented interactions. Global neural weights change only during a separately recorded training job. Neither process establishes improved comprehension without a learner study.

For non-local deployment, set DYSLEXIADAPT_ADMIN_TOKEN before starting and use that token in the lab. Default server binds to localhost; do not expose it as a public service without authentication, HTTPS and a proper privacy/retention design.

Speech weights use CC BY-NC 4.0. The optional vision model uses the original Qwen research license. These research components do not provide unrestricted commercial rights. See DATA/public_sources.json and MODELS manifests for exact sources and hashes.

For a CPU machine, start with the bundled 512-row experiment before a full run. A machine with 16 GB or more RAM is preferable for model training and local generative services. Run heavy training and explanation-quality checks sequentially on smaller machines. The reader serializes its heavy services and unloads the text model before picture inference (and vice versa); this reduces peak memory but adds loading time when switching services.
