// Steps the walking gait with a simulated moving window: measures paw slip and saves frames for review.
// usage: node tools/gaitcheck.js <outdir>
const ROOT = require('path').resolve(__dirname, '..');
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const b = await chromium.launch(); const out = process.argv[2];
  for (const a of ['otter', 'cat', 'dog', 'fox', 'redpanda']) {
    const art = JSON.parse(fs.readFileSync(`${ROOT}/src/pets/${a}.json`, 'utf8'));
    const pg = await b.newPage({ viewport: { width: 330, height: 482 }, deviceScaleFactor: 1 });
    const errs = []; pg.on('pageerror', e => errs.push(String(e)));
    await pg.addInitScript(([a, art]) => {
      window.__sx = 0; Object.defineProperty(window, 'screenX', { get: () => window.__sx });
      let cb, pc; window.otter = { onState: (c) => cb = c, onPose: (c) => pc = c, ignore() {}, art: async () => art,
        ready: () => setTimeout(() => { cb({ queue: [], next: [], todos: 0, settings: { animal: a, size: 1, textSize: 1 }, alert: false }); setTimeout(() => pc({ pose: 'walk', dir: 1 }), 300); }, 30) };
    }, [a, art]);
    await pg.goto('file://' + ROOT + '/src/pet.html');
    await pg.evaluate(() => document.body.style.background = '#6f8fa8');
    await pg.waitForTimeout(900);
    await pg.evaluate(() => stopMotion());
    // walk at 52 px/s, 24 fps for 3 s; record each paw's screen x while it is on the ground
    const r = await pg.evaluate(() => {
      const paws = [...document.querySelectorAll('#slot-walk .shin ellipse')];
      let t = 10, slip = 0, prev = paws.map(() => null), maxLift = 0, ground = null, hz = 0, p0 = null;
      for (let i = 0; i < 72; i++) {
        t += 1 / 24; window.__sx += 52 / 24; walkFrame(t);
        if (i === 30) p0 = gait.p;
        if (i === 54) hz = ((gait.p - p0 + 1) % 1) / 1;   // cycles per second (24 frames)
        if (i < 20) continue;                              // let the start-up blend finish
        paws.forEach((e, k) => {
          const bb = e.getBoundingClientRect(), x = bb.left + bb.width / 2 + window.__sx, y = bb.bottom;
          ground = ground == null ? y : Math.max(ground, y);
          const L = parts.legs[k], q = (gait.p + L.off) % 1;
          if (q > .05 && q < DUTY - .05) { if (prev[k] != null) slip = Math.max(slip, Math.abs(x - prev[k])); prev[k] = x; } else prev[k] = null;
        });
      }
      paws.forEach(e => { maxLift = Math.max(maxLift, ground - e.getBoundingClientRect().bottom); });
      return { slip: +slip.toFixed(2), hz: +hz.toFixed(2) };
    });
    const frames = [];
    for (let i = 0; i < 8; i++) {
      await pg.evaluate(() => { for (let j = 0; j < 3; j++) { window.__sx += 52 / 24; walkFrame(gait.t + 1 / 24); } });
      frames.push(await pg.screenshot({ clip: { x: 60, y: 300, width: 270, height: 182 } }));
    }
    frames.forEach((f, i) => fs.writeFileSync(`${out}/${a}-${i}.png`, f));
    console.log(a, JSON.stringify(r), errs.length ? errs : 'ok');
    await pg.close();
  }
  await b.close();
})();
