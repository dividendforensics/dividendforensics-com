#!/usr/bin/env python3
"""Side-by-side comparison of the same scene in three looks: legacy | v25 | v3d.
usage: python3 tools/compose-cmp.py out food-s13 clash      -> out/compare/food-s13-clash-compare.mp4
       python3 tools/compose-cmp.py out food-s13 still3     -> out/compare/food-s13-still3-compare.jpg (+ close-up crop)
Each panel is the untouched 1080x1920 render scaled to 540x960; a label bar is added on top."""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

out, name, scn = sys.argv[1], sys.argv[2], sys.argv[3]
LOOKS = [('legacy', '기존 방식'), ('v25', '개선 2.5D'), ('v3d', '실제 3D')]
FONT = os.path.join(os.path.dirname(__file__), '..', 'node_modules', 'pretendard', 'dist', 'public', 'static', 'Pretendard-Bold.otf')
font = ImageFont.truetype(FONT, 30)
dst = os.path.join(out, 'compare'); os.makedirs(dst, exist_ok=True)
PW, PH, BAR = 540, 960, 56

def label_bar():
    im = Image.new('RGB', (PW * 3, BAR), (14, 11, 30)); d = ImageDraw.Draw(im)
    for k, (_, t) in enumerate(LOOKS):
        w = d.textlength(t, font=font); d.text((k * PW + (PW - w) / 2, 10), t, fill=(255, 255, 255), font=font)
    return im

if scn == 'still3':
    ims = [Image.open(os.path.join(out, f'{name}-{scn}-{l}', f'{name}-{scn}-{l}.jpg')) for l, _ in LOOKS]
    c = Image.new('RGB', (PW * 3, PH + BAR)); c.paste(label_bar(), (0, 0))
    for k, im in enumerate(ims): c.paste(im.resize((PW, PH), Image.LANCZOS), (k * PW, BAR))
    c.save(os.path.join(dst, f'{name}-{scn}-compare.jpg'), quality=92)
    # close-up at native pixels: legacy camera frames the beads elsewhere, so each look gets its own box
    boxes = {'legacy': (300, 780, 840, 1080), 'v25': (300, 690, 840, 990), 'v3d': (300, 690, 840, 990)}
    z = Image.new('RGB', (PW * 3, 300 + BAR)); z.paste(label_bar(), (0, 0))
    for k, ((l, _), im) in enumerate(zip(LOOKS, ims)): z.paste(im.crop(boxes[l]), (k * PW, BAR))
    z.save(os.path.join(dst, f'{name}-{scn}-closeup.jpg'), quality=92)
    print('wrote', dst)
else:
    bar = os.path.join(dst, 'bar.png'); label_bar().save(bar)
    ins = []
    for l, _ in LOOKS: ins += ['-i', os.path.join(out, f'{name}-{scn}-{l}', f'{name}-{scn}-{l}.mp4')]
    fc = ''.join(f'[{k}:v]scale={PW}:{PH}:flags=lanczos[v{k}];' for k in range(3)) + '[v0][v1][v2]hstack=3[h];[3:v][h]vstack[o]'
    mp4 = os.path.join(dst, f'{name}-{scn}-compare.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ins, '-i', bar, '-filter_complex', fc, '-map', '[o]',
                    '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4], check=True)
    os.remove(bar); print('wrote', mp4)
