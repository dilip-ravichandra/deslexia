import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import BACKEND.app as module
from BACKEND.adaptive import AdaptiveService
from BACKEND.pipeline import Pipeline
from ML.prototype import PrototypeTrainer

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def service(tmp_path,monkeypatch):
    (tmp_path/'DATA').mkdir()
    shutil.copy(ROOT/'DATA'/'prototype_pilots.json',tmp_path/'DATA'/'prototype_pilots.json')
    svc=AdaptiveService(tmp_path)
    # Build an actual tiny TF-IDF pilot in temporary storage; no archived model is active in the product.
    import ML.neural_features as neural
    monkeypatch.setattr(neural,'classifier_candidates',lambda:[])
    report=svc.trainer.train();svc.trainer.promote(report['run_id']);svc.trainer.initial_test()
    from BACKEND.learner import LearnerModel
    learner=LearnerModel(svc.db_path)
    learner.survey('a'*64,{'consent':True,'difficulties':[],'preferred_style':'short'})
    monkeypatch.setattr(module,'learner',learner)
    monkeypatch.setattr(module,'adaptive',svc)
    monkeypatch.setattr(module,'pipe',Pipeline())
    return svc,TestClient(module.app)

def request(client,key='a'*64,style='steps',text='A catalyst can speed up a chemical reaction.'):
    return client.post('/api/adapt',headers={'x-learner-key':key} if key else {},json={
        'span':text,'text':text,'document_text':text,'category_override':'CONCEPTUAL','support_style':style})

def test_opt_in_profile_survives_restart_and_personalizes(service):
    svc,c=service
    for _ in range(2):
        response=request(c).json()
        assert response['explanation']['available']
        assert 'reaction' in response['explanation']['summary']
        assert c.post('/api/feedback',headers={'x-learner-key':'a'*64},json={'trace_id':response['trace_id'],'decision':'accept'}).status_code==200
    restarted=AdaptiveService(svc.root)
    assert restarted.profile('a'*64)['preferences']['CONCEPTUAL']=='steps'
    response=request(c,style='auto').json()
    assert response['personalization']['style']=='steps'
    assert response['personalization']['source']=='saved_feedback'

def test_feedback_idempotency_and_profile_isolation(service):
    svc,c=service;tid=request(c).json()['trace_id']
    for _ in range(3):assert c.post('/api/feedback',headers={'x-learner-key':'a'*64},json={'trace_id':tid,'decision':'accept'}).status_code==200
    assert svc.profile('a'*64)['feedback']['CONCEPTUAL']['steps']['count']==1
    assert c.post('/api/feedback',headers={'x-learner-key':'b'*64},json={'trace_id':tid,'decision':'accept'}).status_code==404

def test_without_opt_in_text_is_not_persisted(service):
    svc,c=service;request(c,key=None)
    with svc.db() as db:assert db.execute('SELECT COUNT(*) FROM traces').fetchone()[0]==0

def test_forget_deletes_reviews_and_traces(service):
    svc,c=service;tid=request(c).json()['trace_id'];svc.feedback('a'*64,tid,'accept',None)
    svc.review(tid,'CONCEPTUAL','Reaction rate needs an explanation.','reviewer-test')
    assert c.delete('/api/profile',headers={'x-learner-key':'a'*64}).status_code==200
    with svc.db() as db:
        assert db.execute('SELECT COUNT(*) FROM traces').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]==0

def test_prototype_prediction_is_not_research(service):
    svc,c=service
    response=c.post('/api/adapt',json={'span':'density','text':'The density of an object compares mass and volume.'}).json()
    assert response['research_mode']=='prototype'
    assert response['category']['is_trained_model_output'] is True
    assert response['valid_for_research'] is False
    assert set(response['category']['probabilities'])=={'VOCABULARY','SYNTACTIC','CONCEPTUAL','OTHER_UNCERTAIN'}

def test_uncertain_prediction_asks_for_choice(service,monkeypatch):
    svc,c=service
    monkeypatch.setattr(svc.trainer,'predict',lambda *a:{'VOCABULARY':.2,'SYNTACTIC':.2,'CONCEPTUAL':.2,'OTHER_UNCERTAIN':.4})
    response=c.post('/api/adapt',json={'span':'clear','text':'This is clear.'}).json()
    assert response['category']['needs_choice'] is True
    assert response['presentable'] is False
    assert response['explanation']['available'] is False

def test_admin_gate_and_review_before_training(service,monkeypatch):
    svc,c=service;monkeypatch.setenv('DYSLEXIADAPT_ADMIN_TOKEN','test-admin-secret')
    assert c.get('/api/admin/learning').status_code==401
    assert c.post('/api/admin/train',json={}).status_code==401
    assert c.get('/api/admin/learning',headers={'x-admin-token':'test-admin-secret'}).status_code==200
    tid=request(c).json()['trace_id'];svc.feedback('a'*64,tid,'accept',None)
    assert svc.reviewed()==[]
    svc.review(tid,'CONCEPTUAL','The underlying chemical idea needs explanation.','teacher')
    assert len(svc.reviewed())==1

def test_heldout_feedback_is_rejected(service):
    svc,c=service
    row=next(r for r in svc.trainer.data()['rows'] if r['split']=='TEST')
    response=c.post('/api/adapt',headers={'x-learner-key':'a'*64},json={'span':row['text'],'text':row['document_text'],
      'document_text':row['document_text'],'category_override':'CONCEPTUAL'}).json()
    svc.feedback('a'*64,response['trace_id'],'reject',None)
    with pytest.raises(ValueError,match='protected'):svc.review(response['trace_id'],'CONCEPTUAL','Review test material.','teacher')

def test_retraining_uses_validation_preserves_test_and_supports_rollback(service):
    svc,c=service
    frozen=(svc.trainer.directory/'initial_test.json').read_bytes()
    previous=svc.trainer.active['run_id'];report=svc.trainer.train()
    assert report['promotion_eligible']
    assert 'test' not in report
    svc.trainer.promote(report['run_id'])
    assert svc.trainer.active['previous_run_id']==previous
    assert svc.trainer.rollback()['run_id']==previous
    assert (svc.trainer.directory/'initial_test.json').read_bytes()==frozen

def test_failed_candidate_cannot_activate(service):
    svc,c=service;report=svc.trainer.train();path=svc.trainer.directory/report['run_id']/'results.json'
    report['promotion_eligible']=False;path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError,match='failed'):svc.trainer.promote(report['run_id'])

def test_no_document_leakage_and_unresolved_labels_preserved(service):
    svc,c=service;rows=svc.trainer.data()['rows'];groups={}
    for row in rows:groups.setdefault(row['document_id'],set()).add(row['split'])
    assert all(len(s)==1 for s in groups.values())
    assert sum(r['category'] is None for r in rows)==45
    assert len(rows)==140

def test_explicit_style_changes_explanation_presentation(service):
    svc,c=service
    assert request(c,style='short').json()['explanation']['style']=='short'
    result=request(c,style='steps',text='Because the reaction needs energy, heating can change its speed.').json()
    assert result['explanation']['relationship']['parts']==['the reaction needs energy','heating can change its speed.']

def test_optional_local_generator_and_failure_fallback(monkeypatch):
    from ML.contextual_support import explain
    import ML.contextual_support as support
    monkeypatch.setenv('DYSLEXIADAPT_LOCAL_MODEL','local-test')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps({'response':json.dumps({'claims':[{'text':'A catalyst speeds a reaction.','evidence':'A catalyst speeds a reaction.','source':'passage'}]})}).encode()
    monkeypatch.setattr(support.urllib.request,'urlopen',lambda *args,**kwargs:Response())
    assert explain('catalyst','A catalyst speeds a reaction.')['is_generated_model_output']
    def failed(*args,**kwargs):raise OSError('offline')
    monkeypatch.setattr(support.urllib.request,'urlopen',failed)
    result=explain('catalyst','A catalyst speeds a reaction.')
    assert result['source']=='context_and_bundled_glossary'
    assert 'unavailable' in result['provider_status']

def test_generated_meaning_change_is_not_delivered(monkeypatch):
    from ML.contextual_support import explain
    import ML.contextual_support as support
    monkeypatch.setenv('DYSLEXIADAPT_LOCAL_MODEL','local-test')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps({'response':'Students must attend.'}).encode()
    monkeypatch.setattr(support.urllib.request,'urlopen',lambda *args,**kwargs:Response())
    result=explain('Students must not attend.','Students must not attend.')
    assert result['generation_checks']['status']=='fail'
    assert not result['is_generated_model_output']

def test_cloud_model_name_is_rejected(monkeypatch):
    from ML.contextual_support import explain
    monkeypatch.setenv('DYSLEXIADAPT_LOCAL_MODEL','anything:cloud')
    assert 'disabled' in explain('catalyst','A catalyst speeds a reaction.')['provider_status']
