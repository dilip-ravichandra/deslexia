import base64
import io
import json
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[2] / 'FRONTEND'
picture = io.BytesIO()
Image.new('RGB', (100, 80), '#f0e0d0').save(picture, format='PNG')
image_data = picture.getvalue()
image_url = 'data:image/png;base64,' + base64.b64encode(image_data).decode()
requests = []
speech_requests = []
explanation = 'A red shape is above a blue shape. ' * 14
state = {'signed_in': False}
weights = {'VOCABULARY': .17, 'SYNTACTIC': .29, 'CONCEPTUAL': .20, 'PRONUNCIATION': .17, 'VISUAL': .17}
event_state = {'revision': 30, 'need_estimates': weights}
report = {
    'profile': {'alias': 'Demo reader', 'id': '12345678-test', 'created_at': '2026-01-01T00:00:00Z'},
    'survey': {'difficulties': [], 'preferred_style': 'short'},
    'metrics': {'sessions': 1, 'support_decisions': 1, 'explicit_requests': {'CONCEPTUAL': 1},
                'feedback': {'helped': 0, 'not_helpful': 0}},
    'states': {'en': {'preferred_style': 'short', 'style_estimates': {'short': .5}}},
    'events': [
        {'id': 'dwell-1', 'kind': 'dwell', 'language': 'en', 'created_at': '2026-01-01T12:01:00Z',
         'reason': 'Ambiguous observation.', 'payload': {}, 'before_state': event_state, 'after_state': event_state},
        {'id': 'help-1', 'kind': 'help_request', 'language': 'en', 'created_at': '2026-01-01T12:00:00Z',
         'reason': 'Learner chose help.', 'payload': {'span': 'plant'},
         'before_state': event_state, 'after_state': event_state},
    ],
    'routes': [],
}


def handle(route):
    path = urlparse(route.request.url).path
    if path.startswith('/api/'):
        if path == '/api/account':
            body = {'signed_in': state['signed_in'], 'setup_complete': True}
        elif path == '/api/learner/report':
            body = report
        elif path == '/api/document-status':
            body = {'ocr_available': True, 'vision_available': True}
        elif path == '/api/documents/extract':
            body = {'page': 1, 'page_count': 1, 'text': '', 'method': 'OCR',
                    'ocr_engine': 'fixture', 'warnings': ['No words found.'],
                    'image': image_url, 'lines': [], 'language': 'en'}
        elif path == '/api/documents/explain':
            requests.append(route.request.post_data_buffer.decode('latin-1'))
            body = {'explanation': explanation,
                    'model': 'test vision model', 'warning': 'Check the source.', 'trace_id': None}
        elif path == '/api/speech':
            speech_requests.append(route.request.post_data)
            route.fulfill(status=503, content_type='application/json', body='{"detail":"Local voice unavailable"}')
            return
        elif path == '/api/learner/state':
            body = {'enrolled': False}
        elif path == '/api/model-status':
            body = {'services': {}, 'human_routing': {'available': False}}
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
    page.locator('#document-file').set_input_files({'name': 'shapes.png', 'mimeType': 'image/png', 'buffer': image_data})
    page.locator('.picture-guide').wait_for(state='visible')
    assert page.locator('#extracted-text').get_attribute('rows') == '3'
    assert page.locator('#read-extracted').is_disabled()
    page.locator('#picture-kind').select_option('geometry')
    assert 'shapes' in page.locator('#visual-question').input_value()
    page.locator('.picture-guide button').click()
    page.locator('#visual-answer').get_by_text('A red shape is above a blue shape.').wait_for()
    assert requests and 'name="kind"' in requests[0] and 'geometry' in requests[0]
    page.evaluate("""() => { window.__spoken = []; speechSynthesis.speak = utterance => {
        window.__spoken.push(utterance.text); setTimeout(() => utterance.onend?.(), 0);
    }; }""")
    page.locator('#visual-speak').click()
    page.locator('.visual-audio-status').get_by_text('Explanation audio finished.').wait_for()
    assert ''.join(page.evaluate('window.__spoken')) == explanation
    assert not speech_requests
    page.evaluate("""() => { speechSynthesis.speak = utterance => setTimeout(() => utterance.onerror?.(), 0); }""")
    page.locator('#visual-speak').click()
    page.locator('.visual-audio-status').get_by_text('Try Local voice', exact=False).wait_for()
    assert not speech_requests
    page.locator('#visual-voice').select_option('local')
    page.locator('#visual-speak').click()
    page.locator('.visual-audio-status').get_by_text('Local voice unavailable').wait_for()
    assert speech_requests
    state['signed_in'] = True
    page.goto('http://127.0.0.1:8099/my-progress.html')
    page.locator('#events .event').wait_for()
    assert page.locator('#events .event').count() == 1
    assert 'help request' in page.locator('#events').inner_text()
    assert 'No visible support-preference change' in page.locator('#comparison').inner_text()
    assert 'Before · revision' not in page.locator('#comparison').inner_text()
    page.locator('#show-activity').check()
    assert page.locator('#events .event').count() == 2
    report['events'][1]['before_state'] = {'revision': 29, 'need_estimates': weights,
                                           'style_estimates': {'short': .5}, 'preferred_style': 'short'}
    report['events'][1]['after_state'] = {'revision': 30, 'need_estimates': weights,
                                          'style_estimates': {'short': .75}, 'preferred_style': 'short'}
    page.locator('#show-activity').uncheck()
    page.locator('#refresh').click()
    page.locator('#comparison').get_by_text('Explanation style: short', exact=False).first.wait_for()
    assert not errors, errors
    browser.close()
