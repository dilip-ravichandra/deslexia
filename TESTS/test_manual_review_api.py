"""API fixtures only. Artifacts are redirected into pytest temporary storage."""
import json
import pytest
from fastapi.testclient import TestClient
import BACKEND.app as module
from ML import human_review as review
from TESTS.test_human_review import fixture_export

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(review,'ROOT',tmp_path)
    monkeypatch.setenv('DYSLEXIADAPT_ADMIN_TOKEN','audit-fixture-admin')
    return TestClient(module.app)

def files():
    return [('files',('a.json',json.dumps(fixture_export()),'application/json')),
            ('files',('b.json',json.dumps(fixture_export('reviewer_b')),'application/json'))]

def test_pool_is_public_but_merge_and_download_require_admin(client):
    assert client.get('/api/review/public-pool').status_code==200
    assert client.post('/api/admin/reviews/merge',files=files()).status_code==401
    response=client.post('/api/admin/reviews/merge',files=files(),headers={'x-admin-token':'audit-fixture-admin'})
    assert response.status_code==200,response.text
    rid=response.json()['review_id'];path=f'/api/admin/review-results/{rid}/reviewed.csv'
    assert client.get(path).status_code==401
    assert client.get(path,headers={'x-admin-token':'audit-fixture-admin'}).status_code==200
    assert client.get(f'/api/admin/review-results/{rid}/active.json',headers={'x-admin-token':'audit-fixture-admin'}).status_code==404

def test_invalid_merge_is_rejected_without_training(client):
    response=client.post('/api/admin/reviews/merge',files=[('files',('bad.json',b'{}','application/json'))],headers={'x-admin-token':'audit-fixture-admin'})
    assert response.status_code==422
