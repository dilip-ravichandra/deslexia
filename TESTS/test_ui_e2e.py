"""Runs the jsdom end-to-end UI checks against a live backend. Skips if node/jsdom/uvicorn are unavailable."""
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

UI = Path(__file__).resolve().parent / "ui"
ROOT = UI.parents[1]


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.skipif(not (UI / "node_modules" / "jsdom").exists(), reason="run `npm install` in TESTS/ui")
def test_ui_end_to_end():
    pytest.importorskip("uvicorn")
    port = _free_port()
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "BACKEND.app:app", "--port", str(port), "--log-level", "warning"],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); break
            except Exception:
                time.sleep(0.5)
        else:
            pytest.fail("backend did not start")
        r = subprocess.run(["node", "--test", "--test-reporter=tap", "ui_e2e.test.js"], cwd=UI, capture_output=True, text=True, timeout=180,
                           env={**os.environ, "BASE": f"http://127.0.0.1:{port}"})
        assert r.returncode == 0, r.stdout + r.stderr[-2000:]
        assert "# fail 0" in r.stdout
    finally:
        srv.terminate(); srv.wait(timeout=10)
