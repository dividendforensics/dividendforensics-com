#!/usr/bin/env python3
"""Turns raw images (from ChatGPT or any image model) into the files the engine reads.

  python3 tools/prep-assets.py raw/bg.png      bg-main     # cover-crop to 9:16, 1080x1920 JPG
  python3 tools/prep-assets.py raw/floor.png   arena-floor # square 1024 PNG (keeps alpha)
  python3 tools/prep-assets.py raw/panel.png   panel       # trim transparent border, 1200px wide PNG
  python3 tools/prep-assets.py raw/rays.png    rays        # square 1024 PNG (keeps alpha)

Output goes to assets/. Missing files are fine: the engine falls back to its built-in look.
"""
import sys, os
from PIL import Image
here = os.path.dirname(os.path.abspath(__file__)); out = os.path.join(here, '..', 'assets')
src, kind = sys.argv[1], sys.argv[2]
im = Image.open(src)
os.makedirs(out, exist_ok=True)
if kind == 'bg-main':
    im = im.convert('RGB'); w, h = im.size; tw = int(h * 9 / 16)
    if tw <= w: im = im.crop(((w - tw) // 2, 0, (w - tw) // 2 + tw, h))
    else:
        th = int(w * 16 / 9); im = im.crop((0, (h - th) // 2, w, (h - th) // 2 + th))
    im.resize((1080, 1920), Image.LANCZOS).save(os.path.join(out, 'bg-main.jpg'), quality=93)
elif kind in ('arena-floor', 'rays'):
    im = im.convert('RGBA'); w, h = im.size; s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    im.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, kind + '.png'))
elif kind == 'panel':
    im = im.convert('RGBA'); box = im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
    if box: im = im.crop(box)
    r = 1200 / im.size[0]; im.resize((1200, max(1, int(im.size[1] * r))), Image.LANCZOS).save(os.path.join(out, 'panel.png'))
else:
    sys.exit('unknown kind: ' + kind)
print('wrote', kind)
