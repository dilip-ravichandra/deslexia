import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[2] / 'FRONTEND'
state = {'signed_in': False, 'setup_complete': True, 'username': 'previous_user', 'created': None, 'logout_calls': 0}


def handle(route):
    path = urlparse(route.request.url).path
    if path == '/api/account':
        body = {'signed_in': state['signed_in'], 'setup_complete': state['setup_complete'], 'username': state['username'], 'profile_id': 'profile-1'}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
    elif path == '/api/account/signup':
        state['created'] = json.loads(route.request.post_data)
        state['signed_in'] = True
        state['setup_complete'] = False
        body = {'signed_in': True, 'username': state['created']['username'], 'recovery_key': 'c' * 64}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
    elif path == '/api/account/logout':
        state['signed_in'] = False
        state['logout_calls'] += 1
        route.fulfill(status=200, content_type='application/json', body='{"signed_in":false}')
    elif path == '/api/learner/report':
        body = {'profile': {'alias': 'Previous Learner', 'id': 'profile-1', 'created_at': '2026-10-16T12:00:00'}, 'survey': {'difficulties': ['SYNTACTIC'], 'preferred_style': 'short', 'preferred_language': 'en'}, 'metrics': {'sessions': 1, 'support_decisions': 0, 'explicit_requests': {}, 'feedback': {'helped': 0, 'not_helpful': 0}}, 'states': {'en': {'preferred_style': 'steps', 'style_estimates': {'steps': 0.7}}}, 'events': [], 'routes': []}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
    elif path.startswith('/api/'):
        route.fulfill(status=200, content_type='application/json', body='{}')
    elif path == '/':
        route.fulfill(status=200, content_type='text/html', body='<html><body>Reading room</body></html>')
    else:
        file = root / (path.lstrip('/') or 'index.html')
        content_type = 'text/css' if file.suffix == '.css' else 'text/javascript' if file.suffix == '.js' else 'text/html'
        route.fulfill(status=200, content_type=content_type, body=file.read_bytes())


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1100, 'height': 800})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('dialog', lambda dialog: dialog.accept())
    page.route('http://app.test/**', handle)
    page.goto('http://app.test/account.html')
    page.locator('#login-panel').wait_for(state='visible')
    assert page.locator('#create-panel').is_hidden()

    page.evaluate("localStorage.setItem('da_learner_key_v1', 'a'.repeat(64))")
    page.reload()
    page.locator('#login-panel').wait_for(state='visible')
    assert 'Previous Learner' not in page.locator('main').inner_text()
    assert not page.locator('#older-profile').evaluate('(element) => element.open')

    page.locator('#choose-create').click()
    page.locator('#create-panel').wait_for(state='visible')
    page.locator('#create-username').fill('new_reader')
    page.locator('#create-password').fill('long-private-password')
    page.locator('#create-form button[type=submit]').click()
    page.locator('#created-panel').wait_for(state='visible')
    assert state['created']['username'] == 'new_reader'
    assert set(state['created']) == {'username', 'password'}
    assert page.locator('#created-key').inner_text() == 'c' * 64
    assert page.locator('#created-continue').get_attribute('href') == 'profile-setup.html'
    assert page.evaluate("localStorage.getItem('da_learner_key_v1')") is None
    assert page.locator('#created-continue').get_attribute('aria-disabled') == 'true'
    page.locator('#created-confirmed').check()
    assert page.locator('#created-continue').get_attribute('aria-disabled') == 'false'

    state['username'] = 'previous_user'
    page.evaluate("localStorage.setItem('da_learner_key_v1', 'b'.repeat(64))")
    page.reload()
    page.locator('#signed-in').wait_for(state='visible')
    page.locator('#new-user').click()
    page.locator('#create-panel').wait_for(state='visible')
    assert state['logout_calls'] == 1
    assert page.evaluate("localStorage.getItem('da_learner_key_v1')") is None

    page.evaluate("localStorage.setItem('da_learner_key_v1', 'a'.repeat(64))")
    page.reload()
    page.locator('#login-panel').wait_for(state='visible')
    assert 'Previous Learner' not in page.locator('main').inner_text()
    page.goto('http://app.test/my-progress.html')
    page.locator('#missing').wait_for(state='visible')
    assert 'Previous Learner' not in page.locator('main').inner_text()
    page.goto('http://app.test/account.html')
    page.locator('#login-panel').wait_for(state='visible')
    page.locator('#older-profile summary').click()
    page.locator('#check-older').click()
    page.get_by_text('Previous Learner', exact=False).wait_for()
    assert page.locator('#link-form').is_visible()
    assert page.locator('#continue-older').is_visible()
    assert page.locator('#older-key-visible').inner_text() == 'a' * 64
    page.locator('#continue-older').click()
    page.wait_for_url('http://app.test/')
    assert page.evaluate("sessionStorage.getItem('da_legacy_active')") == '1'
    state['signed_in'] = True
    state['setup_complete'] = True
    state['username'] = 'new_reader'
    page.goto('http://app.test/my-progress.html')
    page.locator('#report').wait_for(state='visible')
    assert 'new_reader' in page.locator('#account-name').inner_text()
    assert 'Starting profile saved' in page.locator('#created').inner_text()
    assert 'saved once' in page.locator('#survey').inner_text()
    assert 'steps' in page.locator('#preferences').inner_text()
    assert not errors, errors
    state['signed_in'] = False
    mobile = browser.new_page(viewport={'width': 390, 'height': 844})
    mobile.route('http://app.test/**', handle)
    mobile.goto('http://app.test/account.html')
    mobile.locator('#login-panel').wait_for(state='visible')
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    mobile.locator('#choose-create').click()
    assert mobile.locator('#create-panel').is_visible()
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.close()

print('Separate account and explicit legacy-profile browser flows passed.')
