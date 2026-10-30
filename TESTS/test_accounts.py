import sqlite3

import pytest
from fastapi.testclient import TestClient

import BACKEND.app as module
from BACKEND.accounts import AccountStore
from BACKEND.adaptive import AdaptiveService
from BACKEND.learner import LearnerModel, identity


@pytest.fixture
def accounts_api(tmp_path, monkeypatch):
    service = AdaptiveService(tmp_path)
    learner = LearnerModel(service.db_path)
    accounts = AccountStore(service.db_path)
    monkeypatch.setattr(module, 'adaptive', service)
    monkeypatch.setattr(module, 'learner', learner)
    monkeypatch.setattr(module, 'accounts', accounts)
    first_key, second_key = 'a' * 64, 'b' * 64
    learner.survey(first_key, {'consent': True, 'alias': 'First', 'difficulties': ['VOCABULARY']})
    learner.survey(second_key, {'consent': True, 'alias': 'Second', 'difficulties': ['PRONUNCIATION']})
    return TestClient(module.app), service.db_path, first_key, second_key


def test_account_registration_login_and_profile_isolation(accounts_api):
    client, database_path, first_key, second_key = accounts_api
    password = 'a-long-local-password'
    registration = client.post('/api/account/register', headers={'x-learner-key': first_key},
                               json={'username': 'Alice', 'password': password})
    assert registration.status_code == 200
    assert client.get('/api/account').json()['profile_id'] == identity(first_key)
    assert client.get('/api/learner/report', headers={'x-learner-key': second_key}).json()['profile']['alias'] == 'First'
    with sqlite3.connect(database_path) as database:
        row = database.execute('SELECT encrypted_key FROM learner_accounts WHERE username=?', ('alice',)).fetchone()
        assert first_key.encode() not in row[0]
    assert client.post('/api/account/logout').status_code == 200
    assert client.get('/api/learner/report').status_code == 422
    assert client.post('/api/account/login', json={'username': 'alice', 'password': 'wrong-password-123'}).status_code == 401
    assert client.post('/api/account/login', json={'username': 'alice', 'password': password}).status_code == 200
    assert client.get('/api/learner/report').json()['profile']['alias'] == 'First'
    assert client.post('/api/account/register', headers={'x-learner-key': second_key},
                       json={'username': 'Alice', 'password': password}).status_code == 422


def test_account_library_persists_across_login_and_is_isolated(accounts_api):
    client, database_path, first_key, second_key = accounts_api
    password = 'a-long-local-password'
    assert client.get('/api/account/library/passages').status_code == 401
    assert client.post('/api/account/register', headers={'x-learner-key': first_key},
                       json={'username': 'alice', 'password': password}).status_code == 200
    item = {'id': 'passage-1', 'title': 'Science', 'text': 'A seed grows.', 'created_at': ''}
    assert client.put('/api/account/library/passages', json={'items': [item]}).status_code == 200
    assert client.get('/api/account/library/passages').json()['items'] == [item]
    assert client.put('/api/account/library/passages', json={'items': [item, item]}).status_code == 422
    assert client.post('/api/account/logout').status_code == 200
    assert client.get('/api/account/library/passages').status_code == 401
    module.accounts = AccountStore(database_path)
    assert client.post('/api/account/register', headers={'x-learner-key': second_key},
                       json={'username': 'bob', 'password': password}).status_code == 200
    assert client.get('/api/account/library/passages').json()['items'] == []
    assert client.post('/api/account/logout').status_code == 200
    assert client.post('/api/account/login', json={'username': 'alice', 'password': password}).status_code == 200
    assert client.get('/api/account/library/passages').json()['items'] == [item]
    assert client.delete('/api/profile').status_code == 200
    with sqlite3.connect(database_path) as database:
        assert database.execute('SELECT COUNT(*) FROM account_library').fetchone()[0] == 0


def test_accounts_survive_restart_and_deletion_clears_access(accounts_api):
    client, database_path, first_key, _ = accounts_api
    password = 'another-long-password'
    assert client.post('/api/account/register', headers={'x-learner-key': first_key},
                       json={'username': 'reader', 'password': password}).status_code == 200
    assert client.post('/api/account/logout').status_code == 200
    module.accounts = AccountStore(database_path)
    assert client.post('/api/account/login', json={'username': 'reader', 'password': password}).status_code == 200
    replacement = 'a-replacement-password'
    assert client.post('/api/account/reset', headers={'x-learner-key': first_key},
                       json={'username': 'reader', 'password': replacement}).status_code == 200
    assert client.post('/api/account/logout').status_code == 200
    assert client.post('/api/account/login', json={'username': 'reader', 'password': password}).status_code == 401
    assert client.post('/api/account/login', json={'username': 'reader', 'password': replacement}).status_code == 200
    assert client.delete('/api/profile').status_code == 200
    assert client.get('/api/account').json()['signed_in'] is False
    assert client.post('/api/account/login', json={'username': 'reader', 'password': replacement}).status_code == 401
    assert client.post('/api/account/login', headers={'origin': 'http://other.local'},
                       json={'username': 'reader', 'password': password}).status_code == 403


def test_new_account_creates_separate_profile_without_reusing_browser_key(accounts_api):
    client, database_path, first_key, _ = accounts_api
    before = client.get('/api/learner/report', headers={'x-learner-key': first_key}).json()
    old_password = 'first-account-password'
    assert client.post('/api/account/register', headers={'x-learner-key': first_key},
                       json={'username': 'previous_reader', 'password': old_password}).status_code == 200
    assert client.get('/api/account').json()['profile_id'] == identity(first_key)
    payload = {'username': 'new_reader', 'password': 'private-long-password', 'alias': 'New Reader',
               'study_languages': ['en'], 'preferred_language': 'en', 'preferred_style': 'steps',
               'difficulties': ['PRONUNCIATION'], 'consent': True}
    response = client.post('/api/account/create', headers={'x-learner-key': first_key}, json=payload)
    assert response.status_code == 200
    new_key = response.json()['recovery_key']
    assert new_key != first_key
    assert client.get('/api/account').json()['profile_id'] == identity(new_key)
    report = client.get('/api/learner/report').json()
    assert report['profile']['alias'] == 'New Reader'
    assert report['metrics']['events'] == 0
    assert before['profile']['alias'] == 'First'
    with sqlite3.connect(database_path) as database:
        count = database.execute('SELECT COUNT(*) FROM learner_surveys').fetchone()[0]
    assert count == 3

    assert client.post('/api/account/create', json=payload).status_code == 422
    assert client.post('/api/account/create', json={**payload, 'consent': False}).status_code == 422
    with sqlite3.connect(database_path) as database:
        assert database.execute('SELECT COUNT(*) FROM learner_surveys').fetchone()[0] == count
    assert client.get('/api/learner/report').json()['profile']['alias'] == 'New Reader'
    assert client.post('/api/account/logout').status_code == 200
    assert client.post('/api/account/login', json={'username': 'previous_reader',
                                                  'password': old_password}).status_code == 200
    assert client.get('/api/learner/report').json()['profile']['alias'] == 'First'


def test_signup_requires_separate_profile_setup_and_survives_login(accounts_api):
    client, database_path, first_key, _ = accounts_api
    credentials = {'username': 'new_student', 'password': 'private-long-password'}
    signup = client.post('/api/account/signup', headers={'x-learner-key': first_key}, json=credentials)
    assert signup.status_code == 200
    pending_key = signup.json()['recovery_key']
    assert pending_key != first_key
    assert client.get('/api/account').json()['setup_complete'] is False
    assert client.get('/api/learner/state', headers={'x-learner-key': first_key}).json()['enrolled'] is False
    assert client.get('/api/learner/report', headers={'x-learner-key': first_key}).status_code == 422
    with sqlite3.connect(database_path) as database:
        assert database.execute('SELECT COUNT(*) FROM learner_surveys').fetchone()[0] == 2
    assert client.post('/api/account/logout').status_code == 200
    assert client.post('/api/account/login', json=credentials).json()['setup_complete'] is False
    assert client.post('/api/account/profile-setup', json={
        'alias': 'New Student', 'preferred_language': 'en', 'study_languages': ['en'],
        'preferred_style': 'steps', 'difficulties': ['VOCABULARY', 'PRONUNCIATION'],
        'consent': False,
    }).status_code == 422
    assert client.post('/api/account/profile-setup', json={
        'alias': 'New Student', 'preferred_language': 'en', 'study_languages': ['en'],
        'preferred_style': 'steps', 'difficulties': ['VOCABULARY', 'PRONUNCIATION'],
        'consent': True,
    }).status_code == 200
    assert client.get('/api/account').json()['setup_complete'] is True
    report = client.get('/api/learner/report').json()
    assert report['profile']['alias'] == 'New Student'
    assert report['survey']['difficulties'] == ['VOCABULARY', 'PRONUNCIATION']
    assert client.post('/api/account/profile-setup', json={'study_languages': ['en'], 'consent': True}).status_code == 409
    assert client.post('/api/account/logout').status_code == 200
    assert client.post('/api/account/login', json=credentials).json()['setup_complete'] is True
    assert client.get('/api/learner/report').json()['profile']['alias'] == 'New Student'


def test_old_account_table_migrates_to_completed_setup(tmp_path):
    database_path = tmp_path / 'old.sqlite3'
    with sqlite3.connect(database_path) as database:
        database.execute('''CREATE TABLE learner_accounts (
            username TEXT PRIMARY KEY, profile_id TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL, verifier BLOB NOT NULL,
            nonce BLOB NOT NULL, encrypted_key BLOB NOT NULL)''')
    AccountStore(database_path)
    with sqlite3.connect(database_path) as database:
        columns = {row[1] for row in database.execute('PRAGMA table_info(learner_accounts)')}
    assert 'setup_complete' in columns


def test_research_overview_uses_actual_consent_records(accounts_api, monkeypatch):
    client, _, first_key, _ = accounts_api
    monkeypatch.setenv('DYSLEXIADAPT_ADMIN_TOKEN', 'test-research-token')
    assert client.get('/api/admin/learner-overview').status_code == 401
    headers = {'x-admin-token': 'test-research-token'}
    before = client.get('/api/admin/learner-overview', headers=headers).json()
    assert before['profiles'] == 2
    assert sum(before['explicit_requests'].values()) == 0
    session = client.post('/api/learner/session', headers={'x-learner-key': first_key},
                          json={'language': 'en'}).json()['session_id']
    assert client.post('/api/learner/event', headers={'x-learner-key': first_key}, json={
        'client_id': 'request-event-001', 'session_id': session, 'language': 'en',
        'kind': 'help_request', 'payload': {'span': 'photosynthesis', 'category': 'VOCABULARY'},
    }).status_code == 200
    after = client.get('/api/admin/learner-overview', headers=headers).json()
    assert after['explicit_requests']['VOCABULARY'] == 1
    assert 'First' not in str(after)
