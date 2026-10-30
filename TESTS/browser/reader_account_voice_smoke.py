import json
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[2] / 'FRONTEND'
state = {'signed_in': False, 'speech_calls': 0, 'seen_keys': [], 'library': {'passages': [], 'notes': []}}


def handle(route):
    path = urlparse(route.request.url).path
    if path.startswith('/api/'):
        if path == '/api/account':
            time.sleep(0.35)
            body = {'signed_in': state['signed_in'], 'profile_id': 'profile-1', 'setup_complete': True}
        elif path.startswith('/api/account/library/'):
            kind = path.rsplit('/', 1)[-1]
            if route.request.method == 'PUT':
                state['library'][kind] = route.request.post_data_json['items']
                body = {'saved': len(state['library'][kind])}
            else:
                body = {'items': state['library'][kind]}
        elif path == '/api/learner/state':
            state['seen_keys'].append(route.request.headers.get('x-learner-key'))
            body = {'enrolled': False}
        elif path == '/api/model-status':
            body = {'services': {}, 'human_routing': {'available': False}}
        elif path == '/api/document-status':
            body = {'ocr_available': False, 'vision_available': False}
        elif path == '/api/speech':
            state['speech_calls'] += 1
            route.fulfill(status=503, content_type='application/json', body='{"detail":"fixture voice unavailable"}')
            return
        else:
            body = {}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        return
    file = root / (path.lstrip('/') or 'index.html')
    if not file.is_file():
        route.fulfill(status=404, body='not found')
        return
    content_type = 'text/css' if file.suffix == '.css' else 'text/javascript' if file.suffix == '.js' else 'text/html'
    route.fulfill(status=200, content_type=content_type, body=file.read_bytes())


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('http://127.0.0.1:8099/**', handle)
    page.goto('http://127.0.0.1:8099/?guest=1')
    page.wait_for_function("!!window.LEARNER && document.querySelector('#connection').textContent !== 'Connecting'")
    assert page.locator('#read-extracted').inner_text() == 'Open text in reading room →'
    assert page.locator('#document-reocr').inner_text() == 'Extract text again (OCR)'
    assert page.locator('label[for="survey-consent"]').get_attribute('class') == 'checkbox'
    assert page.locator('#survey-consent').get_attribute('type') == 'checkbox'
    page.locator('#account-entry').wait_for(state='visible')
    assert page.locator('#account-entry a[href="account.html"]').is_visible()
    page.locator('#voice-source').select_option('local')
    page.locator('#speak').click()
    page.wait_for_function("document.querySelector('#learner-live-status').textContent.includes('Offline speech unavailable')")
    assert state['speech_calls'] > 0
    page.evaluate('window.LEARNER.stopSpeech()')

    previous_speech_calls = state['speech_calls']
    page.locator('#voice-source').select_option('browser')
    page.evaluate("speechSynthesis.speak = utterance => setTimeout(() => utterance?.onerror?.(), 0)")
    page.locator('#speak').click()
    page.get_by_text('Browser voice could not play. Check your device audio or choose Local voice (slower).').first.wait_for()
    assert state['speech_calls'] == previous_speech_calls
    assert page.locator('#speak').is_enabled()

    long_text = 'x' * 400 + ' y'
    page.evaluate("text => { window.__spoken = []; speechSynthesis.speak = utterance => { window.__spoken.push(utterance.text); setTimeout(() => utterance.onend?.(), 0); }; window.WORKSPACE.openText(text, 'Long speech test'); }", long_text)
    page.locator('#voice-source').select_option('browser')
    page.locator('#speak').click()
    page.wait_for_function("document.querySelector('#learner-live-status').textContent.includes('Read aloud finished')")
    assert ''.join(page.evaluate('window.__spoken')) == long_text

    state['signed_in'] = True
    page.evaluate("localStorage.setItem('da_look_v1', JSON.stringify({bg:'dark'})); localStorage.setItem('da_passages_v2:profile-1', JSON.stringify([{id:'saved-1',title:'My reading',text:'A saved sentence',created_at:new Date().toISOString()}]))")
    page.reload()
    page.wait_for_function("document.querySelector('#library-count').textContent === '1'")
    assert state['library']['passages'][0]['title'] == 'My reading'
    assert page.locator('#account-entry').is_hidden()
    assert page.evaluate('DA.look().bg') == 'cream'

    state['signed_in'] = False
    page.evaluate("sessionStorage.setItem('da_guest_mode', '1'); localStorage.setItem('da_passages_v2', JSON.stringify([{id:'old-1',title:'Previous profile text',text:'Private passage'}]))")
    page.reload()
    page.locator('#account-entry').wait_for(state='visible')
    assert page.locator('#library-count').inner_text() == '0'
    assert page.evaluate('DA.look().bg') == 'cream'
    page.evaluate("sessionStorage.removeItem('da_guest_mode'); localStorage.setItem('da_learner_key_v1', 'a'.repeat(64))")
    page.goto('http://127.0.0.1:8099/')
    page.wait_for_url('http://127.0.0.1:8099/account.html')
    page.goto('http://127.0.0.1:8099/?guest=1')
    page.locator('#account-entry').wait_for(state='visible')
    assert page.locator('#library-count').inner_text() == '0'
    assert state['seen_keys'][-1] is None
    page.evaluate("sessionStorage.setItem('da_legacy_active', '1')")
    page.reload()
    page.wait_for_function("document.querySelector('#library-count').textContent === '1'")
    assert state['seen_keys'][-1] == 'a' * 64
    assert not errors, errors
    browser.close()

print('Reader account storage and local-voice handler smoke passed.')
