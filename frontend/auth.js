const Auth = (() => {
  const API_BASE = 'http://127.0.0.1:8000';
  let _accessToken = null;

  const handoff = sessionStorage.getItem('_at_handoff');
  if (handoff) {
    _accessToken = handoff;
    sessionStorage.removeItem('_at_handoff');
  }

  if (!_accessToken && !sessionStorage.getItem('refresh_token')) {
    window.location.replace('index.html');
  }

  async function _refresh() {
    const rt = sessionStorage.getItem('refresh_token');
    if (!rt) { logout(); return null; }
    const res = await fetch(`${API_BASE}/admin/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) { logout(); return null; }
    const data = await res.json();
    _accessToken = data.access_token;
    sessionStorage.setItem('refresh_token', data.refresh_token);
    return _accessToken;
  }

  async function authFetch(url, options = {}) {
    if (!_accessToken) { _accessToken = await _refresh(); }
    if (!_accessToken) return null;
    const headers = { ...options.headers, 'Authorization': `Bearer ${_accessToken}` };
    let res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      _accessToken = await _refresh();
      if (!_accessToken) return null;
      res = await fetch(url, { ...options, headers: { ...options.headers, 'Authorization': `Bearer ${_accessToken}` } });
    }
    return res;
  }

  function logout() {
    const rt = sessionStorage.getItem('refresh_token');
    if (rt) {
      fetch(`${API_BASE}/admin/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      }).catch(() => {});
    }
    sessionStorage.clear();
    window.location.replace('index.html');
  }

  return {
    authFetch,
    logout,
    get username() { return sessionStorage.getItem('admin_username') || ''; },
  };
})();
