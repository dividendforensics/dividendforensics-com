"""Builds the Lottie edition of ASCENT: lottie/ascent.json (1080x1080, 30 fps, 12 s).

The idea is a match cut in four steps: a bubble leaves the seabed, rises, pops at the
surface, its ring becomes the setting sun, and the sun becomes the 'ㅇ' of 오름
("rising" in Korean), the logotype. Every shape is drawn here as vector paths;
no fonts or images are embedded, so the file renders the same in any Lottie player.

usage: python3 tools/make_lottie.py lottie/ascent.json
"""
import json
import math
import random
import sys

W = H = 1080
FR = 30
OP = 360
random.seed(7)

# ───────────────────────────────────────── property helpers
EASE = {
    'inout': ({'x': 0.42, 'y': 0.0}, {'x': 0.58, 'y': 1.0}),
    'out': ({'x': 0.16, 'y': 1.0}, {'x': 0.3, 'y': 1.0}),
    'in': ({'x': 0.55, 'y': 0.0}, {'x': 0.9, 'y': 0.45}),
    'linear': ({'x': 0.0, 'y': 0.0}, {'x': 1.0, 'y': 1.0}),
    'back': ({'x': 0.34, 'y': 1.56}, {'x': 0.64, 'y': 1.0}),
}


def static(v):
    return {'a': 0, 'k': v}


def anim(keys, dims=None, scalar_ease=False):
    """keys: [(frame, value, ease)], ease names the curve that leaves this key."""
    out = []
    for n, (f, v, e) in enumerate(keys):
        kf = {'t': f, 's': v if isinstance(v, list) else [v]}
        if n < len(keys) - 1:
            if e == 'hold':
                kf['h'] = 1
            else:
                o, i = EASE[e]
                if scalar_ease:
                    kf['o'] = {'x': o['x'], 'y': o['y']}
                    kf['i'] = {'x': i['x'], 'y': i['y']}
                else:
                    d = dims or (len(v) if isinstance(v, list) else 1)
                    kf['o'] = {'x': [o['x']] * d, 'y': [o['y']] * d}
                    kf['i'] = {'x': [i['x']] * d, 'y': [i['y']] * d}
        out.append(kf)
    return {'a': 1, 'k': out}


def prop(v):
    return v if isinstance(v, dict) else static(v)


def pos_anim(keys):
    return anim([(f, [x, y, 0], e) for f, (x, y), e in keys], scalar_ease=True)


def rgb(h, a=1.0):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [a]


# ───────────────────────────────────────── shapes
def ellipse(cx, cy, w, h=None):
    return {'ty': 'el', 'd': 1, 'p': prop([cx, cy]), 's': prop([w, w if h is None else h]), 'nm': 'Ellipse'}


def rect(cx, cy, w, h, r=0):
    return {'ty': 'rc', 'd': 1, 'p': prop([cx, cy]), 's': prop([w, h]), 'r': prop(r), 'nm': 'Rect'}


def shape_val(pts, ins=None, outs=None, closed=False):
    n = len(pts)
    return {'i': ins or [[0, 0]] * n, 'o': outs or [[0, 0]] * n, 'v': pts, 'c': closed}


def path(pts=None, ins=None, outs=None, closed=False, ks=None):
    return {'ty': 'sh', 'd': 1, 'ks': ks if ks else static(shape_val(pts, ins, outs, closed)), 'nm': 'Path'}


def fill(color, o=100):
    return {'ty': 'fl', 'c': prop(color), 'o': prop(o), 'r': 1, 'bm': 0, 'nm': 'Fill'}


def gfill(stops, s, e, o=100):
    flat = []
    for p, c in stops:
        flat += [p] + rgb(c)[:3]
    return {'ty': 'gf', 'o': prop(o), 'r': 1, 'bm': 0, 'g': {'p': len(stops), 'k': static(flat)},
            's': static(s), 'e': static(e), 't': 1, 'nm': 'Gradient'}


def stroke(color, w, o=100, cap=2):
    return {'ty': 'st', 'c': prop(color), 'o': prop(o), 'w': prop(w), 'lc': cap, 'lj': 2, 'ml': 4, 'bm': 0, 'nm': 'Stroke'}


def trim(e, s=0):
    return {'ty': 'tm', 's': prop(s), 'e': prop(e), 'o': static(0), 'm': 1, 'nm': 'Trim'}


def tr(p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100):
    return {'ty': 'tr', 'p': prop(list(p) if not isinstance(p, dict) else p), 'a': prop(list(a)),
            's': prop(list(s) if not isinstance(s, dict) else s), 'r': prop(r), 'o': prop(o),
            'sk': static(0), 'sa': static(0), 'nm': 'Transform'}


def group(nm, items, **t):
    return {'ty': 'gr', 'nm': nm, 'np': len(items), 'it': items + [tr(**t)]}


# ───────────────────────────────────────── layers
layers = []


def layer(nm, shapes, p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100, ip=0, op=OP, parent=None):
    ks = {
        'o': prop(o), 'r': prop(r),
        'p': p if isinstance(p, dict) else static([p[0], p[1], 0]),
        'a': static([a[0], a[1], 0]),
        's': s if isinstance(s, dict) else static([s[0], s[1], 100]),
    }
    L = {'ddd': 0, 'ind': len(layers) + 1, 'ty': 4, 'nm': nm, 'sr': 1, 'ks': ks, 'ao': 0,
         'shapes': shapes, 'ip': ip, 'op': op, 'st': 0, 'bm': 0}
    if parent:
        L['parent'] = parent
    layers.append(L)
    return L['ind']


def null(nm, p=(0, 0), ip=0, op=OP):
    ks = {'o': static(0), 'r': static(0), 'p': p if isinstance(p, dict) else static([p[0], p[1], 0]),
          'a': static([0, 0, 0]), 's': static([100, 100, 100])}
    layers.append({'ddd': 0, 'ind': len(layers) + 1, 'ty': 3, 'nm': nm, 'sr': 1, 'ks': ks, 'ao': 0,
                   'ip': ip, 'op': op, 'st': 0, 'bm': 0})
    return layers[-1]['ind']


# Layers are listed top-most first; we build bottom-up and reverse at the end.

# ── timing (frames)
F_FORM, F_RISE, F_SURF, F_POP = 18, 62, 246, 252
F_SUN, F_DUSK, F_LOGO = 262, 296, 308
BX, BY0 = 540, 846          # bubble birth point
BY_MID, BY_SURF = 560, 392  # held height while rising, surface line


# ── 1. background water: three tones that cross-fade as the bubble climbs
layer('Water deep', [group('bg', [rect(540, 540, W, H), gfill([(0, '#06213a'), (1, '#020a16')], [540, 0], [540, 1080])])])
layer('Water mid', [group('bg', [rect(540, 540, W, H), gfill([(0, '#0f6a84'), (1, '#063049')], [540, 0], [540, 1080])])],
      o=anim([(90, 0, 'inout'), (165, 100, 'inout')]))
layer('Water shallow', [group('bg', [rect(540, 540, W, H), gfill([(0, '#6fd3dc'), (0.55, '#1b8fa6'), (1, '#0b5a75')], [540, 0], [540, 1080])])],
      o=anim([(160, 0, 'inout'), (236, 100, 'inout')]))

# ── 2. light shafts
rays = []
for k, (x0, w0, ang) in enumerate([(180, 70, 14), (420, 110, 16), (650, 60, 13), (860, 90, 15), (300, 40, 17)]):
    dx = 1100 * math.tan(math.radians(ang))
    rays.append(group(f'ray {k}', [
        path([[x0, -20], [x0 + w0, -20], [x0 + w0 * 2.6 + dx, 1120], [x0 - w0 * 0.6 + dx, 1120]], closed=True),
        fill(rgb('#e8fbff'), 9 + 3 * (k % 2))]))
layer('Light shafts', [group('rays', rays, o=anim([(70, 15, 'inout'), (150, 55, 'inout'), (240, 100, 'inout')]))])

# ── 3. the seabed world, carried away downward as the camera follows the bubble
world = null('World', p=pos_anim([(0, (0, 0), 'inout'), (F_RISE, (0, 0), 'in'), (200, (0, 1150), 'linear')]))
bed = [group('sand', [
    path([[-40, 900], [140, 868], [330, 898], [470, 876], [610, 884], [760, 858], [930, 896], [1120, 872], [1120, 1200], [-40, 1200]],
         ins=[[0, 0], [-60, 0], [-60, 0], [-40, 0], [-40, 0], [-50, 0], [-50, 0], [-60, 0], [0, 0], [0, 0]],
         outs=[[60, 0], [60, 0], [40, 0], [40, 0], [50, 0], [50, 0], [60, 0], [0, 0], [0, 0], [0, 0]], closed=True),
    gfill([(0, '#1d4a55'), (1, '#071a24')], [540, 860], [540, 1080])])]
for k, (x, y, w, h, c) in enumerate([(470, 880, 150, 90, '#0b2c37'), (612, 884, 130, 76, '#0d3340'), (210, 900, 220, 120, '#082531'),
                                     (900, 890, 260, 150, '#072230'), (60, 910, 140, 80, '#0a2a36')]):
    bed.append(group(f'rock {k}', [ellipse(x, y, w, h), fill(rgb(c))]))
layer('Seabed', bed, parent=world)
for k, (x, hgt, ph) in enumerate([(120, 520, 0), (300, 640, 20), (780, 600, 9), (960, 470, 31), (690, 380, 14)]):
    leaves = [path([[0, 0], [0, -hgt]], ins=[[0, 0], [30, 120]], outs=[[-30, -120], [0, 0]]), stroke(rgb('#2f5a33'), 9)]
    for j in range(5):
        yy = -hgt * (0.2 + 0.16 * j)
        side = 1 if j % 2 else -1
        leaves = [group(f'leaf {j}', [ellipse(side * 24, yy, 46, 18), fill(rgb('#3d6a3a'))], r=side * -25, a=(0, yy), p=(0, yy))] + leaves
    layer(f'Kelp {k}', [group('kelp', leaves)], p=(x, 900), parent=world,
          r=anim([(f, (5 if (n % 2) else -5) * (1 if k % 2 else -1), 'inout') for n, f in enumerate(range(-ph, OP + 60, 60))]))

# ── 4. fish passing across the light
fish_items = []
for k, (dx, dy, sc) in enumerate([(0, 0, 1.0), (-70, 38, 0.8), (-120, -30, 0.9), (-190, 18, 0.7), (-240, -14, 0.85)]):
    body = path([[46, 0], [0, -16], [-40, 0], [0, 16]], ins=[[0, -10], [26, 0], [0, -8], [-26, 0]],
                outs=[[0, 10], [-26, 0], [0, 8], [26, 0]], closed=True)
    tail = path([[-36, 0], [-62, -16], [-56, 0], [-62, 16]], closed=True)
    wig = [(f, (6 if n % 2 else -6), 'inout') for n, f in enumerate(range(0, OP, 6 + k % 3))]
    fish_items.append(group(f'fish {k}', [body, tail, fill(rgb('#062a3a'))], p=(dx, dy), s=(100 * sc, 100 * sc), r=anim(wig)))
layer('Fish', fish_items, p=pos_anim([(100, (-160, 300), 'linear'), (215, (1340, 250), 'linear')]), ip=100, op=216)

# ── 5. the surface, descending into view
surf_edge = [[-60, 0]] + [[x, 10 * math.sin(x / 70)] for x in range(0, 1141, 90)] + [[1140, -600], [-60, -600]]
layer('Surface', [
    group('underside', [path(surf_edge, closed=True), gfill([(0, '#e9fdff'), (1, '#9ee6ef')], [540, -300], [540, 0], o=92)]),
    group('rim', [path([[x, 10 * math.sin(x / 70)] for x in range(-60, 1141, 30)]), stroke(rgb('#ffffff'), 4, 85)]),
], p=pos_anim([(180, (0, -40), 'out'), (240, (0, BY_SURF), 'inout')]), ip=170, op=F_SUN + 24,
      o=anim([(F_SUN, 100, 'inout'), (F_SUN + 22, 0, 'linear')]))

# ── 6. tiny bubbles keeping the hero company
for k in range(16):
    start = 30 + k * 13 + random.randint(-4, 4)
    x0 = BX + random.randint(-60, 60)
    size = random.choice([8, 10, 12, 14])
    dur = random.randint(55, 80)
    sway = random.choice([-30, -20, 20, 30])
    layer(f'Microbubble {k}', [group('b', [ellipse(0, 0, size), stroke(rgb('#d9fbff'), 2, 85), fill(rgb('#ffffff'), 18)])],
          p=pos_anim([(start, (x0, 900), 'linear'), (start + dur // 2, (x0 + sway, 480), 'linear'), (start + dur, (x0 - sway // 2, 60), 'linear')]),
          ip=start, op=min(start + dur, F_POP))

# ── 7. the hero bubble
zig = [(F_RISE + 20 * n, (BX + (36 if n % 2 else -36) * min(1, n / 3), BY_MID), 'inout') for n in range(1, 9)]
bubble_pos = pos_anim([(F_FORM, (BX, BY0), 'hold'), (F_RISE - 6, (BX, BY0), 'in'), (F_RISE + 20, (BX - 12, BY_MID + 40), 'out')]
                      + zig + [(222, (BX, BY_MID), 'inout'), (F_SURF, (BX, BY_SURF + 8), 'out'), (F_POP, (BX, BY_SURF), 'linear')])
bubble = [
    group('highlight', [ellipse(-15, -17, 18, 11), fill(rgb('#ffffff'), 92)], r=-35, a=(-15, -17), p=(-15, -17)),
    group('rim light', [ellipse(10, 14, 50, 50), trim(32, 8), stroke(rgb('#ffffff'), 3, 55)]),
    group('ring', [ellipse(0, 0, 72), stroke(rgb('#c9f6ff'), 5), gfill([(0, '#ffffff'), (1, '#7fdcef')], [-20, -30], [30, 40], o=22)]),
]
layer('Bubble', [group('bubble', bubble, s=anim([(F_RISE - 4, [100, 100], 'out'), (F_RISE + 6, [92, 110], 'out'), (F_RISE + 18, [106, 94], 'inout'),
                                                 (F_RISE + 30, [100, 100], 'inout'), (F_SURF, [104, 96], 'out'), (F_POP - 1, [120, 84], 'linear')]))],
      p=bubble_pos, s=anim([(F_FORM, [0, 0, 100], 'back'), (F_RISE - 8, [100, 100, 100], 'inout'), (220, [118, 118, 100], 'linear')]),
      ip=F_FORM, op=F_POP)

# ── 8. the pop: a ring and a burst of droplets
layer('Pop ring', [group('ring', [ellipse(0, 0, 80), stroke(rgb('#ffffff'), anim([(F_POP, 10, 'out'), (F_POP + 26, 1, 'linear')]))])],
      p=(BX, BY_SURF), s=anim([(F_POP, [100, 100, 100], 'out'), (F_POP + 26, [330, 330, 100], 'linear')]),
      o=anim([(F_POP, 100, 'in'), (F_POP + 26, 0, 'linear')]), ip=F_POP, op=F_POP + 27)
for k in range(9):
    a = math.radians(-160 + k * 17.5)
    d = random.randint(70, 130)
    layer(f'Droplet {k}', [group('d', [ellipse(0, 0, random.choice([7, 9, 11])), fill(rgb('#ffffff'))])],
          p=pos_anim([(F_POP, (BX, BY_SURF - 6), 'out'), (F_POP + 14, (BX + d * math.cos(a), BY_SURF - 6 + d * math.sin(a)), 'in'),
                      (F_POP + 30, (BX + d * 1.4 * math.cos(a), BY_SURF + 40), 'linear')]),
          o=anim([(F_POP + 18, 100, 'linear'), (F_POP + 30, 0, 'linear')]), ip=F_POP, op=F_POP + 31)

# ── 9. dusk: sky, sea, and the sun born from the ring
HZ = 610
layer('Sky', [group(f'glint {k}', [rect(540, HZ + 22 + k * 30, 260 - k * 34 + random.randint(-20, 20), 6, 3), fill(rgb('#ffcf86'), 70 - k * 9)])
               for k in range(6)] + [
    group('sky', [rect(540, HZ / 2, W, HZ), gfill([(0, '#141238'), (0.55, '#7a3a63'), (0.85, '#d9685a'), (1, '#f7a55b')], [540, 0], [540, HZ])]),
    group('sea', [rect(540, HZ + (H - HZ) / 2, W, H - HZ), gfill([(0, '#c25a52'), (0.25, '#5b2f4f'), (1, '#120f2c')], [540, HZ], [540, H])]),
],
    o=anim([(F_SUN - 4, 0, 'inout'), (F_SUN + 18, 100, 'linear')]), ip=F_SUN - 4)
# night falls over the scene so the logotype can sit on it
layer('Dusk veil', [group('veil', [rect(540, 540, W, H), fill(rgb('#0b0b1e'))])],
      o=anim([(F_DUSK, 0, 'inout'), (F_DUSK + 34, 88, 'linear')]), ip=F_DUSK)

# the sun: same place and size as the popped ring, then it settles into the logotype
O_X, O_Y, O_D = 402, 452, 124       # where the 'ㅇ' of 오름 sits
sun_pos = pos_anim([(F_SUN, (BX, BY_SURF), 'inout'), (F_SUN + 26, (BX, 470), 'inout'), (F_DUSK + 4, (BX, 470), 'inout'), (F_LOGO + 18, (O_X, O_Y), 'linear')])
layer('Sun glow', [group('glow', [ellipse(0, 0, 360), gfill([(0, '#ffd38a'), (1, '#f08a4b')], [0, 0], [180, 0], o=30)])],
      p=sun_pos, s=anim([(F_SUN, [20, 20, 100], 'out'), (F_SUN + 26, [100, 100, 100], 'inout'), (F_DUSK, [100, 100, 100], 'inout'), (F_LOGO + 18, [40, 40, 100], 'linear')]),
      o=anim([(F_SUN, 0, 'out'), (F_SUN + 20, 100, 'inout'), (F_LOGO + 4, 100, 'inout'), (F_LOGO + 30, 0, 'linear')]), ip=F_SUN)
layer('Sun', [group('sun', [
    ellipse(0, 0, 176),
    stroke(rgb('#f6c06b'), anim([(F_LOGO, 0, 'inout'), (F_LOGO + 18, 13 * 176 / O_D * 2, 'linear')])),
    gfill([(0, '#fff1c9'), (1, '#f3a04f')], [-40, -60], [60, 80], o=anim([(F_LOGO + 4, 100, 'inout'), (F_LOGO + 20, 0, 'linear')])),
])], p=sun_pos, s=anim([(F_SUN, [46, 46, 100], 'out'), (F_SUN + 26, [100, 100, 100], 'inout'), (F_DUSK + 4, [100, 100, 100], 'inout'),
                       (F_LOGO + 18, [O_D / 176 * 100] * 2 + [100], 'linear')]), ip=F_SUN)

# ── 10. the logotype 오름 drawn on around the sun, and ASCENT beneath it
INK = rgb('#f6ead7')


def drawn(nm, paths, start, dur, w=26, color=INK):
    layer(nm, [group(nm, paths + [trim(anim([(start, 0, 'inout'), (start + dur, 100, 'linear')])), stroke(color, w, cap=2)])], ip=start)


s0 = F_LOGO + 12
drawn('ㅗ stem', [path([[O_X, O_Y + 74], [O_X, O_Y + 120]])], s0, 10)
drawn('ㅗ bar', [path([[O_X - 112, O_Y + 128], [O_X + 112, O_Y + 128]])], s0 + 6, 14)
RX = 590
drawn('ㄹ', [path([[RX, 388], [RX + 190, 388], [RX + 190, 442], [RX + 4, 442], [RX + 4, 496], [RX + 196, 496]])], s0 + 10, 18)
drawn('ㅡ', [path([[RX - 18, 540], [RX + 214, 540]])], s0 + 18, 12)
drawn('ㅁ', [path([[RX + 14, 578], [RX + 182, 578], [RX + 182, 650], [RX + 14, 650]], closed=True)], s0 + 22, 16)

# ASCENT, built from strokes (unit box 0..1, scaled)
GL = {
    'A': [[[0, 1], [0.5, 0], [1, 1]], [[0.22, 0.62], [0.78, 0.62]]],
    'E': [[[0.9, 0], [0, 0], [0, 1], [0.9, 1]], [[0, 0.5], [0.75, 0.5]]],
    'N': [[[0, 1], [0, 0], [1, 1], [1, 0]]],
    'T': [[[0, 0], [1, 0]], [[0.5, 0], [0.5, 1]]],
}


def glyph(ch, x, y, s):
    P = lambda u, v: [x + u * s * 0.8, y + v * s]
    if ch == 'C':
        cx, cy, rx, ry = x + 0.42 * s, y + s / 2, s * 0.44, s / 2
        pts = [[cx + rx * math.cos(math.radians(a)), cy - ry * math.sin(math.radians(a))] for a in range(50, 311, 13)]
        return [path(pts)]
    if ch == 'S':
        pts = [P(0.88, 0.17), P(0.5, 0.0), P(0.12, 0.25), P(0.5, 0.5), P(0.88, 0.75), P(0.5, 1.0), P(0.1, 0.83)]
        k = s
        ins = [[0, 0], [0.22 * k, 0], [0, -0.12 * k], [-0.24 * k, -0.1 * k], [0, -0.12 * k], [0.22 * k, 0], [0.08 * k, 0.08 * k]]
        outs = [[-0.08 * k, -0.08 * k], [-0.22 * k, 0], [0, 0.12 * k], [0.24 * k, 0.1 * k], [0, 0.12 * k], [-0.22 * k, 0], [0, 0]]
        return [path(pts, ins, outs)]
    return [path([P(u, v) for u, v in stroke_pts]) for stroke_pts in GL[ch]]


TX, TY, TS, GAP = 401, 724, 34, 49
for n, ch in enumerate('ASCENT'):
    shapes = glyph(ch, TX + n * GAP, TY, TS)
    start = s0 + 14 + n * 2
    if False:
        pass
    else:
        layer(f'Type {ch}', [group(ch, shapes + [trim(anim([(start, 0, 'inout'), (start + 14, 100, 'linear')])), stroke(INK, 4.5, cap=2)])], ip=start)

# a hairline under the type, the horizon remembered
drawn('Rule', [path([[TX - 6, TY + 70], [TX + 5 * GAP + TS * 0.8 + 6, TY + 70]])], s0 + 22, 14, w=2, color=rgb('#f6c06b'))

doc = {
    'v': '5.12.2', 'fr': FR, 'ip': 0, 'op': OP, 'w': W, 'h': H, 'nm': 'Ascent', 'ddd': 0, 'assets': [],
    'meta': {'g': 'make_lottie.py', 'd': 'A bubble rises, pops, becomes the sun, becomes the ㅇ of 오름.'},
    'layers': list(reversed(layers)),
}
# parents are referenced by index, which stays valid after reversing the list order
with open(sys.argv[1] if len(sys.argv) > 1 else 'ascent.json', 'w') as f:
    json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
print(f'{len(layers)} layers, {OP / FR:.0f} s @ {FR} fps')
