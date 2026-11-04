// Renders idle actions (frozen mid-animation) and mouse-follow poses for visual review.
const ROOT = require('path').resolve(__dirname, '..');
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const shots = [];
  for (const animal of ['otter', 'cat', 'fox']) {
    const art = JSON.parse(fs.readFileSync(`${ROOT}/src/pets/${animal}.json`, 'utf8'));
    const pg = await b.newPage({ viewport: { width: 330, height: 482 }, deviceScaleFactor: 2 });
    const errs = []; pg.on('pageerror', e => errs.push(String(e)));
    await pg.addInitScript(([animal, art]) => {
      let cb; window.__cur = null;
      window.otter = { onState: (c) => cb = c, onCursor: (f) => window.__cur = f, ignore() {}, art: async () => art,
        ready: () => setTimeout(() => cb({ queue: [], next: [], todos: 0, settings: { animal, size: 1, textSize: 1 }, alert: false }), 30) };
    }, [animal, art]);
    await pg.goto('file://' + ROOT + '/src/pet.html');
    await pg.evaluate(() => document.body.style.background = '#3a6ea5');
    await pg.waitForTimeout(600);
    const shot = async (name) => { await pg.waitForTimeout(450); const f = `${process.argv[2]}/act-${animal}-${name}.png`; await pg.screenshot({ path: f, clip: { x: 80, y: 300, width: 250, height: 182 } }); shots.push(f); };
    await shot('rest');
    for (const [a, t] of [['look', 700], ['tilt', 1000], ['stretch', 950], ['swish', 0]]) {
      await pg.evaluate(([a, t]) => { stage.classList.add(a); document.getAnimations().forEach(x => { x.pause(); x.currentTime = t; }); }, [a, t]);
      await shot(a);
      await pg.evaluate((a) => { stage.classList.remove(a); document.getAnimations().forEach(x => x.play()); }, a);
    }
    await pg.evaluate(() => flash('yawn', 4000)); await shot('yawn');
    await pg.evaluate(() => { flashMood = null; applyMood(); });
    await pg.evaluate(() => window.__cur({ x: 20, y: 380 })); await shot('mouse-left');
    await pg.evaluate(() => window.__cur({ x: 320, y: 200 })); await shot('mouse-right-up');
    const w = await pg.evaluate(() => { const r = wrap.getBoundingClientRect(); return { x: r.left + r.width * .7, y: r.top + r.height * .5 }; });
    await pg.evaluate((w) => window.__cur(w), w); await shot('hover-perk');
    console.log(animal, 'errors:', errs.length ? errs : 'none');
    await pg.close();
  }
  await b.close();
})();
