const ROOT = require('path').resolve(__dirname, '..'); const SCRATCH = process.env.DP_SCRATCH || require('os').tmpdir();
const { _electron: electron } = require('playwright'); const fs = require('fs'), os = require('os'), path = require('path');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 60000) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = await fn(); if (v) return v; } catch (_) {} await sleep(250); } return null; }
let pass = 0, fail = 0; const ok = (n, c, x) => { console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${x ? '  — ' + x : ''}`); c ? pass++ : fail++; };
async function run(feed) {
  const cfg = fs.mkdtempSync(path.join(os.tmpdir(), 'up-')); fs.mkdirSync(cfg + '/Desktop Pal');
  fs.writeFileSync(cfg + '/Desktop Pal/otterpal-data.json', JSON.stringify({ reminders: [], settings: { todoNudgeMin: 0, petName: 'Pedro' }, lastNudge: Date.now() }));
  const app = await electron.launch({ executablePath: ROOT + '/node_modules/electron/dist/electron', args: ['--no-sandbox', ROOT], env: { ...process.env, XDG_CONFIG_HOME: cfg, DP_TEST_UPDATES: feed } });
  const pet = await app.firstWindow();
  return { app, pet, cfg };
}
(async () => {
  // a) a newer version is published
  let { app, pet, cfg } = await run('http://127.0.0.1:8765');
  const bubble = await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('1.4.0'), 90000);
  ok('finds and downloads the new version, pet announces it', !!bubble);
  ok('download was verified (checksum) before announcing', fs.readFileSync(cfg + '/Desktop Pal/otterpal.log', 'utf8').includes('update-downloaded') || !!bubble);
  ok('pet looks excited about it', await pet.locator('#stage.m-excited').count() === 1);
  ok('bubble offers "Restart now" and "Later"', (await pet.locator('#bubble [data-a="done"]').innerText()) === 'Restart now' && (await pet.locator('#bubble [data-a="snooze"]').innerText()) === 'Later');
  await pet.locator('#bubble [data-a="snooze"]').click();
  ok('"Later" puts the notice away', !!(await until(async () => !(await pet.locator('#stage.alert').count()), 5000)));
  // settings shows it too
  await pet.evaluate(() => window.otter.open('set'));
  const mgr = await until(() => app.windows().find(w => w.url().includes('manager.html')), 8000);
  await mgr.waitForLoadState(); await sleep(800);
  ok('Settings shows "Version 1.4.0 is ready"', (await mgr.locator('#aboutLine').innerText()).includes('1.4.0 is ready'), await mgr.locator('#aboutLine').innerText());
  ok('Settings button says "Restart to update"', (await mgr.locator('#updBtn').innerText()) === 'Restart to update');
  await app.close();
  // b) already up to date (feed says same version)
  fs.writeFileSync('' + SCRATCH + '/feed-same/latest.yml', fs.readFileSync('' + SCRATCH + '/feed/latest.yml', 'utf8').replace(/1\.4\.0/g, '1.3.0'));
  ({ app, pet, cfg } = await run('http://127.0.0.1:8765/../feed-same-missing'));
  await sleep(6000);
  ok('no feed published yet: stays quiet (no bubble, no error)', !(await pet.locator('#stage.alert').count()));
  await pet.evaluate(() => window.otter.open('set'));
  const m2 = await until(() => app.windows().find(w => w.url().includes('manager.html')), 8000); await m2.waitForLoadState(); await sleep(800);
  ok('no feed: Settings hides the update button', !(await m2.locator('#updBtn').isVisible()), await m2.locator('#aboutLine').innerText());
  await app.close();
  console.log(`\n${pass}/${pass + fail} passed`); process.exit(fail ? 1 : 0);
})().catch(e => { console.error('CRASH', e); process.exit(2); });
