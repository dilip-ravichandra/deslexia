from fastapi.testclient import TestClient

import BACKEND.app as appmod
from ML.context import build_context
from ML.contextual_support import explain


SENTENCE = 'We have extra curriculars after classes and we finish up our projects at night.'


def test_full_sentence_stops_at_its_own_boundary():
    passage = 'Class has ended. ' + SENTENCE + ' Tomorrow we meet again.'
    context = build_context(passage, SENTENCE, passage.index(SENTENCE))
    assert context['sentence'] == SENTENCE


def test_sentence_help_splits_source_clauses_without_a_glossary():
    result = explain(SENTENCE, SENTENCE, category='SYNTACTIC', allow_generation=False)
    assert result['source'] == 'source_sentence_chunks'
    assert result['chunks'] == [
        'We have extra curriculars after classes',
        'and we finish up our projects at night.',
    ]
    assert 'meaning for' not in result['summary']
    assert result['is_generated_model_output'] is False


def test_sentence_help_reports_when_no_safe_split_exists():
    sentence = 'The students finished their homework.'
    result = explain(sentence, sentence, category='SYNTACTIC', allow_generation=False)
    assert result['source'] == 'source_sentence_no_split'
    assert 'complete sentence' in result['summary']
    assert 'glossary' not in result['summary']


def test_sentence_help_api_uses_the_selected_sentence():
    passage = 'Class has ended. ' + SENTENCE + ' Tomorrow we meet again.'
    response = TestClient(appmod.app).post('/api/support', json={
        'text': passage, 'span': SENTENCE, 'span_start': passage.index(SENTENCE),
        'category_override': 'SYNTACTIC', 'document_language': 'en',
    })
    assert response.status_code == 200
    result = response.json()
    assert result['input']['sentence'] == SENTENCE
    assert result['explanation']['source'] == 'source_sentence_chunks'
    assert len(result['explanation']['chunks']) == 2
