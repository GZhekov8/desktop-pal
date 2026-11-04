// End-to-end tests for 1.6 features: focus timer, treats + feeding, petting, walking, sounds settings.
// Minutes are shortened (DP_FOCUS_MINUTE_MS) and walks start quickly (DP_WALK_SCALE).
const ROOT = require('path').resolve(__dirname, '..');
const { _electron: electron } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');
const results = []; let failures = 0;
function ok(name, cond, extra) { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`); if (!cond) failures++; }
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 8000, step = 150) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = await fn(); if (v) return v; } catch (_) {} await sleep(step); } return null; }

async function launch(settings, extraEnv = {}) {
  const cfg = fs.mkdtempSync(path.join(os.tmpdir(), 'dp16-')); fs.mkdirSync(cfg + '/Desktop Pal');
  const due = new Date(Date.now() + 2500), p = n => String(n).padStart(2, '0');
  fs.writeFileSync(cfg + '/Desktop Pal/otterpal-data.json', JSON.stringify({
    reminders: [{ id: 'r1', type: 'once', title: 'Pay the bill', at: `${due.getFullYear()}-${p(due.getMonth() + 1)}-${p(due.getDate())}T${p(due.getHours())}:${p(due.getMinutes())}`, enabled: true }],
    settings: { todoNudgeMin: 0, petName: 'Pedro', walk: 'off', ...settings }, lastNudge: Date.now()
  }));
  const app = await electron.launch({ executablePath: ROOT + '/node_modules/electron/dist/electron', args: ['--no-sandbox', ROOT],
    env: { ...process.env, XDG_CONFIG_HOME: cfg, DP_FOCUS_MINUTE_MS: '1000', ...extraEnv } });
  const pet = await app.firstWindow(); const errors = [];
  pet.on('pageerror', e => errors.push(String(e)));
  await pet.waitForSelector('#otterWrap', { state: 'attached' }); await sleep(1500);
  const data = () => JSON.parse(fs.readFileSync(cfg + '/Desktop Pal/otterpal-data.json', 'utf8'));
  return { app, pet, errors, data, cfg };
}
const bounds = (app) => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('pet.html')).getBounds());

(async () => {
  // ---------------- focus, reminders held as a badge (default) ----------------
  let { app, pet, errors, data } = await launch({ focusPreset: 'custom', focusMin: 4, breakMin: 3, longBreakMin: 5 });
  await pet.evaluate(() => window.otter.done('r1')).catch(() => {});
  await until(() => !data().queue.includes('r1'));
  await pet.evaluate(() => window.otter.focus(true));
  ok('focus starts from the pet', !!(await until(() => data().focus.state === 'focus')));
  await pet.evaluate(() => window.otter.test());   // a reminder comes due during focus
  ok('countdown chip shows on the pet', !!(await until(() => pet.locator('#chip.on').count())), await pet.locator('#chip').innerText().catch(() => ''));
  ok('reminder due during focus is held, not shown', !!(await until(() => data().held.includes('r1'), 6000)) && !(await pet.locator('#stage.alert').count()));
  ok('chip shows "1 waiting"', (await pet.locator('#chip').innerText()).includes('1 waiting'), await pet.locator('#chip').innerText());
  ok('break bubble appears when focus ends', !!(await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('Break time'), 8000)));
  ok('held reminder released at the break', !!(await until(() => data().held.length === 0 && data().queue.includes('r1'), 3000)));
  ok('break message shown first, released reminder after it', (await pet.locator('#bubble .b-head').innerText()).includes('1 of 2'));
  ok('finished session counted + treat earned', data().stats.sessions === 1 && data().treats >= 1, JSON.stringify({ s: data().stats, t: data().treats }));
  ok('break bubble offers Skip break / Stop focusing', (await pet.locator('#bubble [data-a="done"]').innerText()) === 'Skip break' && (await pet.locator('#bubble [data-a="snooze"]').innerText()) === 'Stop focusing');
  ok('"next round" prompt appears when the break ends', !!(await until(async () => {
    for (let i = 0; i < 3; i++) { const t = await pet.locator('#bubble.show .b-title').innerText(); if (t.includes('Ready for round 2')) return true; if ((await pet.locator('#nextItem').count())) await pet.locator('#nextItem').click(); }
    return false; }, 9000)));
  // stop focus from the prompt
  await pet.evaluate(() => window.otter.focus(false));
  ok('stopping focus returns to idle', !!(await until(() => data().focus.state === 'idle')));
  ok('chip hides when not focusing', !!(await until(async () => !(await pet.locator('#chip.on').count()))));
  ok('no page errors (focus)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  // ---------------- focus with "show as usual" ----------------
  ({ app, pet, errors, data } = await launch({ focusPreset: 'custom', focusMin: 30, focusReminders: 'show' }));
  await pet.evaluate(() => window.otter.focus(true));
  ok('"show as usual": reminder pops up during focus', !!(await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('Pay the bill'), 8000)));
  ok('"show as usual": nothing held', data().held.length === 0);
  await pet.locator('#bubble [data-a="done"]').click();
  ok('finishing a reminder earns a treat', !!(await until(() => data().treats === 1)));
  // feeding
  await pet.evaluate(() => { closeBubble(); });
  const box = await pet.locator('#otterWrap').boundingBox();
  await pet.mouse.move(box.x + box.width * .75, box.y + box.height * .5); await pet.mouse.down(); await pet.mouse.up();
  const treatBtn = await until(() => pet.locator('#bubble [data-a="treat"]').count());
  ok('pet bubble shows the treat button', !!treatBtn);
  await pet.locator('#bubble [data-a="treat"]').click();
  ok('feeding uses up the treat', !!(await until(() => data().treats === 0)));
  ok('snack appears and pet chews / looks happy', !!(await until(async () => (await pet.locator('.snack').count()) || (await pet.locator('#stage.m-chew1, #stage.m-chew2, #stage.m-love').count()), 3000)));
  ok('no treat button when there are none', !!(await until(async () => { await pet.mouse.move(box.x + box.width * .75, box.y + box.height * .5); await pet.mouse.down(); await pet.mouse.up(); await sleep(300); return !(await pet.locator('#bubble [data-a="treat"]').count()); }, 6000)));
  await pet.evaluate(() => closeBubble());
  // petting
  await sleep(2700);
  await pet.mouse.move(box.x + 120, box.y + 90);
  for (let i = 0; i < 8; i++) { await pet.mouse.move(box.x + (i % 2 ? 160 : 110), box.y + 90, { steps: 3 }); await sleep(60); }
  ok('stroking the pet makes it happy (love face + lean)', !!(await until(() => pet.locator('#stage.petting, #stage.m-love').count(), 2000)));
  ok('no page errors (treats/petting)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  // ---------------- walking ----------------
  ({ app, pet, errors, data } = await launch({ walk: 'often' }, { DP_WALK_SCALE: '40' }));
  await pet.evaluate(() => window.otter.done('r1')).catch(() => {});
  const home = await bounds(app);
  const walked = await until(async () => { const b = await bounds(app); return Math.abs(b.x - home.x) > 30 && b; }, 12000);
  ok('pet goes for a walk along the screen', !!walked, walked && `${home.x} -> ${walked.x}`);
  ok('walking pose with legs is shown', !!(await until(() => pet.locator('#stage.pose-walk, #stage.pose-stand').count(), 4000)));
  ok('walk stays on the same line (y unchanged)', walked && walked.y === home.y);
  ok('legs move while walking', !!(await until(() => pet.evaluate(() => [...document.querySelectorAll('#slot-walk .swing')].some(s => /rotate\(-?[1-9]/.test(s.getAttribute('transform') || ''))), 4000)));
  // a reminder during a walk: stop and show the bubble
  await pet.evaluate(() => window.otter.settings({ walk: 'often' }));
  await app.evaluate(() => {});
  await pet.evaluate(() => window.otter.test && 0);
  const mgrless = await pet.evaluate(async () => { await window.otter.test(); return true; });
  ok('reminder while out: pet stops and shows the bubble', !!(await until(async () => (await pet.locator('#bubble.show').count()) && !(await pet.locator('#stage.pose-walk').count()), 6000)));
  await pet.locator('#bubble [data-a="done"]').click();
  const back = await until(async () => { const b = await bounds(app); return b.x === home.x && b; }, 25000);
  ok('after Done it walks back home', !!back);
  ok('back home: resting pose again', !!(await until(async () => !(await pet.locator('#stage.pose-walk, #stage.pose-stand').count()), 4000)));
  await pet.evaluate(() => window.otter.settings({ walk: 'off' }));
  await sleep(3000); const b1 = await bounds(app); await sleep(4000); const b2 = await bounds(app);
  ok('"Off" stops walking', b1.x === b2.x && b2.x === home.x);
  ok('no page errors (walking)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  // ---------------- every animal can walk ----------------
  for (const a of ['cat', 'dog', 'fox', 'redpanda']) {
    ({ app, pet, errors } = await launch({ animal: a, walk: 'often' }, { DP_WALK_SCALE: '60' }));
    await pet.evaluate(() => window.otter.done('r1')).catch(() => {});
    const h = await bounds(app);
    const w = await until(async () => { const b = await bounds(app); return Math.abs(b.x - h.x) > 20; }, 12000);
    ok(`${a} walks`, !!w && await pet.evaluate(() => document.querySelectorAll('#slot-walk .swing').length === 4));
    ok(`${a}: no page errors`, errors.length === 0, errors.slice(0, 2).join(' | '));
    await app.close();
  }

  // ---------------- sounds settings ----------------
  ({ app, pet, errors, data } = await launch({}));
  await pet.evaluate(() => window.otter.settings({ volume: 35, voices: false, quietOn: true, quietFrom: '00:00', quietTo: '23:59' }));
  const s = await until(() => { const d = data().settings; return d.volume === 35 && d.voices === false && d.quietOn === true && d; });
  ok('volume / voice / quiet hours saved', !!s);
  ok('quiet hours silence sounds', await pet.evaluate(() => quietNow() === true && audio() === null));
  await pet.evaluate(() => window.otter.settings({ quietOn: false, voices: true, volume: 80 }));
  await sleep(600);
  ok('voices play without errors for every animal', await pet.evaluate(async () => {
    for (const a of ['otter', 'cat', 'dog', 'fox', 'redpanda']) { state.settings.animal = a; for (const k of ['pet', 'happy', 'call']) voice(k); }
    munch(); chime(); return true; }));
  ok('no page errors (sounds)', errors.length === 0, errors.slice(0, 2).join(' | '));
  await app.close();

  console.log(results.join('\n'));
  console.log(`\n${results.length - failures}/${results.length} passed`);
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log(results.join('\n')); console.error('CRASH', e); process.exit(2); });
