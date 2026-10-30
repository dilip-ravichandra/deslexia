"""Authored engineering fixtures. None of these judgments are human research data."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
import BACKEND.app as module
from BACKEND.adaptive import AdaptiveService
from BACKEND.learner import LearnerModel
from BACKEND.accounts import AccountStore
from ML.context import codepoint_offset

@pytest.fixture
def client(tmp_path,monkeypatch):
    service=AdaptiveService(tmp_path)
    learner=LearnerModel(service.db_path)
    monkeypatch.setattr(module,'adaptive',service)
    monkeypatch.setattr(module,'learner',learner)
    monkeypatch.setattr(module,'accounts',AccountStore(service.db_path))
    # These tests exercise the real rule fallback, not generation quality.
    monkeypatch.setenv('DYSLEXIADAPT_GENERATION','off')
    return TestClient(module.app),service,learner

def enroll(client,needs=None):
    c,service,learner=client;key=uuid.uuid4().hex+uuid.uuid4().hex;h={'x-learner-key':key}
    assert c.post('/api/learner/survey',headers=h,json={'consent':True,'difficulties':needs or []}).status_code==200
    sid=c.post('/api/learner/session',headers=h,json={'language':'en'}).json()['session_id']
    return key,h,sid

def test_selected_concept_is_not_replaced_by_nearby_glossary(client,monkeypatch):
    c,_,_=client
    import ML.public_experiment as lexical
    monkeypatch.setattr(lexical,'predict_word',lambda *a:pytest.fail('A manual request must not depend on lexical inference.'))
    r=c.post('/api/support',json={'text':'A catalyst speeds up a chemical reaction.','span':'chemical reaction','category_override':'CONCEPTUAL'})
    assert r.status_code==200
    assert 'substances change' in r.json()['explanation']['summary']
    assert r.json()['category']['source']=='learner_choice'

def test_quick_help_skips_local_generation_and_explains_known_word_in_sentence(client,monkeypatch):
    import ML.local_generation as generation
    client_api,_,_=client
    monkeypatch.setattr(generation,'available',lambda:True)
    monkeypatch.setattr(generation,'generate',lambda *args,**kwargs:pytest.fail('Quick help must not load Qwen.'))
    sentence='Plants use photosynthesis to turn sunlight into food.'
    response=client_api.post('/api/support',json={'text':sentence,'span':sentence,'category_override':'CONCEPTUAL','document_language':'en'})
    assert response.status_code==200
    explanation=response.json()['explanation']
    assert explanation['quick_help'] is True
    assert explanation['ai_available'] is True
    assert explanation['is_generated_model_output'] is False
    assert 'light energy' in explanation['summary'].lower()
    assert 'reading prompt' not in explanation['summary']

def test_deeper_ai_help_is_explicit_opt_in(client,monkeypatch):
    import ML.local_generation as generation
    import ML.onnx_verification as verification
    client_api,_,_=client
    calls=[]
    monkeypatch.setattr(generation,'available',lambda:True)
    monkeypatch.setattr(verification,'available',lambda:False)
    def generated(*args,**kwargs):
        calls.append(args)
        return {'explanation':'Photosynthesis uses sunlight to help plants make food.','model':'test-local-model','quality':{'status':'screened','claims':[]}}
    monkeypatch.setattr(generation,'generate',generated)
    response=client_api.post('/api/support',json={'text':'Plants use photosynthesis to make food.','span':'photosynthesis','category_override':'CONCEPTUAL','document_language':'en','response_mode':'local_ai'})
    assert response.status_code==200
    assert len(calls)==1
    assert response.json()['explanation']['source']=='native_local_qwen'
    assert response.json()['explanation']['is_generated_model_output'] is True
    assert client_api.post('/api/support',json={'text':'word','span':'word','response_mode':'unknown'}).status_code==422


def test_online_ai_requires_per_request_consent_and_sends_only_sentence(client, monkeypatch):
    import ML.cloud_help as cloud
    client_api, _, _ = client
    sentence = 'A seed begins to grow.'
    payload = {'text': sentence + '\n\nPrivate unrelated paragraph.', 'span': 'seed',
               'category_override': 'VOCABULARY', 'document_language': 'en',
               'response_mode': 'online_ai'}
    calls = []
    monkeypatch.setattr(cloud, 'available', lambda: True)
    monkeypatch.setattr(cloud, 'explain', lambda *args: calls.append(args) or {
        'summary': 'A seed is the selected word.', 'available': True,
        'source': 'groq_opt_in', 'is_generated_model_output': True})
    assert client_api.post('/api/support', json=payload).status_code == 422
    assert not calls
    response = client_api.post('/api/support', json={**payload, 'cloud_consent': True})
    assert response.status_code == 200
    assert response.json()['explanation']['source'] == 'groq_opt_in'
    assert calls[0][0] == 'seed'
    assert calls[0][1] == sentence


def test_online_ai_withholds_ungrounded_answer(monkeypatch):
    import ML.cloud_help as cloud
    monkeypatch.setenv('GROQ_API_KEY', 'fixture-secret')
    captured = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _):
            return json.dumps({'choices': [{'message': {'content': json.dumps({'claims': [
                {'text': 'The moon made the seed grow.', 'evidence': 'The moon made it grow.', 'source': 'passage'}
            ]})}}]}).encode()

    def fake_urlopen(request, timeout):
        captured.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(cloud.urllib.request, 'urlopen', fake_urlopen)
    with pytest.raises(RuntimeError, match='withheld'):
        cloud.explain('seed', 'A seed begins to grow.', 'VOCABULARY', 'short', 'en')
    sent = json.loads(captured[0][0].data)
    assert sent['model'] == cloud.MODEL
    assert 'fixture-secret' not in json.dumps(sent)
    assert 'A seed begins to grow.' in sent['messages'][1]['content']

def test_shoot_quick_help_uses_plant_context_without_hollow_passage_quote(client):
    client_api,_,_=client
    passage='A seed begins to grow. A shoot grows upwards towards the light.'
    response=client_api.post('/api/support',json={'text':passage,'span':'shoot','span_start':passage.index('shoot'),'category_override':'VOCABULARY','document_language':'en'})
    assert response.status_code==200
    explanation=response.json()['explanation']
    assert explanation['quick_help'] is True
    assert 'part of a plant' in explanation['summary']
    assert 'A shoot grows upwards' not in explanation['summary']
    unrelated=client_api.post('/api/support',json={'text':'I shoot a photo.','span':'shoot','category_override':'VOCABULARY','document_language':'en'}).json()['explanation']
    assert unrelated['source']=='context_only_no_definition'
    assert 'part of a plant' not in unrelated['summary']
    assert 'reliable meaning' in unrelated['summary']

def test_quick_help_combines_two_known_terms_in_selected_sentence(client):
    client_api,_,_=client
    sentence='A catalyst can speed up a chemical reaction.'
    response=client_api.post('/api/support',json={'text':sentence,'span':sentence,'category_override':'CONCEPTUAL','document_language':'en'})
    assert response.status_code==200
    summary=response.json()['explanation']['summary']
    assert 'Catalyst:' in summary
    assert 'Chemical reaction:' in summary
    assert 'reliable meaning' not in summary

def test_selected_bank_uses_second_sentence(client):
    c,_,_=client;text='I left money at the bank. We sat beside the river bank.'
    r=c.post('/api/support',json={'text':text,'span':'bank','span_start':text.rfind('bank'),'category_override':'VOCABULARY'})
    assert r.status_code==200
    assert r.json()['explanation']['source']=='contextual_dictionary'
    assert 'land along the edge' in r.json()['explanation']['summary']

def test_browser_utf16_offsets_and_invalid_surrogates(client):
    c,_,_=client
    r=c.post('/api/support',json={'text':'🌿 word','span':'word','span_start':3,'span_offset_unit':'utf16','category_override':'PRONUNCIATION'})
    assert r.status_code==200
    with pytest.raises(ValueError):codepoint_offset('🌿 word',1,'utf16')
    assert c.post('/api/support',json={'text':'🌿 word','span':'word','span_start':2,'span_offset_unit':'utf16'}).status_code==422

def test_pronunciation_and_visual_instructions_are_distinct(client):
    client_api,_,_=client
    request={'text':'Read this word.','span':'word','document_language':'en'}
    pronunciation=client_api.post('/api/support',json={**request,'category_override':'PRONUNCIATION'}).json()['explanation']
    visual=client_api.post('/api/support',json={**request,'category_override':'VISUAL'}).json()['explanation']
    assert pronunciation['pronunciation_text']=='word'
    assert 'Speech is a support action' in pronunciation['note']
    assert visual['pronunciation_text'] is None
    assert 'Reading presentation changes how text looks' in visual['note']

def test_duplicate_requests_do_not_unlock_automatic_suggestion(client):
    _,_,learner=client;key,_,sid=enroll(client)
    for _ in range(3):
        learner.record(key,{'client_id':uuid.uuid4().hex,'session_id':sid,'language':'en','kind':'help_request','payload':{'span':'word','category':'VOCABULARY'}})
        assert learner.choose(key,sid,'en','word')['selected']=='OTHER_UNCERTAIN'

def test_request_retry_does_not_save_two_help_events(client):
    c,_,learner=client;key,h,sid=enroll(client)
    body={'text':'This word.','span':'word','category_override':'PRONUNCIATION','document_language':'en','session_id':sid,'request_id':uuid.uuid4().hex}
    assert c.post('/api/support',headers=h,json=body).status_code==200
    assert c.post('/api/support',headers=h,json=body).status_code==200
    assert learner.state(key)['revision']==1

def test_learner_report_requires_own_capability(client):
    client_api,_,_=client
    key,headers,_=enroll(client,['VOCABULARY'])
    response=client_api.get('/api/learner/report',headers=headers)
    assert response.status_code==200
    assert response.headers['Cache-Control']=='no-store'
    assert response.json()['profile']['id']==__import__('hashlib').sha256(key.encode()).hexdigest()
    assert response.json()['survey']['difficulties']==['VOCABULARY']
    assert client_api.get('/api/learner/report').status_code==422
    assert client_api.get('/api/learner/report',headers={'x-learner-key':'b'*64}).status_code==404

def test_late_picture_result_and_quality_cannot_restore_deleted_history(client):
    c,service,learner=client;key,h,sid=enroll(client)
    consent=service.consent_version(key)
    route=learner.choose(key,sid,'en','word','VOCABULARY')
    assert c.delete('/api/profile',headers=h).status_code==200
    assert service.record_visual(key,'short','fixture',{'explanation':'fixture','model':'fixture'},consent) is None
    learner.record_quality(key,route['route_id'],{'fixture':True})
    with service.db() as db:
        for table in ['visual_traces','learner_routes','learner_surveys']:
            assert db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    # Re-enrolling the same capability still must not authorize the old completion.
    c.post('/api/learner/survey',headers=h,json={'consent':True})
    assert service.record_visual(key,'short','fixture',{'explanation':'fixture','model':'fixture'},consent) is None

def test_visual_endpoint_captures_consent_before_inference(client,monkeypatch):
    import io
    from PIL import Image
    import ML.visual_support as vision
    c,service,learner=client;key,h,_=enroll(client)
    def finish_after_forget(*args):
        learner.forget(key)
        return {'explanation':'Controlled test completion','model':'fixture'}
    monkeypatch.setattr(vision,'explain',finish_after_forget)
    image=io.BytesIO();Image.new('RGB',(10,10)).save(image,format='PNG')
    r=c.post('/api/documents/explain',headers=h,files={'file':('fixture.png',image.getvalue())})
    assert r.status_code==200 and r.json()['trace_id'] is None

@pytest.mark.parametrize('language',['hi','kn','ta'])
def test_native_data_loader_works_with_normal_windows_encoding(client,language):
    c,_,_=client
    assert c.get('/api/admin/public-materials',params={'language':language}).status_code==200
