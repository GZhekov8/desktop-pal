"""Cute chibi artwork for all six pets (resting pose + walking pose).

Big round heads, small soft bodies, short stubby legs and large glossy eyes, drawn with clean
shapes, soft gradients and a warm outline in each animal's own colour. No filters, so it is cheap
to draw and animates smoothly.

Every head uses the same local face coordinates (eyes at x=+-12.5, y=1; nose ~y=6..10; mouth
below), so the shared expressions in FACE fit every animal. Heads are placed with
<g class="headpos" transform="translate(x y) ...">, which build.py looks for."""

import re

# ---------------------------------------------------------------- drawing helpers
def S(d, fill, line, w=1.8, extra=''):
    return f'<path d="{d}" fill="{fill}" stroke="{line}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{extra}/>'

def mirror(d):
    """mirror a path drawn on the left side (negative x) to the right side"""
    out, cmd, n = [], '', 0
    for tok in re.findall(r'[A-Za-z]|-?\d*\.?\d+', d):
        if tok.isalpha(): cmd, n = tok, 0; out.append(tok); continue
        v = float(tok)
        if (cmd in 'MLCQST' and n % 2 == 0) or cmd == 'H': v = -v
        out.append(f'{v:g}'); n += 1
    return ' '.join(out)

def both(d, fill, line, w=1.8):
    return S(d, fill, line, w) + S(mirror(d), fill, line, w)

def grad(id, stops, x2=0, y2=1, radial=False, cx=.5, cy=.4, r=.65, fx=None, fy=None):
    st = ''.join(f'<stop offset="{s[0]}" stop-color="{s[1]}"' + (f' stop-opacity="{s[2]}"' if len(s) > 2 else '') + '/>' for s in stops)
    if radial:
        f = f' fx="{fx}" fy="{fy}"' if fx is not None else ''
        return f'<radialGradient id="{id}" cx="{cx}" cy="{cy}" r="{r}"{f}>{st}</radialGradient>'
    return f'<linearGradient id="{id}" x1="0" y1="0" x2="{x2}" y2="{y2}">{st}</linearGradient>'

def body_grad(id, top, mid, bot): return grad(id, [(0, top), (.55, mid), (1, bot)])
def head_grad(id, hi, mid, edge): return grad(id, [(0, hi), (.62, mid), (1, edge)], radial=True, cx=.42, cy=.36, r=.72)

SHADOW = lambda cx, cy, rx, ry, op=1: f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#cbShadow)" opacity="{op}"/>'
SHINE = '<ellipse cx="-13" cy="-15" rx="10" ry="5.5" fill="#fff" opacity=".26" transform="rotate(-24 -13 -15)"/>'
CHEEKS = '<ellipse cx="-20" cy="10" rx="5.4" ry="3.2" fill="#ff8e86" opacity=".28"/><ellipse cx="20" cy="10" rx="5.4" ry="3.2" fill="#ff8e86" opacity=".28"/>'

DEFS = ''.join([
    grad('cbShadow', [(0, '#1b130c', .32), (1, '#1b130c', 0)], radial=True, cy=.5, r=.5),
    grad('cbShine', [(0, '#fff', .5), (1, '#fff', 0)]),
    body_grad('cbCat', '#f9c486', '#f1a05a', '#d97c3a'), head_grad('cbCatH', '#ffd6a2', '#f4a862', '#de8240'),
    grad('cbCushion', [(0, '#a9cbd6'), (1, '#6b93a3')]),
    body_grad('cbDog', '#ecc391', '#dba56b', '#bd844b'), head_grad('cbDogH', '#f6d4a6', '#e2ad72', '#c48a50'),
    body_grad('cbDogEar', '#a96d3f', '#8a5430', '#6a3e22'),
    grad('cbBed', [(0, '#e7a7a0'), (1, '#b86d6a')]), grad('cbBedIn', [(0, '#f6efe4'), (1, '#dcd0bf')]),
    body_grad('cbFox', '#f9ae6a', '#f08a3e', '#d3692a'), head_grad('cbFoxH', '#ffc48a', '#f49548', '#d8702e'),
    grad('cbMoss', [(0, '#a3bd68'), (1, '#64803c')]),
    body_grad('cbRp', '#ea8656', '#d76435', '#b44a24'), head_grad('cbRpH', '#f39a6a', '#dc6d3c', '#bb5028'),
    grad('cbBark', [(0, '#9a7656'), (.5, '#7a583c'), (1, '#55392a')]),
    body_grad('cbTig', '#fbbf72', '#f6973d', '#dc7726'), head_grad('cbTigH', '#ffd08e', '#f8a24c', '#e07e2c'),
    grad('cbRock', [(0, '#d4cab9'), (.55, '#aa9d8b'), (1, '#7f7364')]),
    body_grad('cbOtter', '#a07556', '#866044', '#644430'), head_grad('cbOtterH', '#f6ebd8', '#e3cfb2', '#c6ab8a'),
    grad('cbShell', [(0, '#fff8ee'), (1, '#e3d2bf')]),
])

# ---------------------------------------------------------------- the shared face (all expressions)
def _eye(cx, wide=False):
    rx, ry = (5.2, 6.2) if wide else (4.6, 5.4)
    cy = 1
    return (f'<g class="eye"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#24150f"/>'
            f'<ellipse cx="{cx}" cy="{cy + ry * .34:.2f}" rx="{rx * .74:.2f}" ry="{ry * .52:.2f}" fill="var(--iris, #6b4630)" opacity=".95"/>'
            f'<ellipse cx="{cx}" cy="{cy + .2}" rx="{rx * .5:.2f}" ry="{ry * .56:.2f}" fill="#160c08"/>'
            f'<circle cx="{cx + rx * .33:.2f}" cy="{cy - ry * .42:.2f}" r="{rx * .38:.2f}" fill="#fff"/>'
            f'<circle cx="{cx - rx * .36:.2f}" cy="{cy + ry * .46:.2f}" r="{rx * .17:.2f}" fill="#fff" opacity=".85"/>'
            + (f'<circle cx="{cx + rx * .05:.2f}" cy="{cy - ry * .1:.2f}" r=".7" fill="#fff" opacity=".9"/>' if wide else '') + '</g>')

FACE = f'''
          <g class="x x-eyes-open">{_eye(-12.5)}{_eye(12.5)}</g>
          <g class="x x-eyes-wide">{_eye(-12.5, True)}{_eye(12.5, True)}</g>
          <g class="x x-eyes-happy" stroke="#24150f" stroke-width="2.2" stroke-linecap="round" fill="none">
            <path d="M-17 3 C-15.5 -2.6 -9.5 -2.6 -8 3"/><path d="M8 3 C9.5 -2.6 15.5 -2.6 17 3"/>
          </g>
          <g class="x x-eyes-sleepy" stroke="#24150f" stroke-width="2" stroke-linecap="round" fill="none">
            <path d="M-17 1.2 C-15 4.6 -10 4.6 -8 1.2"/><path d="M8 1.2 C10 4.6 15 4.6 17 1.2"/>
            <path d="M-16.4 3.4 l-1.6 1.4 M16.4 3.4 l1.6 1.4" stroke-width="1.3"/>
          </g>
          <g class="x x-eyes-squint">
            <path d="M-17.4 -1.6 L-7.8 .2 C-8 5.6 -17 5.8 -17.4 1 Z" fill="#24150f"/><path d="M17.4 -1.6 L7.8 .2 C8 5.6 17 5.8 17.4 1 Z" fill="#24150f"/>
            <circle cx="-11" cy="2.4" r=".9" fill="#fff" opacity=".8"/><circle cx="14" cy="2.4" r=".9" fill="#fff" opacity=".8"/>
          </g>
          <g stroke="var(--brow, #6b4c36)" stroke-width="2" stroke-linecap="round" fill="none" opacity=".9">
            <g class="x x-brows-up"><path d="M-17 -9 C-15 -11.4 -10.5 -11.6 -8.4 -9.6"/><path d="M17 -9 C15 -11.4 10.5 -11.6 8.4 -9.6"/></g>
            <g class="x x-brows-down"><path d="M-17.5 -8.6 L-8.4 -5.8"/><path d="M17.5 -8.6 L8.4 -5.8"/></g>
            <g class="x x-brows-worried"><path d="M-17 -6.4 L-8.6 -9.4"/><path d="M17 -6.4 L8.6 -9.4"/></g>
          </g>
          <g class="x x-blush" fill="#ff7f86" opacity=".55"><ellipse cx="-20" cy="10" rx="6" ry="3.4"/><ellipse cx="20" cy="10" rx="6" ry="3.4"/></g>
          <g stroke="#3a2420" stroke-width="1.2" fill="none" stroke-linecap="round">
            <path d="M0 9.6 V11.4"/>
            <path class="x x-mouth-neutral" d="M0 11.4 C-1.1 13 -3.2 13.3 -4.8 12.2 M0 11.4 C1.1 13 3.2 13.3 4.8 12.2"/>
            <path class="x x-mouth-flat" d="M-3.8 12.6 C-1.5 12.1 1.5 12.1 3.8 12.6"/>
            <path class="x x-mouth-frown" d="M-4.4 14.4 C-2.4 11.6 2.4 11.6 4.4 14.4"/>
          </g>
          <g class="x x-mouth-smile">
            <path d="M-5.6 11 C-4.2 17.8 4.2 17.8 5.6 11 C3 12.4 -3 12.4 -5.6 11 Z" fill="#4a2018" stroke="#3a2420" stroke-width=".8" stroke-linejoin="round"/>
            <ellipse cx="0" cy="14.8" rx="2.7" ry="1.5" fill="#f08a8e"/>
          </g>
          <g class="x x-mouth-o"><ellipse cx="0" cy="13.6" rx="2.3" ry="2.7" fill="#3b1a14"/><ellipse cx="0" cy="14.8" rx="1.4" ry=".9" fill="#e07a7e"/></g>
          <g class="x x-mouth-yawn"><ellipse cx="0" cy="14.4" rx="3.4" ry="4.2" fill="#3b1a14"/><ellipse cx="0" cy="16.4" rx="2.1" ry="1.4" fill="#e07a7e"/></g>
'''

def whiskers(col='#fffaf2', op=.8, x0=12, x1=30):
    d = ''.join(f'M{-x0} {y0}C{-(x0 + x1) / 2:.1f} {y0 + dy * .4:.1f} {-x1 + 3} {y0 + dy * .8:.1f} {-x1} {y0 + dy}' for y0, dy in ((10, -2), (12, 1), (14, 4)))
    return f'<path d="{d}{mirror(d)}" stroke="{col}" stroke-width=".7" stroke-linecap="round" fill="none" opacity="{op}"/>'

NOSE_PINK = '<path d="M-3 6.6 C-3 5 3 5 3 6.6 C3 8 1.1 9.4 0 9.6 C-1.1 9.4 -3 8 -3 6.6 Z" fill="#f0909a" stroke="#c76574" stroke-width=".7"/><ellipse cx="-1" cy="6.2" rx="1" ry=".5" fill="#fff" opacity=".6"/>'
NOSE_DARK = '<path d="M-4 6 C-4 3.8 4 3.8 4 6 C4 8 1.6 9.5 0 9.7 C-1.6 9.5 -4 8 -4 6 Z" fill="#2c1d18"/><ellipse cx="-1.4" cy="5.2" rx="1.4" ry=".6" fill="#fff" opacity=".45"/>'
ROUND = 'M-31 3 C-31 -15 -17 -26 0 -26 C17 -26 31 -15 31 3 C31 18 17 25 0 25 C-17 25 -31 18 -31 3 Z'
PAWLINES = lambda x, y, c: f'<path d="M{x - 2.6} {y + 2.6} v-2.4 M{x + 2.6} {y + 2.6} v-2.4" stroke="{c}" stroke-width=".9" stroke-linecap="round"/>'

def headpos(x, y, rot, inner):
    return f'<g class="headpos" transform="translate({x} {y}) rotate({rot})">{inner}</g>'

# ================================================================ HEADS (local coords, centre 0,0)
def cat_head():
    OUT, CREAM, STR = '#a3561f', '#fff4e6', '#d9732e'
    ear = 'M-28 -7 C-30 -21 -27 -33 -22 -38 C-15 -34 -10 -28 -7 -24 Z'
    inner = 'M-24.6 -12 C-25.6 -21 -24.2 -28.6 -21.6 -32 C-17.6 -29 -14.4 -25 -12.4 -22 Z'
    head = 'M-31 3 C-31 -15 -17 -26 0 -26 C17 -26 31 -15 31 3 C31 7 34.5 9 33.6 12.2 C31.2 12.4 30.6 14.6 28.8 15.4 C22 22 12 25 0 25 C-12 25 -22 22 -28.8 15.4 C-30.6 14.6 -31.2 12.4 -33.6 12.2 C-34.5 9 -31 7 -31 3 Z'
    return (both(ear, 'url(#cbCatH)', OUT) + S(inner, '#f7b5ae', 'none', 0) + S(mirror(inner), '#f7b5ae', 'none', 0) +
            S(head, 'url(#cbCatH)', OUT, 2) + SHINE +
            f'<path d="M-6 -25 C-5.4 -21 -4.6 -19 -3.4 -16 M0 -26 V-17.4 M6 -25 C5.4 -21 4.6 -19 3.4 -16" stroke="{STR}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'
            f'<path d="M-31.4 1 L-25.4 2 M-31.8 6 L-25.8 6 M31.4 1 L25.4 2 M31.8 6 L25.8 6" stroke="{STR}" stroke-width="2" stroke-linecap="round" fill="none"/>'
            f'<path d="M-11 10.4 C-11 4.6 -5 3.6 0 5.4 C5 3.6 11 4.6 11 10.4 C11 16.4 5.6 19.4 0 19.4 C-5.6 19.4 -11 16.4 -11 10.4 Z" fill="{CREAM}"/>'
            + CHEEKS + NOSE_PINK + '@@FACE@@' + whiskers())

def dog_head():
    OUT, WHITE = '#7a4a26', '#fffaf2'
    ear = 'M-22 -20 C-34 -22 -42 -6 -41 10 C-40 22 -34 28 -27.6 25 C-24.4 15 -22.6 2 -19 -10 Z'
    return (S(ROUND, 'url(#cbDogH)', OUT, 2) + SHINE +
            f'<path d="M-4 -25.6 C-3.4 -16 -6.4 -8 -9.4 -1 C-9 4 9 4 9.4 -1 C6.4 -8 3.4 -16 4 -25.6 C1.4 -26 -1.4 -26 -4 -25.6 Z" fill="{WHITE}"/>'
            f'<path d="M-12.4 10 C-12.4 3.6 -5.4 2.4 0 3.6 C5.4 2.4 12.4 3.6 12.4 10 C12.4 16.6 6.4 20.6 0 20.6 C-6.4 20.6 -12.4 16.6 -12.4 10 Z" fill="{WHITE}"/>'
            + both(ear, 'url(#cbDogEar)', '#5a3418', 1.8) +
            '<path d="M-36 2 C-36.6 10 -35 18 -31 22 M36 2 C36.6 10 35 18 31 22" stroke="#c48a58" stroke-width="1.4" stroke-linecap="round" fill="none" opacity=".6"/>'
            + CHEEKS + NOSE_DARK + '<g fill="#b89a80" opacity=".8"><circle cx="-6" cy="12" r=".7"/><circle cx="-8.4" cy="14.4" r=".7"/><circle cx="6" cy="12" r=".7"/><circle cx="8.4" cy="14.4" r=".7"/></g>' + '@@FACE@@')

def fox_head():
    OUT, WHITE, DARK = '#a84a17', '#fff6ec', '#3a2420'
    ear = 'M-26 -10 C-30 -25 -28 -37 -21 -44 C-13 -38 -8 -30 -5 -24 Z'
    tip = 'M-21 -44 C-24 -40 -26.4 -35 -27.4 -30 C-24 -32 -20.4 -34.6 -16.4 -38.6 Z'
    inner = 'M-22.4 -14 C-24.6 -24 -23.6 -32 -20.6 -37 C-16.4 -33 -13 -28 -11 -24 Z'
    head = 'M-30 -2 C-30 -17 -17 -26 0 -26 C17 -26 30 -17 30 -2 C30 4 33.6 9.6 37 14.4 C27 16.4 17 22 0 24 C-17 22 -27 16.4 -37 14.4 C-33.6 9.6 -30 4 -30 -2 Z'
    low = 'M-37 14.4 C-29 8 -19 6.4 -11 8.4 C-6.4 4 6.4 4 11 8.4 C19 6.4 29 8 37 14.4 C27 16.4 17 22 0 24 C-17 22 -27 16.4 -37 14.4 Z'
    return (both(ear, 'url(#cbFoxH)', OUT) + S(tip, DARK, 'none', 0) + S(mirror(tip), DARK, 'none', 0) + S(inner, '#ffe2cc', 'none', 0) + S(mirror(inner), '#ffe2cc', 'none', 0) +
            S(head, 'url(#cbFoxH)', OUT, 2) + SHINE + S(low, WHITE, 'none', 0) +
            '<path d="M-15 -6 C-14 -9 -12 -11 -9.6 -12 M15 -6 C14 -9 12 -11 9.6 -12" stroke="#c45a1e" stroke-width="1.4" fill="none" stroke-linecap="round" opacity=".7"/>'
            + CHEEKS + NOSE_DARK + '@@FACE@@' + whiskers('#3a2a22', .45, 13, 29))

def redpanda_head():
    OUT, WHITE, DARK = '#86321a', '#fff8f0', '#4a1d12'
    ear = 'M-29 -6 C-33 -18 -29 -30 -21 -34 C-15 -32 -10 -26 -7 -21 Z'
    inner = 'M-25.4 -10 C-28 -18 -26 -26 -21 -29 C-17 -27 -14 -23 -12 -20 Z'
    return (both(ear, WHITE, '#c9b4a4', 1.6) + S(inner, DARK, 'none', 0) + S(mirror(inner), DARK, 'none', 0) +
            S(ROUND, 'url(#cbRpH)', OUT, 2) + SHINE +
            f'<ellipse cx="-12.5" cy="-11.6" rx="5" ry="3" fill="{WHITE}"/><ellipse cx="12.5" cy="-11.6" rx="5" ry="3" fill="{WHITE}"/>'
            f'<ellipse cx="-22" cy="9" rx="8" ry="7.4" fill="{WHITE}"/><ellipse cx="22" cy="9" rx="8" ry="7.4" fill="{WHITE}"/>'
            f'<path d="M-11.4 9.6 C-11.4 4.4 -5 3.4 0 4.6 C5 3.4 11.4 4.4 11.4 9.6 C11.4 16 5.8 19.4 0 19.4 C-5.8 19.4 -11.4 16 -11.4 9.6 Z" fill="{WHITE}"/>'
            '<path d="M-13.4 6 C-14.4 11 -15.2 15 -16.8 19 M13.4 6 C14.4 11 15.2 15 16.8 19" stroke="#9c3a1c" stroke-width="3.4" stroke-linecap="round" fill="none" opacity=".75"/>'
            + CHEEKS + NOSE_DARK + '@@FACE@@' + whiskers('#fffaf2', .7, 12, 28))

def tiger_head():
    OUT, WHITE, STR = '#a3561a', '#fff6ea', '#33201a'
    head = 'M-31 3 C-31 -15 -17 -26 0 -26 C17 -26 31 -15 31 3 C31 7 34 9 33.4 12.4 C31 12.6 30.4 14.8 28.6 15.6 C22 22 12 25 0 25 C-12 25 -22 22 -28.6 15.6 C-30.4 14.8 -31 12.6 -33.4 12.4 C-34 9 -31 7 -31 3 Z'
    return (f'<circle cx="-22" cy="-19" r="9.6" fill="url(#cbTigH)" stroke="{STR}" stroke-width="2.6"/><circle cx="22" cy="-19" r="9.6" fill="url(#cbTigH)" stroke="{STR}" stroke-width="2.6"/>'
            f'<circle cx="-21.4" cy="-18" r="5" fill="#ffe6d0"/><circle cx="21.4" cy="-18" r="5" fill="#ffe6d0"/>' +
            S(head, 'url(#cbTigH)', OUT, 2) + SHINE +
            f'<path d="M0 -25.6 L0 -17.4 M-5.6 -24.6 L-4 -18.6 M5.6 -24.6 L4 -18.6 M-11 -22.4 L-8.2 -18 M11 -22.4 L8.2 -18" stroke="{STR}" stroke-width="2.4" stroke-linecap="round"/>'
            f'<path d="M-32 -1 C-28 -2 -25 -2 -22 -1 M-32.4 5 C-28.4 4 -25.4 4 -22.6 5 M32 -1 C28 -2 25 -2 22 -1 M32.4 5 C28.4 4 25.4 4 22.6 5" stroke="{STR}" stroke-width="2.2" stroke-linecap="round" fill="none"/>'
            f'<path d="M-24 10 C-22 5.4 -16 4.6 -10.4 6.4 C-6 3.6 6 3.6 10.4 6.4 C16 4.6 22 5.4 24 10 C22 18.4 12 24 0 24 C-12 24 -22 18.4 -24 10 Z" fill="{WHITE}"/>'
            f'<ellipse cx="-11.4" cy="-10.4" rx="4" ry="2.4" fill="{WHITE}"/><ellipse cx="11.4" cy="-10.4" rx="4" ry="2.4" fill="{WHITE}"/>'
            + CHEEKS + NOSE_PINK + '@@FACE@@' + whiskers())

def otter_head():
    OUT, PALE = '#6a4a32', '#fffaf0'
    head = 'M-31 4 C-31 -14 -17 -24 0 -24 C17 -24 31 -14 31 4 C31 18 17 25 0 25 C-17 25 -31 18 -31 4 Z'
    return (f'<circle cx="-26" cy="-13" r="5.4" fill="#8a6446" stroke="{OUT}" stroke-width="1.6"/><circle cx="26" cy="-13" r="5.4" fill="#8a6446" stroke="{OUT}" stroke-width="1.6"/>' +
            S(head, 'url(#cbOtterH)', OUT, 2) + SHINE +
            '<path d="M-24 -16 C-14 -24 14 -24 24 -16 C14 -20 -14 -20 -24 -16 Z" fill="#a98a6c" opacity=".5"/>'
            f'<ellipse cx="-6" cy="12" rx="8.4" ry="6.4" fill="{PALE}"/><ellipse cx="6" cy="12" rx="8.4" ry="6.4" fill="{PALE}"/>'
            '<g fill="#a8907a" opacity=".85"><circle cx="-9" cy="11" r=".7"/><circle cx="-6" cy="13.4" r=".7"/><circle cx="-10.6" cy="14" r=".7"/><circle cx="9" cy="11" r=".7"/><circle cx="6" cy="13.4" r=".7"/><circle cx="10.6" cy="14" r=".7"/></g>'
            + CHEEKS + '<path d="M-6 5.6 C-5 2.6 5 2.6 6 5.6 C6 8.6 2.6 10 0 10.2 C-2.6 10 -6 8.6 -6 5.6 Z" fill="#2c1d18"/><ellipse cx="-2" cy="4.6" rx="2" ry=".8" fill="#fff" opacity=".4"/>'
            + '@@FACE@@' + whiskers('#fffaf2', .85, 13, 31))

HEADS = {'cat': cat_head, 'dog': dog_head, 'fox': fox_head, 'redpanda': redpanda_head, 'tiger': tiger_head, 'otter': otter_head}
HEAD_AT = {'cat': (182, 84, 3), 'dog': (182, 86, 2), 'fox': (182, 86, 3), 'redpanda': (186, 82, 4), 'tiger': (182, 84, 3), 'otter': (190, 86, 8)}

def _head(name):
    x, y, r = HEAD_AT[name]
    return headpos(x, y, r, SHADOW(-2, 24, 24, 5, .5) + HEADS[name]())

# ================================================================ RESTING POSES
LOAF = 'M106 148 C82 149 72 132 78 116 C84 99 106 89 132 89 C160 89 180 101 185 121 C189 141 176 149 158 148 Z'

def paws(c, line, xs=(168, 194), y=143):
    return ''.join(S(f'M{x - 9} {y} C{x - 9} {y - 6} {x - 3} {y - 7} {x} {y - 7} C{x + 4} {y - 7} {x + 9} {y - 5} {x + 9} {y} C{x + 9} {y + 4} {x - 9} {y + 4} {x - 9} {y} Z', c, line, 1.5) + PAWLINES(x, y - 1, line) for x in xs)

def cat():
    OUT, CREAM, STR = '#a3561f', '#fff4e6', '#d9732e'
    tail = 'M96 132 C78 128 66 140 74 149 C84 158 136 157 158 151 C167 148 166 140 158 140 C134 146 98 147 88 141 C86 137 90 135 97 136 Z'
    back = f'''<ellipse cx="136" cy="147" rx="86" ry="14" fill="url(#cbCushion)" stroke="#557a89" stroke-width="1.6"/>
        <ellipse cx="136" cy="143" rx="76" ry="8" fill="#c4e0e8" opacity=".55"/>
        <path d="M58 150 C90 158 182 158 214 150" stroke="#eaf6fa" stroke-width="1.2" stroke-dasharray="3 3" fill="none" opacity=".8"/>'''
    float = f'''{SHADOW(136, 145, 70, 7)}
        {S(LOAF, 'url(#cbCat)', OUT, 2)}
        <path d="M102 94 C100 102 102 110 100 117 M118 90 C116 99 118 107 116 115 M134 89 C132 98 134 106 132 114 M150 92 C148 100 150 106 148 112" stroke="{STR}" stroke-width="3.4" stroke-linecap="round" fill="none"/>
        <path d="M92 104 C104 94 130 91 156 94" stroke="#fff" stroke-width="3.4" stroke-opacity=".32" fill="none" stroke-linecap="round"/>
        {S('M158 108 C174 104 190 114 192 132 C184 142 166 142 160 132 C156 124 155 114 158 108 Z', CREAM, '#d9b896', 1.4)}
        <g class="alert-tail" style="transform-origin:92px 138px">
          {S(tail, 'url(#cbCat)', OUT, 2)}
          <path d="M100 146 l1 5 M116 147 l.6 5 M132 147 l0 5 M146 146 l-.6 5" stroke="{STR}" stroke-width="3" stroke-linecap="round"/>
        </g>
        {paws(CREAM, '#c9a07a')}
        {_head('cat')}'''
    return back, float, ''

def dog():
    OUT, WHITE = '#7a4a26', '#fffaf2'
    back = '''<path d="M14 148 C14 126 58 120 134 120 C210 120 236 126 236 148 C236 158 14 158 14 148 Z" fill="url(#cbBed)" stroke="#9a5552" stroke-width="1.8"/>
        <ellipse cx="128" cy="143" rx="90" ry="10" fill="url(#cbBedIn)"/>
        <path d="M26 132 C70 124 190 124 226 132" stroke="#f6c7c1" stroke-width="2" fill="none" stroke-linecap="round" opacity=".7"/>'''
    float = f'''{SHADOW(134, 144, 70, 6)}
        <g class="alert-tail" style="transform-origin:90px 122px">
          {S('M90 124 C78 116 72 102 76 90 C78 85 84 86 84 91 C82 102 88 112 98 120 Z', 'url(#cbDog)', OUT, 2)}
          {S('M76 90 C78 85 84 86 84 91 C82 93 78 94 76.4 93 Z', WHITE, 'none', 0)}
        </g>
        {S(LOAF, 'url(#cbDog)', OUT, 2)}
        <path d="M86 110 C90 96 112 89 136 89 C156 89 168 95 173 103 C160 113 118 118 86 110 Z" fill="#6e4428" opacity=".92"/>
        <path d="M100 104 C112 99 128 98 144 99" stroke="#fff" stroke-width="2.6" stroke-opacity=".22" fill="none" stroke-linecap="round"/>
        {S('M158 108 C174 104 190 114 192 132 C184 142 166 142 160 132 C156 124 155 114 158 108 Z', WHITE, '#d8c6b0', 1.4)}
        {paws(WHITE, '#c9b29a')}
        {_head('dog')}'''
    return back, float, ''

def fox():
    OUT, WHITE, DARK = '#a84a17', '#fff6ec', '#3a2420'
    tail = 'M92 128 C70 124 58 140 68 150 C84 162 150 160 186 153 C200 150 206 144 201 137 C191 134 179 141 165 143 C131 148 99 147 92 140 Z'
    tip = 'M175 141 C185 137 195 133 201 137 C206 144 200 150 186 153 C181 149 178 146 175 141 Z'
    back = '''<path d="M10 148 C16 132 54 126 100 126 C154 126 214 128 232 140 C236 148 226 154 212 154 L28 154 C14 154 8 152 10 148 Z" fill="url(#cbMoss)" stroke="#4f6a2e" stroke-width="1.6"/>
        <path d="M24 138 c2 -5 5 -8 8 -9 M40 134 c1 -5 3 -8 6 -9 M210 136 c1 -5 3 -8 6 -9 M224 140 c1 -5 4 -7 7 -8" stroke="#c4d98a" stroke-width="1.6" stroke-linecap="round" fill="none"/>
        <circle cx="34" cy="144" r="2.6" fill="#fff3b0"/><circle cx="220" cy="146" r="2.2" fill="#f4bccb"/>'''
    float = f'''{SHADOW(136, 146, 74, 7)}
        {S(LOAF, 'url(#cbFox)', OUT, 2)}
        <path d="M92 104 C104 94 130 91 156 94" stroke="#fff" stroke-width="3.4" stroke-opacity=".32" fill="none" stroke-linecap="round"/>
        {S('M158 108 C174 104 190 114 192 132 C184 142 166 142 160 132 C156 124 155 114 158 108 Z', WHITE, '#e0c8b2', 1.4)}
        <g class="alert-tail" style="transform-origin:90px 134px">
          {S(tail, 'url(#cbFox)', OUT, 2)}
          {S(tip, WHITE, '#e0c8b2', 1.4)}
          <path d="M90 146 C110 152 140 152 164 148" stroke="#fff" stroke-width="2.6" stroke-opacity=".3" fill="none" stroke-linecap="round"/>
        </g>
        {paws('#4a2a20', '#1c100c', xs=(168, 190), y=139)}
        {_head('fox')}'''
    return back, float, ''

def redpanda():
    OUT, DARK = '#86321a', '#3e1a12'
    body = 'M90 127 C74 124 72 104 86 95 C100 86 140 84 164 90 C182 95 190 110 185 124 C160 131 112 131 90 127 Z'
    tail = 'M90 116 C76 118 68 128 66 142 C64 154 68 162 74 167 L86 165 C82 157 80 148 82 140 C84 130 90 125 98 122 Z'
    rings = ''.join(f'<path d="M{67 + i * .2:.1f} {131 + i * 8} C{73 + i * .4:.1f} {134 + i * 8} {80 + i * .2:.1f} {133 + i * 8} {85 - i * .4:.1f} {129 + i * 8}" stroke="#f6c08c" stroke-width="3.6" fill="none" stroke-linecap="round"/>' for i in range(4))
    leg = lambda x, a: (f'<g transform="rotate({a} {x} 122)">' + S(f'M{x - 7} 118 C{x - 7.4} 128 {x - 7} 136 {x - 6} 142 C{x - 5} 149 {x + 5} 149 {x + 6} 142 C{x + 7} 136 {x + 7.4} 128 {x + 7} 118 Z', DARK, '#1c0c08', 1.6)
                        + S(f'M{x - 8} 145 C{x - 8} 140 {x + 8} 140 {x + 8} 145 C{x + 8} 150 {x - 8} 150 {x - 8} 145 Z', '#2a100a', '#1c0c08', 1.4) + '</g>')
    back = '''<path d="M-10 122 C60 116 170 116 252 122 L252 138 C170 132 60 132 -10 140 Z" fill="url(#cbBark)" stroke="#3f2a1c" stroke-width="1.6"/>
        <path d="M6 127 C40 124 70 125 96 127 M112 130 C140 128 170 128 200 131 M20 135 C50 133 80 133 104 135 M150 136 C180 135 210 136 236 138" stroke="#3f2a1c" stroke-width="1" fill="none" opacity=".5" stroke-linecap="round"/>
        <path d="M118 120 c8 -5 18 -5 26 0 c-6 5 -18 5 -26 0z" fill="#93b257" stroke="#55702c" stroke-width="1"/>'''
    float = f'''{SHADOW(132, 126, 62, 5, .7)}
        <g class="alert-tail" style="transform-origin:92px 120px">
          {S(tail, 'url(#cbRp)', OUT, 2)}
          {rings}
          <path d="M74 167 L86 165 C84 161 84 158 84.6 155 C80 156 76 158 72 160 Z" fill="{DARK}"/>
        </g>
        {leg(110, 6)}
        {S(body, 'url(#cbRp)', OUT, 2)}
        <path d="M90 120 C116 126 156 126 182 120 C178 126 170 128 160 129 C136 131 108 131 90 126 Z" fill="{DARK}" opacity=".9"/>
        <path d="M96 102 C112 94 136 92 160 95" stroke="#fff" stroke-width="3" stroke-opacity=".28" fill="none" stroke-linecap="round"/>
        {leg(164, -5)}
        {_head('redpanda')}'''
    return back, float, ''

def tiger():
    OUT, WHITE, STR = '#a3561a', '#fff6ea', '#33201a'
    tail = 'M96 132 C78 128 66 140 74 149 C84 158 136 157 158 151 C167 148 166 140 158 140 C134 146 98 147 88 141 C86 137 90 135 97 136 Z'
    back = '''<path d="M14 144 C18 126 50 118 96 117 C150 116 206 120 228 130 C236 136 234 145 224 149 C170 155 70 155 22 150 C14 149 12 147 14 144 Z" fill="url(#cbRock)" stroke="#6a5f52" stroke-width="1.6"/>
        <path d="M30 127 C70 121 160 120 214 127" stroke="#f0e8dc" stroke-width="2" stroke-opacity=".8" fill="none" stroke-linecap="round"/>
        <path d="M8 149 c2 -10 4 -16 6 -20 c0 6 0 12 -2 20z M16 149 c1 -8 4 -13 7 -16 c-2 6 -3 11 -3 16z M226 149 c1 -9 3 -14 6 -18 c-1 6 -1 12 -2 18z M233 149 c2 -7 5 -11 8 -13 c-3 5 -4 9 -4 13z" fill="#86ab48" stroke="#4f6a2e" stroke-width=".8"/>'''
    float = f'''{SHADOW(136, 142, 70, 7)}
        {S(LOAF, 'url(#cbTig)', OUT, 2)}
        <path d="M102 93 C99 101 103 109 99 118 M116 90 C113 99 117 108 113 118 M130 89 C127 98 131 107 127 118 M144 90 C141 99 145 107 141 117 M158 95 C156 102 159 107 156 113" stroke="{STR}" stroke-width="3.6" stroke-linecap="round" fill="none"/>
        <path d="M84 126 C88 130 92 132 96 133 M84 116 C89 119 93 120 97 120" stroke="{STR}" stroke-width="3" stroke-linecap="round" fill="none"/>
        <path d="M92 104 C104 94 130 91 156 94" stroke="#fff" stroke-width="3.4" stroke-opacity=".32" fill="none" stroke-linecap="round"/>
        {S('M158 108 C174 104 190 114 192 132 C184 142 166 142 160 132 C156 124 155 114 158 108 Z', WHITE, '#e0c4a6', 1.4)}
        <g class="alert-tail" style="transform-origin:92px 138px">
          {S(tail, 'url(#cbTig)', OUT, 2)}
          <path d="M102 146 l1 5.4 M118 147 l.6 5.6 M134 147 l0 5.6" stroke="{STR}" stroke-width="3.4" stroke-linecap="round"/>
          <path d="M150 141 C155 140 160 139 164 141 C166 145 163 149 156 151 C153 148 151 145 150 141 Z" fill="{STR}"/>
        </g>
        {paws(WHITE, '#c9a684')}
        {_head('tiger')}'''
    return back, float, ''

def otter():
    OUT = '#4e3222'
    body = 'M44 118 C42 101 70 90 110 89 C146 88 170 92 181 103 C189 112 186 125 173 129 C142 135 82 135 56 131 C47 129 44 125 44 118 Z'
    flip = lambda x: S(f'M{x} 106 C{x - 4} 98 {x - 8} 90 {x - 6} 84 C{x - 4} 77 {x + 6} 76 {x + 9} 81 C{x + 11} 88 {x + 10} 98 {x + 10} 106 Z', '#5e3e2c', '#2e1c12', 1.6)
    paw = lambda x, y: S(f'M{x - 6} {y + 2} C{x - 7} {y - 3} {x - 3} {y - 6} {x} {y - 6} C{x + 4} {y - 6} {x + 7} {y - 3} {x + 6} {y + 2} C{x + 4} {y + 5} {x - 4} {y + 5} {x - 6} {y + 2} Z', '#6e4a34', '#2e1c12', 1.4)
    float = f'''<ellipse cx="112" cy="125" rx="80" ry="7" fill="#123a4d" opacity=".3"/>
        {S('M48 117 C34 113 18 114 6 120 C4 124 10 127 18 127 C30 128 44 126 52 124 Z', 'url(#cbOtter)', OUT, 1.8)}
        <g class="feet">{flip(60)}{flip(78)}</g>
        {S(body, 'url(#cbOtter)', OUT, 2)}
        {S('M104 96 C134 91 162 92 176 101 C184 107 184 114 180 118 C160 114 130 108 106 104 C100 102 100 98 104 96 Z', '#e8d6bc', '#b89c7c', 1.2)}
        <path d="M60 104 C80 96 108 93 136 93" stroke="#fff" stroke-width="3" stroke-opacity=".25" fill="none" stroke-linecap="round"/>
        <g transform="translate(144 80) rotate(-10)">
          {S('M0 13 C-1 4 6 -2 13 -2 C20 -2 27 4 26 13 C20 16 6 16 0 13 Z', 'url(#cbShell)', '#a8968a', 1.2)}
          <path d="M3 12 C4 6 8 2 13 1 M8 13 C8 7 10 3 13 1 M13 14 L13 1 M18 13 C18 7 16 3 13 1 M23 12 C22 6 18 2 13 1" stroke="#c4b3a6" stroke-width=".8" fill="none"/>
        </g>
        <g class="rest-arm">{paw(146, 94)}</g>
        {paw(170, 94)}
        <g class="wave-arm">
          {S('M140 102 C134 90 133 76 137 64 L149 65 C147 77 149 90 154 100 Z', '#6e4a34', '#2e1c12', 1.6)}
          {S('M134 62 C132 53 138 47 144 47 C151 47 155 54 153 60 C151 66 138 68 134 62 Z', '#5e3e2c', '#2e1c12', 1.6)}
        </g>
        {_head('otter')}'''
    return None, float, None      # the otter keeps its animated water (back/front) from the page

ANIMALS = {'otter': otter, 'cat': cat, 'dog': dog, 'fox': fox, 'redpanda': redpanda, 'tiger': tiger}

# ================================================================ WALKING POSES (side view, leg rig used by the motion engine)
BEAN = 'M84 106 C82 89 97 79 121 79 C146 79 165 88 171 102 C176 117 166 129 150 129 L103 129 C90 129 85 120 84 106 Z'
BIB = 'M157 99 C167 97 175 104 176 114 C175 122 168 126 160 125 C155 118 154 107 157 99 Z'
WALKERS = {
    'cat': dict(body=BEAN, fill='url(#cbCat)', out='#a3561f', leg='#f1a05a', farleg='#d68240', paw='#fff4e6', legLen=23, hipY=120, hips=(100, 110, 146, 156),
                tail='M78 98 C62 94 54 80 56 64 C57 58 64 58 64 64 C63 78 70 88 82 92 Z', tailFill='url(#cbCat)',
                tailMarks='<path d="M56 74 l7 1 M58 84 l6 -2" stroke="#d9732e" stroke-width="3" stroke-linecap="round"/>',
                marks='<path d="M108 81 C106 89 108 96 106 103 M122 79 C120 88 122 95 120 102 M136 80 C134 88 136 95 134 101" stroke="#d9732e" stroke-width="3.4" stroke-linecap="round" fill="none"/>',
                belly=('M96 123 C116 129 140 129 160 123 C156 127 152 129 148 129 L104 129 C100 129 98 127 96 123 Z', '#fff4e6'),
                chest='M150 84 C161 87 168 94 171 102 C176 117 166 129 150 129 L146 129 C139 116 140 97 150 84 Z', chestFill='#fff4e6', neck='', head=(172, 72)),
    'dog': dict(body=BEAN, fill='url(#cbDog)', out='#7a4a26', leg='#fffaf2', farleg='#e8dccb', paw='#fffaf2', legLen=23, hipY=120, hips=(100, 110, 146, 156),
                tail='M80 96 C70 88 66 76 70 66 C72 62 77 63 76 68 C75 78 80 86 88 92 Z', tailFill='url(#cbDog)',
                tailMarks='<path d="M70 66 C72 62 77 63 76 68 C74 69 71 69 70.2 68.4 Z" fill="#fffaf2"/>',
                marks='<path d="M88 96 C94 85 112 80 132 80 C148 80 160 86 164 93 C150 103 114 106 88 96 Z" fill="#6e4428" opacity=".92"/>',
                belly=('M96 123 C116 129 140 129 160 123 C156 127 152 129 148 129 L104 129 C100 129 98 127 96 123 Z', '#fffaf2'),
                chest='M150 84 C161 87 168 94 171 102 C176 117 166 129 150 129 L146 129 C139 116 140 97 150 84 Z', chestFill='#fffaf2', neck='', head=(172, 72)),
    'fox': dict(body=BEAN, fill='url(#cbFox)', out='#a84a17', leg='#3a2420', farleg='#24140f', paw='#24140f', legLen=23, hipY=120, hips=(100, 110, 146, 156),
                tail='M78 100 C56 98 32 106 20 120 C16 128 24 133 32 129 C46 121 62 115 80 112 Z', tailFill='url(#cbFox)',
                tailMarks='<path d="M20 120 C16 128 24 133 32 129 C29 126 26 121 25 116 C23 117 21 118 20 120 Z" fill="#fff6ec"/>',
                marks='', belly=('M140 123 C150 127 158 127 166 120 C162 126 156 129 148 129 Z', '#fff6ec'),
                chest='M150 84 C161 87 168 94 171 102 C176 117 166 129 150 129 L146 129 C139 116 140 97 150 84 Z', chestFill='#fff6ec', neck='', head=(172, 72)),
    'redpanda': dict(body=BEAN, fill='url(#cbRp)', out='#86321a', leg='#3e1a12', farleg='#2a100a', paw='#2a100a', legLen=22, hipY=120, hips=(100, 110, 146, 156),
                tail='M78 98 C58 96 36 100 22 110 C16 116 20 124 28 120 C42 112 60 108 80 108 Z', tailFill='url(#cbRp)',
                tailMarks=''.join(f'<path d="M{64 - i * 11} {98 + i * 2.6:.0f} l{-1 - i * .6:.1f} {9 - i * .6:.1f}" stroke="#f6c08c" stroke-width="3.6" stroke-linecap="round"/>' for i in range(4)),
                marks='', belly=('M88 118 C108 128 148 128 170 114 C166 124 158 129 150 129 L102 129 C94 129 90 124 88 118 Z', '#3e1a12'),
                neck='', head=(172, 72)),
    'tiger': dict(body=BEAN, fill='url(#cbTig)', out='#a3561a', leg='#f6973d', farleg='#d97a2c', paw='#fff6ea', legLen=23, hipY=120, hips=(100, 110, 146, 156),
                tail='M78 98 C60 100 48 110 44 126 C42 134 48 138 54 133 C56 120 64 110 80 106 Z', tailFill='url(#cbTig)',
                tailMarks='<path d="M62 102 l2 6 M52 110 l5 4 M46 120 l6 2" stroke="#33201a" stroke-width="3.2" stroke-linecap="round"/><path d="M44 126 C42 134 48 138 54 133 C52 130 50 127 49 124 Z" fill="#33201a"/>',
                marks=''.join(f'<path d="M{x} 80 C{x - 3} 88 {x + 2} 96 {x - 2} 105 C{x + 2} 97 {x + 1} 89 {x + 4} 80 Z" fill="#33201a"/>' for x in (100, 113, 126, 139)),
                belly=('M96 123 C116 129 140 129 160 123 C156 127 152 129 148 129 L104 129 C100 129 98 127 96 123 Z', '#fff6ea'),
                chest='M150 84 C161 87 168 94 171 102 C176 117 166 129 150 129 L146 129 C139 116 140 97 150 84 Z', chestFill='#fff6ea', neck='', head=(172, 72)),
    'otter': dict(body='M80 112 C78 97 94 90 118 90 C143 90 161 96 167 107 C171 118 164 128 150 129 L96 129 C84 129 80 122 80 112 Z',
                fill='url(#cbOtter)', out='#4e3222', leg='#6e4a34', farleg='#4e3424', paw='#5e3e2c', legLen=18, hipY=122, hips=(96, 106, 142, 152),
                tail='M84 112 C66 112 46 116 32 124 C46 129 68 129 86 121 Z', tailDx=0, tailFill='url(#cbOtter)', tailMarks='', marks='',
                belly=('', '#e8d6bc'),
                chest='M136 92 C150 92 162 98 167 107 C171 118 164 128 150 129 L134 129 C129 117 129 103 136 92 Z', chestFill='#e8d6bc', neck='', head=(170, 80)),
}
for _n, _w in WALKERS.items():           # head offset relative to its resting place (build.py moves the head with it)
    _x, _y, _ = HEAD_AT[_n]; _w['headAt'] = _w['head']; _w['head'] = (_w['head'][0] - _x, _w['head'][1] - _y)

def walker(name):
    w = WALKERS[name]; L = w['legLen']; OUT = w['out']
    def leg(x, color, phase, far, front):
        U = round(L * .52); D = L - U
        paw = w['paw'] if not far else color
        th, sh = 7.4, 6.4                                 # thigh / shin half-widths: short and chubby
        line = f'stroke="{OUT}" stroke-width="1.6" stroke-linecap="round" fill="none" stroke-opacity=".8"'
        return (f'<g class="leg" transform="translate({x} {w["hipY"]})"><g class="swing" data-far="{1 if far else 0}" data-phase="{phase}" data-len="{L}" data-front="{1 if front else 0}">'
                f'<path d="M{-th} -9 L{-th} {U} A{th} {th} 0 0 0 {th} {U} L{th} -9 Z" fill="{color}"/>'
                f'<path d="M{-th} -2 L{-th} {U} M{th} -2 L{th} {U}" {line}/>'
                f'<g transform="translate(0 {U})"><g class="shin">'
                f'<circle r="{th}" fill="{color}"/>'
                f'<path d="M{-sh} 0 L{-sh} {D} L{sh} {D} L{sh} 0 Z" fill="{color}"/>'
                f'<path d="M{-sh} 1 L{-sh} {D} M{sh} 1 L{sh} {D}" {line}/>'
                f'<ellipse cx="1.6" cy="{D + 1}" rx="8.4" ry="5" fill="{paw}" stroke="{OUT}" stroke-width="1.5" stroke-opacity=".8"/>'
                f'<path d="M-.6 {D + 4} v-2 M3.8 {D + 4} v-2" stroke="{OUT}" stroke-width=".8" stroke-linecap="round" opacity=".6"/></g></g></g></g>')
    b1, b2, f1, f2 = w['hips']
    ground = w['hipY'] + L + 4
    bd, bc = w['belly']
    return (f'<g class="walker">'
            f'<ellipse class="wshadow" cx="122" cy="{ground}" rx="62" ry="5" fill="url(#cbShadow)"/>'
            f'<g class="wmove"><g class="wtail"><g transform="translate({w.get("tailDx", 10)} {w.get("tailDy", 0)})">{S(w["tail"], w["tailFill"], OUT, 2)}{w["tailMarks"]}</g></g>'
            + leg(b2, w['farleg'], 3.14, True, False) + leg(f2, w['farleg'], 0, True, True)
            + leg(b1, w['leg'], 0, False, False) + leg(f1, w['leg'], 3.14, False, True) +
            f'<g class="wbody">{S(w["body"], w["fill"], OUT, 2)}<path d="{bd}" fill="{bc}" opacity=".95"/>{w["marks"]}'
            + (f'<path d="{w["chest"]}" fill="{w["chestFill"]}"/>{S(w["body"], "none", OUT, 2)}' if w.get('chest') else '') +
            f'<path d="M96 90 C108 83 128 82 148 85" stroke="#fff" stroke-width="3.2" stroke-opacity=".3" fill="none" stroke-linecap="round"/></g>'
            f'<g class="wfront">'
            f'@@HEAD@@</g></g></g>')
