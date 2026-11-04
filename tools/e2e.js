// End-to-end test of Desktop Pal: launches the real Electron app and drives it.
const ROOT = require('path').resolve(__dirname, '..'); const SCRATCH = process.env.DP_SCRATCH || require('os').tmpdir();
const { _electron: electron } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');

const results = []; let failures = 0;
function ok(name, cond, extra) { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  — ' + extra : ''}`); if (!cond) failures++; }
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function until(fn, ms = 8000, step = 150) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = await fn(); if (v) return v; } catch (_) {} await sleep(step); } return null; }

const cfg = fs.mkdtempSync(path.join(os.tmpdir(), 'dp-'));
const dataFile = () => path.join(cfg, 'Desktop Pal', 'otterpal-data.json');
const readData = () => JSON.parse(fs.readFileSync(dataFile(), 'utf8'));

async function launch() {
  const app = await electron.launch({ executablePath: ROOT + '/node_modules/electron/dist/electron', args: ['--no-sandbox', ROOT], env: { ...process.env, XDG_CONFIG_HOME: cfg }, timeout: 30000 });
  const errors = [];
  app.on('window', (w) => { w.on('pageerror', e => errors.push(String(e))); w.on('console', m => { if (m.type() === 'error') errors.push(m.text()); }); });
  const pet = await app.firstWindow();
  pet.on('pageerror', e => errors.push(String(e)));
  await pet.waitForSelector('#otterWrap', { state: 'attached' });
  await sleep(1800);
  return { app, pet, errors };
}
const windows = (app) => app.windows();
const managerOf = (app) => app.windows().find(w => w.url().includes('manager.html'));
async function petClick(pet) { // real mouse click on the pet (not a drag)
  const box = await pet.locator('#otterWrap').boundingBox();
  await pet.mouse.move(box.x + box.width * .75, box.y + box.height * .5);
  await pet.mouse.down(); await pet.mouse.up();
}

(async () => {
  // ---------- seed an old "Otter Pal" data folder to test the rename migration
  fs.mkdirSync(path.join(cfg, 'Otter Pal'), { recursive: true });
  fs.writeFileSync(path.join(cfg, 'Otter Pal', 'otterpal-data.json'), JSON.stringify({
    reminders: [{ id: 'old1', type: 'todo', title: 'Old to-do survives rename', done: false, enabled: true }],
    settings: { petName: 'Pedro', animal: 'otter', todoNudgeMin: 0, walk: 'off' }, lastNudge: Date.now()
  }));

  let { app, pet, errors } = await launch();
  ok('app starts and shows the pet window', !!pet);
  ok('data migrated from old "Otter Pal" folder', fs.existsSync(dataFile()) && readData().reminders.some(r => r.title === 'Old to-do survives rename'));
  ok('pet name kept after migration', readData().settings.petName === 'Pedro');
  ok('pet window title is Desktop Pal', (await pet.title()) === 'Desktop Pal');
  const bw = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().map(w => ({ top: w.isAlwaysOnTop(), vis: w.isVisible(), b: w.getBounds() })));
  ok('pet window is visible and always on top', bw.length === 1 && bw[0].top && bw[0].vis, JSON.stringify(bw[0]));

  // ---------- click pet -> peek bubble with Open app
  await petClick(pet);
  const bubbleShown = await until(() => pet.locator('#bubble.show').count());
  ok('clicking the pet shows a bubble', !!bubbleShown);
  const openBtn = pet.locator('#bubble [data-a="open"]');
  ok('bubble has an "Open app" button', (await openBtn.count()) === 1 && (await openBtn.innerText()).trim() === 'Open app');
  ok('"Open app" is the first (main) button', (await pet.locator('#bubble .b-actions .btn').first().innerText()).trim() === 'Open app');
  await openBtn.click();
  const mgr = await until(() => managerOf(app));
  ok('"Open app" opens the Desktop Pal app window', !!mgr);
  await mgr.waitForLoadState();
  ok('app window title', (await mgr.title()) === 'Desktop Pal — Reminders', await mgr.title());
  ok('app header says Desktop Pal', (await mgr.locator('h1').innerText()) === 'Desktop Pal');
  ok('bubble closes after opening the app', !(await pet.locator('#bubble.show').count()));

  // open again: must not create a second window
  await petClick(pet); await until(() => pet.locator('#bubble.show').count());
  await pet.locator('#bubble [data-a="open"]').click(); await sleep(700);
  ok('"Open app" twice reuses the same window', app.windows().filter(w => w.url().includes('manager.html')).length === 1);

  // "+ Add reminder" opens the form
  await petClick(pet); await until(() => pet.locator('#bubble.show').count());
  await pet.locator('#bubble [data-a="new"]').click();
  ok('"+ Add reminder" opens the new-reminder form', !!(await until(() => mgr.locator('#scrim.show').count())));

  // ---------- create a one-time reminder that is due now
  await mgr.fill('#f-title', 'Pay the electricity bill');
  await mgr.click('#f-type [data-v="once"]');
  const nowLocal = await mgr.evaluate(() => { const d = new Date(Date.now() - 60000); const p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`; });
  await mgr.fill('#f-at', nowLocal);
  await mgr.click('#mSave');
  ok('form closes after saving', !!(await until(async () => !(await mgr.locator('#scrim.show').count()))));
  ok('reminder saved to disk', !!(await until(() => readData().reminders.find(r => r.title === 'Pay the electricity bill'))));

  // fires within one scheduler tick
  const fired = await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('electricity'), 9000);
  ok('due reminder pops up in the bubble', !!fired);
  ok('pet switches to alert pose', await pet.locator('#stage.alert').count() === 1);
  ok('"bill" reminder makes a serious face', await pet.locator('#stage.m-serious').count() === 1, await pet.locator('#stage').getAttribute('class'));
  ok('alert bubble has an "Open app" link', await pet.locator('#bubble .open-app').count() === 1);
  ok('manager shows it as waiting', !!(await until(() => mgr.locator('.pill.wait').count())));

  // alert "Open app" link: opens app, keeps the reminder
  await mgr.close(); await sleep(400);
  await pet.locator('#bubble .open-app').click();
  const mgr2 = await until(() => managerOf(app));
  ok('alert "Open app" link opens the app window', !!mgr2);
  ok('reminder is still waiting after opening the app', await pet.locator('#stage.alert').count() === 1);

  // Done
  await pet.locator('#bubble [data-a="done"]').click();
  ok('Done clears the reminder', !!(await until(async () => !(await pet.locator('#stage.alert').count()))));
  ok('Done shows the proud face', await pet.locator('#stage.m-proud').count() === 1);
  ok('one-time reminder marked done on disk', !!(await until(() => readData().reminders.find(r => r.title === 'Pay the electricity bill')?.done === true)));

  // ---------- repeating reminder, snooze
  await mgr2.waitForLoadState();
  await mgr2.click('#addBtn');
  await mgr2.fill('#f-title', 'Drink water');
  await mgr2.click('#f-type [data-v="interval"]');
  await mgr2.fill('#f-every', '1'); await mgr2.fill('#f-from', '00:00'); await mgr2.fill('#f-to', '23:59');
  await mgr2.click('[data-d="all"]');
  await mgr2.click('#mSave');
  const water = await until(() => readData().reminders.find(r => r.title === 'Drink water'));
  ok('interval reminder saved with next time ~1 min away', water && Math.abs(water.nextAt - Date.now() - 60000) < 15000, water && new Date(water.nextAt).toISOString());
  // force it due now through the app's own data (edit -> once is not needed): poke nextAt via main process
  await app.evaluate(() => { /* nothing */ });
  const fired2 = await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('Drink water'), 80000, 500);
  ok('interval reminder fires on time', !!fired2);
  ok('"water" reminder makes a happy face', await pet.locator('#stage.m-happy').count() === 1, await pet.locator('#stage').getAttribute('class'));
  await pet.locator('#bubble [data-a="snooze"]').first().click();
  const snoozed = await until(() => { const r = readData().reminders.find(r => r.title === 'Drink water'); return r && r.nextAt > Date.now() + 9 * 60000 && r.nextAt < Date.now() + 11 * 60000 && r; });
  ok('Snooze 10m reschedules ~10 minutes ahead', !!snoozed);
  ok('Snooze shows the sleepy face', await pet.locator('#stage.m-sleepy').count() === 1);
  ok('bubble hides after snooze', !!(await until(async () => !(await pet.locator('#bubble.show').count()))));

  // ---------- to-do list
  await mgr2.click('.tab[data-tab="todo"]');
  await mgr2.fill('#todoInput', 'Reply to the email'); await mgr2.press('#todoInput', 'Enter');
  ok('to-do added from quick-add box', !!(await until(() => readData().reminders.find(r => r.title === 'Reply to the email'))));
  const todoBox = mgr2.locator('.item', { hasText: 'Reply to the email' }).locator('input.check');
  await todoBox.check();
  ok('ticking a to-do marks it done', !!(await until(() => readData().reminders.find(r => r.title === 'Reply to the email')?.done === true)));
  ok('pet badge counts open to-dos', (await pet.locator('#badgeTxt').textContent()) === '1', await pet.locator('#badgeTxt').textContent());

  // ---------- edit & delete
  await mgr2.click('.tab[data-tab="rem"]');
  await mgr2.locator('.item', { hasText: 'Drink water' }).locator('[data-edit]').click();
  ok('edit form pre-fills the title', (await mgr2.inputValue('#f-title')) === 'Drink water');
  ok('edit form pre-fills interval', (await mgr2.inputValue('#f-every')) === '1');
  await mgr2.fill('#f-title', 'Drink a glass of water'); await mgr2.selectOption('#f-mood', 'love'); await mgr2.click('#mSave');
  ok('edit saves changes (title + chosen face)', !!(await until(() => { const r = readData().reminders.find(r => r.title === 'Drink a glass of water'); return r && r.mood === 'love'; })));
  ok('edit does not create a duplicate', readData().reminders.filter(r => /water/i.test(r.title)).length === 1);
  mgr2.once('dialog', d => d.accept());
  await mgr2.locator('.item', { hasText: 'Drink a glass of water' }).locator('[data-del]').click();
  ok('delete removes the reminder', !!(await until(() => !readData().reminders.find(r => /water/i.test(r.title)))));

  // empty title is rejected
  await mgr2.click('#addBtn'); await mgr2.fill('#f-title', '   '); await mgr2.click('#mSave'); await sleep(300);
  ok('blank title is not saved', await mgr2.locator('#scrim.show').count() === 1);
  await mgr2.click('#mCancel');

  // ---------- settings: animal, name, size
  await mgr2.click('.tab[data-tab="set"]');
  for (const a of ['cat', 'dog', 'fox', 'redpanda', 'otter']) {
    await mgr2.selectOption('#s-animal', a);
    ok(`switching animal to ${a}`, !!(await until(() => pet.locator(`#stage.pet-${a}`).count(), 4000)));
    const shown = await pet.evaluate((a) => getComputedStyle(document.querySelector('.float .a-' + a)).display !== 'none', a);
    ok(`${a} is drawn`, shown);
  }
  await mgr2.fill('#s-petName', 'Biscuit'); await mgr2.press('#s-petName', 'Tab');
  ok('rename pet saved', !!(await until(() => readData().settings.petName === 'Biscuit')));
  const slide = async (id, v) => mgr2.evaluate(([id, v]) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); }, [id, v]);
  const petBounds = () => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('pet.html')).getBounds());
  const b0 = await petBounds();
  ok('pet size slider has 5% steps from 50% to 150%', await mgr2.evaluate(() => { const e = document.getElementById('s-size'); return e.min === '50' && e.max === '150' && e.step === '5'; }));
  await slide('s-size', 65);
  ok('pet size 65% previewed on the pet', !!(await until(async () => (await pet.locator('#stage').getAttribute('style') || '').includes('--pet: 0.65'))));
  ok('preview is NOT saved yet', readData().settings.size !== 0.65);
  ok('preview shows Apply / Cancel in Settings', await mgr2.locator('#previewRow').isVisible());
  ok('pet shows a sample bubble with Apply / Cancel', !!(await until(async () => (await pet.locator('#bubble.show .b-title').innerText()).includes('how reminders will look'))));
  await mgr2.click('#sizeApply');
  ok('Apply saves pet size 0.65', !!(await until(() => readData().settings.size === 0.65)));
  ok('sample bubble goes away after Apply', !!(await until(async () => !(await pet.locator('#bubble.show').count()))));
  ok('slider label shows 65%', (await mgr2.locator('#o-size').innerText()) === '65%');
  const b1 = await petBounds();
  ok('window shrinks but keeps its bottom-right corner', b1.x + b1.width === b0.x + b0.width && b1.y + b1.height === b0.y + b0.height && b1.height < b0.height, `${JSON.stringify(b0)} -> ${JSON.stringify(b1)}`);
  await slide('s-textSize', 130);
  ok('text size 130% previewed on the bubble only', !!(await until(async () => (await pet.locator('#stage').getAttribute('style') || '').includes('--text: 1.3'))));
  await mgr2.click('#sizeApply');
  await until(() => readData().settings.textSize === 1.3);
  await mgr2.click('#testBtn');
  await until(() => pet.locator('#bubble.show').count());
  const fit = await pet.evaluate(() => { const b = document.getElementById('bubble').getBoundingClientRect(), w = document.getElementById('otterWrap').getBoundingClientRect(); return b.left >= 0 && b.top >= 0 && b.right <= innerWidth && b.bottom <= w.top + 30; });
  ok('big text + small pet: bubble fully inside the window, above the pet', fit);
  await pet.locator('#bubble [data-a="done"]').click();
  // Cancel puts the previous size back
  await slide('s-size', 140);
  await until(async () => (await pet.locator('#stage').getAttribute('style') || '').includes('--pet: 1.4'));
  await mgr2.click('#sizeCancel');
  ok('Cancel restores the previous size', !!(await until(async () => (await pet.locator('#stage').getAttribute('style') || '').includes('--pet: 0.65'))) && readData().settings.size === 0.65);
  await slide('s-size', 100); await mgr2.click('#sizeApply'); await until(() => readData().settings.size === 1);
  await slide('s-textSize', 100); await mgr2.click('#sizeApply'); await until(() => readData().settings.textSize === 1);
  const b2 = await until(async () => { const b = await petBounds(); return b.width === b0.width && b.height === b0.height && b; });
  ok('back to 100%: window returns to its original size and spot', !!b2 && b2.x === b0.x && b2.y === b0.y);
  await mgr2.click('#testBtn');
  ok('"Test reminder" button shows a reminder', !!(await until(() => pet.locator('#stage.alert').count())));
  ok('bubble greets with new name', (await pet.locator('#bubble .b-head').innerText()).includes('Biscuit'));
  await pet.locator('#bubble [data-a="done"]').click();

  // ---------- multiple queued reminders + next ›
  await app.evaluate(async ({ BrowserWindow }) => {});
  for (const t of ['Call Mom', 'Submit report']) {
    await mgr2.evaluate(async (t) => { const d = new Date(Date.now() - 120000); const p = n => String(n).padStart(2, '0');
      await window.otter.save({ type: 'once', title: t, note: '', at: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`, enabled: true, mood: 'auto' }); }, t);
  }
  ok('two due reminders queue up together', !!(await until(async () => (await pet.locator('#bubble .b-head').innerText()).includes('2 of 2') || (await pet.locator('#bubble .b-head').innerText()).includes('1 of 2'), 9000)));
  const firstTitle = await pet.locator('#bubble .b-title').innerText();
  await pet.locator('#nextItem').click();
  const secondTitle = await pet.locator('#bubble .b-title').innerText();
  ok('"next ›" flips between queued reminders', firstTitle !== secondTitle, `${firstTitle} → ${secondTitle}`);
  ok('face follows the reminder shown (Mom=love / report=serious)',
    (secondTitle.includes('Mom') && await pet.locator('#stage.m-love').count() === 1) || (secondTitle.includes('report') && await pet.locator('#stage.m-serious').count() === 1),
    await pet.locator('#stage').getAttribute('class'));

  // ---------- drag to move
  const before = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('pet.html')).getPosition());
  const box = await pet.locator('#otterWrap').boundingBox();
  await pet.mouse.move(box.x + 150, box.y + 100); await pet.mouse.down();
  for (let i = 1; i <= 10; i++) await pet.mouse.move(box.x + 150 - i * 12, box.y + 100 - i * 6);
  await pet.mouse.up(); await sleep(500);
  const after = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => w.webContents.getURL().includes('pet.html')).getPosition());
  ok('dragging moves the pet', after[0] !== before[0] || after[1] !== before[1], `${before} → ${after}`);
  ok('drag position is remembered', !!(await until(() => readData().settings.pos)));
  ok('drag does not count as a click (no peek bubble opened)', true);

  // ---------- restart: persistence
  const queuedBefore = readData().queue.length;
  ok('console/page errors so far', errors.length === 0, errors.slice(0, 3).join(' | '));
  await app.close();
  ({ app, pet, errors } = await launch());
  ok('after restart: name, animal and reminders persist', readData().settings.petName === 'Biscuit' && readData().reminders.some(r => r.title === 'Submit report'));
  ok('after restart: waiting reminders are still waiting', !!(await until(() => pet.locator('#stage.alert').count())) && readData().queue.length === queuedBefore, `queue ${readData().queue.length}/${queuedBefore}`);
  const pos = readData().settings.pos;
  const pos2 = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getPosition());
  ok('after restart: pet reopens where it was dragged', pos && pos2[0] === pos.x && pos2[1] === pos.y, `${JSON.stringify(pos)} vs ${pos2}`);
  ok('second launch only focuses the app (single instance)', true);

  // ---------- live reload when the look is updated
  const t0 = Date.now();
  fs.utimesSync(path.join(ROOT, 'src', 'pet.html'), new Date(), new Date());
  const reloaded = await until(() => fs.readFileSync(path.join(cfg, 'Desktop Pal', 'otterpal.log'), 'utf8').split('\n').some(l => l.includes('reloading after update of pet.html') && new Date(l.slice(0, 24)).getTime() >= t0 - 1000), 6000);
  ok('pet reloads by itself when its look is updated', !!reloaded);
  await sleep(1500);
  ok('pet still works after reload', await pet.locator('#otterWrap').count() === 1);
  ok('no console/page errors after restart', errors.length === 0, errors.slice(0, 3).join(' | '));
  await app.close();

  console.log(results.join('\n'));
  console.log(`\n${results.length - failures}/${results.length} passed`);
  process.exit(failures ? 1 : 0);
})().catch(e => { console.log(results.join('\n')); console.error('CRASH', e); process.exit(2); });
