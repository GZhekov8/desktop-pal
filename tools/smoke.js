// Quick launch test, used on GitHub's Mac (and Windows) machines before building the installers:
// starts the real app, checks the pet appears and draws, the app window opens, nothing errors,
// and the game-check helper answers. Saves screenshots to smoke/ for a look.
// usage: node tools/smoke.js [path to game-check helper]
const ROOT = require('path').resolve(__dirname, '..');
const { _electron: electron } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const results = []; let failures = 0;
function ok(name, cond, extra) { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`); if (!cond) failures++; }
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 10000, step = 200) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = await fn(); if (v) return v; } catch (_) {} await sleep(step); } return null; }
const out = path.join(ROOT, 'smoke'); fs.mkdirSync(out, { recursive: true });

(async () => {
  const helper = process.argv[2];
  if (helper) {
    const line = await new Promise((res) => {
      const p = spawn(helper, [], { stdio: ['pipe', 'pipe', 'inherit'] }); let buf = '';
      const t = setTimeout(() => { p.kill(); res(buf); }, 8000);
      p.stdout.on('data', d => { buf += d; if (buf.includes('\n')) { clearTimeout(t); p.stdin.end(); setTimeout(() => res(buf), 500); } });
      p.on('error', e => { clearTimeout(t); res('error ' + e); });
    });
    ok('game-check helper answers', /^\d\|[01]\|/.test(line), JSON.stringify(line.trim()));
  }
  // start like a returning user (a first run opens the app window by itself)
  const os = require('os');
  const base = process.platform === 'darwin' ? path.join(os.homedir(), 'Library', 'Application Support')
    : process.platform === 'win32' ? process.env.APPDATA : (process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config'));
  const dir = path.join(base, 'Desktop Pal'); fs.mkdirSync(dir, { recursive: true });
  const due = new Date(Date.now() + 3600000), p2 = n => String(n).padStart(2, '0');
  fs.writeFileSync(path.join(dir, 'otterpal-data.json'), JSON.stringify({ reminders: [{ id: 'r1', type: 'once', title: 'Pay the bill',
    at: `${due.getFullYear()}-${p2(due.getMonth() + 1)}-${p2(due.getDate())}T${p2(due.getHours())}:${p2(due.getMinutes())}`, enabled: true }],
    settings: { todoNudgeMin: 0, walk: 'off', startWithWindows: false }, lastNudge: Date.now() }));
  const app = await electron.launch({ executablePath: require('electron'), args: [ROOT], env: { ...process.env, DP_WALK_SCALE: '1' } });
  const errors = [];
  const pet = await app.firstWindow(); pet.on('pageerror', e => errors.push(String(e)));
  await pet.waitForSelector('#otterWrap', { state: 'attached', timeout: 20000 });
  ok('pet window opens', true, process.platform + ' ' + process.arch);
  ok('pet artwork is drawn', !!(await until(() => pet.evaluate(() => document.querySelectorAll('#slot-float path').length > 50))));
  const info = await app.evaluate(({ BrowserWindow, app }) => {
    const w = BrowserWindow.getAllWindows().find(x => x.webContents.getURL().includes('pet.html'));
    return { visible: w.isVisible(), top: w.isAlwaysOnTop(), b: w.getBounds(), name: app.getName(), dock: process.platform === 'darwin' ? app.dock.isVisible() : null };
  });
  ok('pet is visible and always on top', info.visible && info.top, JSON.stringify(info.b));
  if (process.platform === 'darwin') ok('no Dock icon while only the pet is showing', info.dock === false);
  await sleep(1500);
  await pet.screenshot({ path: path.join(out, 'pet.png') });
  await pet.evaluate(() => window.otter.test());
  ok('a reminder shows the speech bubble', !!(await until(() => pet.locator('#bubble.show').count())));
  await sleep(800); await pet.screenshot({ path: path.join(out, 'bubble.png') });
  await pet.locator('#bubble [data-a="open"]').click();
  const mgr = await until(async () => app.windows().find(w => w.url().includes('manager.html')));
  ok('the app window opens', !!mgr);
  if (mgr) {
    mgr.on('pageerror', e => errors.push(String(e)));
    await mgr.waitForLoadState(); await sleep(1200);
    await mgr.screenshot({ path: path.join(out, 'app.png') });
    if (process.platform === 'darwin') {
      ok('Mac wording in settings', await mgr.evaluate(() => document.documentElement.classList.contains('mac')));
      ok('Dock icon shows while the app window is open', await app.evaluate(({ app }) => app.dock.isVisible()));
    }
  }
  ok('voices decode', !!(await until(() => pet.evaluate(() => { loadClips('cat'); return Object.keys(clipBufs).length >= 4; }), 8000)));
  ok('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await app.close();
  console.log(results.join('\n'));
  console.log(`\n${results.length - failures}/${results.length} passed`);
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log(results.join('\n')); console.error('CRASH', e); process.exit(2); });
