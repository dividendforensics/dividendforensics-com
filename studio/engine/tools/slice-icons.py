#!/usr/bin/env python3
"""Cuts a sheet of icons (transparent background, gaps between icons) into assets/icons/<slug>.png.

  python3 tools/slice-icons.py raw/food-sheet.png configs/food.json --rows 3
  python3 tools/slice-icons.py raw/food-a.png configs/food.json --rows 2 --start 0 --count 6   # half-sheets
  python3 tools/slice-icons.py raw/food-b.png configs/food.json --rows 2 --start 6 --count 6

Icons are matched to the config's entries in reading order (left to right, top to bottom), and each
entry needs a "slug". Also writes a numbered preview next to the sheet so a wrong order is easy to see.
"""
import sys, os, json, argparse
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('sheet'); ap.add_argument('cfg')
ap.add_argument('--rows', type=int, default=3)
ap.add_argument('--start', type=int, default=0); ap.add_argument('--count', type=int, default=None)
ap.add_argument('--size', type=int, default=384)
a = ap.parse_args()

cfg = json.load(open(a.cfg)); entries = cfg['entries'][a.start:(a.start + a.count) if a.count else None]
slugs = [e.get('slug') for e in entries]
if not all(slugs): sys.exit('every entry in the range needs a "slug" in ' + a.cfg)

im = Image.open(a.sheet).convert('RGBA'); W, H = im.size
alpha = np.array(im.getchannel('A')) > 24
if alpha.mean() > 0.9:  # no transparency: treat the border colour as background
    px = np.array(im.convert('RGB')).astype(int); bg = np.median(np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]]), axis=0)
    alpha = (np.abs(px - bg).sum(axis=2) > 60)

# connected components on a downscaled mask
k = 4; sm = alpha[:H // k * k, :W // k * k].reshape(H // k, k, W // k, k).any(axis=(1, 3))
lab = np.zeros(sm.shape, int); n = 0
for sy, sx in zip(*np.nonzero(sm)):
    if lab[sy, sx]: continue
    n += 1; st = [(sy, sx)]; lab[sy, sx] = n
    while st:
        y, x = st.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < sm.shape[0] and 0 <= xx < sm.shape[1] and sm[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; st.append((yy, xx))
boxes = []
for i in range(1, n + 1):
    ys, xs = np.nonzero(lab == i); boxes.append([xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k, len(ys)])
big = max(b[4] for b in boxes); boxes = [b for b in boxes if b[4] > big * 0.12]  # drop sparkles/crumbs

def merge_near(boxes, pad):  # an icon made of loose pieces (a bowl and its steam) counts as one icon
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                A, B = boxes[i], boxes[j]
                if A[0] - pad < B[2] and B[0] - pad < A[2] and A[1] - pad < B[3] and B[1] - pad < A[3]:
                    boxes[i] = [min(A[0], B[0]), min(A[1], B[1]), max(A[2], B[2]), max(A[3], B[3]), A[4] + B[4]]; boxes.pop(j); changed = True; break
            if changed: break
    return boxes
boxes = merge_near(boxes, 6)

if len(boxes) != len(slugs):
    dbg = im.convert('RGB'); d = ImageDraw.Draw(dbg)
    for i, b in enumerate(boxes): d.rectangle(b[:4], outline=(255, 0, 0), width=4); d.text((b[0] + 6, b[1] + 6), str(i + 1), fill=(255, 255, 0))
    p = a.sheet.rsplit('.', 1)[0] + '-debug.png'; dbg.save(p)
    sys.exit(f'found {len(boxes)} icons but expected {len(slugs)}. See {p}. Ask the image model for clearer gaps between icons.')

# reading order: split into rows by y, then sort each row by x
boxes.sort(key=lambda b: (b[1] + b[3]) / 2); per = len(boxes) // a.rows; ordered = []
for r in range(a.rows):
    row = boxes[r * per:(r + 1) * per] if r < a.rows - 1 else boxes[r * per:]
    ordered += sorted(row, key=lambda b: (b[0] + b[2]) / 2)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'icons'); os.makedirs(out, exist_ok=True)
prev = im.convert('RGB'); d = ImageDraw.Draw(prev)
for slug, b in zip(slugs, ordered):
    c = im.crop((b[0], b[1], b[2], b[3])); s = max(c.size); sq = Image.new('RGBA', (s, s), (0, 0, 0, 0)); sq.paste(c, ((s - c.size[0]) // 2, (s - c.size[1]) // 2))
    sq = sq.resize((a.size, a.size), Image.LANCZOS); sq.save(os.path.join(out, slug + '.png'))
    d.rectangle(b[:4], outline=(0, 255, 0), width=3); d.text((b[0] + 6, b[1] + 6), slug, fill=(255, 255, 0))
prev.save(a.sheet.rsplit('.', 1)[0] + '-sliced.png'); print('wrote', ', '.join(slugs))
