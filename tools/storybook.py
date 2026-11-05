"""Storybook-style artwork for all six pets (resting pose + walking pose).

Clean shapes, soft gradient shading, a darker outline in the animal's own colour and a few
hand-placed fur tufts, instead of thousands of tiny strands. It reads well at small sizes and is
far cheaper to draw (no turbulence filters).

Every head uses the same local face coordinates (eyes at x=+-11, y=-5; nose ~y=0..7; mouth below)
so the shared expressions (@@FACE@@) fit every animal. Heads are placed with
<g transform="translate(19x y) ...">, which build.py relies on."""
import math, random
from animals import parse, region   # outline sampling + point-in-shape helpers

# ---------------------------------------------------------------- drawing helpers
def shape(d, fill, line, w=1.2, op=.75, extra=''):
    return f'<path d="{d}" fill="{fill}" stroke="{line}" stroke-width="{w}" stroke-opacity="{op}" stroke-linejoin="round"{extra}/>'

def leaf(x, y, ang, ln, w, bend=0.0):
    """a tapered tuft of fur starting at (x, y) pointing along ang"""
    ca, sa = math.cos(ang), math.sin(ang); nx, ny = -sa, ca
    lx, ly = x + nx * w / 2, y + ny * w / 2; rx, ry = x - nx * w / 2, y - ny * w / 2
    tx, ty = x + ca * ln + nx * bend, y + sa * ln + ny * bend
    c1 = (x + ca * ln * .55 + nx * w * .45, y + sa * ln * .55 + ny * w * .45)
    c2 = (x + ca * ln * .55 - nx * w * .45, y + sa * ln * .55 - ny * w * .45)
    return f'M{lx:.1f} {ly:.1f}Q{c1[0]:.1f} {c1[1]:.1f} {tx:.1f} {ty:.1f}Q{c2[0]:.1f} {c2[1]:.1f} {rx:.1f} {ry:.1f}Z'

def tufts(d, fill, line, pick=lambda x, y: True, every=7, ln=(2.6, 4.2), w=(3, 4.2), seed=1, op=.7, lw=.9):
    """little fur tufts poking out of an outline (drawn before the shape so their roots are hidden)"""
    rnd = random.Random(seed); path, pts = region(d); out = []
    for k in range(every // 2, len(pts) - 1, every):
        x, y = pts[k]
        if not pick(x, y): continue
        (ax, ay), (bx, by) = pts[k - 1], pts[(k + 1) % len(pts)]
        tx, ty = bx - ax, by - ay; L = math.hypot(tx, ty) or 1
        nx, ny = ty / L, -tx / L
        if path.contains_point((x + nx * 1.5, y + ny * 1.5)): nx, ny = -nx, -ny
        ang = math.atan2(ny, nx) + rnd.uniform(-.35, .35)
        out.append(leaf(x - nx * 1.2, y - ny * 1.2, ang, rnd.uniform(*ln), rnd.uniform(*w), rnd.uniform(-1, 1)))
    return f'<path d="{"".join(out)}" fill="{fill}" stroke="{line}" stroke-width="{lw}" stroke-opacity="{op}" stroke-linejoin="round"/>' if out else ''

def hatch(d, color, n, ang_fn, ln=(3, 5.5), w=.8, op=.2, seed=1, pick=lambda x, y: True):
    """a few soft brush strokes inside a shape that show which way the fur lies"""
    rnd = random.Random(seed); path, pts = region(d)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; out = []; tries = 0
    while len(out) < n and tries < n * 40:
        tries += 1
        x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
        if not path.contains_point((x, y)) or not pick(x, y): continue
        a = ang_fn(x, y) + rnd.gauss(0, .18); l = rnd.uniform(*ln)
        ex, ey = x + math.cos(a) * l, y + math.sin(a) * l
        cx, cy = (x + ex) / 2 - math.sin(a) * l * .18, (y + ey) / 2 + math.cos(a) * l * .18
        out.append(f'M{x:.1f} {y:.1f}Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}')
    return f'<path d="{"".join(out)}" stroke="{color}" stroke-width="{w}" stroke-opacity="{op}" stroke-linecap="round" fill="none"/>'

def whiskers(col='#fffaf2', op=.85, span=1.0, droop=0.0):
    s = span
    l = [f'M-9 9 C{-18*s:.0f} {7+droop:.0f} {-27*s:.0f} {7+droop:.0f} {-35*s:.0f} {9+droop*1.5:.0f}', f'M-9 10.5 C{-18*s:.0f} {10.5+droop:.0f} {-27*s:.0f} {12+droop:.0f} {-34*s:.0f} {15+droop*1.5:.0f}',
         f'M-9 12 C{-17*s:.0f} {13.5+droop:.0f} {-25*s:.0f} {17+droop:.0f} {-31*s:.0f} {21+droop*1.5:.0f}']
    r = [p.replace('M-9', 'M9').replace('C-', 'C').replace(' -', ' ') for p in l]
    return f'<path d="{"".join(l + r)}" stroke="{col}" stroke-width=".45" stroke-linecap="round" fill="none" opacity="{op}"/>'

def grad(id, stops, x2=0, y2=1, radial=False, cx=.5, cy=.4, r=.65):
    st = ''.join(f'<stop offset="{o}" stop-color="{c}"{"" if len(s) < 3 else f" stop-opacity=\"{s[2]}\""}/>' for s in stops for o, c in [s[:2]])
    if radial: return f'<radialGradient id="{id}" cx="{cx}" cy="{cy}" r="{r}">{st}</radialGradient>'
    return f'<linearGradient id="{id}" x1="0" y1="0" x2="{x2}" y2="{y2}">{st}</linearGradient>'

SOFT_SHADOW = lambda cx, cy, rx, ry, op=.28: f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#sbShadow)" opacity="{op / .28:.2f}"/>'

DEFS = ''.join([
    grad('sbShadow', [(0, '#1b130c', .28), (1, '#1b130c', 0)], radial=True, cy=.5, r=.5),
    # cat
    grad('sbCat', [(0, '#f6b46c'), (.55, '#e8964b'), (1, '#c46f2e')]),
    grad('sbCatHead', [(0, '#f8bf7c'), (.7, '#ea9a50'), (1, '#cf7934')], radial=True),
    grad('sbCushion', [(0, '#8fb3bf'), (1, '#4f7280')]),
    # dog
    grad('sbDog', [(0, '#e2b07a'), (.6, '#c98d51'), (1, '#9f6633')]),
    grad('sbDogHead', [(0, '#e9bb85'), (.75, '#cf9558'), (1, '#ad7038')], radial=True),
    grad('sbBed', [(0, '#b9a48f'), (1, '#7d6a58')]),
    # fox
    grad('sbFox', [(0, '#f6a25c'), (.55, '#e57a32'), (1, '#b9541b')]),
    grad('sbFoxHead', [(0, '#f8ad68'), (.75, '#e8803a'), (1, '#c25d20')], radial=True),
    grad('sbMoss', [(0, '#8aa152'), (1, '#4f6130')]),
    # red panda
    grad('sbRp', [(0, '#df7a48'), (.55, '#c4532a'), (1, '#8a3318')]),
    grad('sbRpHead', [(0, '#e7895a'), (.75, '#c9592e'), (1, '#9c3c1c')], radial=True),
    grad('sbBark', [(0, '#8a6a4c'), (.5, '#6a4c34'), (1, '#43301f')]),
    grad('sbLimb', [(0, '#3a1c12'), (1, '#1f0e09')]),
    # tiger
    grad('sbTig', [(0, '#f9b062'), (.55, '#ec8a32'), (1, '#c4641c')]),
    grad('sbTigHead', [(0, '#fbbb70'), (.75, '#ee903a'), (1, '#cf6c20')], radial=True),
    grad('sbRock', [(0, '#c3b6a5'), (.55, '#9a8c7b'), (1, '#695e52')]),
    # otter
    grad('sbOtter', [(0, '#8f6749'), (.55, '#6e4a33'), (1, '#4a2f1f')]),
    grad('sbOtterChest', [(0, '#d9c2a3'), (1, '#b39373')]),
    grad('sbOtterHead', [(0, '#e7d6bd'), (.7, '#cdb391'), (1, '#a8896a')], radial=True),
    grad('sbOtterFlip', [(0, '#4b3022'), (1, '#2a1a12')]),
    grad('sbShell', [(0, '#f4ece2'), (1, '#c9b8a6')]),
])

# ================================================================ CAT: a ginger tabby loafing on a round cushion
def cat():
    OUT, CREAM, STRIPE = '#7a3f17', '#fbeedd', '#b55f27'
    body = 'M66 134 C58 120 64 100 88 93 C114 86 156 87 176 95 C192 101 198 118 194 134 Z'
    tail = 'M70 134 C60 128 58 118 66 114 C70 118 72 126 82 130 C104 136 140 137 160 134 C168 133 172 136 168 140 C150 144 98 144 70 134 Z'
    chest = 'M172 98 C186 100 198 112 200 128 C194 134 182 135 174 130 C170 120 168 108 172 98 Z'
    stripes = ''.join(f'<path d="M{x} {y} C{x - 6} {y + 9} {x - 3} {y + 18} {x - 7} {y + 26} C{x - 2} {y + 18} {x + 2} {y + 9} {x + 4} {y + 1} Z" fill="{STRIPE}" opacity=".75"/>'
                      for x, y in [(96, 92), (112, 89), (128, 88), (144, 89), (158, 92)])
    float = f'''
        {SOFT_SHADOW(130, 138, 82, 9)}
        
        {shape(body, 'url(#sbCat)', OUT)}
        {stripes}
        {hatch(body, '#a9561e', 14, lambda x, y: math.pi * .55, seed=4, pick=lambda x, y: y < 126)}
        <path d="M82 102 C100 92 132 88 166 92" stroke="#ffe3bd" stroke-width="2.2" stroke-opacity=".55" fill="none" stroke-linecap="round"/>
        <g class="alert-tail" style="transform-origin:70px 130px">
          {shape(tail, 'url(#sbCat)', OUT)}
          <path d="M86 133 l3 6 M104 135 l2 6 M122 136 l1.5 6 M140 136 l1 5.5" stroke="{STRIPE}" stroke-width="3" stroke-linecap="round" opacity=".7"/>
        </g>
        {tufts(chest, CREAM, '#c9a888', every=6, ln=(2.4, 3.6), seed=5)}
        {shape(chest, CREAM, '#c9a888', 1)}
        <!-- front paws tucked under the chest -->
        {shape('M166 132 C166 127 172 125 177 126 C182 127 184 131 182 135 C178 137 170 137 166 132 Z', CREAM, '#b88f6c', 1)}
        {shape('M184 131 C184 126 190 124 195 125 C200 126 202 130 200 134 C196 136 188 136 184 131 Z', CREAM, '#b88f6c', 1)}
        <path d="M172 132 v-2.6 M176.5 132.5 v-2.8 M190 131 v-2.6 M194.5 131.5 v-2.8" stroke="#b88f6c" stroke-width=".8" stroke-linecap="round"/>
        <g transform="translate(196 82) rotate(4)">
          {SOFT_SHADOW(-4, 20, 22, 5, .3)}
          <!-- ears -->
          {shape('M-24 -2 C-27 -14 -25 -26 -19 -34 C-12 -28 -7 -21 -4 -16 Z', 'url(#sbCatHead)', OUT)}
          {shape('M24 -2 C27 -14 25 -26 19 -34 C12 -28 7 -21 4 -16 Z', 'url(#sbCatHead)', OUT)}
          <path d="M-20 -8 C-21.5 -16 -20.5 -23 -18.6 -28 C-14 -24 -11 -19 -9 -16 Z M20 -8 C21.5 -16 20.5 -23 18.6 -28 C14 -24 11 -19 9 -16 Z" fill="#eaa9a2"/>
          <path d="M-17 -12 l-2.4 -6 M-14.5 -13.5 l-1 -6.4 M17 -12 l2.4 -6 M14.5 -13.5 l1 -6.4" stroke="{CREAM}" stroke-width=".7" stroke-linecap="round"/>
          <!-- head with fluffy cheeks -->
          {tufts('M-26 2 C-27 -11 -16 -20 0 -20 C16 -20 27 -11 26 2 C25 14 14 21 0 21 C-14 21 -25 14 -26 2 Z', 'url(#sbCatHead)', OUT, pick=lambda x, y: y > 0 and abs(x) > 14, every=5, ln=(3, 5), seed=6)}
          {shape('M-26 2 C-27 -11 -16 -20 0 -20 C16 -20 27 -11 26 2 C25 14 14 21 0 21 C-14 21 -25 14 -26 2 Z', 'url(#sbCatHead)', OUT)}
          <!-- forehead "M" and cheek stripes -->
          <path d="M-7 -19 C-6 -15 -5 -13 -3.6 -10 M0 -20 L0 -11 M7 -19 C6 -15 5 -13 3.6 -10" stroke="{STRIPE}" stroke-width="2" stroke-linecap="round" fill="none"/>
          <path d="M-25 0 C-21 -1 -18 -1 -15 0 M-25 5 C-21 4 -18 4 -15.5 5 M25 0 C21 -1 18 -1 15 0 M25 5 C21 4 18 4 15.5 5" stroke="{STRIPE}" stroke-width="1.7" stroke-linecap="round" fill="none" opacity=".85"/>
          <!-- muzzle -->
          <path d="M-12 9 C-12 3 -5 1 0 3 C5 1 12 3 12 9 C12 15 6 19 0 19 C-6 19 -12 15 -12 9 Z" fill="{CREAM}"/>
          <g fill="#c49a76" opacity=".7"><circle cx="-6" cy="8.5" r=".55"/><circle cx="-8.4" cy="10.4" r=".55"/><circle cx="-5" cy="11.2" r=".55"/><circle cx="6" cy="8.5" r=".55"/><circle cx="8.4" cy="10.4" r=".55"/><circle cx="5" cy="11.2" r=".55"/></g>
          <g class="iris"><circle cx="-11" cy="-5" r="4.2" fill="#a9bb4c"/><circle cx="11" cy="-5" r="4.2" fill="#a9bb4c"/><circle cx="-11" cy="-5" r="4.2" fill="none" stroke="#5d6a1f" stroke-width=".8"/><circle cx="11" cy="-5" r="4.2" fill="none" stroke="#5d6a1f" stroke-width=".8"/></g>
          <path d="M-3.6 2.6 C-3.6 1 3.6 1 3.6 2.6 L0.7 6.4 C0.35 6.8 -0.35 6.8 -0.7 6.4 Z" fill="#e2908c" stroke="#a5605d" stroke-width=".5"/>
          @@FACE@@
          {whiskers()}
        </g>'''
    back = f'''
        {SOFT_SHADOW(124, 146, 112, 8, .25)}
        <ellipse cx="124" cy="139" rx="110" ry="17" fill="url(#sbCushion)" stroke="#3b5762" stroke-width="1.2" stroke-opacity=".7"/>
        <ellipse cx="124" cy="134" rx="100" ry="11" fill="#a5c3cd"/>
        <path d="M30 136 C76 150 172 150 218 136" stroke="#d6e6eb" stroke-width="1" stroke-dasharray="2.4 2.8" fill="none" opacity=".8"/>'''
    return back, float, ''

# ================================================================ DOG: a beagle lying sphinx-style, front legs stretched out
def dog():
    OUT, WHITE, SADDLE, EAR = '#5e3a1c', '#f8f1e6', '#6a4122', '#8a5426'
    body = 'M58 132 C50 116 60 96 86 90 C116 84 156 86 176 96 C190 103 194 118 188 132 Z'
    saddle = 'M66 104 C66 94 84 88 110 86 C134 84 152 86 162 90 C158 96 146 100 128 101 C108 102 90 102 78 106 C72 108 66 108 66 104 Z'
    legs = 'M160 126 C178 122 206 122 222 125 C229 127 229 136 222 138 C200 140 178 139 160 136 Z'
    tail = 'M62 124 C46 122 30 114 22 104 C19 99 24 96 28 100 C38 109 52 114 66 116 Z'
    float = f'''
        {SOFT_SHADOW(134, 139, 92, 9)}
        <g class="alert-tail" style="transform-origin:64px 120px">
          {shape(tail, 'url(#sbDog)', OUT)}
          <path d="M24 101 C22 98 25 96 28 99 C30 101 28 104 24 101 Z" fill="{WHITE}"/>
        </g>
        
        {shape(body, 'url(#sbDog)', OUT)}
        <path d="{saddle}" fill="{SADDLE}" opacity=".9"/>
        {hatch(body, '#8a5428', 12, lambda x, y: math.pi * .58, seed=8, pick=lambda x, y: y > 104 and y < 128)}
        <path d="M80 100 C100 92 130 89 156 92" stroke="#c48a58" stroke-width="1.4" stroke-opacity=".6" fill="none" stroke-linecap="round"/>
        <!-- white chest and front legs stretched out in front -->
        {shape('M164 96 C180 98 194 110 196 126 C186 130 172 128 166 122 C162 114 160 104 164 96 Z', WHITE, '#bba78f', 1)}
        {shape('M158 124 C176 121 200 121 214 123 C222 124 224 131 218 133 C200 135 176 134 158 132 Z', '#efe5d6', '#bba78f', 1)}
        {shape('M206 124 C212 121 220 121 224 124 C227 127 225 132 220 133 C214 134 208 132 206 128 Z', '#efe5d6', '#bba78f', 1)}
        {shape('M160 132 C178 129 204 129 218 131 C226 132 228 139 222 141 C204 143 178 142 160 140 Z', WHITE, '#bba78f', 1)}
        {shape('M212 132 C218 129 226 129 230 132 C233 135 231 140 226 141 C220 142 214 140 212 136 Z', WHITE, '#bba78f', 1)}
        <path d="M220 134.6 l1 -2.6 M224 134.8 l1.4 -2.4 M214 125.6 l1 -2.4 M218 125.8 l1.4 -2.2" stroke="#bba78f" stroke-width=".8" stroke-linecap="round"/>
        <g transform="translate(194 80) rotate(3)">
          {SOFT_SHADOW(-4, 21, 22, 5, .3)}
          {shape('M-26 3 C-27 -11 -16 -21 0 -21 C16 -21 27 -11 26 3 C25 15 14 22 0 22 C-14 22 -25 15 -26 3 Z', 'url(#sbDogHead)', OUT)}
          <!-- white blaze down the middle -->
          <path d="M-3 -21 C-4 -12 -5 -5 -9 2 C-6 6 6 6 9 2 C5 -5 4 -12 3 -21 Z" fill="{WHITE}"/>
          <path d="M-12 10 C-12 4 -6 2 0 3 C6 2 12 4 12 10 C12 17 6 21 0 21 C-6 21 -12 17 -12 10 Z" fill="{WHITE}"/>
          <!-- long floppy ears -->
          {shape('M-21 -15 C-30 -14 -35 -2 -34 12 C-33 22 -28 28 -22 26 C-17 24 -16 14 -17 4 C-17.5 -4 -17 -10 -21 -15 Z', EAR, OUT)}
          {shape('M21 -15 C30 -14 35 -2 34 12 C33 22 28 28 22 26 C17 24 16 14 17 4 C17.5 -4 17 -10 21 -15 Z', EAR, OUT)}
          <path d="M-29 -2 C-31 6 -30 16 -27 22 M29 -2 C31 6 30 16 27 22" stroke="#a96b37" stroke-width="1.6" fill="none" stroke-linecap="round" opacity=".6"/>
          <g fill="#b39b82" opacity=".7"><circle cx="-6" cy="11" r=".55"/><circle cx="-8.4" cy="13" r=".55"/><circle cx="6" cy="11" r=".55"/><circle cx="8.4" cy="13" r=".55"/></g>
          <path d="M-5.6 2.4 C-5.6 -0.4 5.6 -0.4 5.6 2.4 C5.6 5.6 2.6 7.6 0 7.8 C-2.6 7.6 -5.6 5.6 -5.6 2.4 Z" fill="#2d1d16"/>
          <ellipse cx="-1.8" cy="1.6" rx="1.6" ry=".9" fill="#fff" opacity=".35"/>
          @@FACE@@
          {whiskers('#e9dccb', .55, .8)}
        </g>'''
    back = f'''
        {SOFT_SHADOW(124, 146, 114, 8, .25)}
        <path d="M10 136 C14 122 40 116 70 115 L180 115 C212 116 236 122 238 136 C236 148 210 152 180 152 L70 152 C38 152 12 148 10 136 Z" fill="url(#sbBed)" stroke="#55473a" stroke-width="1.2" stroke-opacity=".7"/>
        <path d="M24 132 C40 124 70 122 100 122 L156 122 C186 122 212 124 226 132 C212 140 186 142 156 142 L100 142 C70 142 40 140 24 132 Z" fill="#cdbcaa"/>'''
    return back, float, ''

# ================================================================ FOX: curled up, big bushy tail wrapped round the front
def fox():
    OUT, WHITE, BLACK = '#6e2e0c', '#fbf3ea', '#2a1a14'
    body = 'M64 132 C54 116 64 96 92 90 C122 84 160 88 178 98 C190 106 194 120 190 132 Z'
    tail = 'M62 124 C46 132 54 150 84 152 C120 155 164 153 192 147 C206 144 216 138 218 130 C208 124 194 127 184 130 C160 136 120 137 94 132 C80 129 70 124 62 124 Z'
    float = f'''
        {SOFT_SHADOW(134, 141, 90, 9)}
        
        {shape(body, 'url(#sbFox)', OUT)}
        {hatch(body, '#a84a14', 14, lambda x, y: math.pi * .56, seed=10, pick=lambda x, y: y < 126)}
        <path d="M80 100 C100 91 134 88 166 94" stroke="#ffcf9e" stroke-width="2.2" stroke-opacity=".55" fill="none" stroke-linecap="round"/>
        <!-- white chest ruff -->
        {tufts('M168 96 C184 98 196 110 198 126 C188 132 174 130 168 124 C164 116 163 104 168 96 Z', WHITE, '#c8b6a2', every=5, ln=(2.6, 4), seed=11)}
        {shape('M168 96 C184 98 196 110 198 126 C188 132 174 130 168 124 C164 116 163 104 168 96 Z', WHITE, '#c8b6a2', 1)}
        <!-- black socks peeking out -->
        {shape('M170 134 C170 129 176 127 181 128 C185 129 186 133 184 136 C180 138 172 138 170 134 Z', BLACK, '#120a07', 1)}
        <g class="alert-tail" style="transform-origin:62px 130px">
          {tufts(tail, 'url(#sbFox)', OUT, pick=lambda x, y: y > 140 and x < 186, every=6, ln=(3, 5), w=(3.6, 5), seed=12)}
          {shape(tail, 'url(#sbFox)', OUT)}
          {hatch(tail, '#a84a14', 12, lambda x, y: 0, seed=13)}
          {tufts('M182 131 C194 126 208 124 218 130 C216 138 206 144 190 147 C184 142 182 136 182 131 Z', WHITE, '#c8b6a2', pick=lambda x, y: x > 192, every=4, ln=(2.6, 4), seed=25)}
          {shape('M182 131 C194 126 208 124 218 130 C216 138 206 144 190 147 C184 142 182 136 182 131 Z', WHITE, '#c8b6a2', 1)}
        </g>
        <g transform="translate(196 80) rotate(4)">
          {SOFT_SHADOW(-4, 21, 22, 5, .3)}
          <!-- tall ears with black backs -->
          {shape('M-25 -2 C-29 -16 -27 -30 -20 -40 C-12 -32 -7 -23 -4 -16 Z', 'url(#sbFoxHead)', OUT)}
          {shape('M25 -2 C29 -16 27 -30 20 -40 C12 -32 7 -23 4 -16 Z', 'url(#sbFoxHead)', OUT)}
          <path d="M-20 -40 C-23 -35 -25 -30 -26 -25 C-22 -28 -19 -30 -16 -33 Z M20 -40 C23 -35 25 -30 26 -25 C22 -28 19 -30 16 -33 Z" fill="{BLACK}"/>
          <path d="M-21 -8 C-23 -17 -22 -25 -19.5 -31 C-14 -26 -11 -20 -9 -16 Z M21 -8 C23 -17 22 -25 19.5 -31 C14 -26 11 -20 9 -16 Z" fill="#f5e3d2"/>
          {shape('M-27 0 C-27 -12 -16 -20 0 -20 C16 -20 27 -12 27 0 C26 8 18 14 12 18 L0 23 L-12 18 C-18 14 -26 8 -27 0 Z', 'url(#sbFoxHead)', OUT)}
          <!-- white cheeks and muzzle -->
          {tufts('M-27 3 C-22 4 -16 5 -12 7 C-10 13 -6 19 0 22 C-8 20 -18 15 -27 3 Z', WHITE, '#c8b6a2', pick=lambda x, y: x < -14, every=4, ln=(2.4, 3.6), seed=14)}
          <path d="M-27 3 C-20 5 -14 4 -8 6 C-4 4 4 4 8 6 C14 4 20 5 27 3 C24 12 14 20 0 23 C-14 20 -24 12 -27 3 Z" fill="{WHITE}"/>
          <path d="M-14 -6 C-13 -9 -11 -11 -9 -12 M14 -6 C13 -9 11 -11 9 -12" stroke="#b9541b" stroke-width="1.3" fill="none" stroke-linecap="round" opacity=".7"/>
          <g class="iris"><circle cx="-11" cy="-5" r="4" fill="#d79a2c"/><circle cx="11" cy="-5" r="4" fill="#d79a2c"/><circle cx="-11" cy="-5" r="4" fill="none" stroke="#7a4c10" stroke-width=".8"/><circle cx="11" cy="-5" r="4" fill="none" stroke="#7a4c10" stroke-width=".8"/></g>
          <path d="M-3.4 3 C-3.4 1 3.4 1 3.4 3 C3.4 5.4 1.6 6.8 0 7 C-1.6 6.8 -3.4 5.4 -3.4 3 Z" fill="{BLACK}"/>
          @@FACE@@
          {whiskers('#3a2a22', .45, .85)}
        </g>'''
    back = f'''
        {SOFT_SHADOW(124, 148, 114, 8, .22)}
        <path d="M8 146 C14 132 50 126 96 126 C150 126 214 128 234 140 C238 148 228 152 214 152 L28 152 C14 152 6 150 8 146 Z" fill="url(#sbMoss)" stroke="#3b4a24" stroke-width="1.2" stroke-opacity=".7"/>
        <path d="M24 136 c2 -5 5 -8 8 -9 M40 133 c1 -5 3 -8 6 -9 M206 135 c1 -5 3 -8 6 -9 M222 138 c1 -5 4 -7 7 -8" stroke="#a6bd6a" stroke-width="1.4" stroke-linecap="round" fill="none"/>
        <circle cx="34" cy="142" r="2.2" fill="#f1e2a6"/><circle cx="218" cy="144" r="1.8" fill="#e9b7c4"/>'''
    return back, float, ''

# ================================================================ RED PANDA: lying along a branch, legs dangling, ringed tail hanging
def redpanda():
    OUT, BLACK, WHITE = '#4e1c0c', '#2a1410', '#f6efe6'
    body = 'M60 122 C54 106 68 92 96 88 C126 84 160 86 178 96 C190 104 190 118 184 126 C150 130 92 130 60 122 Z'
    tail = 'M66 116 C50 118 38 128 32 142 C28 152 30 162 34 168 L48 168 C44 160 44 150 48 142 C54 132 62 126 72 124 Z'
    leg1 = 'M162 120 C160 130 162 140 164 150 C168 155 178 155 178 148 C176 138 176 128 178 120 Z'
    leg2 = 'M82 120 C80 130 80 140 82 148 C86 153 95 153 95 146 C93 136 93 128 95 120 Z'
    rings = ''.join(f'<path d="M{30 + i * .4:.1f} {128 + i * 8} C{38 + i * .4:.1f} {131 + i * 8} {46 + i * .3:.1f} {130 + i * 8} {52 - i * .6:.1f} {126 + i * 8}" stroke="#ecb27c" stroke-width="3.6" fill="none" opacity=".9"/>' for i in range(5))
    float = f'''
        {SOFT_SHADOW(124, 126, 72, 6, .3)}
        <g class="alert-tail" style="transform-origin:66px 120px">
          {tufts(tail, 'url(#sbRp)', OUT, every=8, seed=15)}
          {shape(tail, 'url(#sbRp)', OUT)}
          {rings}
          <path d="M34 168 L48 168 C46 164 46 160 47 156 C42 158 37 160 33 162 Z" fill="#5a2210"/>
        </g>
        {shape(leg2, 'url(#sbLimb)', '#120806')}
        
        {shape(body, 'url(#sbRp)', OUT)}
        <path d="M66 118 C100 124 150 124 182 118 C180 124 176 127 168 128 C140 131 96 131 66 124 Z" fill="{BLACK}" opacity=".85"/>
        {hatch(body, '#7a2a14', 14, lambda x, y: math.pi * .56, seed=17, pick=lambda x, y: y < 114)}
        <path d="M74 98 C94 90 126 87 160 90" stroke="#f4a37a" stroke-width="2" stroke-opacity=".55" fill="none" stroke-linecap="round"/>
        {shape(leg1, 'url(#sbLimb)', '#120806')}
        <g transform="translate(196 82) rotate(4)">
          {SOFT_SHADOW(-4, 19, 20, 5, .3)}
          <!-- round ears, white rims, dark insides -->
          {shape('M-26 -4 C-30 -15 -27 -26 -19 -29 C-13 -27 -9 -21 -6 -16 Z', WHITE, '#b7a796', 1)}
          {shape('M26 -4 C30 -15 27 -26 19 -29 C13 -27 9 -21 6 -16 Z', WHITE, '#b7a796', 1)}
          <path d="M-22 -8 C-25 -15 -24 -22 -19 -25 C-14 -23 -11 -19 -9 -15 Z M22 -8 C25 -15 24 -22 19 -25 C14 -23 11 -19 9 -15 Z" fill="#7a2a18"/>
          {tufts('M-26 2 C-26 -12 -14 -20 0 -20 C14 -20 26 -12 26 2 C25 13 14 20 0 20 C-14 20 -25 13 -26 2 Z', 'url(#sbRpHead)', OUT, pick=lambda x, y: y > 2, every=5, ln=(2.4, 3.6), seed=18)}
          {shape('M-26 2 C-26 -12 -14 -20 0 -20 C14 -20 26 -12 26 2 C25 13 14 20 0 20 C-14 20 -25 13 -26 2 Z', 'url(#sbRpHead)', OUT)}
          <!-- white face markings: muzzle, cheek patches, eyebrows; dark tear marks -->
          <ellipse cx="0" cy="10" rx="11" ry="9" fill="{WHITE}"/>
          <ellipse cx="-18.5" cy="5" rx="6.6" ry="6.2" fill="{WHITE}"/><ellipse cx="18.5" cy="5" rx="6.6" ry="6.2" fill="{WHITE}"/>
          <ellipse cx="-11" cy="-13" rx="4.4" ry="2.8" fill="{WHITE}"/><ellipse cx="11" cy="-13" rx="4.4" ry="2.8" fill="{WHITE}"/>
          <path d="M-11 -1 C-12 4 -13 10 -15 15 M11 -1 C12 4 13 10 15 15" stroke="#7a2a18" stroke-width="3" stroke-linecap="round" fill="none" opacity=".85"/>
          <path d="M-4.4 2 C-4.4 -.2 4.4 -.2 4.4 2 C4.4 4.6 2 6.6 0 7 C-2 6.6 -4.4 4.6 -4.4 2 Z" fill="{BLACK}"/>
          @@FACE@@
          {whiskers('#fffaf2', .75, .75)}
        </g>'''
    back = f'''
        <path d="M-10 120 C60 114 160 114 250 122 L250 142 C160 136 60 136 -10 142 Z" fill="url(#sbBark)" stroke="#2e1f14" stroke-width="1.2" stroke-opacity=".75"/>
        <path d="M6 126 C40 123 70 124 96 126 M110 129 C140 127 170 127 200 130 M20 134 C50 132 80 132 104 134 M150 135 C180 134 210 135 236 137" stroke="#2e1f14" stroke-width=".9" fill="none" opacity=".5" stroke-linecap="round"/>
        <path d="M118 118 c8 -4 18 -4 26 0 c-6 4 -18 4 -26 0z M28 122 c6 -3 12 -3 16 0 c-4 3 -12 3 -16 0z" fill="#7d9a42" stroke="#46591f" stroke-width=".8"/>'''
    return back, float, ''

# ================================================================ TIGER CUB: lying on a warm rock, big paws out in front
def tiger():
    OUT, WHITE, STRIPE = '#6b3410', '#fcf3e6', '#2a1a10'
    body = 'M62 132 C54 112 66 92 96 86 C128 80 162 83 182 94 C196 102 199 120 193 133 Z'
    tail = 'M66 128 C74 142 116 146 156 142 C166 141 175 138 180 133 C172 135 160 136 150 136 C116 138 86 135 74 123 Z'
    st = lambda x, y, h, w: f'<path d="M{x} {y} C{x - w} {y + h * .35:.1f} {x + w * .4:.1f} {y + h * .7:.1f} {x - w * .5:.1f} {y + h} C{x + w * .9:.1f} {y + h * .65:.1f} {x + w * .6:.1f} {y + h * .3:.1f} {x + w} {y} Z" fill="{STRIPE}"/>'
    stripes = ''.join(st(x, y, h, w) for x, y, h, w in [(86, 92, 22, 4), (100, 88, 26, 4.6), (115, 86, 24, 4), (130, 85, 27, 4.6), (145, 86, 24, 4), (159, 89, 22, 4.2), (172, 94, 16, 3.4)])
    float = f'''
        {SOFT_SHADOW(130, 139, 84, 9)}
        
        {shape(body, 'url(#sbTig)', OUT)}
        {stripes}
        <path d="M70 128 C100 135 160 135 190 128 C186 134 170 137 128 137 C96 137 78 134 70 128 Z" fill="{WHITE}"/>
        <path d="M78 98 C98 88 130 84 166 88" stroke="#ffd9a8" stroke-width="2.2" stroke-opacity=".6" fill="none" stroke-linecap="round"/>
        <g class="alert-tail" style="transform-origin:68px 126px">
          {shape(tail, 'url(#sbTig)', OUT)}
          <path d="M92 136 l2 6 M110 138 l1.6 6 M128 139 l1 5.6 M146 139 l.6 5" stroke="{STRIPE}" stroke-width="3.6" stroke-linecap="round"/>
          <path d="M168 134 C174 133 178 133 180 133 C176 137 170 139 164 140 Z" fill="{STRIPE}"/>
        </g>
        <!-- big front paws -->
        {shape('M164 134 C164 127 172 125 178 126 C184 127 187 132 185 136 C180 139 168 139 164 134 Z', WHITE, '#bb946c', 1)}
        {shape('M185 133 C185 126 193 124 199 125 C205 126 208 131 206 135 C201 138 189 138 185 133 Z', WHITE, '#bb946c', 1)}
        <path d="M169.5 135 v-3 M174.5 135.6 v-3.2 M179.5 135 v-3 M191 134 v-3 M196 134.6 v-3.2 M201 134 v-3" stroke="#bb946c" stroke-width=".8" stroke-linecap="round"/>
        {shape('M168 98 C184 100 196 112 198 128 C188 132 176 131 170 126 C166 116 164 106 168 98 Z', WHITE, '#c9a888', 1)}
        <g transform="translate(196 80) rotate(4)">
          {SOFT_SHADOW(-6, 21, 24, 5, .3)}
          <!-- round ears: dark backs with a white spot, pale insides -->
          <circle cx="-20" cy="-17" r="8.4" fill="url(#sbTigHead)" stroke="{STRIPE}" stroke-width="2.2"/><circle cx="20" cy="-17" r="8.4" fill="url(#sbTigHead)" stroke="{STRIPE}" stroke-width="2.2"/>
          <circle cx="-19" cy="-15.8" r="4.6" fill="#f6e3cf"/><circle cx="19" cy="-15.8" r="4.6" fill="#f6e3cf"/>
          <path d="M-21 -14 l-1.6 -3.4 M-18.6 -14.6 l-.4 -3.6 M21 -14 l1.6 -3.4 M18.6 -14.6 l.4 -3.6" stroke="#fffaf3" stroke-width=".8" stroke-linecap="round"/>
          {tufts('M-28 4 C-29 -10 -17 -20 0 -20 C17 -20 29 -10 28 4 C27 14 15 22 0 22 C-15 22 -27 14 -28 4 Z', 'url(#sbTigHead)', OUT, pick=lambda x, y: y > 0 and abs(x) > 15, every=4, ln=(3, 5), seed=20)}
          {shape('M-28 4 C-29 -10 -17 -20 0 -20 C17 -20 29 -10 28 4 C27 14 15 22 0 22 C-15 22 -27 14 -28 4 Z', 'url(#sbTigHead)', OUT)}
          <!-- forehead and cheek stripes -->
          <path d="M0 -20 L0 -13 M-4.6 -19 L-3.4 -14 M4.6 -19 L3.4 -14 M-9 -17.5 L-6.6 -14.2 M9 -17.5 L6.6 -14.2" stroke="{STRIPE}" stroke-width="2" stroke-linecap="round"/>
          <path d="M-28 -2 C-24 -3 -21 -3 -18 -2 M-28 4 C-24 3 -21 3 -18.5 4 M28 -2 C24 -3 21 -3 18 -2 M28 4 C24 3 21 3 18.5 4" stroke="{STRIPE}" stroke-width="2" stroke-linecap="round" fill="none"/>
          <!-- white cheeks, muzzle and eyebrow spots -->
          <path d="M-24 8 C-22 4 -16 3 -10 5 C-6 3 6 3 10 5 C16 3 22 4 24 8 C22 16 12 22 0 22 C-12 22 -22 16 -24 8 Z" fill="{WHITE}"/>
          <ellipse cx="-10" cy="-12" rx="3.6" ry="2.2" fill="{WHITE}"/><ellipse cx="10" cy="-12" rx="3.6" ry="2.2" fill="{WHITE}"/>
          <g fill="#b89a7c" opacity=".7"><circle cx="-6.5" cy="9.4" r=".55"/><circle cx="-8.8" cy="11.2" r=".55"/><circle cx="-5" cy="12" r=".55"/><circle cx="6.5" cy="9.4" r=".55"/><circle cx="8.8" cy="11.2" r=".55"/><circle cx="5" cy="12" r=".55"/></g>
          <g class="iris"><circle cx="-11" cy="-5" r="4.2" fill="#e2aa3c"/><circle cx="11" cy="-5" r="4.2" fill="#e2aa3c"/><circle cx="-11" cy="-5" r="4.2" fill="none" stroke="#8a5a16" stroke-width=".8"/><circle cx="11" cy="-5" r="4.2" fill="none" stroke="#8a5a16" stroke-width=".8"/></g>
          <path d="M-16.5 -3.5 C-15 -1 -12 0 -8.5 -1.5 M16.5 -3.5 C15 -1 12 0 8.5 -1.5" stroke="{STRIPE}" stroke-width=".9" fill="none" opacity=".6"/>
          <path d="M-4 3 C-4 1.2 4 1.2 4 3 L0.7 7 C0.35 7.4 -0.35 7.4 -0.7 7 Z" fill="#e3938c" stroke="#a5605d" stroke-width=".5"/>
          @@FACE@@
          {whiskers()}
        </g>'''
    back = f'''
        {SOFT_SHADOW(124, 148, 114, 8, .25)}
        <path d="M14 141 C18 125 50 117 96 116 C150 115 206 119 228 129 C236 134 234 143 224 147 C170 153 70 153 22 148 C14 147 12 144 14 141 Z" fill="url(#sbRock)" stroke="#4f463c" stroke-width="1.2" stroke-opacity=".75"/>
        <path d="M30 125 C70 119 160 118 214 125" stroke="#e2d8ca" stroke-width="1.8" stroke-opacity=".7" fill="none" stroke-linecap="round"/>
        <path d="M60 139 C70 135 84 134 92 137 M150 141 C162 138 178 138 188 141" stroke="#4f473e" stroke-width=".9" fill="none" opacity=".5" stroke-linecap="round"/>
        <path d="M8 147 c2 -10 4 -16 6 -20 c0 6 0 12 -2 20z M16 147 c1 -8 4 -13 7 -16 c-2 6 -3 11 -3 16z M226 147 c1 -9 3 -14 6 -18 c-1 6 -1 12 -2 18z M233 147 c2 -7 5 -11 8 -13 c-3 5 -4 9 -4 13z" fill="#7a9a3e" stroke="#46591f" stroke-width=".7"/>'''
    return back, float, ''

# ================================================================ SEA OTTER: floating on its back, holding a clam
def otter():
    OUT, FLIP = '#2c1a10', 'url(#sbOtterFlip)'
    body = 'M52 115 C58 99 84 90 116 88 C140 86 162 85 178 90 C192 93 206 102 209 112 C211 122 205 132 194 134 C150 140 92 140 54 132 Z'
    chest = 'M118 90 C142 85 164 84 178 89 C194 93 204 101 205 112 C180 111 150 106 124 100 Z'
    float = f'''
        <!-- reflection / shadow on the water -->
        <ellipse cx="112" cy="124" rx="78" ry="7" fill="#123a4d" opacity=".3"/>
        {shape('M58 113 C44 108 26 109 12 115 C10 118 14 121 22 121 C34 122 48 121 60 120 Z', 'url(#sbOtter)', OUT)}
        <g class="feet">
          {shape('M66 107 C62 99 56 91 51 84 C49 78 54 72 61 72 C68 72 74 75 76 80 C76 88 74 97 74 106 Z', FLIP, '#120a06', 1)}
          {shape('M81 105 C80 97 78 89 76 80 C75 73 82 68 90 68 C98 68 104 71 103 77 C100 86 95 96 92 106 Z', FLIP, '#120a06', 1)}
          <path d="M57 74 C61 83 65 93 69 102 M66 73 C68 82 70 92 71 102 M84 70 C85 80 86 91 87 102 M95 69 C93 79 91 90 89 102" stroke="#5a3a28" stroke-width=".8" fill="none" opacity=".7" stroke-linecap="round"/>
        </g>
        {tufts(body, 'url(#sbOtter)', OUT, pick=lambda x, y: y > 128 or (y < 100 and x < 120), every=9, seed=21)}
        {shape(body, 'url(#sbOtter)', OUT)}
        {hatch(body, '#3e2416', 22, lambda x, y: 0.05, seed=22, pick=lambda x, y: x < 170)}
        {tufts(chest, 'url(#sbOtterChest)', '#8a6a4c', pick=lambda x, y: y > 102, every=6, ln=(2, 3.4), seed=23)}
        {shape(chest, 'url(#sbOtterChest)', '#8a6a4c', 1)}
        <path d="M64 101 C84 92 112 89 140 89" stroke="#d9bfa2" stroke-width="2.4" stroke-opacity=".5" fill="none" stroke-linecap="round"/>
        <path d="M58 106 C66 96 88 90 116 89 C140 87 162 86 177 91 C190 94 200 100 203 108" stroke="#cfe6f2" stroke-opacity=".4" stroke-width="1.4" fill="none" stroke-linecap="round"/>
        <!-- clam held on the chest -->
        <g transform="translate(151 79) rotate(-12)">
          <path d="M0 13 C-1 4 6 -2 13 -2 C20 -2 27 4 26 13 C20 16 6 16 0 13 Z" fill="url(#sbShell)" stroke="#8d7d70" stroke-width="1"/>
          <path d="M3 12 C4 6 8 2 13 1 M8 13 C8 7 10 3 13 1 M13 14 L13 1 M18 13 C18 7 16 3 13 1 M23 12 C22 6 18 2 13 1" stroke="#a6958a" stroke-width=".7" fill="none"/>
        </g>
        <g class="rest-arm">
          <g transform="translate(150 92)">{shape('M-6 3 C-7 -2 -4 -5.5 0 -5.5 C4 -5.5 6.5 -2.5 5.5 2 C4.5 5 -4 6 -6 3 Z', '#3d2519', '#140a06', 1)}</g>
        </g>
        <g transform="translate(176 91)">{shape('M-6 3 C-7 -2 -4 -5.5 0 -5.5 C4 -5.5 6.5 -2.5 5.5 2 C4.5 5 -4 6 -6 3 Z', '#3d2519', '#140a06', 1)}</g>
        <g class="wave-arm">
          {shape('M139 100 C134 88 133 74 137 62 L148 63 C146 75 148 88 153 98 Z', '#3b2318', '#140a06', 1)}
          {shape('M134 60 C132 52 138 46 144 46 C151 46 154 53 152 59 C150 64 138 66 134 60 Z', '#2b1810', '#0a0503', 1)}
        </g>
        <g transform="translate(197 84) rotate(8)">
          <ellipse cx="-8" cy="17" rx="22" ry="6" fill="#1a0e08" opacity=".25"/>
          {shape('M-26.6 -10 C-28 -14 -24 -17 -21 -15 C-19 -13 -20 -9 -23 -8 Z', '#6a4a33', OUT, 1)}
          {shape('M26.6 -10 C28 -14 24 -17 21 -15 C19 -13 20 -9 23 -8 Z', '#6a4a33', OUT, 1)}
          {tufts('M-27 2 C-28 -12 -15 -20 0 -20 C15 -20 28 -12 27 2 C26 14 15 21 0 21 C-15 21 -26 14 -27 2 Z', 'url(#sbOtterHead)', '#7a5c40', every=5, ln=(2.2, 3.6), seed=24)}
          {shape('M-27 2 C-28 -12 -15 -20 0 -20 C15 -20 28 -12 27 2 C26 14 15 21 0 21 C-15 21 -26 14 -27 2 Z', 'url(#sbOtterHead)', '#7a5c40')}
          <ellipse cx="-11" cy="-5" rx="5.6" ry="4.2" fill="#9d7e60" opacity=".45"/><ellipse cx="11" cy="-5" rx="5.6" ry="4.2" fill="#9d7e60" opacity=".45"/>
          <ellipse cx="-5.5" cy="9" rx="7.8" ry="6" fill="#f1e6d4"/><ellipse cx="5.5" cy="9" rx="7.8" ry="6" fill="#f1e6d4"/>
          <g fill="#9c8670" opacity=".7"><circle cx="-9" cy="8" r=".6"/><circle cx="-6" cy="10" r=".6"/><circle cx="-10" cy="11" r=".6"/><circle cx="9" cy="8" r=".6"/><circle cx="6" cy="10" r=".6"/><circle cx="10" cy="11" r=".6"/></g>
          <path d="M-8.5 1 C-7.5 -2.2 7.5 -2.2 8.5 1 C8.5 4.6 4.2 6.8 0 7 C-4.2 6.8 -8.5 4.6 -8.5 1 Z" fill="#2a1d18"/>
          <ellipse cx="-3" cy="0.6" rx="2.6" ry="1" fill="#fff" opacity=".3"/>
          @@FACE@@
          {whiskers('#f3ede2', .85, 1.0, 1)}
        </g>'''
    return None, float, None      # the otter keeps its animated water (back/front) from the page

ANIMALS = {'otter': otter, 'cat': cat, 'dog': dog, 'fox': fox, 'redpanda': redpanda, 'tiger': tiger}

# ================================================================ WALKING POSES (side view, leg rig used by the motion engine)
WALKERS = {
    'cat': dict(body='M58 96 C60 80 82 74 110 74 C140 74 166 76 180 86 C190 94 189 110 178 117 C150 123 92 123 68 117 C56 113 55 104 58 96 Z',
                fill='url(#sbCat)', out='#7a3f17', leg='url(#sbCat)', farleg='#c06d2c', paw='#fbeedd', legLen=40, hipY=108, hips=(76, 90, 160, 172),
                tail='M62 90 C44 84 32 70 34 52 C35 45 42 44 43 51 C42 66 50 78 66 84 Z', tailFill='url(#sbCat)',
                belly=('M66 112 C90 120 150 120 176 112 C172 118 160 122 150 122 L92 122 C80 122 70 118 66 112 Z', '#fbeedd'),
                marks=''.join(f'<path d="M{x} 76 C{x - 4} 84 {x - 1} 92 {x - 5} 100 C{x} 92 {x + 3} 84 {x + 4} 76 Z" fill="#b55f27" opacity=".75"/>' for x in (86, 102, 118, 134, 150)),
                tailMarks='<path d="M36 60 l6 1 M37 70 l6 -1 M42 79 l5 -3" stroke="#b55f27" stroke-width="3" stroke-linecap="round" opacity=".75"/>',
                neck='M156 98 C158 82 170 66 186 62 C199 59 206 72 201 86 C195 100 176 108 160 106 Z', neckFill='url(#sbCat)', head=(0, -22)),
    'dog': dict(body='M56 98 C58 80 80 74 110 74 C140 74 166 76 180 86 C191 95 190 112 178 118 C150 124 92 124 66 118 C55 114 54 106 56 98 Z',
                fill='url(#sbDog)', out='#5e3a1c', leg='#f8f1e6', farleg='#d9cbb7', paw='#f8f1e6', legLen=40, hipY=110, hips=(74, 88, 160, 173),
                tail='M60 90 C46 80 40 64 46 52 C48 47 53 48 52 54 C50 66 56 78 66 84 Z', tailFill='url(#sbDog)',
                belly=('M64 112 C90 121 150 121 178 112 C172 119 160 123 150 123 L92 123 C80 123 70 119 64 112 Z', '#f8f1e6'),
                marks='<path d="M70 86 C92 76 126 74 156 78 C150 88 130 94 106 94 C90 94 76 92 70 86 Z" fill="#6a4122" opacity=".9"/>',
                tailMarks='<path d="M46 52 C47 48 52 48 52 53 C51 56 47 56 46 52 Z" fill="#f8f1e6"/>',
                neck='M156 98 C158 82 170 66 187 62 C200 59 207 72 202 86 C196 100 177 108 160 106 Z', neckFill='#f8f1e6', head=(-2, -24)),
    'fox': dict(body='M58 96 C60 80 82 74 110 74 C140 74 166 76 180 86 C190 94 189 110 178 117 C150 123 92 123 68 117 C56 113 55 104 58 96 Z',
                fill='url(#sbFox)', out='#6e2e0c', leg='#2a1a14', farleg='#1d120d', paw='#1d120d', legLen=40, hipY=108, hips=(76, 90, 160, 172),
                tail='M62 100 C42 100 20 110 10 126 C8 134 16 136 24 131 C36 122 50 114 64 108 Z', tailFill='url(#sbFox)',
                belly=('M150 112 C162 116 172 114 178 110 C176 116 170 120 160 121 C154 120 150 117 150 112 Z', '#fbf3ea'),
                marks='', tailMarks='<path d="M10 126 C8 134 16 136 24 131 C20 128 16 124 14 120 C12 122 11 124 10 126 Z" fill="#fbf3ea"/>',
                neck='M156 98 C158 82 170 66 186 62 C199 59 206 72 201 86 C195 100 176 108 160 106 Z', neckFill='#fbf3ea', head=(0, -22)),
    'redpanda': dict(body='M58 96 C60 80 82 74 110 74 C140 74 166 76 180 86 C190 94 189 110 178 117 C150 123 92 123 68 117 C56 113 55 104 58 96 Z',
                fill='url(#sbRp)', out='#4e1c0c', leg='url(#sbLimb)', farleg='#1c0d0a', paw='#1c0d0a', legLen=38, hipY=110, hips=(76, 90, 160, 172),
                tail='M62 94 C42 94 22 100 10 114 C6 120 10 126 16 122 C28 112 46 106 64 104 Z', tailFill='url(#sbRp)',
                belly=('M66 110 C92 118 150 118 178 110 C174 117 162 122 150 122 L92 122 C80 122 70 117 66 110 Z', '#2a1410'),
                marks='', tailMarks=''.join(f'<path d="M{50 - i * 9} {98 + i * 3.4:.0f} l{-1 - i * .6:.1f} {7 - i * .4:.1f}" stroke="#ecb27c" stroke-width="3.6" stroke-linecap="round"/>' for i in range(4)),
                neck='M156 98 C158 82 170 66 186 62 C199 59 206 72 201 86 C195 100 176 108 160 106 Z', neckFill='url(#sbRp)', head=(0, -22)),
    'tiger': dict(body='M56 96 C58 79 82 72 110 72 C140 72 166 75 181 85 C192 94 191 111 179 118 C150 124 92 124 67 118 C55 114 53 105 56 96 Z',
                fill='url(#sbTig)', out='#6b3410', leg='url(#sbTig)', farleg='#c4651c', paw='#fcf3e6', legLen=38, hipY=109, pawR=7.6, hips=(76, 90, 160, 172),
                tail='M62 90 C44 94 30 106 24 122 C21 131 25 138 32 134 C34 122 44 106 64 99 Z', tailFill='url(#sbTig)',
                belly=('M66 112 C90 121 150 121 178 112 C172 119 160 123 150 123 L92 123 C80 123 70 119 66 112 Z', '#fcf3e6'),
                marks=''.join(f'<path d="M{x} 73 C{x - 4} 82 {x + 2} 92 {x - 3} {100 + (x % 3)} C{x + 3} 92 {x + 1} 82 {x + 4} 73 Z" fill="#2a1a10"/>' for x in range(74, 176, 12)),
                tailMarks='<path d="M50 96 l3 6 M40 104 l5 4 M32 113 l6 2 M26 124 l6 1" stroke="#2a1a10" stroke-width="3.4" stroke-linecap="round"/><path d="M24 122 C21 131 25 138 32 134 C30 130 28 126 27 121 Z" fill="#2a1a10"/>',
                neck='M156 98 C158 82 170 66 186 62 C199 59 206 72 201 86 C195 100 176 108 160 106 Z', neckFill='#fcf3e6', head=(0, -22)),
    'otter': dict(body='M40 112 C44 98 70 92 110 92 C150 92 176 96 186 106 C192 116 186 126 170 128 C130 132 80 132 52 126 C42 122 38 118 40 112 Z',
                fill='url(#sbOtter)', out='#2c1a10', leg='#3b2318', farleg='#2a1810', paw='#2b1810', legLen=22, hipY=124, hips=(66, 80, 156, 168),
                tail='M44 114 C30 114 14 118 4 125 C12 130 30 130 46 123 Z', tailFill='url(#sbOtter)',
                belly=('M150 102 C166 104 180 108 186 114 C184 122 176 126 166 127 C160 118 154 110 150 102 Z', '#cdb391'),
                marks='', tailMarks='',
                neck='M162 104 C168 96 180 92 192 94 C200 98 202 108 196 116 C188 122 172 122 162 116 Z', neckFill='#cdb391', head=(2, 12)),
}

def walker(name):
    w = WALKERS[name]; L = w['legLen']; OUT = w['out']
    def leg(x, color, phase, far, front):
        U = round(L * .52); D = L - U
        paw = w['paw'] if not far else color
        pr = w.get('pawR', 6)
        return (f'<g class="leg" transform="translate({x} {w["hipY"]})"><g class="swing" data-phase="{phase}" data-len="{L}" data-front="{1 if front else 0}">'
                f'<path d="M-8.6 -6 C-9.2 {U*.5:.0f} -6.4 {U-1} -5.4 {U+2} L5.4 {U+2} C6.4 {U-1} 8.8 {U*.5:.0f} 8.2 -6 Z" fill="{color}" stroke="{OUT}" stroke-width="1" stroke-opacity=".6" stroke-linejoin="round"/>'
                f'<g transform="translate(0 {U})"><g class="shin">'
                f'<path d="M-5.4 -3 C-5.8 {D*.5:.0f} -4.5 {D*.9:.0f} -4 {D} L4 {D} C4.5 {D*.9:.0f} 5.8 {D*.5:.0f} 5.4 -3 Z" fill="{color}" stroke="{OUT}" stroke-width="1" stroke-opacity=".6" stroke-linejoin="round"/>'
                f'<ellipse cx="1.5" cy="{D+1}" rx="{pr}" ry="{pr * .53:.1f}" fill="{paw}" stroke="{OUT}" stroke-width=".9" stroke-opacity=".55"/></g></g></g></g>')
    b1, b2, f1, f2 = w['hips']
    ground = w['hipY'] + L + 2
    bd, bc = w['belly']
    return (f'<g class="walker">'
            f'<ellipse class="wshadow" cx="118" cy="{ground}" rx="72" ry="4.5" fill="url(#sbShadow)" opacity="1"/>'
            f'<g class="wmove"><g class="wtail">{shape(w["tail"], w["tailFill"], OUT)}{w["tailMarks"]}</g>'
            + leg(b2, w['farleg'], 3.14, True, False) + leg(f2, w['farleg'], 0, True, True) +
            f'<g class="wbody">{shape(w["body"], w["fill"], OUT)}<path d="{bd}" fill="{bc}" opacity=".95"/>{w["marks"]}'
            f'{hatch(w["body"], "#000", 14, lambda x, y: math.pi * .55, op=.12, seed=31, pick=lambda x, y: y < 108)}</g>'
            + leg(b1, w['leg'], 0, False, False) + leg(f1, w['leg'], 3.14, False, True) +
            f'<g class="wfront">{shape(w["neck"], w["neckFill"], OUT, 1)}'
            f'@@HEAD@@</g></g></g>')
