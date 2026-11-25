const $ = id => document.getElementById(id);
const TOTAL = 10, VISIBLE = 5;
const STARTER = `def two_sum(nums, target):\n    # Return [i, j] such that nums[i] + nums[j] == target\n    pass\n`;
let editor, remaining = 15 * 60, oppPassed = 0, ended = false;
const status = Array(TOTAL).fill('pending');

const me = getUser();
if (!me) location.href = 'login.html';
$('me').textContent = me.username; $('meElo').textContent = me.elo + ' Elo'; $('meAv').textContent = me.username[0].toUpperCase();
$('opp').textContent = 'Fariz'; $('oppElo').textContent = '1620 Elo'; // replace with data from Member 5 (WebSocket)

// ----- Monaco editor -----
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
require(['vs/editor/editor.main'], () => {
  editor = monaco.editor.create($('editor'), {
    value: STARTER, language: 'python', theme: isDark() ? 'vs-dark' : 'vs',
    automaticLayout: true, fontSize: 14, fontFamily: 'JetBrains Mono, monospace', tabSize: 4, insertSpaces: true,
    lineNumbers: 'on', autoIndent: 'full', minimap: { enabled: false }, scrollBeyondLastLine: false, padding: { top: 12 },
  });
  editor.onDidChangeModelContent(() => window.arena.onTyping && window.arena.onTyping(editor.getValue()));
});
window.addEventListener('themechange', () => window.monaco && monaco.editor.setTheme(isDark() ? 'vs-dark' : 'vs'));
$('fontSize').onchange = e => editor && editor.updateOptions({ fontSize: +e.target.value });

// ----- UI helpers -----
function log(text, type) {
  const c = { ok: 'text-green-400', err: 'text-red-400', info: 'text-slate-300' }[type || 'info'];
  $('console').insertAdjacentHTML('beforeend', `<div class="${c}">$ ${text}</div>`);
  $('console').parentElement.scrollTop = 1e9;
}
function renderTests() {
  const icon = {
    pass: '<svg class="h-4 w-4 text-green-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>',
    fail: '<svg class="h-4 w-4 text-red-500" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    pending: '<span class="block h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>',
  };
  $('tests').innerHTML = status.map((s, i) => `<li class="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800">
    <span>Test ${i + 1} <span class="ml-1 text-xs text-slate-500">${i < VISIBLE ? 'Visible' : 'Hidden'}</span></span>${icon[s]}</li>`).join('');
}
function setBar(who, n) { $(who + 'Bar').style.width = (n / TOTAL * 100) + '%'; $(who + 'Txt').textContent = `${n} / ${TOTAL}`; }
function endMatch(won) {
  if (ended) return; ended = true; clearInterval(tick); clearInterval(sim);
  const d = won ? 16 : -16;
  $('mTitle').textContent = won ? 'Victory' : 'Defeat';
  $('mTitle').className = 'text-3xl font-extrabold tracking-tight ' + (won ? 'text-green-500' : 'text-red-500');
  $('mText').textContent = won ? 'All tests passed. Well played.' : 'Your opponent finished first.';
  $('mElo').textContent = `${me.elo} → ${me.elo + d}  (${d > 0 ? '+' : ''}${d})`;
  $('modal').classList.replace('hidden', 'flex');
}

// ----- Integration hooks for Members 4 and 5 -----
// result = { passed: number, scope: 'visible' | 'all', message: string }
window.arena = {
  onOpponentUpdate(passed) { oppPassed = passed; setBar('opp', passed); if (passed >= TOTAL) endMatch(false); },
  onTestResult(r) {
    const upto = r.scope === 'all' ? TOTAL : VISIBLE;
    for (let i = 0; i < upto; i++) status[i] = i < r.passed ? 'pass' : 'fail';
    renderTests(); setBar('my', r.passed);
    log(r.message, r.passed >= upto ? 'ok' : 'err');
    if (r.scope === 'all' && r.passed >= TOTAL) endMatch(true);
  },
  onMatchEnd: endMatch,
  onTyping: null, // e.g. send a keystroke-activity pulse through the WebSocket
};

// ----- Timer -----
const tick = setInterval(() => {
  remaining--;
  $('timer').textContent = String(Math.floor(remaining / 60)).padStart(2, '0') + ':' + String(remaining % 60).padStart(2, '0');
  if (remaining === 60) $('timer').classList.add('text-red-500');
  if (remaining <= 0) endMatch(false);
}, 1000);

// ----- Buttons (MOCK: replace with the sandbox API / WebSocket) -----
const solved = () => editor && editor.getValue().includes('return');
$('runBtn').onclick = () => {
  log('Running visible tests…');
  setTimeout(() => window.arena.onTestResult(solved()
    ? { passed: VISIBLE, scope: 'visible', message: `${VISIBLE}/${VISIBLE} visible tests passed` }
    : { passed: 0, scope: 'visible', message: 'Test 1 failed: function returned None' }), 500);
};
$('submitBtn').onclick = () => {
  log('Submitting code…');
  setTimeout(() => window.arena.onTestResult(solved()
    ? { passed: TOTAL, scope: 'all', message: `${TOTAL}/${TOTAL} tests passed` }
    : { passed: 0, scope: 'all', message: 'Submission failed: 0/10 tests passed' }), 700);
};
$('forfeitBtn').onclick = () => $('confirm').classList.replace('hidden', 'flex');
$('cancelF').onclick = () => $('confirm').classList.replace('flex', 'hidden');
$('okF').onclick = () => { $('confirm').classList.replace('flex', 'hidden'); endMatch(false); };

// ----- Opponent simulation (MOCK) -----
const sim = setInterval(() => {
  $('oppStatus').textContent = Math.random() < 0.5 ? 'Typing…' : 'Running tests…';
  if (Math.random() < 0.2) window.arena.onOpponentUpdate(Math.min(TOTAL, oppPassed + 1));
}, 1500);
renderTests();
