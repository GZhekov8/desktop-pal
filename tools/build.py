import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT + '/tools')
from animals import ANIMALS, DEFS, neck
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
s = s[:a] + '<g id="slot-float"></g>\n' + s[b:]
a = s.index('        <!-- water droplets glinting on the fur -->'); b = s.index('        <!-- exclamation -->')
art['otter']['float2'] = '<g class="animal a-otter">' + s[a:b] + '</g>'
s = s[:a] + '<g id="slot-float2"></g>\n' + s[b:]

for name, fn in ANIMALS.items():
    bk, hd, fr = fn()
    k = hd.index('<g transform="translate(19')
    hd = hd[:k] + neck(name) + '\n        ' + hd[k:]
    art[name] = {'back': bk, 'float': hd.replace('@@FACE@@', face), 'float2': '', 'front': fr}
anchor = '<linearGradient id="shellG"'
i = s.index(anchor); s = s[:i] + DEFS + s[i:]
assert 'id="catBodyG"' in s

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
for name, parts in art.items():
    json.dump({k: squeeze(v) for k, v in parts.items()}, open(f'{ROOT}/src/pets/{name}.json', 'w'), separators=(',', ':'))

# 5. css
css = '''
  /* ---------- choice of animal ---------- */
  .animal { display: none; }
  .pet-otter .a-otter, .pet-cat .a-cat, .pet-dog .a-dog, .pet-fox .a-fox, .pet-redpanda .a-redpanda { display: inline; }
  .pet-cat, .pet-fox { --brow: #8f4515; } .pet-dog { --brow: #6e4420; } .pet-redpanda { --brow: #5a2214; }
  .alert.pet-cat .float, .alert.pet-dog .float, .alert.pet-fox .float, .alert.pet-redpanda .float { animation: bounce 1.1s ease-in-out infinite; }
  .alert-tail { transform-box: view-box; }
  .alert .alert-tail { animation: wag .35s ease-in-out infinite alternate; }
  .pet-cat.alert .alert-tail, .pet-fox.alert .alert-tail { animation: wag 1s ease-in-out infinite alternate; }
  @keyframes wag { from { transform: rotate(-5deg); } to { transform: rotate(5deg); } }
  .iris { transition: opacity .25s; }
  .m-happy .iris, .m-love .iris, .m-proud .iris, .m-sleepy .iris { opacity: 0; }
</style>'''
s = s.replace('\n</style>', css, 1)
s = s.replace('<div class="stage m-neutral" id="stage">', '<div class="stage m-neutral pet-otter" id="stage">')
# 6. js: load the chosen animal's art on demand
s = s.replace("  stage.classList.toggle('alert', state.queue.length > 0);",
"""  loadArt((state.settings && state.settings.animal) || 'otter');
  stage.classList.toggle('alert', state.queue.length > 0);""", 1)
s = s.replace("/* ---- facial expressions ---- */", """/* ---- animal art: only the chosen pet is loaded ---- */
let artFor = null;
async function loadArt(animal) {
  if (artFor === animal) return;
  artFor = animal;
  let a;
  try { a = await window.otter.art(animal); } catch (e) { a = null; }
  if (!a) { if (animal !== 'otter') { artFor = null; return loadArt('otter'); } return; }
  if (artFor !== animal) return;            // user switched again meanwhile
  for (const k of ['back', 'float', 'float2', 'front']) document.getElementById('slot-' + k).innerHTML = a[k] || '';
  if (typeof collectParts === 'function') collectParts();
  stage.className = (stage.className.replace(/\\bpet-\\w+/g, '') + ' pet-' + animal).replace(/\\s+/g, ' ').trim();
}

/* ---- facial expressions ---- */""", 1)
open(ROOT + '/src/pet.html', 'w').write(s)
print('ok', len(s))
