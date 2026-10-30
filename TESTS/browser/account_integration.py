"""Exercise real local accounts in a browser against an isolated helper database."""
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import BACKEND.app as backend
from BACKEND.accounts import AccountStore
from BACKEND.adaptive import AdaptiveService
from BACKEND.learner import LearnerModel


with tempfile.TemporaryDirectory(prefix='dyslexiadapt-accounts-') as temporary:
    service = AdaptiveService(Path(temporary))
    backend.adaptive = service
    backend.learner = LearnerModel(service.db_path)
    backend.accounts = AccountStore(service.db_path)
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    server = uvicorn.Server(uvicorn.Config(backend.app, host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        raise RuntimeError('Isolated account helper did not start.')
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('dialog', lambda dialog: dialog.accept())
            page.goto(base + '/account.html')

            def create(username, alias):
                page.locator('#choose-create').click()
                page.locator('#create-username').fill(username)
                page.locator('#create-password').fill('private-password-123')
                page.locator('#create-form button[type=submit]').click()
                page.locator('#created-panel').wait_for(state='visible')
                recovery_key = page.locator('#created-key').inner_text()
                assert page.request.get(base + '/api/account').json()['setup_complete'] is False
                page.goto(base + '/profile-setup.html')
                page.locator('#setup-panel').wait_for(state='visible')
                page.locator('#alias').fill(alias)
                page.locator('#consent').check()
                page.locator('#save').click()
                page.wait_for_url(base + '/')
                assert page.request.get(base + '/api/account').json()['setup_complete'] is True
                return recovery_key

            first_key = create('first_reader', 'First Reader')
            page.wait_for_load_state('networkidle', timeout=30000)
            page.wait_for_function('window.LEARNER?.session()')
            first_session_id = page.evaluate('window.LEARNER.session()')
            first_profile = page.request.get(base + '/api/learner/report').json()
            assert first_profile['metrics']['sessions'] >= 1
            support = page.request.post(base + '/api/support', data={
                'text': 'A catalyst helps a reaction.', 'span': 'catalyst',
                'category_override': 'VOCABULARY', 'support_style': 'steps',
                'document_language': 'en', 'session_id': first_session_id,
                'request_id': 'first-reader-help-001',
            })
            assert support.ok, support.text()
            route_id = support.json()['trace_id']
            assert page.request.post(base + '/api/learner/event', data={
                'client_id': 'first-reader-feedback-001', 'session_id': first_session_id,
                'language': 'en', 'kind': 'optional_feedback',
                'payload': {'route_id': route_id, 'decision': 'accept'},
            }).ok

            page.goto(base + '/account.html')
            page.locator('#signed-in').wait_for(state='visible')
            page.evaluate("key => localStorage.setItem('da_learner_key_v1', key)", first_key)
            page.locator('#new-user').click()
            page.locator('#create-panel').wait_for(state='visible')
            second_key = create('second_reader', 'Second Reader')
            assert second_key != first_key
            assert page.evaluate("localStorage.getItem('da_learner_key_v1')") is None
            second_report = page.request.get(base + '/api/learner/report').json()
            assert second_report['profile']['alias'] == 'Second Reader'
            assert second_report['profile']['id'] != first_profile['profile']['id']
            assert all(session['profile_id'] == second_report['profile']['id'] for session in second_report['sessions'])
            assert second_report['metrics']['support_decisions'] == 0

            page.goto(base + '/account.html')
            page.locator('#switch-account').click()
            page.locator('#login-panel').wait_for(state='visible')
            page.locator('#login-username').fill('first_reader')
            page.locator('#login-password').fill('private-password-123')
            page.locator('#login-form button[type=submit]').click()
            page.wait_for_url(base + '/')
            page.wait_for_load_state('networkidle', timeout=30000)
            page.wait_for_function('window.LEARNER?.session()')
            return_session_id = page.evaluate('window.LEARNER.session()')
            first_report = page.request.get(base + '/api/learner/report').json()
            assert first_report['profile']['alias'] == 'First Reader'
            assert first_report['metrics']['sessions'] >= 1
            assert first_report['metrics']['feedback']['helped'] == 1
            suggested = page.request.post(base + '/api/support', data={
                'text': 'A catalyst helps a reaction.', 'span': 'catalyst',
                'category_override': 'VOCABULARY', 'support_style': 'auto',
                'document_language': 'en', 'session_id': return_session_id,
                'request_id': 'first-reader-return-001',
            })
            assert suggested.ok, suggested.text()
            assert suggested.json()['routing']['style'] == 'steps'
            assert suggested.json()['routing']['decision_factors']['style_feedback_count'] == 1
            page.wait_for_load_state('networkidle', timeout=30000)
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)

print('Real browser to local account API to isolated database flow passed.')
