const { app, BrowserWindow, ipcMain, screen, Tray, Menu, Notification, nativeImage, shell, powerMonitor } = require('electron');
const path = require('path');
const fs = require('fs');

const APP_ID = 'com.otterpal.reminders'; // kept so Windows treats the renamed app as the same one
const APP_NAME = 'Desktop Pal';

// Renamed from "Otter Pal": keep the saved reminders by moving them to the new data folder once.
app.setName(APP_NAME);
(() => {
  try {
    const appData = app.getPath('appData');
    const newDir = path.join(appData, APP_NAME), oldDir = path.join(appData, 'Otter Pal');
    app.setPath('userData', newDir);
    const nf = path.join(newDir, 'otterpal-data.json'), of = path.join(oldDir, 'otterpal-data.json');
    if (!fs.existsSync(nf) && fs.existsSync(of)) { fs.mkdirSync(newDir, { recursive: true }); fs.copyFileSync(of, nf); }
  } catch (_) {}
})();
app.setAppUserModelId(APP_ID);
// Transparent always-on-top windows can come out invisible with GPU compositing on some Windows setups,
// so the graphics card is off unless the user turns it on in Settings (read early: must be decided before startup).
const EARLY = (() => { try { return JSON.parse(fs.readFileSync(path.join(app.getPath('userData'), 'otterpal-data.json'), 'utf8')).settings || {}; } catch (_) { return {}; } })();
if (!EARLY.gpu) app.disableHardwareAcceleration();

function log(...a) {
  try { fs.appendFileSync(path.join(app.getPath('userData'), 'otterpal.log'), new Date().toISOString() + ' ' + a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' ') + '\n'); } catch (_) {}
}
process.on('uncaughtException', (e) => log('ERROR', String(e && e.stack || e)));

// One copy at a time. A copy started by our own restart may briefly overlap the old one that is
// still shutting down, so it waits for the lock instead of quitting straight away.
const RELAUNCHED = process.argv.includes('--relaunched');
let gotLock = app.requestSingleInstanceLock();
if (!gotLock && !RELAUNCHED) app.quit();
function waitForLock() {
  return new Promise((resolve) => {
    if (gotLock) return resolve(true);
    const t0 = Date.now();
    const iv = setInterval(() => {
      gotLock = app.requestSingleInstanceLock();
      if (gotLock || Date.now() - t0 > 20000) { clearInterval(iv); resolve(gotLock); }
    }, 300);
  });
}
function restartSelf() {
  const args = process.argv.slice(1).filter(a => a !== '--relaunched').concat('--relaunched');
  app.relaunch({ args }); app.exit(0);
}

const DATA_FILE = () => path.join(app.getPath('userData'), 'otterpal-data.json');
// The pet window fits the pet (50-150%) plus a speech bubble whose text size is set separately (80-150%).
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
let preview = null;        // size/text size being previewed from Settings, not saved yet
function eff() { return preview ? { ...data.settings, ...preview } : data.settings; }
function petDims(s = eff()) {
  const pet = clamp(Number(s.size) || 1, 0.5, 1.5), text = clamp(Number(s.textSize) || 1, 0.8, 1.5);
  return { w: Math.ceil(Math.max(302 * text + 28, 246 * pet + 10)), h: Math.ceil(170 * pet + 12 + 300 * text) };
}

let data = {
  reminders: [],
  settings: {
    sound: true,
    notifications: true,
    startWithWindows: true,
    size: 1,               // 0.75 / 1 / 1.25
    todoNudgeMin: 60,
    snoozeDefault: 10,
    petName: 'Ollie',
    motion: 'lively',      // 'lively' | 'calm'
    gpu: false,            // use the graphics card for drawing
    animal: 'otter',
    textSize: 1,
    walk: 'sometimes',     // 'off' | 'sometimes' | 'often'
    focusPreset: '25/5',   // '25/5' | '50/10' | '90/15' | 'custom'
    focusMin: 25, breakMin: 5, longBreakMin: 15,
    focusReminders: 'badge', // 'badge' (hold until the break) | 'show'
    volume: 70, voices: true,
    quietOn: false, quietFrom: '22:00', quietTo: '08:00',
    gaming: true,          // hide while a full-screen game is running, hold reminders until you stop
    gameBreakMin: 120,     // nudge to take a break after this much play (0 = never)
    bedOn: true, bedTime: '23:30',  // one bedtime warning while playing
    pos: null              // {x,y} the pet's home spot, remembered after dragging
  },
  lastNudge: 0,
  treats: 0,
  focus: { state: 'idle', endsAt: 0, round: 0, prompt: null, released: 0 },
  stats: { day: '', sessions: 0, minutes: 0 },
  held: [],                // reminders that came due during focus (badge mode) or while gaming
  game: { lastBreak: 0, endedAt: 0, bedWarned: '' }
};
let queue = [];            // ids (or 'todo-nudge') currently waiting for the user
let pet, manager, tray;
let hiddenUntil = 0;

/* ---------------- persistence ---------------- */
function load() {
  try {
    const raw = JSON.parse(fs.readFileSync(DATA_FILE(), 'utf8'));
    data.reminders = raw.reminders || [];
    data.settings = Object.assign(data.settings, raw.settings || {});
    data.lastNudge = raw.lastNudge || 0;
    data.treats = raw.treats || 0;
    data.focus = Object.assign(data.focus, raw.focus || {});
    data.stats = Object.assign(data.stats, raw.stats || {});
    data.game = Object.assign(data.game, raw.game || {});
    data.held = (raw.held || []).filter(id => data.reminders.some(r => r.id === id));
    queue = (raw.queue || []).filter(q => q === 'todo-nudge' || data.reminders.some(r => r.id === q));
  } catch (_) {
    // first run: a couple of friendly examples
    firstRun = true;
    const now = Date.now();
    data.reminders = [
      { id: uid(), type: 'interval', title: 'Drink some water', note: 'A glass of water keeps the otter happy.', every: 60, from: '09:00', to: '19:00', days: [1,2,3,4,5], enabled: true },
      { id: uid(), type: 'interval', title: 'Stand up & stretch', note: 'Look away from the screen for 20 seconds too.', every: 90, from: '09:00', to: '19:00', days: [1,2,3,4,5], enabled: true },
      { id: uid(), type: 'todo', title: 'Try adding my first reminder', note: '', done: false, enabled: true, created: now }
    ];
  }
  for (const r of data.reminders) {
    if (queue.includes(r.id)) continue;
    if (r.type === 'interval' && r.nextAt && r.nextAt < Date.now() - r.every * 60000) r.nextAt = null;
    if (r.nextAt == null) r.nextAt = computeNext(r, Date.now());
  }
}
let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      fs.mkdirSync(path.dirname(DATA_FILE()), { recursive: true });
      fs.writeFileSync(DATA_FILE(), JSON.stringify({ ...data, queue }, null, 2));
    } catch (e) { console.error(e); }
  }, 150);
}
function uid() { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4); }

/* ---------------- scheduling ---------------- */
function hm(str) { const [h, m] = (str || '00:00').split(':').map(Number); return h * 60 + m; }
function atMinutes(dayDate, mins) { const d = new Date(dayDate); d.setHours(Math.floor(mins / 60), mins % 60, 0, 0); return d.getTime(); }
function allDays(r) { return r.days && r.days.length ? r.days : [0,1,2,3,4,5,6]; }

function computeNext(r, fromMs) {
  if (!r.enabled) return null;
  if (r.type === 'once') {
    if (r.done || !r.at) return null;
    return new Date(r.at).getTime();
  }
  if (r.type === 'repeat') {
    const days = allDays(r), mins = hm(r.time);
    for (let i = 0; i < 8; i++) {
      const d = new Date(fromMs); d.setDate(d.getDate() + i);
      if (!days.includes(d.getDay())) continue;
      const t = atMinutes(d, mins);
      if (t > fromMs) return t;
    }
    return null;
  }
  if (r.type === 'interval') {
    const every = Math.max(1, Number(r.every) || 30) * 60000;
    const days = allDays(r);
    const fromM = r.from ? hm(r.from) : 0, toM = r.to ? hm(r.to) : 24 * 60;
    const wraps = toM < fromM;                 // e.g. 22:00 -> 02:00 runs past midnight
    const allDay = toM === fromM;
    const inWindow = (t) => {
      const d = new Date(t), m = d.getHours() * 60 + d.getMinutes();
      if (allDay) return days.includes(d.getDay());
      if (!wraps) return days.includes(d.getDay()) && m >= fromM && m <= toM;
      if (m >= fromM) return days.includes(d.getDay());
      if (m <= toM) { const p = new Date(d); p.setDate(p.getDate() - 1); return days.includes(p.getDay()); }
      return false;
    };
    const t = fromMs + every;
    if (inWindow(t)) return t;
    // otherwise: shortly after the next window opens
    for (let i = 0; i < 9; i++) {
      const d = new Date(fromMs); d.setDate(d.getDate() + i);
      if (!days.includes(d.getDay())) continue;
      const start = atMinutes(d, fromM);
      if (start >= t - every && start > fromMs) return start + Math.min(every, 15 * 60000);
    }
    return null;
  }
  return null; // todos are handled by the nudge
}

function fire(id) {
  if (queue.includes(id) || data.held.includes(id)) return;
  if (gaming && id !== 'update') {
    data.held.push(id); log('held while gaming', id); pushManager(); save(); return;          // shown when you stop playing
  }
  if (data.focus.state === 'focus' && data.settings.focusReminders !== 'show' && id !== 'update') {
    data.held.push(id); log('held during focus', id); pushState(false); pushManager(); save(); return;   // shows as a badge until the break
  }
  stopWalk();
  queue.push(id);
  const r = data.reminders.find(x => x.id === id);
  if (data.settings.notifications && Notification.isSupported()) {
    const title = id === 'todo-nudge' ? `${data.settings.petName}: you still have to-dos` : `${data.settings.petName} reminds you`;
    const body = id === 'todo-nudge' ? openTodos().slice(0, 4).map(t => '• ' + t.title).join('\n') : (r.title + (r.note ? '\n' + r.note : ''));
    const n = new Notification({ title, body, silent: true });
    n.on('click', () => showPet());
    n.show();
  }
  if (Date.now() < hiddenUntil && id !== 'todo-nudge') hiddenUntil = 0; // real reminders bring the otter back
  showPet();
  pushState(true);
  pushManager();
  rebuildTray();
  save();
}

function openTodos() { return data.reminders.filter(r => r.type === 'todo' && !r.done); }

function tick() {
  const now = Date.now();
  for (const r of data.reminders) {
    if (!r.enabled || r.type === 'todo' || queue.includes(r.id)) continue;
    if (r.nextAt && r.nextAt <= now) { r.nextAt = null; fire(r.id); }
  }
  const nudge = Number(data.settings.todoNudgeMin) || 0;
  if (nudge > 0 && openTodos().length && !queue.length && now - data.lastNudge >= nudge * 60000) {
    data.lastNudge = now;
    if (now >= hiddenUntil) fire('todo-nudge');
  }
  if (hiddenUntil && now >= hiddenUntil) { hiddenUntil = 0; showPet(); }
  updateCalm();
  pushState(false);
}

/* pause all animation while nobody is looking: screen locked, away for 3+ min, or pet hidden */
let locked = false, calmSent = null;
const CALM_AFTER = Number(process.env.DP_CALM_AFTER) || 180; // seconds without mouse/keyboard
/* tell the pet where the mouse is when it's near, so it can look at it (polls only while the pet is awake) */
let lastCursor = null;
setInterval(() => {
  if (!pet || pet.isDestroyed() || calmSent !== false || !pet.isVisible() || data.settings.motion === 'calm') return;
  let c; try { c = screen.getCursorScreenPoint(); } catch (_) { return; }
  const b = pet.getBounds(), x = c.x - b.x, y = c.y - b.y;
  const near = x > -600 && x < b.width + 600 && y > -600 && y < b.height + 600;
  const msg = near ? { x, y } : null;
  const key = msg ? x + ',' + y : 'far';
  if (key === lastCursor) return;
  lastCursor = key; pet.webContents.send('cursor', msg);
}, 120);

function updateCalm() {
  let idle = 0; try { idle = powerMonitor.getSystemIdleTime(); } catch (_) {}
  const hidden = !pet || pet.isDestroyed() || !pet.isVisible();
  const calm = locked || hidden || (idle >= CALM_AFTER && !queue.length);
  if (calm !== calmSent && pet && !pet.isDestroyed()) {
    calmSent = calm; pet.webContents.send('calm', calm); log('calm', calm, { idle, locked, hidden });
    if (calm) stopWalk(); else scheduleWalk();
  }
}

function complete(id) {
  if (id === 'update') { log('installing update', upd.version); if (updater) setImmediate(() => updater.quitAndInstall(true, true)); return; }
  if (id === 'preview') return applyPreview();
  if (id === 'focus-break' || id === 'focus-next') return startFocus();   // "Skip break" / "Start"
  if (id === 'game-break') { data.game.lastBreak = Date.now(); earnTreat('break'); return endPeek(id); }
  if (id === 'game-bed') return endPeek(id);
  queue = queue.filter(q => q !== id);
  if (id === 'todo-nudge') { data.lastNudge = Date.now(); }
  else {
    const r = data.reminders.find(x => x.id === id);
    if (r) {
      if (r.type === 'once') { r.done = true; r.nextAt = null; }
      else r.nextAt = computeNext(r, Date.now());
      earnTreat('reminder');
    }
  }
  save(); pushState(false); pushManager(); afterQueue();
}
function snooze(id, mins) {
  if (id === 'update') { updDismissed = true; pushState(false); return; }
  if (id === 'preview') return cancelPreview();
  if (id === 'focus-break' || id === 'focus-next') return stopFocus();    // "Stop focusing" / "Not now"
  if (id === 'game-break') { data.game.lastBreak = Date.now() - Math.max(0, gameBreakMs() - 20 * GMIN); return endPeek(id); }   // ask again in 20 min
  if (id === 'game-bed') return endPeek(id);
  queue = queue.filter(q => q !== id);
  if (id === 'todo-nudge') data.lastNudge = Date.now() - (data.settings.todoNudgeMin - mins) * 60000;
  else {
    const r = data.reminders.find(x => x.id === id);
    if (r) r.nextAt = Date.now() + mins * 60000;
  }
  save(); pushState(false); pushManager(); afterQueue();
}
function afterQueue() { if (!queue.length && walkPose !== 'rest') setTimeout(() => { if (!queue.length) walkHome(); }, 1500); }

/* ---------------- treats: earned by finishing reminders and focus sessions ---------------- */
function earnTreat(why) { data.treats = Math.min(99, (data.treats || 0) + 1); data.lastTreat = { at: Date.now(), why }; }

/* ---------------- focus timer ---------------- */
const MIN = Number(process.env.DP_FOCUS_MINUTE_MS) || 60000;   // tests shrink minutes
const PRESETS = { '25/5': [25, 5, 15], '50/10': [50, 10, 20], '90/15': [90, 15, 30] };
function focusLens() {
  const s = data.settings, p = PRESETS[s.focusPreset];
  return p ? { focus: p[0], short: p[1], long: p[2] } :
    { focus: clamp(Number(s.focusMin) || 25, 1, 240), short: clamp(Number(s.breakMin) || 5, 1, 120), long: clamp(Number(s.longBreakMin) || 15, 1, 120) };
}
let focusTimer = null;
function today() { return new Date().toDateString(); }
function scheduleFocus() {
  clearTimeout(focusTimer);
  const f = data.focus;
  if ((f.state === 'focus' || f.state === 'break') && f.endsAt) focusTimer = setTimeout(focusDue, Math.max(0, f.endsAt - Date.now()));
}
function releaseHeld() {
  const n = data.held.length;
  for (const id of data.held) if (!queue.includes(id)) queue.push(id);
  data.held = [];
  return n;
}
function startFocus() {
  const L = focusLens();
  queue = queue.filter(q => q !== 'focus-break' && q !== 'focus-next');
  data.focus = { state: 'focus', endsAt: Date.now() + L.focus * MIN, round: (data.focus.round || 0) + 1, prompt: null, released: 0, len: L.focus };
  stopWalk(); walkHome();
  log('focus start', data.focus);
  scheduleFocus(); save(); pushState(false); pushManager(); rebuildTray();
}
function stopFocus() {
  queue = queue.filter(q => q !== 'focus-break' && q !== 'focus-next');
  const n = releaseHeld();
  data.focus = { state: 'idle', endsAt: 0, round: 0, prompt: null, released: n };
  clearTimeout(focusTimer);
  log('focus stop, released', n);
  save(); pushState(n > 0); pushManager(); rebuildTray(); afterQueue();
}
function focusDue() {
  const f = data.focus, L = focusLens();
  if (f.state === 'focus') {
    if (data.stats.day !== today()) data.stats = { day: today(), sessions: 0, minutes: 0 };
    data.stats.sessions++; data.stats.minutes += f.len || L.focus;
    earnTreat('focus');
    const long = f.round % 4 === 0, mins = long ? L.long : L.short;
    const n = releaseHeld();
    data.focus = { ...f, state: 'break', endsAt: Date.now() + mins * MIN, prompt: 'break', released: n, breakLen: mins, long };
    queue.unshift('focus-break');
    notify(`${data.settings.petName}: break time!`, `${mins} minute ${long ? 'long ' : ''}break.` + (n ? ` ${n} reminder${n > 1 ? 's' : ''} waited for you.` : ''));
  } else if (f.state === 'break') {
    queue = queue.filter(q => q !== 'focus-break');
    data.focus = { ...f, state: 'ready', endsAt: 0, prompt: 'next' };
    queue.unshift('focus-next');
    notify(`${data.settings.petName}: break's over`, `Ready for round ${f.round + 1}?`);
  }
  log('focus', data.focus.state);
  scheduleFocus(); showPet(); save(); pushState(true); pushManager(); rebuildTray();
}
function notify(title, body) {
  if (!data.settings.notifications || !Notification.isSupported()) return;
  try { const n = new Notification({ title, body, silent: true }); n.on('click', () => showPet()); n.show(); } catch (_) {}
}

/* ---------------- size preview (Settings sliders) ---------------- */
function previewSize(p) { preview = { ...(preview || {}), ...p }; resizePet(); pushState(false); pushManager(); }
function applyPreview() {
  if (!preview) return;
  Object.assign(data.settings, preview); preview = null;
  resizePet(); save(); pushState(false); pushManager();
}
function cancelPreview() { if (!preview) return; preview = null; resizePet(); pushState(false); pushManager(); }

/* ---------------- gaming mode ----------------
   A tiny helper (native/gamecheck.exe) tells us which app is in front and whether it's full screen.
   Full-screen / borderless apps count as games, except browsers and video players.
   While playing: the pet hides, every reminder waits, and the pet only peeks in (headset on) for the
   break nudge and the bedtime warning. When you stop, it comes back, cheers, then shows what waited. */
const GMIN = Number(process.env.DP_GAME_MINUTE_MS) || 60000;             // tests shrink minutes
const GAME_ON_MS = Number(process.env.DP_GAME_ON_MS) || 4000, GAME_OFF_MS = Number(process.env.DP_GAME_OFF_MS) || 20000;
const NOT_GAMES = new Set(['chrome.exe', 'msedge.exe', 'firefox.exe', 'opera.exe', 'opera_gx.exe', 'brave.exe', 'vivaldi.exe', 'iexplore.exe',
  'arc.exe', 'vlc.exe', 'mpc-hc.exe', 'mpc-hc64.exe', 'mpc-be.exe', 'mpc-be64.exe', 'potplayer.exe', 'potplayermini.exe', 'potplayermini64.exe',
  'wmplayer.exe', 'video.ui.exe', 'microsoft.media.player.exe', 'netflix.exe', 'spotify.exe', 'kodi.exe', 'plex.exe', 'powerpnt.exe',
  'explorer.exe', 'applicationframehost.exe', 'desktop pal.exe', 'electron.exe', 'lockapp.exe', 'searchhost.exe', 'shellexperiencehost.exe',
  'startmenuexperiencehost.exe', 'obs64.exe', 'zoom.exe', 'teams.exe', 'ms-teams.exe', 'discord.exe']);
let gaming = false, gameSince = 0, gameExe = '', gameProc = null, gameRaw = false, gameRawTimer = null, peeking = false, peekTimer = null, welcomeUntil = 0, gameLoopT = null;
function gameBreakMs() { return Math.max(0, Number(data.settings.gameBreakMin) || 0) * GMIN; }
function playedText() {
  const m = Math.round((Date.now() - (data.game.lastBreak || gameSince)) / GMIN), h = Math.floor(m / 60);
  return h ? `${h} hour${h > 1 ? 's' : ''}${m % 60 >= 10 ? ` ${m % 60} min` : ''}` : `${m} minutes`;
}
function treatEmojiFor() { return ({ otter: '🐟', cat: '🐟', dog: '🦴', fox: '🍇', redpanda: '🎋' })[data.settings.animal] || '🍪'; }
function readProbe(line) {
  const [q, full, exe = ''] = String(line).trim().split('|'); const e = exe.trim().toLowerCase();
  const game = !!e && !NOT_GAMES.has(e) && q !== '4' && (q === '3' || full === '1');
  if (e !== gameExe && (game || gaming)) log('game check', { q, full, exe: e, game });
  gameExe = game ? e : (gaming ? gameExe : '');
  setGameRaw(game);
}
function setGameRaw(game) {
  if (game === gameRaw) return;
  gameRaw = game; clearTimeout(gameRawTimer);
  if (game !== gaming) gameRawTimer = setTimeout(() => { if (gameRaw === game) game ? gameStart() : gameOver(); }, game ? GAME_ON_MS : GAME_OFF_MS);
}
function startGameProbe() {
  if (gameProc || data.settings.gaming === false) return;
  const test = process.env.DP_GAME_PROBE;
  if (test) {            // tests: a file holding a line like the helper prints
    let last = ''; gameProc = { kill() { clearInterval(this.t); }, t: setInterval(() => { let l = ''; try { l = fs.readFileSync(test, 'utf8'); } catch (_) {} if (l !== last) { last = l; readProbe(l); } }, 300) };
    return;
  }
  if (process.platform !== 'win32') return;
  const exe = app.isPackaged ? path.join(process.resourcesPath, 'gamecheck.exe') : path.join(__dirname, '..', 'native', 'gamecheck.exe');
  if (!fs.existsSync(exe)) { log('game check helper missing', exe); return; }
  try {
    const p = require('child_process').spawn(exe, [], { stdio: ['pipe', 'pipe', 'ignore'], windowsHide: true });
    gameProc = p; let buf = '';
    p.stdout.on('data', (d) => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { readProbe(buf.slice(0, i)); buf = buf.slice(i + 1); } });
    p.on('exit', (c) => { log('game check helper exited', c); if (gameProc === p) { gameProc = null; if (data.settings.gaming !== false && !app.isQuitting) setTimeout(startGameProbe, 30000); } });
    p.on('error', (e) => log('game check helper failed', String(e)));
    log('game check started');
  } catch (e) { log('game check spawn failed', String(e)); }
}
function stopGameProbe() { if (gameProc) { const p = gameProc; gameProc = null; try { p.stdin && p.stdin.end(); p.kill(); } catch (_) {} } gameRaw = false; clearTimeout(gameRawTimer); }
function gameStart() {
  if (gaming) return;
  gaming = true; gameSince = Date.now();
  if (!data.game.endedAt || Date.now() - data.game.endedAt > 10 * GMIN) data.game.lastBreak = gameSince;   // a fresh session (a short alt-tab doesn't count as a break)
  log('gaming mode on', gameExe);
  stopWalk(); clearTimeout(walkTimer);
  if (pet && !pet.isDestroyed() && pet.isVisible()) pet.hide();
  clearInterval(gameLoopT); gameLoopT = setInterval(gameLoop, Math.min(30000, GMIN / 2));
  save(); updateCalm(); pushManager(); rebuildTray();
}
function gameOver() {
  if (!gaming) return;
  gaming = false; clearInterval(gameLoopT); clearTimeout(peekTimer);
  queue = queue.filter(q => !q.startsWith('game-')); peeking = false;
  data.game.endedAt = Date.now();
  log('gaming mode off after', Math.round((Date.now() - gameSince) / 60000), 'min');
  welcomeUntil = Date.now() + 4200;
  showPet();
  if (pet && !pet.isDestroyed()) pet.webContents.send('welcome');
  pushState(false);
  // let the pet say hi first, then show what waited (unless focus is still holding them)
  setTimeout(() => {
    welcomeUntil = 0;
    const n = (data.focus.state === 'focus' && data.settings.focusReminders !== 'show') ? 0 : releaseHeld();
    log('released after gaming', n);
    save(); pushState(n > 0); pushManager(); rebuildTray(); if (!n) scheduleWalk();
  }, 3000);
  save(); updateCalm(); pushManager(); rebuildTray();
}
function bedtimeKey(now) {          // the evening this bedtime belongs to, if we're past it (up to 6 hours after)
  const bt = hm(data.settings.bedTime || '23:30'); const d = new Date(now);
  for (const back of [0, 1]) {
    const day = new Date(d); day.setDate(d.getDate() - back);
    const t = atMinutes(day, bt);
    if (now >= t && now - t < 6 * 3600000) return day.toDateString();
  }
  return null;
}
function gameLoop() {
  if (!gaming || peeking) return;
  const now = Date.now();
  if (data.settings.bedOn !== false) {
    const k = bedtimeKey(now);
    if (k && data.game.bedWarned !== k) { data.game.bedWarned = k; return peek('game-bed'); }
  }
  const brk = gameBreakMs();
  if (brk && now - (data.game.lastBreak || gameSince) >= brk) peek('game-break');
}
function peek(id) {
  if (!pet || pet.isDestroyed()) return;
  peeking = true; queue = queue.filter(q => q !== id); queue.unshift(id);
  log('peek', id);
  pet.showInactive(); pet.setAlwaysOnTop(true, 'screen-saver'); pet.moveTop();   // never takes focus from the game
  updateCalm(); pushState(true); save();
  clearTimeout(peekTimer);
  peekTimer = setTimeout(() => {                 // nobody clicked: tuck away again (the break nudge asks again in 20 min)
    if (id === 'game-break') data.game.lastBreak = Date.now() - Math.max(0, gameBreakMs() - 20 * GMIN);
    endPeek(id);
  }, Number(process.env.DP_PEEK_MS) || 12000);
}
function endPeek(id) {
  clearTimeout(peekTimer);
  queue = queue.filter(q => q !== id); peeking = false;
  pushState(false); save();
  if (gaming && pet && !pet.isDestroyed()) setTimeout(() => { if (gaming && !peeking) { pet.hide(); updateCalm(); } }, 1600);
  else afterQueue();
}

/* ---------------- walking along the bottom of the screen ---------------- */
const WALK_SPEED = 52;                                          // px per second at 100% pet size
const WALK_SCALE = Number(process.env.DP_WALK_SCALE) || 1;     // tests shorten the waits
let walkPose = 'rest', walkDir = 1, walkMover = null, walkTimer = null, walkPause = null;
function homePos() { return data.settings.pos || defaultPos(); }
function setPose(p, dir) {
  walkPose = p; if (dir) walkDir = dir;
  if (pet && !pet.isDestroyed()) pet.webContents.send('pose', { pose: p, dir: walkDir });
}
function canWalk() {
  return pet && !pet.isDestroyed() && pet.isVisible() && calmSent === false && !queue.length && !dragStart && !preview &&
    !gaming && data.focus.state !== 'focus' && (data.settings.walk || 'sometimes') !== 'off';
}
function scheduleWalk(ms) {
  clearTimeout(walkTimer);
  const mode = data.settings.walk || 'sometimes';
  if (mode === 'off') return;
  const d = ms != null ? ms : (mode === 'often' ? 60 + Math.random() * 60 : 180 + Math.random() * 180) * 1000 / WALK_SCALE;
  walkTimer = setTimeout(tryWalk, d);
}
function tryWalk() {
  if (!canWalk()) return scheduleWalk();
  const b = pet.getBounds(), wa = screen.getDisplayMatching(b).workArea, home = homePos();
  const minX = wa.x, maxX = wa.x + wa.width - b.width;
  const away = Math.abs(b.x - home.x) > 4;
  let target = home.x;
  if (!away || Math.random() > 0.45) {
    for (let i = 0; i < 12; i++) {
      const t = clamp(Math.round(home.x + (Math.random() * 2 - 1) * 520), minX, maxX);
      if (Math.abs(t - b.x) >= 120) { target = t; break; }
    }
  }
  // on longer strolls, sometimes stop halfway to stand and look around for a moment
  if (Math.abs(target - b.x) > 260 && Math.random() < 0.4) {
    const mid = Math.round(b.x + (target - b.x) * (0.35 + Math.random() * 0.3));
    return walkTo(mid, () => { walkPause = setTimeout(() => { walkPause = null; canWalk() ? walkTo(target, () => scheduleWalk()) : scheduleWalk(); }, (1500 + Math.random() * 2000) / Math.sqrt(WALK_SCALE)); });
  }
  walkTo(target, () => scheduleWalk());
}
// smooth, time-based movement: speeds up gently, cruises, and slows down before stopping
function walkTo(x, then) {
  if (!pet || pet.isDestroyed()) return;
  clearInterval(walkMover); walkMover = null; clearTimeout(walkPause); walkPause = null;
  const b = pet.getBounds(); const y = b.y;
  if (Math.abs(x - b.x) < 2) { setPose(atHome() ? 'rest' : 'stand'); return then && then(); }
  // give the pet a moment to get up (from resting) or turn around before it sets off
  const nd = x > b.x ? 1 : -1, wait = (walkPose === 'rest' ? 380 : 0) + (walkPose !== 'rest' && nd !== walkDir ? 430 : 0);
  setPose('walk', nd);
  const vmax = WALK_SPEED * clamp(Number(data.settings.size) || 1, 0.5, 1.5) * (0.92 + Math.random() * 0.16);
  const acc = vmax / 0.6, dir = Math.sign(x - b.x);
  let cx = b.x, v = 0, last = Date.now() + wait, lastPx = b.x;
  walkMover = setInterval(() => {
    if (!pet || pet.isDestroyed()) { clearInterval(walkMover); walkMover = null; return; }
    if (Date.now() < last) return;
    const now = Date.now(), dt = Math.min(0.05, (now - last) / 1000); last = now;
    const rem = Math.abs(x - cx);
    v = Math.min(v + acc * dt, vmax, Math.sqrt(2 * acc * rem) + 4);
    cx = rem <= v * dt ? x : cx + dir * v * dt;
    const px = Math.round(cx);
    if (px !== lastPx) { pet.setPosition(px, y); lastPx = px; }
    if (cx === x) { clearInterval(walkMover); walkMover = null; setPose(atHome() ? 'rest' : 'stand'); then && then(); }
  }, 16);
}
function atHome() { if (!pet || pet.isDestroyed()) return true; const b = pet.getBounds(), h = homePos(); return Math.abs(b.x - h.x) <= 4 && Math.abs(b.y - h.y) <= 4; }
function stopWalk() {
  if (walkPause) { clearTimeout(walkPause); walkPause = null; }
  if (walkMover) { clearInterval(walkMover); walkMover = null; setPose(atHome() ? 'rest' : 'stand'); }
}
function walkHome() {
  if (!pet || pet.isDestroyed() || atHome()) { if (walkPose !== 'rest' && atHome()) setPose('rest'); return; }
  walkTo(homePos().x, () => { const h = homePos(); pet.setPosition(h.x, h.y); setPose('rest'); scheduleWalk(); });
}

/* ---------------- automatic updates ----------------
   Uses electron-updater. Active only in installed builds that were published with an update feed
   (GitHub releases later); otherwise it stays quietly off. */
let updater = null, upd = { status: 'off', version: null, percent: 0 }, updDismissed = false;
function setUpdate(o) { upd = { ...upd, ...o }; pushManager(); pushState(o.status === 'ready'); rebuildTray(); }
function setupUpdater() {
  const test = process.env.DP_TEST_UPDATES;            // url of a local feed, for testing only
  if ((!app.isPackaged && !test) || LEGACY_INSTALL) return;
  try {
    const eu = require('electron-updater');
    updater = test ? new eu.NsisUpdater({ provider: 'generic', url: test }) : eu.autoUpdater;
    if (test) updater.forceDevUpdateConfig = true;
    updater.autoDownload = true; updater.autoInstallOnAppQuit = true;
    updater.logger = { info: (x) => log('update', String(x)), warn: (x) => log('update warn', String(x)), error: (x) => log('update error', String(x)), debug: () => {} };
    updater.on('checking-for-update', () => setUpdate({ status: 'checking' }));
    updater.on('update-available', (i) => setUpdate({ status: 'downloading', version: i.version, percent: 0 }));
    updater.on('download-progress', (p) => setUpdate({ status: 'downloading', percent: Math.round(p.percent) }));
    updater.on('update-not-available', () => setUpdate({ status: 'latest' }));
    updater.on('update-downloaded', (i) => { updDismissed = false; setUpdate({ status: 'ready', version: i.version }); });
    updater.on('error', (e) => setUpdate({ status: /ENOENT|app-update\.yml|No published versions|404/i.test(String(e)) ? 'off' : 'error' }));
    setUpdate({ status: 'idle' });
    const check = () => { if (upd.status !== 'downloading' && upd.status !== 'ready') updater.checkForUpdates().catch(() => {}); };
    setTimeout(check, test ? 1500 : 20000);
    setInterval(check, 6 * 3600 * 1000);
  } catch (e) { log('updater unavailable', String(e)); updater = null; }
}

/* ---------------- state to renderers ---------------- */
function upcoming() {
  return data.reminders
    .filter(r => r.enabled && r.nextAt && !queue.includes(r.id))
    .sort((a, b) => a.nextAt - b.nextAt);
}
function petState() {
  return {
    queue: queue.map(id => id === 'focus-break'
      ? { id, kind: 'focus', title: `Break time! ${data.focus.breakLen || focusLens().short} min${data.focus.long ? ' (long break)' : ''}`, note: 'Stretch, look away from the screen, sip some water.' + (data.focus.released ? ` ${data.focus.released} reminder${data.focus.released > 1 ? 's' : ''} waited for you.` : ''), mood: 'happy', doneLabel: 'Skip break', laterLabel: 'Stop focusing' }
      : id === 'focus-next'
      ? { id, kind: 'focus', title: `Break's over! Ready for round ${(data.focus.round || 0) + 1}?`, note: `${focusLens().focus} minutes of focus.`, mood: 'excited', doneLabel: 'Start', laterLabel: 'Not now' }
      : id === 'game-break'
      ? { id, kind: 'game', title: `You've been playing for ${playedText()}`, note: 'Time for a short break: stand up, stretch and drink some water. Your game will wait!', mood: 'happy', doneLabel: `Taking a break ${treatEmojiFor()}`, laterLabel: 'Later' }
      : id === 'game-bed'
      ? { id, kind: 'game', title: `It's ${data.settings.bedTime || '23:30'}, getting late!`, note: 'Maybe one more match, then off to bed?', mood: 'sleepy', doneLabel: 'OK', laterLabel: 'Not tonight' }
      : id === 'todo-nudge'
      ? { id, kind: 'nudge', title: 'You still have things on your list', todos: openTodos().slice(0, 5).map(t => t.title), more: Math.max(0, openTodos().length - 5) }
      : (() => { const r = data.reminders.find(x => x.id === id); return r && { id, kind: r.type, title: r.title, note: r.note, mood: r.mood || 'auto', overdue: r.type === 'once' && r.at && new Date(r.at).getTime() < Date.now() - 5 * 60000 ? r.at : null }; })()
    ).filter(Boolean).map(it => it).concat(preview
      ? [{ id: 'preview', kind: 'preview', title: 'This is how reminders will look', note: `Pet size ${Math.round((eff().size || 1) * 100)}% · Text size ${Math.round((eff().textSize || 1) * 100)}%`, mood: 'happy', doneLabel: 'Apply', laterLabel: 'Cancel' }] : []).concat(upd.status === 'ready' && !updDismissed
      ? [{ id: 'update', kind: 'update', title: `Version ${upd.version} is ready`, note: 'Restart Desktop Pal to finish updating. Your reminders stay as they are.' }] : []),
    next: upcoming().slice(0, 3).map(r => ({ title: r.title, at: r.nextAt })),
    todos: openTodos().length,
    settings: eff(),
    treats: data.treats || 0,
    focus: { state: data.focus.state, endsAt: data.focus.endsAt, round: data.focus.round, held: data.held.length, lens: focusLens() },
    headset: peeking || welcomeUntil > Date.now()
  };
}
let lastStateJson = '', stateSends = 0, stateSkips = 0;
function pushState(alert) {
  if (!pet || pet.isDestroyed()) return;
  const st = petState(), json = JSON.stringify(st);
  if (!alert && json === lastStateJson) { stateSkips++; return; }   // nothing changed: don't wake the pet up
  lastStateJson = json; stateSends++;
  pet.webContents.send('state', { ...st, alert });
}
function pushManager() { if (manager && !manager.isDestroyed()) manager.webContents.send('data', managerData()); }
function managerData() {
  if (data.stats.day !== today()) data.stats = { day: today(), sessions: 0, minutes: 0 };
  return { reminders: data.reminders, settings: data.settings, queue, update: upd, treats: data.treats || 0,
           focus: { ...data.focus, held: data.held.length, lens: focusLens() }, stats: data.stats, previewing: !!preview,
           gaming: { on: gaming, exe: gameExe, since: gameSince, probe: !!gameProc || !!process.env.DP_GAME_PROBE } };
}

/* ---------------- windows ---------------- */
function defaultPos() {
  const wa = screen.getPrimaryDisplay().workArea;
  const d = petDims();
  return { x: wa.x + wa.width - d.w - 8, y: wa.y + wa.height - d.h };
}
function validPos(p) {
  if (!p) return false;
  const { w, h } = petDims();
  return screen.getAllDisplays().some(d => {
    const a = d.workArea;
    return p.x + w / 2 >= a.x && p.x + w / 2 <= a.x + a.width && p.y + h / 2 >= a.y && p.y + h / 2 <= a.y + a.height;
  });
}
function createPet() {
  // the window's size depends on settings: keep the pet's bottom-right corner where the user left it
  const dims = petDims();
  if (data.settings.pos) {
    data.settings.pos.x -= dims.w - (data.settings.petW || 340);
    data.settings.pos.y -= dims.h - (data.settings.petH || 400);
  }
  data.settings.petW = dims.w; data.settings.petH = dims.h;
  const p = validPos(data.settings.pos) ? data.settings.pos : defaultPos();
  pet = new BrowserWindow({
    x: p.x, y: p.y, width: dims.w, height: dims.h,
    transparent: true, frame: false, resizable: false, maximizable: false, minimizable: false,
    skipTaskbar: true, alwaysOnTop: true, hasShadow: false, focusable: true, show: false,
    backgroundColor: '#00000000',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, backgroundThrottling: false }
  });
  pet.setAlwaysOnTop(true, 'screen-saver');
  pet.setIgnoreMouseEvents(true, { forward: true });
  pet.loadFile(path.join(__dirname, 'pet.html'));
  let shown = false;
  const reveal = (why) => {
    if (shown || pet.isDestroyed()) return; shown = true;
    pet.showInactive(); pet.setAlwaysOnTop(true, 'screen-saver'); pet.moveTop();
    pushState(queue.length > 0);
    log('pet shown via', why, pet.getBounds(), 'visible=', pet.isVisible(), 'displays=', screen.getAllDisplays().map(d => ({ b: d.bounds, wa: d.workArea, s: d.scaleFactor, primary: d.id === screen.getPrimaryDisplay().id })));
  };
  pet.once('ready-to-show', () => reveal('ready-to-show'));
  pet.webContents.once('did-finish-load', () => setTimeout(() => reveal('did-finish-load'), 300));
  setTimeout(() => reveal('timeout'), 4000);
  pet.webContents.on('render-process-gone', (_e, d) => log('pet renderer gone', d));
  pet.webContents.on('console-message', (_e, level, msg) => { if (level >= 2) log('pet console', msg); });
}
function resizePet() {
  if (!pet || pet.isDestroyed()) return;
  const b = pet.getBounds(), d = petDims();
  if (b.width === d.w && b.height === d.h) return;
  const x = b.x + b.width - d.w, y = b.y + b.height - d.h;   // keep the bottom-right corner in place
  pet.setBounds({ x, y, width: d.w, height: d.h });
  if (data.settings.pos && !preview) data.settings.pos = { x: data.settings.pos.x + b.width - d.w, y: data.settings.pos.y + b.height - d.h };
  data.settings.petW = d.w; data.settings.petH = d.h;
}
function showPet() {
  if (!pet || pet.isDestroyed()) return;
  if (Date.now() < hiddenUntil) return;
  if (gaming && !peeking) return;                 // stays out of the way while you play
  if (!pet.isVisible()) pet.showInactive();
  pet.setAlwaysOnTop(true, 'screen-saver');
  pet.moveTop();
  rebuildTray();
  updateCalm();
}
function hidePet(mins) {
  hiddenUntil = mins ? Date.now() + mins * 60000 : Number.MAX_SAFE_INTEGER;
  pet.hide();
  rebuildTray();
  updateCalm();
}
function openManager(tab) {
  if (manager && !manager.isDestroyed()) { manager.show(); manager.focus(); if (tab) manager.webContents.send('tab', tab); return; }
  manager = new BrowserWindow({
    width: 760, height: 640, minWidth: 560, minHeight: 480,
    title: 'Desktop Pal — Reminders', autoHideMenuBar: true, backgroundColor: '#f6f1ea',
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false }
  });
  manager.loadFile(path.join(__dirname, 'manager.html'), { query: { tab: tab || '' } });
  manager.on('closed', () => { manager = null; cancelPreview(); });
}

/* ---------------- tray ---------------- */
function rebuildTray() {
  if (!tray) return;
  const visible = pet && !pet.isDestroyed() && pet.isVisible();
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open Desktop Pal', click: () => openManager() },
    data.focus.state === 'idle'
      ? { label: `Start focus (${focusLens().focus} min)`, click: () => startFocus() }
      : { label: 'Stop focus', click: () => stopFocus() },
    ...((data.settings.walk || 'sometimes') !== 'off' ? [{ label: 'Go for a walk', click: () => { if (canWalk()) tryWalk(); } }] : []),
    { label: gaming ? `Gaming mode (playing${gameExe ? ' ' + gameExe.replace(/\.exe$/, '') : ''})` : 'Gaming mode', type: 'checkbox', checked: data.settings.gaming !== false,
      click: (mi) => { data.settings.gaming = mi.checked; if (mi.checked) startGameProbe(); else { stopGameProbe(); if (gaming) gameOver(); } save(); pushManager(); rebuildTray(); } },
    { label: data.settings.sound ? 'Mute sounds' : 'Unmute sounds', click: () => { data.settings.sound = !data.settings.sound; save(); pushState(false); pushManager(); rebuildTray(); } },
    { label: 'Add a reminder…', click: () => openManager('new') },
    { type: 'separator' },
    visible
      ? { label: `Hide ${data.settings.petName}`, submenu: [
          { label: 'For 30 minutes', click: () => hidePet(30) },
          { label: 'For 1 hour', click: () => hidePet(60) },
          { label: 'For 2 hours', click: () => hidePet(120) },
          { label: 'Until I bring it back', click: () => hidePet(0) } ] }
      : { label: `Show ${data.settings.petName}`, click: () => { hiddenUntil = 0; showPet(); } },
    { label: 'Move back to corner', click: () => { data.settings.pos = null; const p = defaultPos(); pet.setPosition(p.x, p.y); save(); } },
    { type: 'separator' },
    ...(upd.status === 'ready' ? [{ label: `Restart to update to ${upd.version}`, click: () => complete('update') }] : []),
    { label: `About Desktop Pal ${app.getVersion()}`, click: () => openManager('set') },
    { label: 'Quit Desktop Pal', click: () => { app.isQuitting = true; app.quit(); } }
  ]));
  tray.setToolTip(`Desktop Pal — ${openTodos().length} to-do(s), ${queue.length} waiting`);
}

const LEGACY_INSTALL = /[\\/]runtime[\\/]resources[\\/]app[\\/]src$/.test(__dirname); // the old script-based install on Georgi's PC
let firstRun = false;
function ensureShortcut() {
  if (!LEGACY_INSTALL) return; // the real installer creates its own shortcuts
  // Start Menu shortcut carrying our AppUserModelID lets Windows show our notifications.
  // Also renames the old "Otter Pal" shortcuts to "Desktop Pal".
  if (process.platform !== 'win32' || !app.isPackaged) return;
  const icon = path.join(__dirname, 'assets', 'icon.ico');
  const programs = path.join(app.getPath('appData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs');
  const desktop = app.getPath('desktop');
  const mk = (lnk, opts) => { try { shell.writeShortcutLink(lnk, fs.existsSync(lnk) ? 'replace' : 'create', opts); } catch (e) { log('shortcut', lnk, String(e)); } };
  const rm = (lnk) => { try { if (fs.existsSync(lnk)) fs.unlinkSync(lnk); } catch (e) { log('rm shortcut', lnk, String(e)); } };
  const main = { target: process.execPath, cwd: path.dirname(process.execPath), appUserModelId: APP_ID, description: 'Desktop Pal reminders', icon, iconIndex: 0 };
  mk(path.join(programs, 'Desktop Pal.lnk'), main);
  rm(path.join(programs, 'Otter Pal.lnk'));
  const oldDesk = path.join(desktop, 'Otter Pal.lnk'), newDesk = path.join(desktop, 'Desktop Pal.lnk');
  if (fs.existsSync(oldDesk) || fs.existsSync(newDesk) || !data.settings.shortcutsDone) mk(newDesk, main);
  rm(oldDesk);
  const uninstall = path.join(path.dirname(path.dirname(process.execPath)), 'uninstall.ps1');
  if (fs.existsSync(uninstall)) {
    mk(path.join(programs, 'Uninstall Desktop Pal.lnk'), {
      target: path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
      args: `-NoProfile -ExecutionPolicy Bypass -File "${uninstall}"`, icon, iconIndex: 0, description: 'Remove Desktop Pal' });
    rm(path.join(programs, 'Uninstall Otter Pal.lnk'));
  }
  data.settings.shortcutsDone = true;
}

function applyLogin() {
  if (process.platform !== 'win32' && process.platform !== 'darwin') return;
  if (!app.isPackaged) return;
  app.setLoginItemSettings({ openAtLogin: !!data.settings.startWithWindows, path: process.execPath });
}

/* ---------------- IPC ---------------- */
ipcMain.on('pet:ignore', (_e, ignore) => { if (pet) pet.setIgnoreMouseEvents(ignore, { forward: true }); });
ipcMain.on('pet:done', (_e, id) => complete(id));
ipcMain.on('pet:snooze', (_e, id, mins) => snooze(id, mins));
ipcMain.on('pet:open', (_e, tab) => openManager(tab));
ipcMain.on('pet:hide', (_e, mins) => hidePet(mins));
// animal voices: small recorded clips, loaded only for the animal you picked
ipcMain.handle('pet:sound', (_e, name) => {
  if (!/^[a-z]+-[a-z]+\d?$/.test(String(name))) return null;
  try { return fs.readFileSync(path.join(__dirname, 'sounds', name + '.ogg')); } catch (_) { return null; }
});
ipcMain.on('pet:ready', () => { calmSent = null; lastStateJson = ''; pushState(queue.length > 0); updateCalm(); setPose(walkPose); });
ipcMain.handle('pet:feed', () => { if ((data.treats || 0) < 1) return false; data.treats--; save(); pushState(false); pushManager(); return true; });
ipcMain.on('pet:focus', (_e, on) => on ? startFocus() : stopFocus());
ipcMain.handle('mgr:focus', (_e, on) => { on ? startFocus() : stopFocus(); return managerData(); });
ipcMain.handle('mgr:previewSize', (_e, p) => { previewSize(p); return true; });
ipcMain.handle('mgr:applySize', () => { applyPreview(); return true; });
ipcMain.handle('mgr:cancelSize', () => { cancelPreview(); return true; });
ipcMain.handle('mgr:walkNow', () => { if (canWalk()) tryWalk(); else scheduleWalk(5000); return true; });
let dragStart = null;
ipcMain.on('pet:drag-start', () => { stopWalk(); dragStart = pet.getPosition(); });
ipcMain.on('pet:drag', (_e, dx, dy) => { if (dragStart) pet.setPosition(Math.round(dragStart[0] + dx), Math.round(dragStart[1] + dy)); });
ipcMain.on('pet:drag-end', () => { if (dragStart) { const [x, y] = pet.getPosition(); data.settings.pos = { x, y }; save(); } dragStart = null; });

const ANIMALS = ['otter', 'cat', 'dog', 'fox', 'redpanda'];
const artCache = new Map();
ipcMain.handle('pet:art', (_e, animal) => {
  if (!ANIMALS.includes(animal)) return null;
  if (!artCache.has(animal)) {
    try { artCache.set(animal, JSON.parse(fs.readFileSync(path.join(__dirname, 'pets', animal + '.json'), 'utf8'))); }
    catch (e) { log('art load failed', animal, String(e)); return null; }
  }
  return artCache.get(animal);
});
ipcMain.handle('mgr:get', () => managerData());
ipcMain.handle('mgr:save', (_e, r) => {
  const now = Date.now();
  let ex = data.reminders.find(x => x.id === r.id);
  if (ex) Object.assign(ex, r);
  else { ex = { ...r, id: uid(), created: now, enabled: r.enabled !== false }; data.reminders.push(ex); }
  if (ex.type === 'once') ex.done = new Date(ex.at).getTime() <= now && ex.done ? true : false;
  queue = queue.filter(q => q !== ex.id);
  ex.nextAt = computeNext(ex, now);
  save(); pushState(false); pushManager(); rebuildTray();
  return ex;
});
ipcMain.handle('mgr:delete', (_e, id) => {
  data.reminders = data.reminders.filter(r => r.id !== id);
  queue = queue.filter(q => q !== id);
  save(); pushState(false); pushManager(); rebuildTray();
});
ipcMain.handle('mgr:toggle', (_e, id, field) => {
  const r = data.reminders.find(x => x.id === id); if (!r) return;
  r[field] = !r[field];
  if (field === 'enabled') { queue = queue.filter(q => q !== id); r.nextAt = computeNext(r, Date.now()); }
  if (field === 'done' && r.type === 'once') r.nextAt = computeNext(r, Date.now());
  save(); pushState(false); pushManager(); rebuildTray();
});
ipcMain.handle('mgr:settings', (_e, s) => {
  const gpuChanged = 'gpu' in s && !!s.gpu !== !!data.settings.gpu;
  const resize = ('size' in s && s.size !== data.settings.size) || ('textSize' in s && s.textSize !== data.settings.textSize);
  const walkChanged = 'walk' in s && s.walk !== data.settings.walk;
  data.settings = Object.assign(data.settings, s);
  if (resize) resizePet();
  if (walkChanged) { if (s.walk === 'off') { clearTimeout(walkTimer); stopWalk(); walkHome(); } else scheduleWalk(); }
  if (s.focusReminders === 'show' && data.held.length && !gaming) { releaseHeld(); pushState(true); }
  if ('gaming' in s) { if (s.gaming) startGameProbe(); else { stopGameProbe(); if (gaming) gameOver(); } }
  applyLogin(); save(); pushState(false); pushManager(); rebuildTray();
  if (gpuChanged) {               // drawing mode is fixed at startup: restart to apply
    try { fs.writeFileSync(DATA_FILE(), JSON.stringify({ ...data, queue }, null, 2)); } catch (_) {}
    log('restarting to switch graphics card', !!data.settings.gpu);
    setTimeout(restartSelf, 400);
  }
});
const PKG = require('../package.json');
ipcMain.handle('mgr:about', () => ({ version: app.getVersion(), page: PKG.homepage || '', update: upd, canUpdate: !!updater && upd.status !== 'off' }));
ipcMain.handle('mgr:checkUpdate', async () => {
  if (!updater || upd.status === 'off') return upd;
  if (upd.status === 'ready') { complete('update'); return upd; }
  try { await updater.checkForUpdates(); } catch (_) {}
  return upd;
});
ipcMain.handle('mgr:link', (_e, url) => { if (/^https:\/\/([\w.-]+\.)?itch\.io\//.test(url) || /^https:\/\/github\.com\//.test(url)) shell.openExternal(url); });
ipcMain.handle('mgr:test', () => { fire(data.reminders.find(r => r.type !== 'todo')?.id || 'todo-nudge'); });

/* ---------------- boot ---------------- */
app.on('second-instance', (_e, argv) => { if (!argv.includes('--relaunched')) openManager(); });
app.on('will-quit', () => stopGameProbe());
app.on('will-quit', () => log('state updates sent', stateSends, 'skipped (no change)', stateSkips));
app.on('window-all-closed', (e) => { /* keep running in tray */ });

/* The old hand-made install (Georgi's first copy) steps aside once the real installer's copy exists:
   it removes its own startup entry and the shortcuts that point at it, then starts the new app. */
function retireLegacyIfReplaced() {
  if (!LEGACY_INSTALL || process.platform !== 'win32') return false;
  const newExe = path.join(process.env.LOCALAPPDATA || '', 'Programs', 'desktop-pal', 'Desktop Pal.exe');
  if (!fs.existsSync(newExe)) return false;
  log('retiring old install; new app found at', newExe);
  try { app.setLoginItemSettings({ openAtLogin: false, path: process.execPath }); } catch (e) { log('retire login', String(e)); }
  const mine = (lnk) => { try { const s = shell.readShortcutLink(lnk); return s.target === process.execPath || /OtterPal[\\/]uninstall\.ps1/i.test(s.args || ''); } catch (_) { return false; } };
  const programs = path.join(app.getPath('appData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs');
  for (const lnk of [path.join(app.getPath('desktop'), 'Desktop Pal.lnk'), path.join(app.getPath('desktop'), 'Otter Pal.lnk'),
                     path.join(programs, 'Desktop Pal.lnk'), path.join(programs, 'Otter Pal.lnk'),
                     path.join(programs, 'Uninstall Desktop Pal.lnk'), path.join(programs, 'Uninstall Otter Pal.lnk')]) {
    if (fs.existsSync(lnk) && mine(lnk)) { try { fs.unlinkSync(lnk); log('removed old shortcut', lnk); } catch (e) { log('rm', lnk, String(e)); } }
  }
  try { require('child_process').spawn(newExe, ['--relaunched'], { detached: true, stdio: 'ignore' }).unref(); log('started new app'); } catch (e) { log('start new app failed', String(e)); }
  setTimeout(() => app.exit(0), 300);
  return true;
}

app.whenReady().then(async () => {
  if (!(await waitForLock())) { app.quit(); return; }
  if (retireLegacyIfReplaced()) return;
  try {
    powerMonitor.on('lock-screen', () => { locked = true; updateCalm(); });
    powerMonitor.on('unlock-screen', () => { locked = false; updateCalm(); });
    powerMonitor.on('suspend', () => { locked = true; updateCalm(); });
    powerMonitor.on('resume', () => { locked = false; updateCalm(); setTimeout(tick, 1000); });
  } catch (_) {}
  log('start', app.getVersion(), process.versions.electron);
  load();
  createPet();
  const icon = nativeImage.createFromPath(path.join(__dirname, 'assets', 'tray.png'));
  tray = new Tray(icon);
  tray.on('click', () => openManager());
  rebuildTray();
  applyLogin();
  ensureShortcut();
  save();
  // pick up new looks automatically when pet.html / manager.html are updated (dev / legacy installs only)
  if (!__dirname.includes('app.asar')) try {
    let t = null, relaunchT = null; const changed = new Set();
    fs.watch(__dirname, (_ev, file) => {
      if (!file) return;
      if (/\.(js|json)$/.test(file)) {   // app code changed: restart ourselves to pick it up
        clearTimeout(relaunchT);
        relaunchT = setTimeout(() => {
          log('restarting after update of', file);
          try { fs.writeFileSync(DATA_FILE(), JSON.stringify({ ...data, queue }, null, 2)); } catch (_) {}
          restartSelf();
        }, 1500);
        return;
      }
      if (!/\.html$/.test(file)) return;
      changed.add(file); clearTimeout(t);
      t = setTimeout(() => {
        for (const f of changed) {
          log('reloading after update of', f);
          if (f === 'pet.html' && pet && !pet.isDestroyed()) pet.webContents.reloadIgnoringCache();
          if (f === 'manager.html' && manager && !manager.isDestroyed()) manager.webContents.reloadIgnoringCache();
        }
        changed.clear();
      }, 800);
    });
  } catch (e) { log('watch failed', String(e)); }
  setInterval(tick, 5000);
  setTimeout(tick, 1500);
  screen.on('display-removed', () => { if (!validPos(pet.getBounds())) { const p = defaultPos(); pet.setPosition(p.x, p.y); } });
  setupUpdater();
  if (data.focus.state === 'focus' || data.focus.state === 'break') scheduleFocus();
  else if (data.focus.state === 'ready' && !queue.includes('focus-next')) queue.unshift('focus-next');
  scheduleWalk();
  data.game.endedAt = data.game.endedAt || 0;
  startGameProbe();
  // reminders still waiting from a game that ended while the app was closed
  setTimeout(() => { if (!gaming && data.held.length && data.focus.state !== 'focus') { releaseHeld(); save(); pushState(true); pushManager(); } }, (GAME_ON_MS * 2) + 2000);
  if (firstRun) setTimeout(() => openManager(), 1500);
  if (process.env.OTTER_DEMO) setTimeout(() => fire(data.reminders[0].id), 1200);
});
