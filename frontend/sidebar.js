(function () {
  const NAV_ITEMS = [
    { icon: 'dashboard',  label: 'Dashboard',      href: 'dashboard.html',       page: 'dashboard.html' },
    { icon: 'chat',       label: 'Conversations',  href: 'conversationTab.html', page: 'conversationTab.html' },
    { icon: 'smart_toy',  label: 'Agent Settings', href: 'agentManager.html',    page: 'agentManager.html' },
  ];

  function render() {
    const aside = document.getElementById('sidebar');
    if (!aside) return;

    const page = window.location.pathname.split('/').pop() || 'dashboard.html';

    const navLinks = NAV_ITEMS.map(item => {
      const isActive = item.page !== null && item.page === page;
      const stateClasses = isActive
        ? 'border-l-4 border-[#25D366] bg-slate-800/50 text-white font-semibold'
        : 'rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50';
      const iconColor = isActive ? 'text-[#25D366]' : '';
      const fillStyle = isActive ? "font-variation-settings: 'FILL' 1;" : '';
      return `<a class="flex items-center gap-3 px-4 py-2.5 transition-colors duration-200 group ${stateClasses}" href="${item.href}">
        <span class="material-symbols-outlined text-lg ${iconColor}" style="${fillStyle}">${item.icon}</span>
        <span class="text-sm font-medium">${item.label}</span>
      </a>`;
    }).join('\n');

    aside.innerHTML = `
      <div class="px-5 mb-6 flex items-center gap-2.5">
        <div class="w-8 h-8 bg-[#25D366] rounded-lg flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-white text-lg"
                style="font-variation-settings: 'FILL' 1;">smart_toy</span>
        </div>
        <h1 class="text-lg font-black text-white leading-tight tracking-tight">Vendora AI</h1>
      </div>
      <nav class="flex-1 px-3 space-y-0.5">
        ${navLinks}
      </nav>
      <div class="mt-auto px-3 pt-4 border-t border-slate-800 space-y-0.5">
        <a class="flex items-center gap-3 px-4 py-2.5 text-slate-400 hover:text-white transition-colors duration-200 hover:bg-slate-800/50 rounded-lg"
           href="#">
          <span class="material-symbols-outlined text-lg">settings</span>
          <span class="text-sm font-medium">Settings</span>
        </a>
        <button onclick="if(typeof Auth!=='undefined')Auth.logout()"
                class="w-full flex items-center gap-3 px-4 py-2.5 text-slate-400 hover:text-white hover:bg-red-900/40 transition-colors duration-200 rounded-lg">
          <span class="material-symbols-outlined text-lg">logout</span>
          <span class="text-sm font-medium">Log Out</span>
        </button>
      </div>`;
  }

  function wireHeader() {
    const profileBtn = document.getElementById('profile-btn');
    const dropdown   = document.getElementById('profile-dropdown');
    const usernameEl = document.getElementById('header-username');
    const avatarEl   = document.getElementById('profile-avatar');
    const logoutBtn  = document.getElementById('logout-btn');

    const name = (typeof Auth !== 'undefined' && Auth.username) ? Auth.username : 'Admin';
    if (usernameEl) usernameEl.textContent = name;
    if (avatarEl)   avatarEl.textContent   = name[0].toUpperCase();

    if (profileBtn && dropdown) {
      profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
      });
      document.addEventListener('click', () => dropdown.classList.add('hidden'));
    }

    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        if (typeof Auth !== 'undefined') Auth.logout();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { render(); wireHeader(); });
  } else {
    render();
    wireHeader();
  }
})();
