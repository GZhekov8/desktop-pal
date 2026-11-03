"""Generates the extra pets (cat, dog, fox, red panda) as SVG fragments.
Every pet uses the same head-local face coordinates as the otter
(eyes at x=+-11,y=-5; nose ends ~y=7; mouth below) so the shared
expression parts fit all of them."""
import math, random, re
from matplotlib.path import Path

# ---------------------------------------------------------------- helpers
def parse(d):
    toks = re.findall(r'[MCLQZ]|-?\d*\.?\d+', d)
    pts, i, cur, cmd = [], 0, (0, 0), None
    while i < len(toks):
        t = toks[i]
        if t in 'MCLQZ':
            cmd = t; i += 1
            if t == 'Z': continue
        n = lambda k: float(toks[i + k])
        if cmd == 'M' or cmd == 'L':
            cur = (n(0), n(1)); pts.append(cur); i += 2
        elif cmd == 'C':
            p0, p1, p2, p3 = cur, (n(0), n(1)), (n(2), n(3)), (n(4), n(5))
            for s in range(1, 13):
                u = s / 12; v = 1 - u
                pts.append(tuple(v**3*a + 3*v*v*u*b + 3*v*u*u*c + u**3*e for a, b, c, e in zip(p0, p1, p2, p3)))
            cur = p3; i += 6
        elif cmd == 'Q':
            p0, p1, p2 = cur, (n(0), n(1)), (n(2), n(3))
            for s in range(1, 9):
                u = s / 8; v = 1 - u
                pts.append(tuple(v*v*a + 2*v*u*b + u*u*c for a, b, c in zip(p0, p1, p2)))
            cur = p2; i += 4
        else:
            i += 1
    return pts

def region(d):
    p = parse(d)
    return Path(p), p

def hexmix(a, b, t):
    t = max(0, min(1, t))
    a = [int(a[k:k+2], 16) for k in (1, 3, 5)]; b = [int(b[k:k+2], 16) for k in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(x + (y - x) * t) for x, y in zip(a, b))

class Strands:
    def __init__(self): self.b = {}
    def add(self, col, op, w, x, y, ang, ln, curl):
        ex, ey = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        cx = (x + ex) / 2 + math.cos(ang + 1.57) * curl; cy = (y + ey) / 2 + math.sin(ang + 1.57) * curl
        self.b.setdefault((col, op, w), []).append(f"M{x:.1f} {y:.1f}Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}")
    def svg(self):
        return '<g fill="none" stroke-linecap="round">' + ''.join(
            f'<path d="{"".join(v)}" stroke="{k[0]}" stroke-opacity="{k[1]}" stroke-width="{k[2]}"/>' for k, v in self.b.items()) + '</g>'

def fill_strands(st, d, n, color, ang_fn, len_rng, w=(.45, .6), op=(.5, .7, .85), curl=.7):
    path, pts = region(d)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    got = 0; tries = 0
    while got < n and tries < n * 20:
        tries += 1
        x = random.uniform(min(xs), max(xs)); y = random.uniform(min(ys), max(ys))
        if not path.contains_point((x, y)): continue
        c = color(x, y)
        if not c: continue
        st.add(c, random.choice(op), random.choice(w), x, y, ang_fn(x, y) + random.gauss(0, .28),
               random.uniform(*len_rng), random.uniform(-curl, curl))
        got += 1

def edge_strands(st, d, color, step=2, out=1, len_rng=(1.4, 3.2), skip=lambda x, y: False, op=.8):
    _, pts = region(d)
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    for k in range(0, len(pts), step):
        x, y = pts[k]
        if skip(x, y): continue
        a = math.atan2(y - cy, x - cx) if out else 0
        st.add(color(x, y), op, .5, x, y, a + random.gauss(0, .35), random.uniform(*len_rng), random.uniform(-.8, .8))

def q(c, n=5):  # quantise a 0..1 value so strand colours bucket nicely
    return round(c * n) / n

# shared defs for the new pets (gradients)
DEFS = '''
<linearGradient id="catBodyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e3a05a"/><stop offset=".6" stop-color="#c87835"/><stop offset="1" stop-color="#9c5622"/></linearGradient>
<radialGradient id="catHeadG" cx="50%" cy="45%" r="60%"><stop offset="0" stop-color="#f0b46e"/><stop offset=".8" stop-color="#d4843d"/><stop offset="1" stop-color="#b0632a"/></radialGradient>
<linearGradient id="dogBodyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d49a55"/><stop offset=".6" stop-color="#b57a3c"/><stop offset="1" stop-color="#83552a"/></linearGradient>
<radialGradient id="dogHeadG" cx="50%" cy="40%" r="62%"><stop offset="0" stop-color="#dcaa66"/><stop offset=".85" stop-color="#bb8243"/><stop offset="1" stop-color="#966232"/></radialGradient>
<linearGradient id="foxBodyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2803a"/><stop offset=".6" stop-color="#c3601f"/><stop offset="1" stop-color="#8e4316"/></linearGradient>
<radialGradient id="foxHeadG" cx="50%" cy="35%" r="62%"><stop offset="0" stop-color="#ec9145"/><stop offset=".8" stop-color="#cf6a25"/><stop offset="1" stop-color="#a84f1a"/></radialGradient>
<linearGradient id="rpBodyG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c85a32"/><stop offset=".55" stop-color="#a8432a"/><stop offset="1" stop-color="#5c2418"/></linearGradient>
<radialGradient id="rpHeadG" cx="50%" cy="40%" r="62%"><stop offset="0" stop-color="#d06a3c"/><stop offset=".85" stop-color="#b44e2b"/><stop offset="1" stop-color="#8c3820"/></radialGradient>
<linearGradient id="cushG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7d9aa6"/><stop offset="1" stop-color="#46616d"/></linearGradient>
<linearGradient id="bedG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a39a8e"/><stop offset="1" stop-color="#6e665c"/></linearGradient>
<linearGradient id="mossG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7c8f45"/><stop offset="1" stop-color="#47552a"/></linearGradient>
<linearGradient id="barkG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a5a40"/><stop offset=".5" stop-color="#5e432e"/><stop offset="1" stop-color="#3b281b"/></linearGradient>
<filter id="fabric" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="1.8 .6" numOctaves="2" seed="2" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -.9 .55" result="m"/><feComposite in="m" in2="SourceGraphic" operator="in" result="t"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="t"/></feMerge></filter>
'''

def head_strands(color, n=750, rx=26, ry=20, cy=0, clean=lambda x, y: -15 < x < 15 and -10 < y < 15, fluff=None):
    st = Strands()
    for _ in range(n):
        a = random.uniform(0, 2 * math.pi); r = math.sqrt(random.uniform(0, 1))
        x = rx * r * math.cos(a); y = cy + ry * r * math.sin(a)
        if clean(x, y) and random.random() < .75: continue
        rr = math.hypot(x / rx, (y - cy) / ry)
        c = color(x, y, rr)
        if not c: continue
        st.add(c, random.choice([.5, .75]), .42, x, y, math.atan2(y - cy - 3, x) + random.gauss(0, .35), 1.2 + rr * 2.4, random.uniform(-.5, .5))
    for i in range(170):
        a = 2 * math.pi * i / 170; x = rx * math.cos(a); y = cy + ry * math.sin(a)
        c = (fluff or color)(x, y, 1.0)
        if c: st.add(c, .75, .5, x, y, a + random.gauss(0, .3), random.uniform(1.2, 3), random.uniform(-.6, .6))
    return st.svg()

# ================================================================ CAT
def cat():
    random.seed(21)
    body = 'M64 130 C56 112 66 92 94 86 C124 80 160 82 180 92 C194 100 198 118 192 132 C160 138 96 138 64 130 Z'
    tail = 'M68 126 C76 140 118 143 158 139 C168 138 176 135 180 131 C172 133 160 134 150 134 C118 136 88 133 76 122 Z'
    st = Strands()
    def bcol(x, y):
        stripe = (math.sin((x - y * .35) / 6.5) > .55)
        base = hexmix('#eaa862', '#9c5622', q((y - 84) / 50))
        return hexmix(base, '#9a4c18', .55) if stripe else base
    fill_strands(st, body, 1700, bcol, lambda x, y: math.pi + .2, (2.2, 4.2))
    edge_strands(st, body, lambda x, y: '#e6a25e', skip=lambda x, y: y > 128)
    tst = Strands()
    fill_strands(tst, tail, 420, lambda x, y: '#a65a22' if math.sin(x / 5.5) > .5 else '#dd9450', lambda x, y: 0.05, (2, 3.6))
    edge_strands(tst, tail, lambda x, y: '#d48a48', step=3)
    stripes = ''.join(f'<path d="M{x} {88 - (x - 120) * .03:.0f} C{x - 4} 100 {x - 2} 116 {x - 6} 130" stroke="#a3501b" stroke-width="3.2" stroke-opacity=".5" fill="none" filter="url(#soft1)"/>' for x in range(84, 180, 13))
    def hcol(x, y, rr):
        if abs(x) < 9 and y > 4: return '#fbf0e2'
        if y < -9 and abs(x) < 9 and int((x + 9) / 3.5) % 2 == 0: return '#a4521c'
        return hexmix('#f2b674', '#b0632a', q(max(0, rr - .45) * 1.8))
    head = f'''
      <g class="animal a-cat">
        <ellipse cx="128" cy="134" rx="72" ry="6" fill="#1d2a30" opacity=".35" filter="url(#soft)"/>
        <path d="{body}" fill="url(#catBodyG)" filter="url(#fur)"/>
        {stripes}
        {st.svg()}
        <path d="M70 104 C86 90 120 84 160 86" stroke="#ffe0b8" stroke-opacity=".3" stroke-width="2" fill="none" filter="url(#soft1)"/>
        <g class="alert-tail" style="transform-origin:70px 126px">
          <path d="{tail}" fill="#cf8240" filter="url(#fur)"/>{tst.svg()}
        </g>
        <!-- front paws -->
        <g fill="#f3d7b4" filter="url(#fur)"><ellipse cx="174" cy="134" rx="9" ry="4.6"/><ellipse cx="191" cy="133" rx="8.5" ry="4.4"/></g>
        <g stroke="#b88a62" stroke-width=".6" stroke-linecap="round"><path d="M176 136 v-2.4 M179 135.6 v-2.4 M189 135.4 v-2.4 M192.5 135 v-2.4"/></g>
        <g transform="translate(196 82) rotate(4)">
          <ellipse cx="-6" cy="19" rx="20" ry="5" fill="#3a1f0c" opacity=".3" filter="url(#soft)"/>
          <!-- ears -->
          <path d="M-24 -4 C-26 -14 -25 -25 -20 -33 C-13 -28 -8 -21 -5 -17 Z" fill="#d4843d" filter="url(#fur)"/>
          <path d="M24 -4 C26 -14 25 -25 20 -33 C13 -28 8 -21 5 -17 Z" fill="#d4843d" filter="url(#fur)"/>
          <path d="M-20 -8 C-21 -15 -20.5 -22 -18.5 -27 C-14 -23 -11 -19 -9.5 -16 Z" fill="#e9a29a"/>
          <path d="M20 -8 C21 -15 20.5 -22 18.5 -27 C14 -23 11 -19 9.5 -16 Z" fill="#e9a29a"/>
          <g stroke="#fff4e6" stroke-width=".4" opacity=".85" stroke-linecap="round"><path d="M-17 -12 l-2 -6 M-15 -13 l-.8 -6.5 M-13 -14 l.4 -6 M17 -12 l2 -6 M15 -13 l.8 -6.5 M13 -14 l-.4 -6"/></g>
          <path d="M-25 3 C-26 -10 -16 -19 0 -19 C16 -19 26 -10 25 3 C24 13 14 21 0 21 C-14 21 -24 13 -25 3 Z" fill="url(#catHeadG)" filter="url(#grizzle)"/>
          {head_strands(hcol, rx=25, ry=19, cy=1)}
          <!-- tabby marks -->
          <g stroke="#9a4a16" stroke-width="1.6" stroke-linecap="round" fill="none" opacity=".75">
            <path d="M-6 -18 L-4 -11 M0 -19 L0 -11 M6 -18 L4 -11"/><path d="M-15 -3 C-19 -2 -22 0 -24 3 M15 -3 C19 -2 22 0 24 3"/><path d="M-16 1 C-19 3 -21 6 -22 9 M16 1 C19 3 21 6 22 9"/>
          </g>
          <!-- muzzle -->
          <ellipse cx="-4.6" cy="9.2" rx="6" ry="4.6" fill="#fbf1e4" filter="url(#soft1)"/><ellipse cx="4.6" cy="9.2" rx="6" ry="4.6" fill="#fbf1e4" filter="url(#soft1)"/>
          <ellipse cx="0" cy="15" rx="6" ry="3.5" fill="#fbf1e4" filter="url(#soft1)"/>
          <g fill="#b88a62" opacity=".6"><circle cx="-6" cy="8.5" r=".5"/><circle cx="-8" cy="10.2" r=".5"/><circle cx="-4.5" cy="10.8" r=".5"/><circle cx="6" cy="8.5" r=".5"/><circle cx="8" cy="10.2" r=".5"/><circle cx="4.5" cy="10.8" r=".5"/></g>
          <!-- irises (behind the shared pupils) -->
          <g class="iris"><circle cx="-11" cy="-5" r="4" fill="#9fb041"/><circle cx="11" cy="-5" r="4" fill="#9fb041"/><circle cx="-11" cy="-5" r="4" fill="none" stroke="#5d6a1f" stroke-width=".7"/><circle cx="11" cy="-5" r="4" fill="none" stroke="#5d6a1f" stroke-width=".7"/></g>
          <path d="M-3.4 3 C-3.4 1.4 3.4 1.4 3.4 3 L0.6 6.6 C0.3 7 -0.3 7 -0.6 6.6 Z" fill="#d88b88" stroke="#a5605d" stroke-width=".4"/>
          @@FACE@@
          <g stroke="#fffaf2" stroke-width=".38" stroke-linecap="round" fill="none" opacity=".9">
            <path d="M-8 9 C-17 7 -26 7 -34 9"/><path d="M-8 10.5 C-17 10.5 -26 12 -33 15"/><path d="M-8 12 C-16 13.5 -24 17 -30 21"/>
            <path d="M8 9 C17 7 26 7 34 9"/><path d="M8 10.5 C17 10.5 26 12 33 15"/><path d="M8 12 C16 13.5 24 17 30 21"/>
          </g>
        </g>
      </g>'''
    back = '''
      <g class="animal a-cat">
        <ellipse cx="122" cy="140" rx="112" ry="22" fill="url(#cushG)"/>
        <ellipse cx="122" cy="135" rx="104" ry="16" fill="#86a3ae" filter="url(#fabric)"/>
        <ellipse cx="122" cy="140" rx="112" ry="22" fill="none" stroke="#3b525c" stroke-width="1.4" stroke-opacity=".6"/>
        <path d="M24 135 C70 152 174 152 220 135" stroke="#b9cdd4" stroke-width=".9" stroke-dasharray="2 2.5" fill="none" opacity=".6"/>
      </g>'''
    return back, head, ''

# ================================================================ DOG
def dog():
    random.seed(33)
    body = 'M58 128 C50 110 64 92 94 88 C126 84 160 86 178 96 C190 104 192 120 186 132 C150 138 90 138 58 128 Z'
    legs = 'M156 124 C175 121 202 122 218 125 C224 127 224 135 217 137 C196 139 174 138 156 135 Z'
    tail = 'M62 122 C48 120 32 112 22 103 C19 99 23 96 27 100 C37 108 50 113 64 115 Z'
    st = Strands()
    def bcol(x, y):
        if x > 168 and y > 100: return hexmix('#f2e6d2', '#d9c3a2', q((y - 100) / 35))
        return hexmix('#d8a05c', '#7f5128', q((y - 86) / 48))
    fill_strands(st, body, 1500, bcol, lambda x, y: math.pi + .15, (1.6, 3.2))
    edge_strands(st, body, lambda x, y: '#d39a55', len_rng=(1, 2.2), skip=lambda x, y: y > 128)
    lst = Strands()
    fill_strands(lst, legs, 360, lambda x, y: '#f1e5d0' if x > 200 else '#c48a48', lambda x, y: 0, (1.4, 2.6))
    tst = Strands()
    fill_strands(tst, tail, 200, lambda x, y: '#b37638', lambda x, y: math.pi + .5, (2, 4))
    edge_strands(tst, tail, lambda x, y: '#cf9550', step=2, len_rng=(2, 4))
    def hcol(x, y, rr):
        if abs(x) < 3 and y < 0: return '#f4ead9'
        if abs(x) < 11 and y > 0: return '#e8c08a'
        return hexmix('#d8a35f', '#966232', q(max(0, rr - .5) * 2))
    head = f'''
      <g class="animal a-dog">
        <ellipse cx="128" cy="134" rx="78" ry="6" fill="#2a2420" opacity=".35" filter="url(#soft)"/>
        <g class="alert-tail" style="transform-origin:62px 118px"><path d="{tail}" fill="#b37638" filter="url(#fur)"/>{tst.svg()}</g>
        <path d="{body}" fill="url(#dogBodyG)" filter="url(#fur)"/>
        <ellipse cx="84" cy="116" rx="22" ry="13" fill="none" stroke="#7a4c22" stroke-opacity=".35" stroke-width="1.4" filter="url(#soft1)"/>
        {st.svg()}
        <path d="M68 104 C86 92 120 87 160 89" stroke="#ffe2b6" stroke-opacity=".3" stroke-width="2" fill="none" filter="url(#soft1)"/>
        <path d="{legs}" fill="#c48a48" filter="url(#fur)"/>{lst.svg()}
        <path d="M188 129.5 L216 130" stroke="#9a6a3a" stroke-width=".6" opacity=".6"/>
        <g stroke="#b9a07e" stroke-width=".6" stroke-linecap="round"><path d="M219 127 h2.5 M219.5 130.5 h2.8 M219 134 h2.4"/></g>
        <g transform="translate(198 84) rotate(3)">
          <ellipse cx="-4" cy="20" rx="20" ry="5" fill="#2e1c0c" opacity=".3" filter="url(#soft)"/>
          <path d="M-22 -2 C-22 -15 -12 -21 0 -21 C12 -21 22 -15 22 -2 C22 8 16 14 0 15 C-16 14 -22 8 -22 -2 Z" fill="url(#dogHeadG)" filter="url(#grizzle)"/>
          <path d="M-11 2 C-11 -2 11 -2 11 2 C12 12 7 18.5 0 18.5 C-7 18.5 -12 12 -11 2 Z" fill="#e6bd86" filter="url(#fur)"/>
          <path d="M-2.6 -21 C-2 -12 -3 -6 -4.5 0 L4.5 0 C3 -6 2 -12 2.6 -21 Z" fill="#f4ead9" opacity=".9" filter="url(#soft1)"/>
          {head_strands(hcol, n=600, rx=22, ry=18, cy=-2, clean=lambda x, y: -14 < x < 14 and -10 < y < 18)}
          <!-- floppy ears -->
          <path d="M-17 -16 C-29 -17 -35 -3 -32 11 C-30 18 -23 19 -21 12 C-19 4 -18 -6 -13 -13 Z" fill="#8f5a2a" filter="url(#fur)"/>
          <path d="M17 -16 C29 -17 35 -3 32 11 C30 18 23 19 21 12 C19 4 18 -6 13 -13 Z" fill="#8f5a2a" filter="url(#fur)"/>
          <path d="M-26 -8 C-28 0 -28 8 -26 13 M26 -8 C28 0 28 8 26 13" stroke="#6d4120" stroke-width=".8" fill="none" opacity=".6"/>
          <path d="M-5.2 1.6 C-5.2 -1.6 5.2 -1.6 5.2 1.6 C5.2 4.6 2.4 6.5 0 6.9 C-2.4 6.5 -5.2 4.6 -5.2 1.6 Z" fill="url(#noseG)"/>
          <path d="M-2.4 .4 C-1 -.4 1 -.4 2.4 .4" stroke="#8a7a74" stroke-width=".7" fill="none" opacity=".7"/>
          <g fill="#a87a4c" opacity=".6"><circle cx="-6" cy="9" r=".5"/><circle cx="-7.6" cy="11" r=".5"/><circle cx="6" cy="9" r=".5"/><circle cx="7.6" cy="11" r=".5"/></g>
          @@FACE@@
        </g>
      </g>'''
    back = '''
      <g class="animal a-dog">
        <ellipse cx="122" cy="126" rx="114" ry="32" fill="url(#bedG)" filter="url(#fabric)"/>
        <ellipse cx="122" cy="132" rx="96" ry="21" fill="#8a8277" filter="url(#fabric)"/>
        <ellipse cx="122" cy="134" rx="90" ry="17" fill="#b4ab9e" filter="url(#fabric)"/>
      </g>'''
    front = '''
      <g class="animal a-dog">
        <path d="M8 128 C30 150 214 150 236 128 C240 140 232 156 210 160 C160 168 84 168 34 160 C12 156 4 140 8 128 Z" fill="url(#bedG)" filter="url(#fabric)"/>
        <path d="M14 134 C44 152 200 152 230 134" stroke="#cfc6b9" stroke-width="1.6" stroke-opacity=".55" fill="none" filter="url(#soft1)"/>
      </g>'''
    return back, head, front

# ================================================================ FOX
def fox():
    random.seed(45)
    body = 'M62 128 C54 110 66 92 94 87 C124 82 160 84 178 94 C190 102 194 118 188 132 C150 138 92 138 62 128 Z'
    tail = 'M62 124 C64 144 118 150 166 143 C182 141 194 136 198 128 C188 133 174 134 162 133 C120 132 86 128 72 114 Z'
    st = Strands()
    def bcol(x, y):
        if x > 170 and y > 98: return '#f6efe4'
        return hexmix('#ec8a42', '#8e4316', q((y - 84) / 50))
    fill_strands(st, body, 1700, bcol, lambda x, y: math.pi + .2, (2.4, 4.6))
    edge_strands(st, body, lambda x, y: '#e88a44', skip=lambda x, y: y > 128)
    tst = Strands()
    fill_strands(tst, tail, 900, lambda x, y: '#f8f2ea' if x > 172 else hexmix('#e07c36', '#a34c18', q((y - 124) / 22)),
                 lambda x, y: .05, (3.5, 6.5), curl=1.2)
    edge_strands(tst, tail, lambda x, y: '#f8f2ea' if x > 172 else '#de7a33', step=1, len_rng=(2.5, 5))
    def hcol(x, y, rr):
        if y > 1 and abs(x) > 5 and y > -abs(x) * .3 + 3: return '#f7f0e6'
        if y > 6 and abs(x) < 5: return '#f7f0e6'
        return hexmix('#f09a50', '#b0541b', q(max(0, rr - .5) * 2))
    head = f'''
      <g class="animal a-fox">
        <ellipse cx="128" cy="136" rx="76" ry="6" fill="#1f2610" opacity=".4" filter="url(#soft)"/>
        <path d="{body}" fill="url(#foxBodyG)" filter="url(#fur)"/>
        {st.svg()}
        <path d="M70 104 C86 90 120 85 160 87" stroke="#ffd9b0" stroke-opacity=".3" stroke-width="2" fill="none" filter="url(#soft1)"/>
        <g fill="#2a1a14" filter="url(#fur)"><ellipse cx="180" cy="134" rx="8" ry="4.4"/><ellipse cx="195" cy="132.5" rx="7.5" ry="4.2"/></g>
        <g class="alert-tail" style="transform-origin:70px 124px"><path d="{tail}" fill="#d06c2a" filter="url(#fur)"/>{tst.svg()}</g>
        <g transform="translate(197 82) rotate(3)">
          <ellipse cx="-4" cy="20" rx="18" ry="5" fill="#2e1606" opacity=".3" filter="url(#soft)"/>
          <path d="M-22 -6 C-25 -19 -25 -32 -20 -40 C-13 -33 -8 -25 -5 -18 Z" fill="#d46e2a" filter="url(#fur)"/>
          <path d="M22 -6 C25 -19 25 -32 20 -40 C13 -33 8 -25 5 -18 Z" fill="#d46e2a" filter="url(#fur)"/>
          <path d="M-22.6 -27 C-23 -32 -22 -37 -20 -40 C-17 -37 -14.5 -33 -13 -30 Z" fill="#2a1a14" filter="url(#fur)"/>
          <path d="M22.6 -27 C23 -32 22 -37 20 -40 C17 -37 14.5 -33 13 -30 Z" fill="#2a1a14" filter="url(#fur)"/>
          <path d="M-19 -10 C-20.5 -18 -20 -26 -18 -31 C-14 -26 -11 -21 -9 -16 Z" fill="#f3e6d6" opacity=".9" filter="url(#fur)"/>
          <path d="M19 -10 C20.5 -18 20 -26 18 -31 C14 -26 11 -21 9 -16 Z" fill="#f3e6d6" opacity=".9" filter="url(#fur)"/>
          <path d="M-26 -2 C-24 -13 -13 -19 0 -19 C13 -19 24 -13 26 -2 C23 6 15 12 9 16 C5 19 2 21 0 21 C-2 21 -5 19 -9 16 C-15 12 -23 6 -26 -2 Z" fill="url(#foxHeadG)" filter="url(#grizzle)"/>
          <path d="M-26 -1 C-19 5 -11 8 -5 8 C-4 12 -3 16 -2 20 C-8 17 -18 10 -26 -1 Z" fill="#f7f0e6" filter="url(#fur)"/>
          <path d="M26 -1 C19 5 11 8 5 8 C4 12 3 16 2 20 C8 17 18 10 26 -1 Z" fill="#f7f0e6" filter="url(#fur)"/>
          {head_strands(hcol, n=650, rx=25, ry=18, cy=0)}
          <path d="M-8 -3 C-7 3 -5 8 -3.5 10 M8 -3 C7 3 5 8 3.5 10" stroke="#5a2a10" stroke-width=".9" fill="none" opacity=".55"/>
          <g class="iris"><circle cx="-11" cy="-5" r="3.8" fill="#d39a2c"/><circle cx="11" cy="-5" r="3.8" fill="#d39a2c"/><circle cx="-11" cy="-5" r="3.8" fill="none" stroke="#7a4a10" stroke-width=".7"/><circle cx="11" cy="-5" r="3.8" fill="none" stroke="#7a4a10" stroke-width=".7"/></g>
          <path d="M-3.6 3 C-3.6 1 3.6 1 3.6 3 C3.6 5 1.7 6.6 0 6.9 C-1.7 6.6 -3.6 5 -3.6 3 Z" fill="url(#noseG)"/>
          @@FACE@@
          <g stroke="#2a1a14" stroke-width=".35" stroke-linecap="round" fill="none" opacity=".75">
            <path d="M-6 9 C-14 8 -21 9 -27 11"/><path d="M-6 10.5 C-13 11 -19 13 -24 16"/><path d="M6 9 C14 8 21 9 27 11"/><path d="M6 10.5 C13 11 19 13 24 16"/>
          </g>
        </g>
      </g>'''
    tufts = ''.join(f'<path d="M{x} 150 q-1 -6 -3 -9 M{x + 2} 150 q0 -7 1 -10 M{x + 4} 150 q2 -5 4 -7" stroke="#5f7432" stroke-width="1" fill="none" stroke-linecap="round"/>' for x in (18, 52, 96, 150, 204))
    back = f'''
      <g class="animal a-fox">
        <ellipse cx="122" cy="140" rx="116" ry="20" fill="url(#mossG)" filter="url(#fabric)"/>
        <path d="M40 146 c3 -3 7 -2 8 1 c-3 2 -6 2 -8 -1z M180 147 c3 -3 7 -2 8 1 c-3 2 -6 2 -8 -1z" fill="#b5651d" opacity=".85"/>
      </g>'''
    front = f'<g class="animal a-fox">{tufts}</g>'
    return back, head, front

# ================================================================ RED PANDA
def redpanda():
    random.seed(57)
    body = 'M60 122 C54 106 68 92 96 88 C126 84 160 86 178 96 C190 104 190 118 184 126 C150 130 92 130 60 122 Z'
    tail = 'M66 116 C50 118 38 128 32 142 C28 152 30 162 34 168 L46 168 C42 160 42 150 46 142 C52 132 60 126 70 124 Z'
    leg1 = 'M164 120 C162 130 164 140 166 150 C170 154 178 154 178 148 C176 138 176 128 178 120 Z'
    leg2 = 'M82 120 C80 130 80 140 82 148 C86 152 94 152 94 146 C92 136 92 128 94 120 Z'
    st = Strands()
    fill_strands(st, body, 1600, lambda x, y: hexmix('#d0643a', '#4a1c12', q((y - 88) / 38)) if y < 118 else '#3a1810',
                 lambda x, y: math.pi + .2, (2.4, 4.6))
    edge_strands(st, body, lambda x, y: '#cf6238', skip=lambda x, y: y > 120)
    tst = Strands()
    fill_strands(tst, tail, 700, lambda x, y: '#e7a06a' if int((y - 110) / 7) % 2 else '#a63d22', lambda x, y: math.pi / 2 + .3, (3, 5.5), curl=1)
    edge_strands(tst, tail, lambda x, y: '#c45a32', step=1, len_rng=(2, 4))
    lst = Strands()
    for d in (leg1, leg2):
        fill_strands(lst, d, 160, lambda x, y: '#2a1410', lambda x, y: math.pi / 2, (1.6, 3))
    def hcol(x, y, rr):
        if y > 2 and abs(x) < 10: return '#f6efe5'
        if abs(abs(x) - 18) < 6 and abs(y - 4) < 6: return '#f6efe5'
        return hexmix('#d8703f', '#8c3820', q(max(0, rr - .5) * 2))
    head = f'''
      <g class="animal a-redpanda">
        <ellipse cx="124" cy="126" rx="70" ry="5" fill="#1d120a" opacity=".4" filter="url(#soft)"/>
        <g class="alert-tail" style="transform-origin:66px 120px"><path d="{tail}" fill="#b04a28" filter="url(#fur)"/>{tst.svg()}</g>
        <path d="{leg2}" fill="#2a1410" filter="url(#fur)"/>
        <path d="{body}" fill="url(#rpBodyG)" filter="url(#fur)"/>
        {st.svg()}
        <path d="M70 100 C88 90 120 86 160 88" stroke="#ffcaa6" stroke-opacity=".3" stroke-width="2" fill="none" filter="url(#soft1)"/>
        <path d="{leg1}" fill="#2a1410" filter="url(#fur)"/>{lst.svg()}
        <g transform="translate(196 82) rotate(4)">
          <ellipse cx="-4" cy="19" rx="18" ry="5" fill="#1d0c06" opacity=".35" filter="url(#soft)"/>
          <path d="M-25 -4 C-29 -14 -27 -25 -19 -28 C-13 -26 -9 -20 -6 -16 Z" fill="#f2e9dc" filter="url(#fur)"/>
          <path d="M25 -4 C29 -14 27 -25 19 -28 C13 -26 9 -20 6 -16 Z" fill="#f2e9dc" filter="url(#fur)"/>
          <path d="M-21 -8 C-24 -15 -23 -22 -18.5 -24 C-14 -22 -11 -18 -9 -15 Z" fill="#7a2a18"/>
          <path d="M21 -8 C24 -15 23 -22 18.5 -24 C14 -22 11 -18 9 -15 Z" fill="#7a2a18"/>
          <path d="M-26 2 C-26 -12 -14 -20 0 -20 C14 -20 26 -12 26 2 C25 13 14 20 0 20 C-14 20 -25 13 -26 2 Z" fill="url(#rpHeadG)" filter="url(#grizzle)"/>
          <ellipse cx="0" cy="9" rx="10.5" ry="8.5" fill="#f6efe5" filter="url(#fur)"/>
          <ellipse cx="-18" cy="5" rx="6.5" ry="6" fill="#f6efe5" filter="url(#fur)"/><ellipse cx="18" cy="5" rx="6.5" ry="6" fill="#f6efe5" filter="url(#fur)"/>
          <ellipse cx="-11" cy="-13" rx="4.2" ry="2.8" fill="#f6efe5" filter="url(#fur)"/><ellipse cx="11" cy="-13" rx="4.2" ry="2.8" fill="#f6efe5" filter="url(#fur)"/>
          {head_strands(hcol, n=650, rx=25, ry=19, cy=0)}
          <path d="M-11 -1 C-12 4 -13 10 -15 15 M11 -1 C12 4 13 10 15 15" stroke="#7a2a18" stroke-width="3" stroke-linecap="round" fill="none" opacity=".8" filter="url(#soft1)"/>
          <path d="M-4.2 2 C-4.2 -.2 4.2 -.2 4.2 2 C4.2 4.6 2 6.5 0 6.9 C-2 6.5 -4.2 4.6 -4.2 2 Z" fill="url(#noseG)"/>
          @@FACE@@
          <g stroke="#fffaf2" stroke-width=".35" stroke-linecap="round" fill="none" opacity=".8">
            <path d="M-7 9 C-14 8 -20 9 -25 11"/><path d="M-7 10.5 C-13 11.5 -18 13.5 -22 16"/><path d="M7 9 C14 8 20 9 25 11"/><path d="M7 10.5 C13 11.5 18 13.5 22 16"/>
          </g>
        </g>
      </g>'''
    back = '''
      <g class="animal a-redpanda">
        <path d="M-10 120 C60 114 160 114 250 122 L250 142 C160 136 60 136 -10 142 Z" fill="url(#barkG)"/>
        <g stroke="#2e1f14" stroke-width=".8" fill="none" opacity=".55" stroke-linecap="round">
          <path d="M6 126 C40 123 70 124 96 126"/><path d="M110 129 C140 127 170 127 200 130"/><path d="M20 134 C50 132 80 132 104 134"/><path d="M150 135 C180 134 210 135 236 137"/>
        </g>
        <path d="M120 118 c8 -3 18 -3 26 0 c-6 3 -18 3 -26 0z M30 122 c6 -2 12 -2 16 0 c-4 2 -12 2 -16 0z" fill="#6f8a3a" opacity=".85"/>
      </g>'''
    return back, head, ''

ANIMALS = {'cat': cat, 'dog': dog, 'fox': fox, 'redpanda': redpanda}

# ---------------------------------------------------------------- neck / chest joining head to body
NECKS = {
    'cat': ('url(#catBodyG)', lambda x, y: '#f6e3c8' if x > 192 and y > 100 else hexmix('#e6a45c', '#b8692c', q((y - 86) / 40))),
    'dog': ('url(#dogBodyG)', lambda x, y: '#f2e6d2' if x > 186 and y > 96 else hexmix('#d8a05c', '#a06a34', q((y - 86) / 40))),
    'fox': ('#f2e8dc', lambda x, y: '#f7f0e6' if x > 184 else hexmix('#ec8a42', '#b0541b', q((y - 86) / 40))),
    'redpanda': ('url(#rpBodyG)', lambda x, y: '#3a1810' if x > 186 and y > 100 else hexmix('#d0643a', '#6a2a18', q((y - 86) / 36))),
}
def neck(name):
    random.seed(99)
    fill, col = NECKS[name]
    d = 'M168 94 C180 84 202 86 211 100 C216 112 210 126 196 131 C184 132 172 124 168 110 Z' if name != 'redpanda' else \
        'M168 94 C180 84 202 86 210 99 C214 108 210 118 200 123 C186 126 172 120 168 108 Z'
    st = Strands()
    fill_strands(st, d, 520, col, lambda x, y: math.atan2(y - 92, x - 186) * .4 + math.pi / 2 * .6, (2, 4))
    edge_strands(st, d, col, skip=lambda x, y: y > 126 or x < 172)
    return f'<path d="{d}" fill="{fill}" filter="url(#fur)"/>{st.svg()}'
