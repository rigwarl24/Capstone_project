// ===== Config: set USE_MOCK to false once the backend (Member 2) is ready =====
const USE_MOCK = true;
const API_URL = 'http://localhost:8000';

// ===== Ranks =====
const RANKS = [
  { name: 'Bronze', min: 0, cls: 'bg-orange-500/10 text-orange-600 ring-orange-500/20 dark:text-orange-400' },
  { name: 'Silver', min: 1200, cls: 'bg-slate-500/10 text-slate-600 ring-slate-500/20 dark:text-slate-300' },
  { name: 'Gold', min: 1500, cls: 'bg-yellow-500/10 text-yellow-700 ring-yellow-500/20 dark:text-yellow-400' },
  { name: 'Diamond', min: 1800, cls: 'bg-cyan-500/10 text-cyan-700 ring-cyan-500/20 dark:text-cyan-400' },
];
const rankInfo = e => [...RANKS].reverse().find(r => e >= r.min);
const rankOf = e => rankInfo(e).name;
const rankBadge = e => { const r = rankInfo(e); return `<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${r.cls}">${r.name}</span>`; };

const getUser = () => JSON.parse(localStorage.getItem('cr_user') || 'null');
const isDark = () => document.documentElement.classList.contains('dark');

function applyTheme(t) {
  document.documentElement.classList.toggle('dark', t === 'dark');
  localStorage.setItem('cr_theme', t);
  window.dispatchEvent(new Event('themechange'));
}
applyTheme(localStorage.getItem('cr_theme') || 'dark');

// ===== Demo data =====
const MOCK_PLAYERS = [
  { username: 'Sara_Dev', elo: 1795, wins: 52, losses: 9 },
  { username: 'Fariz', elo: 1620, wins: 34, losses: 12 },
  { username: 'Hafiza', elo: 1480, wins: 28, losses: 15 },
  { username: 'Danial', elo: 1310, wins: 19, losses: 14 },
  { username: 'Newbie42', elo: 1050, wins: 5, losses: 7 },
];
const lsUsers = () => JSON.parse(localStorage.getItem('cr_users') || '[]');

async function http(path, opts = {}) {
  const r = await fetch(API_URL + path, {
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (localStorage.getItem('cr_token') || '') },
    ...opts,
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Server error');
  return r.json();
}

// ===== API layer: endpoints expected from Member 2 =====
const api = {
  async register(username, email, password) {
    if (!USE_MOCK) return http('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) });
    const users = lsUsers();
    if (users.find(u => u.username.toLowerCase() === username.toLowerCase())) throw new Error('This username is already taken.');
    const u = { username, email, elo: 1000, wins: 0, losses: 0 };
    users.push(u);
    localStorage.setItem('cr_users', JSON.stringify(users));
    localStorage.setItem('cr_user', JSON.stringify(u));
    return u;
  },
  async login(username, password) {
    if (!USE_MOCK) {
      const d = await http('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      localStorage.setItem('cr_token', d.token);
      localStorage.setItem('cr_user', JSON.stringify(d.user));
      return d.user;
    }
    const u = lsUsers().find(x => x.username.toLowerCase() === username.toLowerCase());
    if (!u) throw new Error('No account found. Please create one first.');
    localStorage.setItem('cr_user', JSON.stringify(u));
    return u;
  },
  async leaderboard() {
    if (!USE_MOCK) return http('/leaderboard');
    return [...MOCK_PLAYERS, ...lsUsers()].sort((a, b) => b.elo - a.elo);
  },
  async history() {
    if (!USE_MOCK) return http('/users/me/matches');
    return [
      { opponent: 'Fariz', mode: 'Speed Duel', result: 'win', delta: 18, date: 'Nov 20, 2026' },
      { opponent: 'Hafiza', mode: 'Bug Hunt', result: 'loss', delta: -14, date: 'Nov 18, 2026' },
      { opponent: 'Danial', mode: 'Optimization Battle', result: 'win', delta: 12, date: 'Nov 15, 2026' },
    ];
  },
};

// ===== Shared navigation bar and footer =====
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.getElementById('nav');
  if (nav) {
    const u = getUser();
    const link = 'text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white';
    nav.className = 'sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80';
    nav.innerHTML = `
    <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
      <a href="index.html" class="flex items-center gap-2 text-lg font-bold tracking-tight">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 font-mono text-sm text-white">&lt;/&gt;</span>CodeRace
      </a>
      <nav class="flex items-center gap-5">
        <a href="leaderboard.html" class="${link}">Leaderboard</a>
        ${u ? `<a href="profile.html" class="${link}">${u.username}</a>
               <button id="logout" class="${link}">Log out</button>`
            : `<a href="login.html" class="${link}">Log in</a>
               <a href="register.html" class="btn-primary !py-1.5">Sign up</a>`}
        <button id="themeBtn" aria-label="Toggle theme" class="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
        </button>
      </nav>
    </div>`;
    document.getElementById('themeBtn').onclick = () => applyTheme(isDark() ? 'light' : 'dark');
    const lo = document.getElementById('logout');
    if (lo) lo.onclick = () => { localStorage.removeItem('cr_user'); localStorage.removeItem('cr_token'); location.href = 'index.html'; };
  }
  const f = document.getElementById('footer');
  if (f) {
    f.className = 'mt-24 border-t border-slate-200 dark:border-slate-800';
    f.innerHTML = `<div class="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:px-6">
      <span>© 2026 CodeRace · Capstone Project, Fall 2026–2027</span>
      <span>Real-time coding duels</span></div>`;
  }
});
