(() => {
  'use strict';

  const by = id => document.getElementById(id);
  const keyName = 'da_learner_key_v1';
  let profileId = '';
  let checkedOlderKey = '';
  let createdKey = '';

  function status(message) {
    by('status').textContent = message;
  }

  function browserKey() {
    return localStorage.getItem(keyName);
  }

  async function request(path, body, recoveryKey) {
    const headers = {'Content-Type': 'application/json'};
    if (recoveryKey) headers['x-learner-key'] = recoveryKey;
    const response = await fetch(path, {method: 'POST', headers, body: JSON.stringify(body)});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (path === '/api/account/signup' && response.status === 404) {
        throw Error('Restart the local helper to enable the new signup flow.');
      }
      throw Error(typeof result.detail === 'string' ? result.detail : 'This action could not be completed.');
    }
    return result;
  }

  function show(view) {
    by('login-panel').hidden = view !== 'login';
    by('create-panel').hidden = view !== 'create';
    by('created-panel').hidden = view !== 'created';
    by('choose-login').setAttribute('aria-pressed', String(view === 'login'));
    by('choose-create').setAttribute('aria-pressed', String(view === 'create'));
    by('entry-tabs').hidden = view === 'created';
    by('older-profile').hidden = view === 'created';
    by('reset-panel').hidden = view === 'created';
  }

  function confirmDisconnect() {
    if (!browserKey()) return true;
    return confirm('An older profile key is stored in this browser. If it belongs to you, choose Cancel and open "Have an older profile or recovery key?" to copy it first. Continuing disconnects the browser but does not delete that profile. Continue?');
  }

  function clearOldConnection() {
    localStorage.removeItem(keyName);
    sessionStorage.removeItem('da_legacy_active');
    checkedOlderKey = '';
    by('older-key').value = '';
    by('older-key-visible').textContent = '';
    by('older-key-visible').hidden = true;
    by('link-form').hidden = true;
    by('continue-older').hidden = true;
  }

  async function refresh() {
    const response = await fetch('/api/account', {cache: 'no-store'});
    if (!response.ok) throw Error('Account status is unavailable.');
    const account = await response.json();
    by('signed-in').hidden = !account.signed_in;
    by('entry').hidden = !!account.signed_in;
    if (account.signed_in) {
      profileId = account.profile_id;
      by('current-username').textContent = account.username;
      by('signed-ready').hidden = account.setup_complete === false;
      by('signed-pending').hidden = account.setup_complete !== false;
      by('old-library').hidden = account.setup_complete === false || !['da_passages_v2', 'da_notes_v2'].some(name => localStorage.getItem(name));
      status(account.setup_complete === false ? 'Your account is ready. Finish profile setup before reading.' : 'Your local account is still signed in. Choose Continue, Switch, or Create a separate account.');
    } else {
      profileId = '';
      show(new URLSearchParams(location.search).has('create') ? 'create' : 'login');
      status('Choose Sign in, Create account, or Read as guest.');
    }
  }

  async function leaveAccount(view) {
    if (!confirmDisconnect()) return;
    await request('/api/account/logout', {});
    clearOldConnection();
    sessionStorage.removeItem('da_guest_mode');
    by('signed-in').hidden = true;
    by('entry').hidden = false;
    by('login-form').reset();
    by('create-form').reset();
    by('older-profile').open = false;
    by('reset-panel').open = false;
    show(view);
    status(view === 'create' ? 'Create a new account with a fresh profile.' : 'Signed out. Choose the account you want to open.');
    by(view === 'create' ? 'create-username' : 'login-username').focus();
  }

  async function guest() {
    if (!confirmDisconnect()) return;
    await request('/api/account/logout', {});
    clearOldConnection();
    sessionStorage.setItem('da_guest_mode', '1');
    location.href = '/?guest=1';
  }

  by('choose-login').onclick = () => show('login');
  by('choose-create').onclick = () => show('create');
  by('switch-account').onclick = () => leaveAccount('login').catch(error => status(error.message));
  by('new-user').onclick = () => leaveAccount('create').catch(error => status(error.message));
  by('guest').onclick = () => guest().catch(error => status(error.message));
  by('guest-signed-in').onclick = () => guest().catch(error => status(error.message));
  by('show-reset').onclick = () => {
    by('reset-panel').open = true;
    by('reset-username').focus();
  };

  by('login-form').onsubmit = async event => {
    event.preventDefault();
    if (!confirmDisconnect()) return;
    const button = event.submitter;
    button.disabled = true;
    try {
      const result = await request('/api/account/login', {
        username: by('login-username').value,
        password: by('login-password').value,
      });
      clearOldConnection();
      sessionStorage.removeItem('da_guest_mode');
      location.href = result.setup_complete === false ? 'profile-setup.html' : '/';
    } catch (error) {
      status(error.message);
    } finally {
      button.disabled = false;
    }
  };

  by('create-form').onsubmit = async event => {
    event.preventDefault();
    if (!confirmDisconnect()) return;
    const button = event.submitter;
    button.disabled = true;
    status('Creating your separate local account…');
    try {
      const result = await request('/api/account/signup', {
        username: by('create-username').value,
        password: by('create-password').value,
      });
      createdKey = result.recovery_key;
      clearOldConnection();
      sessionStorage.removeItem('da_guest_mode');
      by('created-key').textContent = createdKey;
      by('created-confirmed').checked = false;
      by('created-continue').setAttribute('aria-disabled', 'true');
      show('created');
      status('Account created. Save the recovery key, then set up reading support.');
      by('created-title').focus();
    } catch (error) {
      status(error.message);
    } finally {
      button.disabled = false;
    }
  };

  by('created-confirmed').onchange = () => {
    by('created-continue').setAttribute('aria-disabled', String(!by('created-confirmed').checked));
  };
  by('created-continue').onclick = event => {
    if (!by('created-confirmed').checked) event.preventDefault();
  };
  by('copy-created-key').onclick = async () => {
    try {
      await navigator.clipboard.writeText(createdKey);
      status('Recovery key copied. Keep it private.');
    } catch {
      status('Copy unavailable. Select and copy the visible key.');
    }
  };

  by('check-older').onclick = async () => {
    const candidate = (by('older-key').value.trim() || browserKey() || '').toLowerCase();
    checkedOlderKey = '';
    by('link-form').hidden = true;
    by('continue-older').hidden = true;
    by('older-key-visible').hidden = true;
    if (!/^[a-f0-9]{64}$/.test(candidate)) {
      by('older-status').textContent = 'Enter a 64-character recovery key, or use a profile already saved in this browser.';
      return;
    }
    try {
      const response = await fetch('/api/learner/report', {headers: {'x-learner-key': candidate}});
      const report = await response.json();
      if (!response.ok) throw Error('That key did not open a profile on this helper.');
      checkedOlderKey = candidate;
      by('older-status').textContent = 'This key opens the profile named ' + report.profile.alias + '. Link it only if it is yours.';
      by('older-key-visible').textContent = candidate;
      by('older-key-visible').hidden = false;
      by('link-form').hidden = false;
      by('continue-older').hidden = false;
    } catch (error) {
      by('older-status').textContent = error.message;
    }
  };

  by('continue-older').onclick = () => {
    if (!checkedOlderKey) return;
    if (browserKey() && browserKey() !== checkedOlderKey && !confirmDisconnect()) return;
    localStorage.setItem(keyName, checkedOlderKey);
    sessionStorage.setItem('da_legacy_active', '1');
    sessionStorage.removeItem('da_guest_mode');
    location.href = '/';
  };

  by('link-form').onsubmit = async event => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      await request('/api/account/register', {
        username: by('link-username').value,
        password: by('link-password').value,
      }, checkedOlderKey);
      clearOldConnection();
      sessionStorage.removeItem('da_guest_mode');
      location.href = '/';
    } catch (error) {
      status(error.message);
    } finally {
      button.disabled = false;
    }
  };

  by('reset-form').onsubmit = async event => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    try {
      const result = await request('/api/account/reset', {
        username: by('reset-username').value,
        password: by('reset-password').value,
      }, by('reset-key').value.trim().toLowerCase());
      clearOldConnection();
      sessionStorage.removeItem('da_guest_mode');
      location.href = result.setup_complete === false ? 'profile-setup.html' : '/';
    } catch (error) {
      status(error.message);
    } finally {
      button.disabled = false;
    }
  };

  by('import-old').onclick = async () => {
    if (!profileId || !confirm('Move the old browser-only passages and notes into this account? Only continue if they are yours.')) return;
    try {
      const changes = [];
      for (const [name, kind] of [['da_passages_v2', 'passages'], ['da_notes_v2', 'notes']]) {
        const old = JSON.parse(localStorage.getItem(name) || '[]');
        const response = await fetch('/api/account/library/' + kind);
        if (!response.ok) throw Error('Could not load this account’s library.');
        const current = (await response.json()).items;
        if (!Array.isArray(old) || !Array.isArray(current)) throw Error('Saved library format is invalid.');
        const seen = new Set(current.map(item => item.id));
        const merged = [...current, ...old.filter(item => item && typeof item.id === 'string' && !seen.has(item.id))].slice(0, 200);
        changes.push({name, kind, merged});
      }
      for (const change of changes) {
        const response = await fetch('/api/account/library/' + change.kind, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items: change.merged})});
        if (!response.ok) throw Error('Could not save the ' + change.kind + '. Your old browser copies remain.');
        localStorage.removeItem(change.name);
      }
      by('old-library').hidden = true;
      status('Old browser library moved into this account.');
    } catch (error) {
      status('Could not move the old library: ' + error.message);
    }
  };

  refresh().catch(error => {
    by('entry').hidden = false;
    show('login');
    status('Could not reach the local helper: ' + error.message);
  });
})();
