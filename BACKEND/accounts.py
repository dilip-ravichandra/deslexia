"""Local password accounts and consented learner profile setup."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SESSION_SECONDS = 12 * 60 * 60
KDF_ITERATIONS = 1_200_000
COOKIE = 'da_account_session'


class AccountStore:
    def __init__(self, path):
        self.path = path
        self.sessions = {}
        self.failures = {}
        self.lock = threading.Lock()
        with self.db() as database:
            database.execute('''CREATE TABLE IF NOT EXISTS learner_accounts (
                username TEXT PRIMARY KEY, profile_id TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL, verifier BLOB NOT NULL,
                nonce BLOB NOT NULL, encrypted_key BLOB NOT NULL,
                setup_complete INTEGER NOT NULL DEFAULT 1
            )''')
            columns = {row['name'] for row in database.execute('PRAGMA table_info(learner_accounts)')}
            if 'setup_complete' not in columns:
                database.execute('ALTER TABLE learner_accounts ADD COLUMN setup_complete INTEGER NOT NULL DEFAULT 1')
            database.execute('''CREATE TABLE IF NOT EXISTS account_library (
                profile_id TEXT NOT NULL, kind TEXT NOT NULL, items_json TEXT NOT NULL,
                PRIMARY KEY (profile_id, kind)
            )''')

    @contextmanager
    def db(self):
        database = sqlite3.connect(self.path, timeout=20)
        database.row_factory = sqlite3.Row
        try:
            with database:
                yield database
        finally:
            database.close()

    def library(self, profile_id, kind):
        with self.db() as database:
            row = database.execute('SELECT items_json FROM account_library WHERE profile_id=? AND kind=?',
                                   (profile_id, kind)).fetchone()
        return json.loads(row['items_json']) if row else []

    def save_library(self, profile_id, kind, items):
        with self.db() as database:
            database.execute('''INSERT INTO account_library (profile_id, kind, items_json)
                VALUES (?, ?, ?) ON CONFLICT(profile_id, kind) DO UPDATE SET items_json=excluded.items_json''',
                (profile_id, kind, json.dumps(items, ensure_ascii=False)))

    @staticmethod
    def username(value):
        username = value.strip().casefold()
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,31}', username):
            raise ValueError('Use 3–32 letters, numbers, underscores or hyphens for the username.')
        return username

    @staticmethod
    def password(value):
        if not 12 <= len(value) <= 128:
            raise ValueError('Use a password of 12–128 characters.')
        return value.encode('utf-8')

    @staticmethod
    def derived(password, salt):
        return hashlib.pbkdf2_hmac('sha256', password, salt, KDF_ITERATIONS, dklen=32)

    def register(self, username, password, learner_key, learner, pending=False):
        username = self.username(username)
        password = self.password(password)
        if not pending and not learner.enrolled(learner_key):
            raise ValueError('Create a consented learner profile before linking an account.')
        profile_id = hashlib.sha256(learner_key.encode()).hexdigest()
        salt, nonce = os.urandom(16), os.urandom(12)
        derived = self.derived(password, salt)
        verifier = hmac.digest(derived, b'DyslexiAdapt local account v1', 'sha256')
        ciphertext = AESGCM(derived).encrypt(nonce, learner_key.encode(), username.encode())
        try:
            with self.db() as database:
                database.execute('''INSERT INTO learner_accounts
                    (username,profile_id,salt,verifier,nonce,encrypted_key,setup_complete)
                    VALUES (?,?,?,?,?,?,?)''',
                                 (username, profile_id, salt, verifier, nonce, ciphertext, int(not pending)))
        except sqlite3.IntegrityError as error:
            raise ValueError('That username or learner profile already has an account.') from error
        return self.new_session(username, profile_id, learner_key, not pending)

    def complete_setup(self, learner_key, learner):
        if not learner.enrolled(learner_key):
            raise ValueError('Complete the reading profile before starting.')
        profile_id = hashlib.sha256(learner_key.encode()).hexdigest()
        with self.db() as database:
            updated = database.execute('''UPDATE learner_accounts SET setup_complete=1
                WHERE profile_id=? AND setup_complete=0''', (profile_id,)).rowcount
        if not updated:
            raise ValueError('This account is not waiting for profile setup.')
        with self.lock:
            for token_hash, session in list(self.sessions.items()):
                if session[1] == profile_id:
                    self.sessions[token_hash] = (*session[:4], True)

    def login(self, username, password, learner):
        username = self.username(username)
        password = self.password(password)
        with self.lock:
            count, until = self.failures.get(username, (0, 0))
            if count >= 5 and time.time() < until:
                raise ValueError('Too many attempts. Wait 15 minutes before trying again.')
        with self.db() as database:
            account = database.execute('SELECT * FROM learner_accounts WHERE username=?', (username,)).fetchone()
        salt = account['salt'] if account else b'\0' * 16
        derived = self.derived(password, salt)
        valid = account is not None and hmac.compare_digest(
            hmac.digest(derived, b'DyslexiAdapt local account v1', 'sha256'), account['verifier'])
        if not valid:
            with self.lock:
                attempts = self.failures.get(username, (0, 0))[0] + 1
                self.failures[username] = (attempts, time.time() + 900)
            raise ValueError('Username or password is incorrect.')
        try:
            learner_key = AESGCM(derived).decrypt(account['nonce'], account['encrypted_key'], username.encode()).decode()
        except (InvalidTag, UnicodeDecodeError) as error:
            raise ValueError('This account could not be opened. Use the original recovery key.') from error
        if account['setup_complete'] and not learner.enrolled(learner_key):
            raise ValueError('This learner profile no longer exists. Use the original recovery key.')
        with self.lock:
            self.failures.pop(username, None)
        return self.new_session(username, account['profile_id'], learner_key, bool(account['setup_complete']))

    def reset_password(self, username, password, learner_key, learner):
        username = self.username(username)
        password = self.password(password)
        profile_id = hashlib.sha256(learner_key.encode()).hexdigest()
        with self.db() as database:
            account = database.execute('SELECT setup_complete FROM learner_accounts WHERE username=? AND profile_id=?',
                                       (username, profile_id)).fetchone()
        if account is None or (account['setup_complete'] and not learner.enrolled(learner_key)):
            raise ValueError('The username and recovery key do not match an available account.')
        salt, nonce = os.urandom(16), os.urandom(12)
        derived = self.derived(password, salt)
        verifier = hmac.digest(derived, b'DyslexiAdapt local account v1', 'sha256')
        ciphertext = AESGCM(derived).encrypt(nonce, learner_key.encode(), username.encode())
        with self.db() as database:
            updated = database.execute('''UPDATE learner_accounts
                SET salt=?, verifier=?, nonce=?, encrypted_key=?
                WHERE username=? AND profile_id=?''',
                (salt, verifier, nonce, ciphertext, username, profile_id)).rowcount
        if not updated:
            raise ValueError('The username and recovery key do not match a linked account.')
        with self.lock:
            for token_hash, session in list(self.sessions.items()):
                if session[1] == profile_id:
                    self.sessions.pop(token_hash, None)
            self.failures.pop(username, None)
        return self.new_session(username, profile_id, learner_key, bool(account['setup_complete']))

    def new_session(self, username, profile_id, learner_key, setup_complete=True):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            self.sessions[token_hash] = (username, profile_id, learner_key, time.time() + SESSION_SECONDS, setup_complete)
        return token

    def current(self, token):
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            session = self.sessions.get(token_hash)
            if session and session[3] > time.time():
                return {'username': session[0], 'profile_id': session[1], 'learner_key': session[2],
                        'setup_complete': session[4]}
            self.sessions.pop(token_hash, None)
        return None

    def logout(self, token):
        if token:
            with self.lock:
                self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)

    def forget_profile(self, learner_key):
        profile_id = hashlib.sha256(learner_key.encode()).hexdigest()
        with self.db() as database:
            database.execute('DELETE FROM learner_accounts WHERE profile_id=?', (profile_id,))
            database.execute('DELETE FROM account_library WHERE profile_id=?', (profile_id,))
        with self.lock:
            for token_hash, session in list(self.sessions.items()):
                if session[1] == profile_id:
                    self.sessions.pop(token_hash, None)
