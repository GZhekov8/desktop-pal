// Renders the pet + an alert bubble at several pet/text sizes, in a window sized like main.js does.
const ROOT = require('path').resolve(__dirname, '..');
const { chromium } = require('playwright'); const fs = require('fs');
const art = JSON.parse(fs.readFileSync(ROOT + '/src/pets/otter.json', 'utf8'));
const dims = (p, t) => ({ width: Math.ceil(Math.max(302 * t + 28, 246 * p + 10)), height: Math.ceil(170 * p + 12 + 300 * t) });
(async () => {
  const b = await chromium.launch();
  for (const [p, t] of [[0.5, 1], [0.5, 1.3], [1, 1], [1.5, 1], [1.5, 1.5]]) {
    const pg = await b.newPage({ viewport: dims(p, t) });
    await pg.addInitScript(([p, t, art]) => {
      let cb; window.otter = { onState: (c) => cb = c, ignore() {}, done() {}, snooze() {}, open() {}, hide() {}, dragStart() {}, drag() {}, dragEnd() {}, art: async () => art,
        ready: () => setTimeout(() => cb({ queue: [{ id: 'a', kind: 'once', title: 'Pay the electricity bill', note: 'Due today' }], next: [], todos: 0, settings: { animal: 'otter', size: p, textSize: t, snoozeDefault: 10, petName: 'Pedro' }, alert: false }), 50) };
    }, [p, t, art]);
    await pg.goto('file://' + ROOT + '/src/pet.html');
    await pg.evaluate(() => document.body.style.background = '#3a6ea5');
    await pg.waitForTimeout(700);
    await pg.evaluate(() => document.querySelectorAll('*').forEach(e => e.style.animationPlayState = 'paused'));
    const r = await pg.evaluate(() => { const bb = document.getElementById('bubble').getBoundingClientRect(), w = document.getElementById('otterWrap').getBoundingClientRect(); return { bubbleTop: Math.round(bb.top), bubbleBottom: Math.round(bb.bottom), bubbleLeft: Math.round(bb.left), petTop: Math.round(w.top), petLeft: Math.round(w.left) }; });
    console.log(`pet ${p * 100}% text ${t * 100}%  window ${JSON.stringify(dims(p, t))}  ${JSON.stringify(r)}  ${r.bubbleTop >= 0 && r.bubbleBottom <= r.petTop + 30 && r.bubbleLeft >= 0 && r.petLeft >= 0 ? 'fits' : 'CLIPPED/OVERLAP'}`);
    await pg.screenshot({ path: `${process.argv[2]}/size-${p}-${t}.png` });
    await pg.close();
  }
  await b.close();
})();
