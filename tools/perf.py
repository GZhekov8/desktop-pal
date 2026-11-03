"""Measures Desktop Pal's CPU and memory under a virtual display.
usage: python3 tools/perf.py <label> [animal] [seconds] [extra electron args...]
Runs the app with a fresh data folder, waits for it to settle, then samples all
Electron processes. Prints idle CPU %, peak/avg RSS and startup time."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import json, os, subprocess, sys, tempfile, time
import psutil

label = sys.argv[1]; animal = sys.argv[2] if len(sys.argv) > 2 else 'otter'
secs = int(sys.argv[3]) if len(sys.argv) > 3 else 20
extra = sys.argv[4:]
root = ROOT
cfg = tempfile.mkdtemp(prefix='perf-')
os.makedirs(f'{cfg}/Desktop Pal')
json.dump({'reminders': [{'id': 't1', 'type': 'todo', 'title': 'x', 'done': True, 'enabled': True}],
           'settings': {'animal': animal, 'todoNudgeMin': 0, 'sound': False, 'notifications': False, 'startWithWindows': False, **json.loads(os.environ.get('PERF_SETTINGS', '{}'))},
           'lastNudge': int(time.time() * 1000)}, open(f'{cfg}/Desktop Pal/otterpal-data.json', 'w'))
xv = subprocess.Popen(['Xvfb', ':91', '-screen', '0', '1600x1000x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
env = dict(os.environ, DISPLAY=':91', XDG_CONFIG_HOME=cfg)
t0 = time.time()
app = subprocess.Popen([f'{root}/node_modules/electron/dist/electron', '--no-sandbox', root, *extra], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
log = f'{cfg}/Desktop Pal/otterpal.log'
startup = None
while time.time() - t0 < 30:
    if os.path.exists(log) and 'pet shown' in open(log).read():
        startup = time.time() - t0; break
    time.sleep(.05)
time.sleep(6)  # settle
def procs():
    p = psutil.Process(app.pid); return [p] + p.children(recursive=True)
ps = procs()
for p in ps: p.cpu_percent(None)
rss = []
for _ in range(secs):
    time.sleep(1)
    try: rss.append(sum(p.memory_info().rss for p in procs()))
    except psutil.Error: pass
cpu = 0.0; per = []
for p in ps:
    try:
        c = p.cpu_percent(None); cpu += c
        t = next((a.split('=', 1)[1] for a in p.cmdline() if a.startswith('--type=')), 'main')
        if t == 'utility': t = next((a.split('=', 1)[1] for a in p.cmdline() if a.startswith('--utility-sub-type=')), t).split('.')[-1]
        per.append((round(c, 1), t))
    except psutil.Error: pass
app.terminate()
try: app.wait(5)
except Exception: app.kill()
xv.terminate()
print(json.dumps({'label': label, 'animal': animal, 'cpu_pct': round(cpu, 1),
                  'ram_mb_avg': round(sum(rss) / len(rss) / 1e6), 'ram_mb_peak': round(max(rss) / 1e6),
                  'startup_s': round(startup or -1, 2), 'by_process': sorted(per, reverse=True)[:4]}))
