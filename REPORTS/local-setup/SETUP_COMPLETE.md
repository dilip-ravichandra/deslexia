**Local model setup completed — 16 October 2026**

All requested pinned model assets are downloaded and verified by the normal multilingual setup, including the optional vision model and its projector. `MODELS/multilingual-verified.json` records successful completion. Python 3.12.10 is in `.venv`; `pip check` reports no broken requirements.

Ready services: Qwen3 text generation, multilingual DistilBERT backbone, semantic checks, English/Hindi/Kannada/Tamil speech, native Tesseract OCR and Qwen vision. No human-reviewed routing classifier was manufactured or activated; the trained routing experiment still requires actual reviewed data.

Fresh engineering checks:

- A real local English text explanation completed with source-linked claims and automated screening. See `text-runtime.json` (47.48 seconds for this cold-start case).
- All four speech models produced nonempty 16-kHz WAV output. See `speech-runtime.json` and `speech-en.wav`, `speech-hi.wav`, `speech-kn.wav`, `speech-ta.wav`.
- Document tests: **19 passed**, including actual image/scanned-PDF OCR and embedded-PDF extraction. See `document-tests.txt`. The initial missing test-fixture dependency is retained in `document-tests-initial.txt`; reportlab was installed and the checks rerun.
- Real local vision inference loaded the downloaded weights and identified the authored red triangle as a red triangle. See `vision-runtime.json` and `vision-fixture.png` (126.42 seconds for this cold-start case).

These are runtime smoke cases, not estimates of native-language quality, broad visual reasoning, student benefit or research accuracy. Picture explanations remain explicitly unverified. The first CPU inference can take a minute or longer.

The setup encountered connection failures and certificate-chain issues. Completion used the existing Windows trusted root certificates plus certifi, with TLS validation enabled, and standard HTTPS range downloads. Each entire vision file was checked against its original pinned SHA-256 before installation. The source models, revisions, hashes and licenses were not changed. Temporary download helpers and their progress metadata are under `.audit-tmp`/the local model directory; completed assets are retained for future starts.

The reader was started locally at http://127.0.0.1:8000/ . Refresh the page after setup to update service status. The evidence lab is `/learner-lab.html`; independent review is `/human-review.html`.

For later starts, use `START_DYSLEXIADAPT.bat`. The background test server's logs and launcher PID are in this report directory (`app-stdout.log`, `app-stderr.log`, `app.pid`). Avoid launching a second copy while port 8000 is already occupied.
