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
const PET_W = 340, PET_H = 470;

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
    pos: null              // {x,y} remembered after dragging
  },
  lastNudge: 0
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
  if (queue.includes(id)) return;
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
function updateCalm() {
  let idle = 0; try { idle = powerMonitor.getSystemIdleTime(); } catch (_) {}
  const hidden = !pet || pet.isDestroyed() || !pet.isVisible();
  const calm = locked || hidden || (idle >= CALM_AFTER && !queue.length);
  if (calm !== calmSent && pet && !pet.isDestroyed()) { calmSent = calm; pet.webContents.send('calm', calm); log('calm', calm, { idle, locked, hidden }); }
}

function complete(id) {
  if (id === 'update') { log('installing update', upd.version); if (updater) setImmediate(() => updater.quitAndInstall(true, true)); return; }
  queue = queue.filter(q => q !== id);
  if (id === 'todo-nudge') { data.lastNudge = Date.now(); }
  else {
    const r = data.reminders.find(x => x.id === id);
    if (r) {
      if (r.type === 'once') { r.done = true; r.nextAt = null; }
      else r.nextAt = computeNext(r, Date.now());
    }
  }
  save(); pushState(false); pushManager();
}
function snooze(id, mins) {
  if (id === 'update') { updDismissed = true; pushState(false); return; }
  queue = queue.filter(q => q !== id);
  if (id === 'todo-nudge') data.lastNudge = Date.now() - (data.settings.todoNudgeMin - mins) * 60000;
  else {
    const r = data.reminders.find(x => x.id === id);
    if (r) r.nextAt = Date.now() + mins * 60000;
  }
  save(); pushState(false); pushManager();
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
    queue: queue.map(id => id === 'todo-nudge'
      ? { id, kind: 'nudge', title: 'You still have things on your list', todos: openTodos().slice(0, 5).map(t => t.title), more: Math.max(0, openTodos().length - 5) }
      : (() => { const r = data.reminders.find(x => x.id === id); return r && { id, kind: r.type, title: r.title, note: r.note, mood: r.mood || 'auto', overdue: r.type === 'once' && r.at && new Date(r.at).getTime() < Date.now() - 5 * 60000 ? r.at : null }; })()
    ).filter(Boolean).concat(upd.status === 'ready' && !updDismissed
      ? [{ id: 'update', kind: 'update', title: `Version ${upd.version} is ready`, note: 'Restart Desktop Pal to finish updating. Your reminders stay as they are.' }] : []),
    next: upcoming().slice(0, 3).map(r => ({ title: r.title, at: r.nextAt })),
    todos: openTodos().length,
    settings: data.settings
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
function managerData() { return { reminders: data.reminders, settings: data.settings, queue, update: upd }; }

/* ---------------- windows ---------------- */
function defaultPos() {
  const wa = screen.getPrimaryDisplay().workArea;
  return { x: wa.x + wa.width - PET_W - 8, y: wa.y + wa.height - PET_H };
}
function validPos(p) {
  if (!p) return false;
  return screen.getAllDisplays().some(d => {
    const a = d.workArea;
    return p.x + PET_W / 2 >= a.x && p.x + PET_W / 2 <= a.x + a.width && p.y + PET_H / 2 >= a.y && p.y + PET_H / 2 <= a.y + a.height;
  });
}
function createPet() {
  // window grew taller (400 -> 470): keep the pet's feet where the user left them
  if (data.settings.pos && (data.settings.petH || 400) !== PET_H) { data.settings.pos.y -= PET_H - (data.settings.petH || 400); }
  data.settings.petH = PET_H;
  const p = validPos(data.settings.pos) ? data.settings.pos : defaultPos();
  pet = new BrowserWindow({
    x: p.x, y: p.y, width: PET_W, height: PET_H,
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
function showPet() {
  if (!pet || pet.isDestroyed()) return;
  if (Date.now() < hiddenUntil) return;
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
  manager.on('closed', () => { manager = null; });
}

/* ---------------- tray ---------------- */
function rebuildTray() {
  if (!tray) return;
  const visible = pet && !pet.isDestroyed() && pet.isVisible();
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open Desktop Pal', click: () => openManager() },
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
ipcMain.on('pet:ready', () => { calmSent = null; lastStateJson = ''; pushState(queue.length > 0); updateCalm(); });
let dragStart = null;
ipcMain.on('pet:drag-start', () => { dragStart = pet.getPosition(); });
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
  data.settings = Object.assign(data.settings, s);
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
app.on('will-quit', () => log('state updates sent', stateSends, 'skipped (no change)', stateSkips));
app.on('window-all-closed', (e) => { /* keep running in tray */ });
app.whenReady().then(async () => {
  if (!(await waitForLock())) { app.quit(); return; }
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
  if (firstRun) setTimeout(() => openManager(), 1500);
  if (process.env.OTTER_DEMO) setTimeout(() => fire(data.reminders[0].id), 1200);
});
