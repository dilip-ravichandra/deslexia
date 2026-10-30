"""Optional local launcher: open browser only after the app answers a health check."""
import threading
import time
import urllib.request
import webbrowser


def open_when_ready():
    for _ in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open('http://127.0.0.1:8000/account.html')
                    return
        except Exception:
            time.sleep(.5)


if __name__ == '__main__':
    try:
        import uvicorn
    except ImportError:
        raise SystemExit('Install dependencies from BACKEND/requirements.txt first. See RUN_NEW_INTERFACE.md.')
    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run('BACKEND.app:app', host='127.0.0.1', port=8000)
