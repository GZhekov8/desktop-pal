// Screenshots of 1.6 states for review: walking, focus chip, break bubble, feeding, size preview.
const ROOT = require('path').resolve(__dirname, '..');
const { chromium } = require('playwright'); const fs = require('fs');
const now = Date.now();
const scenes = [
  { n: 'walk-fox', animal: 'fox', pose: 'walk', dir: 1 },
  { n: 'walk-dog-left', animal: 'dog', pose: 'walk', dir: -1 },
  { n: 'otter-scamper', animal: 'otter', pose: 'walk', dir: 1 },
  { n: 'focus-cat', animal: 'cat', focus: { state: 'focus', endsAt: now + 1421000, round: 2, held: 2, lens: { focus: 25 } } },
  { n: 'break-panda', animal: 'redpanda', focus: { state: 'break', endsAt: now + 244000, round: 2, held: 0, lens: { focus: 25 } },
    queue: [{ id: 'focus-break', kind: 'focus', title: 'Break time! 5 min', note: 'Stretch, look away from the screen, sip some water. 2 reminders waited for you.', mood: 'happy', doneLabel: 'Skip break', laterLabel: 'Stop focusing' }] },
  { n: 'preview-otter', animal: 'otter', size: 0.7, textSize: 1.25, queue: [{ id: 'preview', kind: 'preview', title: 'This is how reminders will look', note: 'Pet size 70% · Text size 125%', mood: 'happy', doneLabel: 'Apply', laterLabel: 'Cancel' }] },
  { n: 'feed-dog', animal: 'dog', feed: true, treats: 3 },
];
(async () => {
  const b = await chromium.launch();
  for (const sc of scenes) {
    const art = JSON.parse(fs.readFileSync(`${ROOT}/src/pets/${sc.animal}.json`, 'utf8'));
    const pg = await b.newPage({ viewport: { width: 400, height: 520 }, deviceScaleFactor: 2 });
    await pg.addInitScript(([sc, art]) => {
      let cb, pcb; window.otter = { onState: (c) => cb = c, onPose: (c) => pcb = c, ignore() {}, art: async () => art, feed: async () => true, done() {}, snooze() {},
        ready: () => setTimeout(() => { cb({ queue: sc.queue || [], next: [], todos: 0, treats: sc.treats || 0, focus: sc.focus || { state: 'idle', lens: { focus: 25 } },
          settings: { animal: sc.animal, size: sc.size || 1, textSize: sc.textSize || 1, petName: 'Pedro', snoozeDefault: 10, sound: false }, alert: false });
          if (sc.pose) setTimeout(() => pcb({ pose: sc.pose, dir: sc.dir }), 300); }, 30) };
    }, [sc, art]);
    await pg.goto('file://' + ROOT + '/src/pet.html');
    await pg.evaluate(() => document.body.style.background = '#5f86a6');
    await pg.waitForTimeout(sc.pose ? 1300 : 900);
    if (sc.feed) { await pg.evaluate(() => feed()); await pg.waitForTimeout(500); }
    await pg.evaluate(() => { document.querySelectorAll('*').forEach(e => e.style.animationPlayState = 'paused'); stopMotion(); });
    await pg.screenshot({ path: `${process.argv[2]}/v16-${sc.n}.png` });
    await pg.close();
  }
  await b.close();
})();
