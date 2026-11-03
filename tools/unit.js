// Unit tests for the reminder scheduler (computeNext) in src/main.js
const src = require('fs').readFileSync(__dirname + '/../src/main.js', 'utf8');
const a = src.indexOf('function hm('), b = src.indexOf('function fire(');
eval(src.slice(a, b).replace(/function (\w+)/g, 'globalThis.$1 = function $1'));
let pass = 0, fail = 0;
const L = (s) => new Date(s).getTime();
const f = (t) => t == null ? 'null' : new Date(t).toString().slice(0, 21);
function eq(name, got, want) { const okk = (want === null ? got === null : f(got) === f(L(want))); okk ? pass++ : fail++; console.log(`${okk ? 'PASS' : 'FAIL'}  ${name}  → ${f(got)}${okk ? '' : '   (want ' + (want === null ? 'null' : f(L(want))) + ')'}`); }
const W = { type: 'interval', enabled: true, every: 60, from: '09:00', to: '19:00', days: [1, 2, 3, 4, 5] };
eq('interval: before work hours → shortly after 09:00', computeNext(W, L('2026-11-02T07:30')), '2026-11-02T09:15');
eq('interval: an hour before start → exactly 09:00', computeNext(W, L('2026-11-02T08:00')), '2026-11-02T09:00');
eq('interval: inside hours → +60 min', computeNext(W, L('2026-11-02T12:10')), '2026-11-02T13:10');
eq('interval: last slot exactly at end', computeNext(W, L('2026-11-02T18:00')), '2026-11-02T19:00');
eq('interval: after hours Fri → Mon morning', computeNext(W, L('2026-11-06T18:30')), '2026-11-09T09:15');
eq('interval: weekend → Monday', computeNext(W, L('2026-11-07T11:00')), '2026-11-09T09:15');
eq('interval: no days ticked = every day', computeNext({ ...W, days: [] }, L('2026-11-07T11:00')), '2026-11-07T12:00');
eq('interval: all-day window keeps going past midnight', computeNext({ ...W, from: '00:00', to: '23:59', days: [] }, L('2026-11-02T23:30')), '2026-11-03T00:30');
eq('interval: same from/to = all day', computeNext({ ...W, from: '09:00', to: '09:00', days: [] }, L('2026-11-02T23:30')), '2026-11-03T00:30');
eq('interval: overnight window respects start day (Fri night only)', computeNext({ ...W, from: '22:00', to: '02:00', days: [5] }, L('2026-11-06T23:30')), '2026-11-07T00:30');
eq('interval: overnight window, Sat night not allowed', computeNext({ ...W, from: '22:00', to: '02:00', days: [5] }, L('2026-11-07T01:30')), '2026-11-13T22:15');
eq('interval: overnight window 22:00–02:00, at 23:00', computeNext({ ...W, from: '22:00', to: '02:00', days: [] }, L('2026-11-02T23:00')), '2026-11-03T00:00');
eq('interval: overnight window 22:00–02:00, at 01:30', computeNext({ ...W, from: '22:00', to: '02:00', days: [] }, L('2026-11-03T01:30')), '2026-11-03T22:15');
eq('interval: overnight window, at 21:00', computeNext({ ...W, from: '22:00', to: '02:00', days: [] }, L('2026-11-03T21:00')), '2026-11-03T22:00');
eq('interval: every 1 min', computeNext({ ...W, every: 1, from: '00:00', to: '23:59', days: [] }, L('2026-11-02T10:00')), '2026-11-02T10:01');
eq('interval: bad "every" falls back to 30', computeNext({ ...W, every: 'abc', days: [] }, L('2026-11-02T10:00')), '2026-11-02T10:30');
eq('interval: disabled → null', computeNext({ ...W, enabled: false }, L('2026-11-02T10:00')), null);
eq('daily: later today', computeNext({ type: 'repeat', enabled: true, time: '14:00', days: [] }, L('2026-11-02T10:00')), '2026-11-02T14:00');
eq('daily: already passed → tomorrow', computeNext({ type: 'repeat', enabled: true, time: '09:00', days: [] }, L('2026-11-02T10:00')), '2026-11-03T09:00');
eq('weekly: Wednesdays only', computeNext({ type: 'repeat', enabled: true, time: '10:00', days: [3] }, L('2026-11-02T08:00')), '2026-11-04T10:00');
eq('weekly: same day after time → next week', computeNext({ type: 'repeat', enabled: true, time: '10:00', days: [3] }, L('2026-11-04T10:00')), '2026-11-11T10:00');
eq('daily: across clocks-change (Sofia, 25 Oct)', computeNext({ type: 'repeat', enabled: true, time: '09:00', days: [] }, L('2026-10-24T10:00')), '2026-10-25T09:00');
eq('daily: across clocks-change spring (29 Mar)', computeNext({ type: 'repeat', enabled: true, time: '03:30', days: [] }, L('2026-03-28T10:00')), '2026-03-29T04:30');  // 03:30 does not exist that night (clocks jump 03:00→04:00)
eq('once: future', computeNext({ type: 'once', enabled: true, at: '2026-11-05T14:30' }, L('2026-11-02T10:00')), '2026-11-05T14:30');
eq('once: done → null', computeNext({ type: 'once', enabled: true, done: true, at: '2026-11-05T14:30' }, L('2026-11-02T10:00')), null);
eq('once: missing date → null', computeNext({ type: 'once', enabled: true }, L('2026-11-02T10:00')), null);
eq('todo → null (nudged separately)', computeNext({ type: 'todo', enabled: true }, L('2026-11-02T10:00')), null);
console.log(`\n${pass}/${pass + fail} passed`); process.exit(fail ? 1 : 0);
