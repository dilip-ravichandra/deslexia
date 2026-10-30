"""Capture reproducible guide images from an isolated engineering demo profile."""
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
import shutil

import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
IMAGES = ROOT / "GUIDE_IMAGES"
IMAGES.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix="dyslexiadapt-guide-") as temporary:
    temporary_root = Path(temporary)
    (temporary_root / "DATA").mkdir()
    shutil.copyfile(ROOT / "DATA/public_sources.json", temporary_root / "DATA/public_sources.json")

    import BACKEND.app as backend
    from BACKEND.adaptive import AdaptiveService
    from BACKEND.learner import LearnerModel

    backend.adaptive = AdaptiveService(temporary_root)
    backend.learner = LearnerModel(backend.adaptive.db_path)
    backend.ROOT = temporary_root

    with socket.socket() as socket_handle:
        socket_handle.bind(("127.0.0.1", 0))
        port = socket_handle.getsockname()[1]

    server = uvicorn.Server(uvicorn.Config(backend.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        raise RuntimeError("The isolated screenshot server did not start.")

    base = f"http://127.0.0.1:{port}"
    errors = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base, wait_until="domcontentloaded")
            expect(page.locator("#survey-panel")).to_be_visible()
            page.locator("#survey-alias").fill("Guide demo — test profile")
            page.locator('input[name="survey-need"][value="VOCABULARY"]').check()
            page.locator('input[name="survey-need"][value="CONCEPTUAL"]').check()
            page.locator('input[name="survey-need"][value="PRONUNCIATION"]').check()
            page.locator("#survey-consent").check()
            page.locator("#survey-panel").screenshot(path=str(IMAGES / "01_starting_profile.png"))

            page.locator("#survey-save").click()
            expect(page.locator("#survey-panel")).to_be_hidden(timeout=15000)
            page.locator("#reader-area").screenshot(path=str(IMAGES / "02_reading_room.png"))

            page.evaluate("""() => {
                const start = DA.S.text.indexOf("photosynthesis");
                DA.setSelection({span:"photosynthesis",start});
            }""")
            page.locator("#m-c").check()
            page.locator("#go").click()
            expect(page.locator("#result")).to_contain_text("Quick help", timeout=15000)
            page.locator("#reader-area").screenshot(path=str(IMAGES / "03_quick_help.png"))

            page.evaluate("""() => {
                const start = DA.S.text.indexOf("catalyst");
                DA.setSelection({span:"catalyst",start});
            }""")
            page.locator("#m-v").check()
            page.locator("#go").click()
            expect(page.locator("#result")).to_contain_text("catalyst", timeout=15000)
            page.evaluate("""() => {
                const start = DA.S.text.indexOf("catalyst");
                DA.setSelection({span:"catalyst",start});
            }""")
            page.locator("#m-p").check()
            page.locator("#go").click()
            expect(page.locator("#result")).to_contain_text("Listen to selected text", timeout=15000)
            page.locator("#reader-area").screenshot(path=str(IMAGES / "04_pronunciation_help.png"))

            page.locator('[data-view="comfort-view"]').click()
            expect(page.locator("#comfort-view")).to_be_visible()
            page.locator("#comfort-view").screenshot(path=str(IMAGES / "05_reading_comfort.png"))
            page.locator('[data-view="reader-view"]').click()

            page.locator("#document-file").set_input_files(str(ROOT / "TESTS/fixtures/documents/Two_Page_Textbook.pdf"))
            page.wait_for_function(
                "document.querySelector('#document-status').textContent.includes('ready. Check')",
                timeout=90000,
            )
            page.locator("#document-workspace").screenshot(path=str(IMAGES / "06_pdf_extraction.png"))

            profile = context.new_page()
            profile.on("pageerror", lambda error: errors.append(str(error)))
            profile.goto(base + "/my-progress.html")
            expect(profile.locator("#alias")).to_contain_text("Guide demo", timeout=15000)
            profile.locator("#report .profile-card").screenshot(path=str(IMAGES / "07_saved_profile.png"))
            profile.locator("#metrics").screenshot(path=str(IMAGES / "08_profile_counts.png"))
            profile.locator("#report .two").nth(1).screenshot(path=str(IMAGES / "09_profile_history.png"))

            lab = context.new_page()
            lab.on("pageerror", lambda error: errors.append(str(error)))
            lab.goto(base + "/research-demo.html")
            expect(lab.locator("#name")).to_contain_text("Guide demo", timeout=15000)
            lab.screenshot(path=str(IMAGES / "10_live_lab_overview.png"))
            lab.locator("#before-after").screenshot(path=str(IMAGES / "11_evidence_change.png"))
            lab.locator("#shown").screenshot(path=str(IMAGES / "12_support_shown.png"))

            advanced = context.new_page()
            advanced.on("pageerror", lambda error: errors.append(str(error)))
            advanced.goto(base + "/learner-lab.html")
            expect(advanced.locator("#survey")).to_contain_text("Study languages", timeout=15000)
            advanced.screenshot(path=str(IMAGES / "13_advanced_lab.png"))

            mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            mobile_page = mobile.new_page()
            mobile_page.goto(base + "/research-demo.html")
            expect(mobile_page.locator("#name")).to_contain_text("Guide demo", timeout=15000)
            mobile_page.screenshot(path=str(IMAGES / "14_mobile_lab.png"))
            mobile.close()
            if errors:
                raise RuntimeError("Browser errors: " + "; ".join(errors))
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)

print(f"Captured {len(list(IMAGES.glob('*.png')))} screenshots in {IMAGES}")
