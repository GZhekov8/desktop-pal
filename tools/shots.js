// Renders transparent PNGs of each pet + bubble for the itch.io page.
const ROOT = require('path').resolve(__dirname, '..'); const SCRATCH = process.env.DP_SCRATCH || require('os').tmpdir();
const { chromium } = require('playwright');
const OUT = ROOT + '/itch/raw';
const now = Date.now();
const scenes = [
  { n: 'otter-water',  animal: 'otter',    name: 'Pedro',  queue: [{ id: 'a', kind: 'interval', title: 'Drink some water', note: 'A glass of water keeps me happy.' }] },
  { n: 'cat-bill',     animal: 'cat',      name: 'Mochi',  queue: [{ id: 'b', kind: 'once', title: 'Pay the electricity bill', note: 'Due today!' }] },
  { n: 'fox-peek',     animal: 'fox',      name: 'Rusty',  peek: true, next: [{ title: 'Team stand-up', at: now + 25 * 60000 }, { title: 'Stretch break', at: now + 70 * 60000 }, { title: 'Send the weekly report', at: now + 26 * 3600000 }] },
  { n: 'dog-mom',      animal: 'dog',      name: 'Biscuit', queue: [{ id: 'c', kind: 'repeat', title: 'Call Mom', note: "It's Sunday :)" }] },
  { n: 'panda-sleepy', animal: 'redpanda', name: 'Maple',  mood: 'sleepy' },
  { n: 'otter-nudge',  animal: 'otter',    name: 'Pedro',  queue: [{ id: 'todo-nudge', kind: 'nudge', title: 'You still have things on your list', todos: ['Reply to Anna', 'Book dentist', 'Water the plants'], more: 0 }] },
];
(async () => {
  const b = await chromium.launch();
  for (const sc of scenes) {
    const p = await b.newPage({ viewport: { width: 340, height: 470 }, deviceScaleFactor: 2 });
    await p.addInitScript((sc) => {
      let cb; window.otter = { onState: (c) => cb = c, ignore() {}, done() {}, snooze() {}, open() {}, hide() {}, dragStart() {}, drag() {}, dragEnd() {},
        ready: () => setTimeout(() => cb({ queue: sc.queue || [], next: sc.next || [], todos: 3, settings: { animal: sc.animal, petName: sc.name, size: 1, snoozeDefault: 10 }, alert: false }), 50) };
    }, sc);
    await p.goto('file://' + ROOT + '/src/pet.html');
    await p.waitForTimeout(500);
    if (sc.peek) { const bx = await p.locator('#otterWrap').boundingBox(); await p.mouse.move(bx.x + 180, bx.y + 90); await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(2200); }
    if (sc.mood) await p.evaluate((m) => { const s = document.getElementById('stage'); s.className = s.className.replace(/\bm-\w+/, 'm-' + m); }, sc.mood);
    await p.evaluate(() => document.querySelectorAll('.happy').forEach(e => e.classList.remove('happy')));
    await p.waitForTimeout(700);
    await p.evaluate(() => document.querySelectorAll('*').forEach(e => e.style.animationPlayState = 'paused'));
    await p.screenshot({ path: `${OUT}/${sc.n}.png`, omitBackground: true });
    await p.close();
  }
  // app window
  const m = await b.newPage({ viewport: { width: 760, height: 560 }, deviceScaleFactor: 2 });
  await m.addInitScript((now) => {
    const d = { reminders: [
      { id: '1', type: 'interval', title: 'Drink some water', every: 60, from: '09:00', to: '19:00', days: [1,2,3,4,5], enabled: true, nextAt: now + 18 * 60000 },
      { id: '2', type: 'repeat', title: 'Team stand-up', time: '10:00', days: [1,2,3,4,5], enabled: true, nextAt: now + 25 * 60000 },
      { id: '3', type: 'interval', title: 'Stretch break', note: 'Look away from the screen for 20 seconds', every: 90, from: '09:00', to: '18:00', days: [1,2,3,4,5], enabled: true, nextAt: now + 70 * 60000 },
      { id: '4', type: 'once', title: 'Pay the electricity bill', at: '2026-11-05T12:00', enabled: true, nextAt: now + 4 * 864e5 },
      { id: '5', type: 'todo', title: 'Reply to Anna', done: false }], settings: { animal: 'otter', petName: 'Pedro', size: 1, sound: true, notifications: true, startWithWindows: true, snoozeDefault: 10, todoNudgeMin: 60 }, queue: [] };
    window.otter = { get: async () => d, onData() {}, onTab() {}, save: async () => {}, toggle() {}, remove() {}, settings() {}, test() {}, about: async () => ({ version: '1.2.0', page: '' }), link() {} };
  }, now);
  await m.goto('file://' + ROOT + '/src/manager.html');
  await m.waitForTimeout(400); await m.screenshot({ path: `${OUT}/app-list.png` });
  await m.click('#addBtn'); await m.fill('#f-title', 'Stretch break'); await m.click('[data-v=interval]'); await m.waitForTimeout(300);
  await m.screenshot({ path: `${OUT}/app-form.png` });
  await b.close();
})();
