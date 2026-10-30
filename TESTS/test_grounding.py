"""Authored failure cases and controlled completions, not live model evaluation."""
import json
import pytest
from ML.grounding import screen

def raw(text,evidence,source='passage'):
    return json.dumps({'claims':[{'text':text,'evidence':evidence,'source':source}]},ensure_ascii=False)

@pytest.mark.parametrize('language,text,added',[
    ('en','Plants use sunlight.','Plants require a high temperature.'),
    ('hi','पौधे सूर्य के प्रकाश का उपयोग करते हैं।','पौधों के लिए उच्च तापमान जरूरी है।'),
    ('kn','ಸಸ್ಯಗಳು ಬೆಳಕನ್ನು ಬಳಸುತ್ತವೆ.','ಸಸ್ಯಗಳಿಗೆ ಹೆಚ್ಚಿನ ತಾಪಮಾನ ಬೇಕು.'),
    ('ta','தாவரங்கள் ஒளியைப் பயன்படுத்துகின்றன.','தாவரங்களுக்கு அதிக வெப்பநிலை தேவை.')])
def test_unsupported_temperature_is_rejected(language,text,added):
    result=screen(raw(added,text),text,'',language)
    assert result['status']=='rejected' and 'introduced_temperature' in result['flags']
    assert not result['claims'] and not result['meaning_guaranteed']

def test_invented_quote_quantity_and_lost_negation():
    assert 'evidence_not_in_source' in screen(raw('Water freezes.','Made up quote.'),'Real source.','','en')['flags']
    assert 'introduced_quantity' in screen(raw('It takes 20 days.','It takes 2 days.'),'It takes 2 days.','','en')['flags']
    assert 'lost_negation' in screen(raw('Students may enter.','Students may not enter.'),'Students may not enter.','','en')['flags']

def test_empty_and_malformed_output_are_withheld():
    for value in ['plain prose','{}','{"claims":[]}',raw('Valid claim.','tiny',source='invented')]:
        assert screen(value,'tiny','','en')['status']=='rejected'

def test_real_generation_path_retries_and_never_returns_rejected_draft(monkeypatch):
    import ML.local_generation as generation
    import ML.visual_support as vision
    outputs=iter([raw('Plants require a high temperature.','Plants use sunlight.'),raw('Plants use light.','Plants use sunlight.')])
    class ControlledCompletion:
        def create_completion(self,**kwargs):return {'choices':[{'text':next(outputs),'finish_reason':'stop'}]}
    monkeypatch.setattr(generation,'available',lambda:True)
    monkeypatch.setattr(generation,'_MODEL',ControlledCompletion())
    monkeypatch.setattr(vision,'close',lambda:None)
    result=generation.generate('Plants','Plants use sunlight.','CONCEPTUAL','short')
    assert result['explanation']=='Plants use light.'
    assert len(result['quality']['attempts'])==2
    assert result['quality']['status']=='screened'

def test_two_rejected_drafts_are_withheld(monkeypatch):
    import ML.local_generation as generation
    import ML.visual_support as vision
    class ControlledCompletion:
        def create_completion(self,**kwargs):return {'choices':[{'text':'not json','finish_reason':'stop'}]}
    monkeypatch.setattr(generation,'available',lambda:True)
    monkeypatch.setattr(generation,'_MODEL',ControlledCompletion())
    monkeypatch.setattr(vision,'close',lambda:None)
    result=generation.generate('Plants','Plants use sunlight.','CONCEPTUAL','short')
    assert result['withheld'] and result['explanation']==''
