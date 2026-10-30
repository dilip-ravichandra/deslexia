"""Engineering invariants; these fixtures are not human research annotations."""
import uuid
import pytest
from BACKEND.learner import LearnerModel,identity
@pytest.fixture
def learner(tmp_path):return LearnerModel(tmp_path/'state.sqlite3')
def setup(learner,key='a'*64,lang='en'):
 learner.survey(key,{'consent':True,'alias':'Engineering test','difficulties':['PRONUNCIATION'],'preferred_style':'short','reading_settings':{}})
 return key,learner.start(key,lang)['session_id']
def event(learner,key,sid,kind,payload,lang='en',client=None):return learner.record(key,{'client_id':client or uuid.uuid4().hex,'session_id':sid,'language':lang,'kind':kind,'payload':payload})
def test_ambiguous_signals_do_not_label_difficulty(learner):
 key,sid=setup(learner);before=learner.state(key)
 for kind in ['dwell','reread','attention_return']:
  r=event(learner,key,sid,kind,{'duration_ms':20000});assert not r['parameters_changed']
 assert learner.state(key)['need_parameters']==before['need_parameters']
def test_repeated_requests_across_sessions_and_manual_override(learner):
 key,sid=setup(learner)
 event(learner,key,sid,'help_request',{'span':'photosynthesis','category':'PRONUNCIATION'})
 before=learner.state(key,'en','photosynthesis')['need_parameters']
 event(learner,key,sid,'help_request',{'span':'photosynthesis','category':'PRONUNCIATION'})
 assert learner.state(key,'en','photosynthesis')['need_parameters']==pytest.approx(before,abs=1e-6)
 event(learner,key,sid,'session_end',{});sid=learner.start(key,'en')['session_id']
 event(learner,key,sid,'help_request',{'span':'photosynthesis','category':'PRONUNCIATION'})
 assert learner.choose(key,sid,'en','photosynthesis')['selected']=='PRONUNCIATION'
 assert learner.choose(key,sid,'en','photosynthesis','VOCABULARY')['selected']=='VOCABULARY'
def test_duplicate_and_language_isolation(learner):
 key,sid=setup(learner);payload={'span':'photosynthesis','category':'VOCABULARY'}
 first=event(learner,key,sid,'help_request',payload,client='duplicate');again=event(learner,key,sid,'help_request',payload,client='duplicate')
 assert first['event_id']==again['event_id'];assert again['duplicate']
 assert not learner.state(key,'hi')['evidence']
 with pytest.raises(ValueError):event(learner,key,sid,'help_request',payload,lang='hi')
def test_ownership_and_deletion(learner):
 key,sid=setup(learner);other,_=setup(learner,'b'*64)
 with pytest.raises(ValueError):event(learner,other,sid,'dwell',{})
 event(learner,key,sid,'help_request',{'span':'word','category':'VOCABULARY'});learner.forget(key)
 assert not learner.state(key)['enrolled'];assert all(p['id']!=identity(key) for p in learner.dashboard()['profiles'])
def test_undo_requires_own_route(learner):
 key,sid=setup(learner)
 with pytest.raises(ValueError):event(learner,key,sid,'undo',{'route_id':'unknown'})
 route=learner.choose(key,sid,'en','word','VOCABULARY')
 assert event(learner,key,sid,'optional_feedback',{'route_id':route['route_id'],'decision':'reject'})['parameters_changed']

def test_starting_survey_informs_first_suggestion(learner):
 key,sid=setup(learner)
 route=learner.choose(key,sid,'en','new word')
 assert route['selected']=='PRONUNCIATION'
 assert any('Starting survey' in reason for reason in route['reasons'])

def test_alternative_style_does_not_relabel_needs(learner):
 key,sid=setup(learner);before=learner.state(key)['need_parameters']
 route=learner.choose(key,sid,'en','word','VOCABULARY','short',variant=1)
 assert route['style']=='steps'
 assert learner.state(key)['need_parameters']==before

def test_session_end_retry_is_idempotent(learner):
 key,sid=setup(learner)
 first=event(learner,key,sid,'session_end',{},client='end-once')
 again=event(learner,key,sid,'session_end',{},client='end-once')
 assert again['duplicate'] and first['event_id']==again['event_id']
 with pytest.raises(ValueError):event(learner,key,sid,'dwell',{})

def test_profile_report_survives_restart_and_is_key_scoped(learner):
 key,sid=setup(learner)
 event(learner,key,sid,'help_request',{'span':'photosynthesis','category':'PRONUNCIATION'})
 route=learner.choose(key,sid,'en','photosynthesis','PRONUNCIATION')
 event(learner,key,sid,'optional_feedback',{'route_id':route['route_id'],'decision':'accept'})
 resumed=learner.start(key,'en')
 assert resumed=={'session_id':sid,'language':'en','status':'resumed'}
 reopened=LearnerModel(learner.path)
 report=reopened.report(key)
 assert report['profile']['alias']=='Engineering test'
 assert report['metrics']['sessions']==1
 assert report['metrics']['explicit_requests']['PRONUNCIATION']==1
 assert report['metrics']['feedback']['helped']==1
 assert report['metrics']['support_decisions']==1
 assert 'profiles' not in report
 with pytest.raises(LookupError):reopened.report('c'*64)
 event(reopened,key,sid,'session_end',{})
 assert reopened.start(key,'en')['session_id']!=sid

def test_overview_counts_only_consented_recorded_activity(learner):
 assert learner.overview()['profiles']==0
 first,first_session=setup(learner)
 second,second_session=setup(learner,'b'*64)
 event(learner,first,first_session,'help_request',{'span':'photosynthesis','category':'PRONUNCIATION'})
 event(learner,second,second_session,'help_request',{'span':'catalyst','category':'VOCABULARY'})
 route=learner.choose(first,first_session,'en','photosynthesis','PRONUNCIATION')
 event(learner,first,first_session,'optional_feedback',{'route_id':route['route_id'],'decision':'accept'})
 overview=LearnerModel(learner.path).overview()
 assert overview['profiles']==2
 assert overview['sessions']==2
 assert overview['support_responses']==1
 assert overview['explicit_requests']['PRONUNCIATION']==1
 assert overview['explicit_requests']['VOCABULARY']==1
 assert overview['optional_feedback']['helped']==1
 assert 'alias' not in str(overview)
 learner.forget(second)
 assert learner.overview()['profiles']==1
 assert learner.overview()['explicit_requests']['VOCABULARY']==0

def test_two_learners_keep_separate_multi_need_evidence(learner):
 first='a'*64
 second='b'*64
 learner.survey(first,{'consent':True,'alias':'First','difficulties':['PRONUNCIATION','VOCABULARY'],'preferred_style':'short','reading_settings':{}})
 learner.survey(second,{'consent':True,'alias':'Second','difficulties':['CONCEPTUAL','SYNTACTIC'],'preferred_style':'steps','reading_settings':{}})
 first_session=learner.start(first,'en')['session_id']
 second_session=learner.start(second,'en')['session_id']
 event(learner,first,first_session,'help_request',{'span':'catalyst','category':'PRONUNCIATION'})
 event(learner,first,first_session,'help_request',{'span':'catalyst','category':'VOCABULARY'})
 event(learner,second,second_session,'help_request',{'span':'catalyst','category':'CONCEPTUAL'})
 first_report=learner.report(first)
 second_report=learner.report(second)
 assert first_report['metrics']['explicit_requests']['PRONUNCIATION']==1
 assert first_report['metrics']['explicit_requests']['VOCABULARY']==1
 assert first_report['metrics']['explicit_requests']['CONCEPTUAL']==0
 assert second_report['metrics']['explicit_requests']['CONCEPTUAL']==1
 assert second_report['metrics']['explicit_requests']['PRONUNCIATION']==0
 assert learner.choose(first,first_session,'en','catalyst','SYNTACTIC')['selected']=='SYNTACTIC'


def test_relevant_history_and_helpfulness_personalize_one_learner(learner):
 first='a'*64
 second='b'*64
 for key in (first,second):
  learner.survey(key,{'consent':True,'alias':'Test reader','difficulties':['VOCABULARY','CONCEPTUAL'],'preferred_style':'short','reading_settings':{}})
 first_session=learner.start(first,'en')['session_id']
 second_session=learner.start(second,'en')['session_id']
 event(learner,first,first_session,'help_request',{'span':'catalyst','category':'VOCABULARY'})
 event(learner,first,first_session,'session_end',{})
 first_session=learner.start(first,'en')['session_id']
 event(learner,first,first_session,'help_request',{'span':'catalyst','category':'VOCABULARY'})
 recommended=learner.choose(first,first_session,'en','catalyst')
 assert recommended['selected']=='VOCABULARY'
 assert recommended['source']=='learner_history'
 assert recommended['decision_factors']['relevant_request_counts']['VOCABULARY']==2
 steps=learner.choose(first,first_session,'en','catalyst','VOCABULARY','steps')
 event(learner,first,first_session,'optional_feedback',{'route_id':steps['route_id'],'decision':'accept'})
 updated=learner.choose(first,first_session,'en','catalyst')
 assert updated['style']=='steps'
 assert updated['decision_factors']['style_feedback_count']==1
 assert learner.choose(second,second_session,'en','catalyst')['selected']=='OTHER_UNCERTAIN'
 assert learner.choose(second,second_session,'en','catalyst','VOCABULARY')['style']=='short'
