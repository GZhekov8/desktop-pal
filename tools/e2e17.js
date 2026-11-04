// End-to-end tests for 1.7 gaming mode. A file stands in for the Windows game-check helper
// (DP_GAME_PROBE); minutes are shortened (DP_GAME_MINUTE_MS) so the 2-hour break nudge comes in seconds.
const ROOT = require('path').resolve(__dirname, '..');
const { _electron: electron } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');
const results = []; let failures = 0;
function ok(name, cond, extra) { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`); if (!cond) failures++; }
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 8000, step = 150) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = await fn(); if (v) return v; } catch (_) {} await sleep(step); } return null; }
const p2 = n => String(n).padStart(2, '0');

async function launch(settings, dueIn = 2500) {
  const cfg = fs.mkdtempSync(path.join(os.tmpdir(), 'dp17-')); fs.mkdirSync(cfg + '/Desktop Pal');
  const probe = cfg + '/probe.txt'; fs.writeFileSync(probe, '5|0|explorer.exe\n');
  const due = new Date(Date.now() + dueIn);
  fs.writeFileSync(cfg + '/Desktop Pal/otterpal-data.json', JSON.stringify({
    reminders: [{ id: 'r1', type: 'once', title: 'Pay the bill', at: `${due.getFullYear()}-${p2(due.getMonth() + 1)}-${p2(due.getDate())}T${p2(due.getHours())}:${p2(due.getMinutes())}`, enabled: true }],
    settings: { todoNudgeMin: 0, petName: 'Pedro', walk: 'off', bedOn: false, gameBreakMin: 120, ...settings }, lastNudge: Date.now()
  }));
  const app = await electron.launch({ executablePath: ROOT + '/node_modules/electron/dist/electron', args: ['--no-sandbox', ROOT],
    env: { ...process.env, XDG_CONFIG_HOME: cfg, DP_GAME_PROBE: probe, DP_GAME_ON_MS: '600', DP_GAME_OFF_MS: '1500', DP_GAME_MINUTE_MS: '100', DP_PEEK_MS: '3000' } });
  const pet = await app.firstWindow(); const errors = [];
  pet.on('pageerror', e => errors.push(String(e)));
  await pet.waitForSelector('#otterWrap', { state: 'attached' }); await sleep(1500);
  const data = () => JSON.parse(fs.readFileSync(cfg + '/Desktop Pal/otterpal-data.json', 'utf8'));
  const game = (line) => fs.writeFileSync(probe, line + '\n');
  const visible = () => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('pet.html')).isVisible());
  return { app, pet, errors, data, game, visible };
}
const title = (pet) => pet.locator('#bubble.show .b-title').innerText().catch(() => '');

(async () => {
  // ---------------- a game starts: hide, hold, nudge, welcome back ----------------
  let { app, pet, errors, data, game, visible } = await launch({}, 600000);
  ok('pet visible before playing', await visible());
  game('2|1|eldenring.exe');
  ok('full-screen game hides the pet', !!(await until(async () => !(await visible()), 4000)));
  await pet.evaluate(() => window.otter.test());    // a reminder comes due mid-game
  ok('reminder due while playing is held, not shown', !!(await until(() => data().held.includes('r1'), 8000)) && !(await visible()) && !data().queue.includes('r1'));
  ok('break nudge peeks in after 2 hours of play', !!(await until(async () => (await visible()) && (await title(pet)).includes('playing for'), 16000)), await title(pet));
  ok('peek wears the headset', (await pet.locator('#stage.headset-on').count()) === 1);
  ok('peek did not release the held reminder', data().held.includes('r1'));
  const treats0 = data().treats || 0;
  await pet.locator('#bubble [data-a="done"]').click();
  ok('"Taking a break" earns a treat', !!(await until(() => (data().treats || 0) === treats0 + 1)));
  ok('pet tucks away again after the nudge', !!(await until(async () => !(await visible()), 4000)));
  // bedtime: once, then it goes away by itself if ignored
  const now = new Date();
  await pet.evaluate((t) => window.otter.settings({ bedOn: true, bedTime: t, gameBreakMin: 0 }), `${p2(now.getHours())}:${p2(now.getMinutes())}`);
  ok('bedtime warning peeks in', !!(await until(async () => (await visible()) && (await title(pet)).includes('getting late'), 6000)), await title(pet));
  ok('ignored peek hides by itself', !!(await until(async () => !(await visible()), 7000)));
  await sleep(2500);
  ok('bedtime warning only once', !(await visible()) && !!data().game.bedWarned);
  // alt-tab out briefly doesn't end the session
  game('5|0|explorer.exe'); await sleep(700); game('2|1|eldenring.exe'); await sleep(1500);
  ok('short alt-tab keeps gaming mode on', !(await visible()));
  // the game ends
  game('5|0|explorer.exe');
  ok('pet comes back when the game ends', !!(await until(visible, 5000)));
  ok('welcome back with the headset on', !!(await until(() => pet.locator('#stage.headset-on').count(), 2000)));
  ok('held reminder shown after the welcome', !!(await until(async () => (await title(pet)).includes('Pay the bill'), 6000)) && data().held.length === 0);
  ok('headset comes off again', !!(await until(async () => !(await pet.locator('#stage.headset-on').count()), 5000)));
  ok('no page errors (gaming)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  // ---------------- what counts as a game ----------------
  ({ app, pet, errors, data, game, visible } = await launch({}, 600000));
  game('2|1|chrome.exe'); await sleep(2200);
  ok('full-screen browser is not a game', await visible());
  game('2|1|vlc.exe'); await sleep(2200);
  ok('full-screen video player is not a game', await visible());
  game('4|1|someapp.exe'); await sleep(2200);
  ok('presentation mode is not a game', await visible());
  game('5|0|notepad.exe'); await sleep(2200);
  ok('normal window is not a game', await visible());
  game('3|0|oldgame.exe');
  ok('exclusive full-screen (Direct3D) counts', !!(await until(async () => !(await visible()), 4000)));
  game('5|0|explorer.exe'); await until(visible, 5000);
  game('5|1|borderless.exe');
  ok('borderless full-screen window counts', !!(await until(async () => !(await visible()), 4000)));
  game('5|0|explorer.exe'); await until(visible, 5000);
  // switched off
  await pet.evaluate(() => window.otter.settings({ gaming: false }));
  game('2|1|eldenring.exe'); await sleep(2500);
  ok('"Gaming mode" off: pet stays', await visible());
  await pet.evaluate(() => window.otter.settings({ gaming: true }));
  ok('switched back on: detects the running game', !!(await until(async () => !(await visible()), 5000)));
  ok('no page errors (detection)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  console.log(results.join('\n'));
  console.log(`\n${results.length - failures}/${results.length} passed`);
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log(results.join('\n')); console.error('CRASH', e); process.exit(2); });
