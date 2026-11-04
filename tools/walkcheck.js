// Renders each animal's walking pose (standing + mid-stride) for visual review.
const ROOT = require('path').resolve(__dirname, '..');
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  for (const a of ['otter', 'cat', 'dog', 'fox', 'redpanda']) {
    const art = JSON.parse(fs.readFileSync(`${ROOT}/src/pets/${a}.json`, 'utf8'));
    const pg = await b.newPage({ viewport: { width: 330, height: 482 }, deviceScaleFactor: 2 });
    const errs = []; pg.on('pageerror', e => errs.push(String(e)));
    await pg.addInitScript(([a, art]) => {
      let cb; window.otter = { onState: (c) => cb = c, ignore() {}, art: async () => ({ back: '', float: art.walk, float2: '', front: '' }),
        ready: () => setTimeout(() => cb({ queue: [], next: [], todos: 0, settings: { animal: a, size: 1, textSize: 1 }, alert: false }), 30) };
    }, [a, art]);
    await pg.goto('file://' + ROOT + '/src/pet.html');
    await pg.evaluate(() => document.body.style.background = '#6f8fa8');
    await pg.waitForTimeout(700);
    await pg.evaluate(() => stopMotion());
    for (const [n, ang] of [['stand', 0], ['stride', 22]]) {
      await pg.evaluate((ang) => document.querySelectorAll('.swing').forEach(s => s.setAttribute('transform', `rotate(${(Math.cos(+s.dataset.phase) * ang).toFixed(1)})`)), ang);
      await pg.waitForTimeout(150);
      await pg.screenshot({ path: `${process.argv[2]}/walk-${a}-${n}.png`, clip: { x: 80, y: 290, width: 250, height: 192 } });
    }
    console.log(a, errs.length ? errs : 'ok');
    await pg.close();
  }
  await b.close();
})();
