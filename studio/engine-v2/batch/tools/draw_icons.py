#!/usr/bin/env python3
"""Draws the four named dessert/fruit icons as 512x512 transparent PNGs (drawn at 1024 and downscaled).
usage: python3 batch/tools/draw_icons.py <out_dir>"""
import math, random, sys, os
from PIL import Image, ImageDraw, ImageFilter

S = 1024
def canvas():
    return Image.new('RGBA', (S, S), (0, 0, 0, 0))

def shade_disc(im, box, base, edge, hi, grain=None, seed=1):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.ellipse(box, fill=edge)                                   # rim / shadow side
    d.ellipse((x0 + 14, y0 + 10, x1 - 22, y1 - 18), fill=base)  # body, lit from top-left
    if grain:
        rnd = random.Random(seed)
        for _ in range(grain[0]):
            r = rnd.uniform(grain[1], grain[2])
            a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(0, 0.8)
            cx = (x0 + x1) / 2 + math.cos(a) * rr * (x1 - x0) / 2
            cy = (y0 + y1) / 2 + math.sin(a) * rr * (y1 - y0) / 2
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=grain[3])
    d.ellipse((x0 + 90, y0 + 60, x0 + 250, y0 + 170), fill=hi)  # soft highlight
    return im

def soft_shadow(im, box):
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((box[0] + 20, box[1] + 40, box[2] + 10, box[3] + 40), fill=(0, 0, 0, 110))
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), im)

def injeolmi():   # soy-flour dusted mochi: off-white with tan powder
    im = canvas(); box = (150, 170, 874, 830)
    im = soft_shadow(im, box)
    return shade_disc(im, box, (246, 238, 218, 255), (205, 186, 150, 255), (255, 252, 240, 200),
                      grain=(420, 3, 7, (214, 196, 160, 255)), seed=3)

def heukimja():   # black sesame mochi: charcoal with pale flecks
    im = canvas(); box = (150, 170, 874, 830)
    im = soft_shadow(im, box)
    return shade_disc(im, box, (58, 56, 64, 255), (22, 21, 26, 255), (150, 146, 160, 200),
                      grain=(260, 4, 9, (210, 206, 214, 255)), seed=5)

def chocochip():  # golden cookie with dark chocolate chips
    im = canvas(); box = (120, 120, 904, 904)
    im = soft_shadow(im, box)
    im = shade_disc(im, box, (222, 165, 84, 255), (150, 92, 36, 255), (250, 214, 150, 230))
    d = ImageDraw.Draw(im); rnd = random.Random(7)
    for _ in range(26):
        a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(0.1, 0.78)
        cx = 512 + math.cos(a) * rr * 330; cy = 512 + math.sin(a) * rr * 330
        r = rnd.uniform(26, 44)
        d.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill=(64, 36, 20, 255))
    return im

def jadu():       # plum: deep purple-red fruit with bloom, a leaf and a stem
    im = canvas(); box = (170, 200, 854, 880)
    im = soft_shadow(im, box)
    im = shade_disc(im, box, (112, 32, 82, 255), (58, 12, 46, 255), (200, 120, 170, 210))
    d = ImageDraw.Draw(im)
    d.line((512, 210, 528, 120), fill=(92, 60, 36, 255), width=18)          # stem
    d.ellipse((520, 120, 700, 210), fill=(96, 170, 70, 255))                 # leaf
    d.line((530, 140, 660, 190), fill=(60, 120, 46, 255), width=6)           # leaf vein
    d.ellipse((230, 300, 300, 380), fill=(160, 90, 140, 90))                 # bloom spot
    return im

if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for name, fn in [('injeolmi', injeolmi), ('heukimja', heukimja), ('chocochip', chocochip), ('jadu', jadu)]:
        fn().resize((512, 512), Image.LANCZOS).save(os.path.join(out, name + '.png'))
        print('wrote', name)
