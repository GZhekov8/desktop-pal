import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT + '/tools')
from chibi import ANIMALS, DEFS, walker, WALKERS, FACE   # cute chibi art for all six pets
s = open(ROOT + '/tools/pet.otter-base.html').read()

def cut(s, a, b):
    i = s.index(a); j = s.index(b, i)
    return s[:i] + s[j:], s[i:j]

# 1. pull the shared face out of the otter head
s, eyes = cut(s, '          <!-- eyes: small, dark, glossy -->', '          <!-- whisker pads -->')
s, mouths = cut(s, '          <!-- MOUTHS (one per expression) -->', '          <!-- whiskers: long, pale, drooping -->')
face = (eyes + mouths).replace('stroke="#6b4c36" stroke-width="1.7"', 'stroke="var(--brow, #6b4c36)" stroke-width="1.7"')
s = s.replace('          <!-- whiskers: long, pale, drooping -->', face + '          <!-- whiskers: long, pale, drooping -->', 1)

# 2. cut the otter-only parts out of the page; every animal is now its own file loaded on demand
art = {'otter': {}}
a = s.index('        <!-- reflection / shadow on the water -->'); b = s.index('        <!-- EXPRESSION EXTRAS -->')
art['otter']['float'] = '<g class="animal a-otter">' + s[a:b] + '</g>'
s = s[:a] + '<g id="slot-float"></g><g id="slot-walk"></g>\n' + s[b:]
a = s.index('        <!-- water droplets glinting on the fur -->'); b = s.index('        <!-- exclamation -->')
art['otter']['float2'] = '<g class="animal a-otter">' + s[a:b] + '</g>'
s = s[:a] + '<g id="slot-float2"></g>\n' + s[b:]

for name, fn in ANIMALS.items():
    bk, hd, fr = fn()
    wrap = lambda t: f'<g class="animal a-{name}">{t}</g>'
    if name == 'otter':     # the otter keeps its animated water (back/front) and droplets from the page
        art['otter']['float'] = wrap(hd.replace('@@FACE@@', FACE))
        continue
    art[name] = {'back': wrap(bk), 'float': wrap(hd.replace('@@FACE@@', FACE)), 'float2': '', 'front': wrap(fr) if fr else ''}
anchor = '<linearGradient id="shellG"'
i = s.index(anchor); s = s[:i] + DEFS + s[i:]
assert 'id="cbCat"' in s

# 3./4. back + front layers: otter water moves into the otter file, slots left behind
a = s.index('      <ellipse cx="118" cy="134" rx="120" ry="30" fill="url(#poolG)"/>')
b = s.index('    </svg>', a)
art['otter']['back'] = '<g class="animal a-otter">' + s[a:b] + '</g>'
s = s[:a] + '<g id="slot-back"></g>\n' + s[b:]
a = s.index('      <g clip-path="url(#waterClip)" mask="url(#waterMask)">')
b = s.index('    </svg>', a)
art['otter']['front'] = '<g class="animal a-otter">' + s[a:b] + '</g>'
s = s[:a] + '<g id="slot-front"></g>\n' + s[b:]
import json, os, re
os.makedirs(ROOT + '/src/pets', exist_ok=True)
squeeze = lambda t: re.sub(r'>\s+<', '><', t).strip()
def wrap_head(f):
    # wrap the head group in an outer <g class="head"> (no transform of its own) so CSS can turn the
    # head around its real position; the inner group keeps its translate/rotate placement
    i = f.index('<g class="headpos"')
    depth, j = 0, i
    for m in re.finditer(r'<g[\s>]|</g>', f[i:]):
        depth += -1 if m.group(0) == '</g>' else 1
        if depth == 0: j = i + m.end(); break
    return f[:i] + '<g class="head">' + f[i:j] + '</g>' + f[j:]

def head_of(f):
    i = f.index('<g class="head">'); depth = 0
    for m in re.finditer(r'<g[\s>]|</g>', f[i:]):
        depth += -1 if m.group(0) == '</g>' else 1
        if depth == 0: return f[i:i + m.end()]

for name, parts in art.items():
    parts['float'] = wrap_head(parts['float'])
    dx, dy = WALKERS[name]['head']
    parts['walk'] = walker(name).replace('@@HEAD@@', f'<g transform="translate({dx} {dy})">' + head_of(parts['float']) + '</g>')
    json.dump({k: squeeze(v) for k, v in parts.items()}, open(f'{ROOT}/src/pets/{name}.json', 'w'), separators=(',', ':'))

# 5. css
css = '''
  /* ---------- choice of animal ---------- */
  .animal { display: none; }
  .pet-otter .a-otter, .pet-cat .a-cat, .pet-dog .a-dog, .pet-fox .a-fox, .pet-redpanda .a-redpanda, .pet-tiger .a-tiger { display: inline; }
  .pet-cat, .pet-fox { --brow: #8f4515; } .pet-dog { --brow: #6e4420; } .pet-redpanda { --brow: #5a2214; } .pet-tiger { --brow: #2a1a10; }
  .pet-otter { --iris: #6b4630; } .pet-cat { --iris: #8fbf3c; } .pet-dog { --iris: #7a4a26; } .pet-fox { --iris: #e0a028; } .pet-redpanda { --iris: #8a4a26; } .pet-tiger { --iris: #e6b032; }
  .alert-tail { transform-box: view-box; }   /* wags and drifts via the motion engine */
  .iris { transition: opacity .25s; }
  .m-happy .iris, .m-love .iris, .m-proud .iris, .m-sleepy .iris { opacity: 0; }
</style>'''
s = s.replace('\n</style>', css, 1)
s = s.replace('<div class="stage m-neutral" id="stage">', '<div class="stage m-neutral pet-otter" id="stage">')
# 6. js: load the chosen animal's art on demand
anchor = "  stage.classList.toggle('alert', state.queue.some(q => q.kind !== 'preview'));"
assert anchor in s, 'loadArt anchor missing'
s = s.replace(anchor, "  loadArt((state.settings && state.settings.animal) || 'otter');\n" + anchor, 1)
s = s.replace("/* ---- facial expressions ---- */", """/* ---- animal art: only the chosen pet is loaded ---- */
let artFor = null;
async function loadArt(animal) {
  if (artFor === animal) return;
  artFor = animal;
  let a;
  try { a = await window.otter.art(animal); } catch (e) { a = null; }
  if (!a) { if (animal !== 'otter') { artFor = null; return loadArt('otter'); } return; }
  if (artFor !== animal) return;            // user switched again meanwhile
  for (const k of ['back', 'float', 'float2', 'front', 'walk']) document.getElementById('slot-' + k).innerHTML = a[k] || '';
  if (typeof collectParts === 'function') collectParts();
  stage.className = (stage.className.replace(/\\bpet-\\w+/g, '') + ' pet-' + animal).replace(/\\s+/g, ' ').trim();
}

/* ---- facial expressions ---- */""", 1)
open(ROOT + '/src/pet.html', 'w').write(s)
# the settings window shows little portraits of the pets: give it the same colour gradients
m = open(ROOT + '/src/manager.html', encoding='utf-8').read()
a, z = m.index('<!--SBDEFS-->') + len('<!--SBDEFS-->'), m.index('<!--/SBDEFS-->')
open(ROOT + '/src/manager.html', 'w', encoding='utf-8').write(m[:a] + DEFS + m[z:])
print('ok', len(s))
