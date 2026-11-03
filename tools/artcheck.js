const ROOT = require('path').resolve(__dirname, '..'); const SCRATCH = process.env.DP_SCRATCH || require('os').tmpdir();
const { _electron: electron } = require('playwright'); const fs = require('fs'), os = require('os'), path = require('path');
(async () => {
  const cfg = fs.mkdtempSync(path.join(os.tmpdir(), 'ac-'));
  fs.mkdirSync(cfg + '/Desktop Pal');
  fs.writeFileSync(cfg + '/Desktop Pal/otterpal-data.json', JSON.stringify({ reminders: [], settings: { animal: 'otter', todoNudgeMin: 0 }, lastNudge: Date.now() }));
  const app = await electron.launch({ executablePath: ROOT + '/node_modules/electron/dist/electron', args: ['--no-sandbox', ROOT], env: { ...process.env, XDG_CONFIG_HOME: cfg } });
  const pet = await app.firstWindow(); await new Promise(r => setTimeout(r, 2500));
  const errs = []; pet.on('pageerror', e => errs.push(String(e)));
  for (const a of ['otter', 'cat', 'dog', 'fox', 'redpanda']) {
    await pet.evaluate((a) => window.otter.settings({ animal: a }), a);
    await new Promise(r => setTimeout(r, 900));
    const info = await pet.evaluate(() => ({ cls: document.getElementById('stage').className, n: document.querySelectorAll('#slot-float *').length }));
    await pet.screenshot({ path: `${process.argv[2]}/art-${a}.png` });
    console.log(a, JSON.stringify(info));
  }
  console.log('errors:', errs.length ? errs : 'none');
  await app.close();
})();
