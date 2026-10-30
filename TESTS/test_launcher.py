import launch_interface


def test_launcher_opens_local_sign_in_first(monkeypatch):
    opened = []

    class HealthResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *unused):
            return None

    monkeypatch.setattr(launch_interface.urllib.request, 'urlopen', lambda *_args, **_kwargs: HealthResponse())
    monkeypatch.setattr(launch_interface.webbrowser, 'open', opened.append)

    launch_interface.open_when_ready()

    assert opened == ['http://127.0.0.1:8000/account.html']
