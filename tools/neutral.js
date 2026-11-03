const ROOT = require('path').resolve(__dirname, '..'); const SCRATCH = process.env.DP_SCRATCH || require('os').tmpdir();
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch();
  for (const [a, m] of [['otter','happy'],['cat','neutral'],['dog','excited'],['fox','neutral'],['redpanda','love']]) {
    const p = await b.newPage({ viewport: { width: 340, height: 400 }, deviceScaleFactor: 3 });
    await p.addInitScript(() => { window.otter = { onState() {}, ready() {}, ignore() {} }; });
    await p.goto('file://' + ROOT + '/src/pet.html');
    await p.evaluate(([a, m]) => { document.getElementById('stage').className = `stage pet-${a} m-${m}`; }, [a, m]);
    await p.waitForTimeout(600); await p.evaluate(() => document.querySelectorAll('*').forEach(e => e.style.animationPlayState = 'paused'));
    await p.screenshot({ path: `${ROOT}/itch/raw/n-${a}.png`, omitBackground: true, clip: { x: 95, y: 215, width: 245, height: 185 } });
    await p.close(); }
  await b.close(); })();
