from fastapi.testclient import TestClient

import BACKEND.app as appmod
from BACKEND.learner import LearnerModel
from ML.paragraph_rewrite import rewrite_paragraph
import ML.paragraph_rewrite as rewrite_module


def test_paragraph_support_keeps_source_and_uses_saved_history(tmp_path, monkeypatch):
    learner = LearnerModel(tmp_path / 'learner.sqlite3')
    monkeypatch.setattr(appmod, 'learner', learner)
    key = 'a' * 64
    learner.survey(key, {'consent': True, 'alias': 'Test reader', 'difficulties': ['VOCABULARY', 'SYNTACTIC'],
                         'preferred_style': 'steps', 'reading_settings': {}})
    paragraph = 'The catalyst helped. It made the reaction faster.'
    for _ in range(2):
        session = learner.start(key, 'en')['session_id']
        learner.record(key, {'client_id': session, 'session_id': session, 'language': 'en',
                             'kind': 'help_request', 'payload': {'span': 'catalyst', 'category': 'VOCABULARY'}})
        learner.record(key, {'client_id': session + '-end', 'session_id': session,
                             'language': 'en', 'kind': 'session_end', 'payload': {}})
    client = TestClient(appmod.app)
    response = client.post('/api/paragraph-support', headers={'x-learner-key': key},
                           json={'paragraph': paragraph, 'document_language': 'en'})
    assert response.status_code == 200
    data = response.json()
    assert data['original'] == paragraph
    assert ''.join(data['sentences']) == paragraph
    assert data['text_changed'] is False
    assert data['source'] == 'learner_history'
    assert data['category'] == 'VOCABULARY'
    assert data['style'] == 'steps'
    assert any(note['word'] == 'catalyst' for note in data['glossary'])
    assert client.post('/api/paragraph-support', headers={'x-learner-key': key},
                       json={'paragraph': paragraph, 'category': 'CONCEPTUAL'}).json()['source'] == 'learner_choice'
    unrelated = client.post('/api/paragraph-support', headers={'x-learner-key': key},
                            json={'paragraph': 'The river flowed past the school.'}).json()
    assert unrelated['source'] == 'default_layout'
    assert unrelated['category'] == 'SYNTACTIC'
    assert learner.state(key)['revision'] == 4


def test_paragraph_support_rejects_blank_and_settings():
    client = TestClient(appmod.app)
    assert client.post('/api/paragraph-support', json={'paragraph': '   '}).status_code == 422
    assert client.post('/api/paragraph-support', json={'paragraph': 'A sentence.', 'font': 'mono'}).status_code == 422


def test_easier_version_shows_only_checked_changes():
    paragraph = 'The object accelerated. The result was approximately 10 units.'
    data = rewrite_paragraph(paragraph, 'VOCABULARY')
    assert data['original'] == paragraph
    assert data['adapted'] == 'The object sped up. The result was about 10 units.'
    assert data['changed_count'] == 2
    assert data['meaning_preservation_guaranteed'] is False
    for sentence in data['sentences']:
        assert sentence['checks']['status'] == 'pass'
        assert ''.join(part['text'] for part in sentence['original_parts']) == sentence['original']
        assert ''.join(part['text'] for part in sentence['adapted_parts']) == sentence['adapted']
        assert any(part['changed'] for part in sentence['adapted_parts'])


def test_easier_version_keeps_unsafe_and_unsupported_sentences():
    risky = 'Although the experiment ran for days, the result was unclear.'
    result = rewrite_paragraph(risky, 'SYNTACTIC')
    assert result['changed_count'] == 0
    assert result['adapted'] == risky
    assert 'relationship word' in result['sentences'][0]['reason']
    relative = 'The scientist found a result, which explained the earlier test.'
    assert rewrite_paragraph(relative, 'SYNTACTIC')['adapted'] == relative
    hindi = 'यह एक वाक्य है।'
    assert rewrite_paragraph(hindi, 'VOCABULARY', 'hi')['adapted'] == hindi


def test_easier_version_hides_a_candidate_that_changes_a_number(monkeypatch):
    monkeypatch.setattr(rewrite_module, 'vocabulary', lambda sentence, variant: {
        'adapted': sentence.replace('10', '20'),
        'operations': [{'rule': 'lexicon_replace'}],
    })
    original = 'The result was 10 units.'
    result = rewrite_paragraph(original, 'VOCABULARY')
    assert result['adapted'] == original
    assert result['changed_count'] == 0
    assert result['sentences'][0]['checks']['status'] == 'fail'


def test_easier_version_endpoint_is_separate_and_validated():
    client = TestClient(appmod.app)
    response = client.post('/api/paragraph-rewrite', json={
        'paragraph': 'The object accelerated.', 'category': 'VOCABULARY'})
    assert response.status_code == 200
    data = response.json()
    assert data['source'] == 'learner_choice'
    assert data['changed_count'] == 1
    assert data['adapted'] == 'The object sped up.'
    assert client.post('/api/paragraph-rewrite', json={'paragraph': ' ', 'font': 'mono'}).status_code == 422
