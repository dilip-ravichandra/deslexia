"""Synthetic reviewer decisions, isolated outputs; no genuine annotation claim."""
import copy
import csv
import json
from datetime import datetime,timedelta,timezone
import pytest
from ML import human_review as review

def fixture_export(reviewer='reviewer_a',category='VOCABULARY'):
    source=review.pool();row=next(r for r in source['rows'] if r['language']=='en');now=datetime.now(timezone.utc)
    return {'protocol':source['protocol'],'source_pool_sha256':source['sha256'],'reviewer_id':reviewer,
        'language':'en','session_id':'engineering_fixture_session','independent_review':True,'language_competent':True,
        'started_at':(now-timedelta(minutes=2)).isoformat(),'submitted_at':(now-timedelta(seconds=1)).isoformat(),
        'judgments':[{'span_id':row['span_id'],'source':row,'category':category,'confidence':3,
            'rationale':'Engineering fixture only; no actual human judgment.', 'reviewed_at':(now-timedelta(minutes=1)).isoformat()}]}

def test_blank_public_pool_excludes_routing_labels():
    source=review.pool()
    assert len(source['rows'])==100
    assert 'category' not in source['source_columns']

@pytest.mark.parametrize('mutate',[
    lambda x:x.update(source_pool_sha256='0'*64),
    lambda x:x.update(independent_review=False),
    lambda x:x.update(language_competent=False),
    lambda x:x.update(reviewer_id='gpt'),
    lambda x:x['judgments'][0].update(confidence=True),
    lambda x:x['judgments'][0].update(confidence=0.5),
    lambda x:x['judgments'][0]['source'].update(text='Changed source'),
    lambda x:x['judgments'].append(copy.deepcopy(x['judgments'][0])),
    lambda x:x['judgments'][0].update(rationale=''),
])
def test_invalid_review_exports_rejected(mutate):
    value=fixture_export();mutate(value)
    with pytest.raises(ValueError):review.validate(value,review.pool())

def test_merge_preserves_disagreement_missing_reviews_and_raw_opinions(tmp_path):
    first=fixture_export();second=fixture_export('reviewer_b','CONCEPTUAL')
    result=review.merge([first,second],tmp_path)
    assert result['counts']['disagreement']==1 and result['counts']['unreviewed']==99
    folder=tmp_path/result['review_id']
    with (folder/'reviewed.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==1 and rows[0]['category']=='OTHER_UNCERTAIN'
    assert len(json.loads((folder/'raw-exports.json').read_text(encoding='utf-8')))==2
    assert result['agreement']['hi']['unanimous_fraction'] is None

def test_agreement_on_uncertainty_is_not_forced_to_primary_label(tmp_path):
    result=review.merge([fixture_export(category='OTHER_UNCERTAIN'),fixture_export('reviewer_b','OTHER_UNCERTAIN')],tmp_path)
    assert result['counts']['agreed']==1
    assert result['agreement']['en']['pairwise'][0]['cohen_kappa'] is None

def test_same_reviewer_cannot_count_as_two_people(tmp_path):
    with pytest.raises(ValueError):review.merge([fixture_export('Reviewer_A'),fixture_export('reviewer_a')],tmp_path)
