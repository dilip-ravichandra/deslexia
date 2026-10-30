(() => {
  'use strict';

  const by = id => document.getElementById(id);
  const status = message => { by('status').textContent = message; };

  async function checkAccount() {
    const response = await fetch('/api/account', {cache: 'no-store'});
    if (!response.ok) throw Error('The local helper is unavailable. Restart it and try again.');
    const account = await response.json();
    if (!account.signed_in) {
      location.replace('account.html');
      return;
    }
    by('username').textContent = account.username;
    by('setup-panel').hidden = !!account.setup_complete;
    by('already-done').hidden = !account.setup_complete;
    status(account.setup_complete ? 'Your saved profile is ready.' : 'Choose a starting point. You can change support choices later.');
  }

  by('setup-form').onsubmit = async event => {
    event.preventDefault();
    const languages = [...document.querySelectorAll('[name=study-language]:checked')].map(input => input.value);
    if (!languages.length) {
      status('Choose at least one language you read or study in.');
      return;
    }
    by('save').disabled = true;
    status('Saving your starting profile…');
    try {
      const response = await fetch('/api/account/profile-setup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          alias: by('alias').value,
          preferred_language: by('language').value,
          study_languages: languages,
          preferred_style: by('style').value,
          difficulties: [...document.querySelectorAll('[name=need]:checked')].map(input => input.value),
          consent: by('consent').checked,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw Error(typeof result.detail === 'string' ? result.detail : 'Profile setup could not be saved.');
      location.href = '/';
    } catch (error) {
      status(error.message);
      by('save').disabled = false;
    }
  };

  by('logout').onclick = async () => {
    try {
      const response = await fetch('/api/account/logout', {method: 'POST'});
      if (!response.ok) throw Error('Log out failed. Try again.');
      sessionStorage.removeItem('da_legacy_active');
      sessionStorage.removeItem('da_guest_mode');
      location.href = 'account.html';
    } catch (error) {
      status(error.message);
    }
  };

  checkAccount().catch(error => status(error.message));
})();
