"""A 12-second score for the Lottie edition (bubble -> pop -> sun -> 오름).

usage: python3 tools/lottie_score.py out.wav
Frame numbers match tools/make_lottie.py at 30 fps.
"""
import sys
import numpy as np
import scipy.signal as sg
from scipy.io import wavfile

SR, DUR = 48000, 12.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)
F = lambda frame: frame / 30.0
F_FORM, F_RISE, F_POP, F_SUN, F_DUSK, F_LOGO = F(18), F(62), F(252), F(262), F(296), F(308)


def midi(n):
    k = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return 440 * 2 ** ((k[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def smooth(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def place(buf, at, sig, pan=0.0, g=1.0):
    i = int(at * SR)
    j = min(N, i + len(sig))
    a = (pan + 1) * np.pi / 4
    buf[i:j, 0] += sig[: j - i] * g * np.cos(a)
    buf[i:j, 1] += sig[: j - i] * g * np.sin(a)


def bell(f, L=2.4, br=1.0):
    tt = np.arange(int(L * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d) for r, a, d in [(1, 1, 2), (2, .3, 1.1), (3.01, .12 * br, .5)]) * (1 - np.exp(-tt / .004))


def bloop(f0, tau, chirp, L=0.25):
    tt = np.arange(int(L * SR)) / SR
    return np.sin(2 * np.pi * np.cumsum(f0 * (1 + chirp * tt)) / SR) * np.exp(-tt / tau) * (1 - np.exp(-tt / .0006))


mus, sfx = np.zeros((N, 2)), np.zeros((N, 2))
# pad: D drone that opens into a full D major add9 at the sun
for notes, a, b in [(['D2', 'A2', 'E3', 'F#3'], 0, F_SUN + 0.6), (['D2', 'A2', 'D3', 'F#3', 'A3', 'E4'], F_SUN - 0.3, DUR)]:
    i0, i1 = int(a * SR), int(min(b, DUR) * SR)
    tt = t[i0:i1]
    env = smooth(a, a + 1.0, tt) * (1 - smooth(b - 0.6, b, tt)) if b < DUR else smooth(a, a + 1.0, tt)
    for n in notes:
        ph = 2 * np.pi * midi(n) * tt
        s = sum(np.sin(h * ph) / h ** 2.2 for h in range(1, 8))
        mus[i0:i1] += (s * env * 0.035)[:, None]
# bubble is born, then the rising line
place(sfx, F_FORM + 0.1, bloop(380, .06, 1.2, .4), 0, .35)
place(sfx, F_RISE, bloop(300, .07, 1.6, .5), 0, .45)
scale = ['D5', 'E5', 'F#5', 'A5', 'B5', 'D6', 'E6', 'F#6', 'A6']
for k, at in enumerate(np.linspace(F_RISE + 0.3, F_POP - 0.4, 9)):
    place(mus, at, bell(midi(scale[k]), 2.2, .8), .5 * np.sin(k * 1.7), .08 + .01 * k)
for _ in range(30):
    place(sfx, rng.uniform(1.0, F_POP), bloop(rng.uniform(1200, 3000), rng.uniform(.005, .012), 8, .06), rng.uniform(-.3, .3), .05)
# pop, then the sun rises out of the ring
place(sfx, F_POP, bloop(3000, .006, 6, .06), 0, .5)
click = np.zeros(400); click[:80] = rng.standard_normal(80) * np.exp(-np.arange(80) / 15)
place(sfx, F_POP, sg.sosfilt(sg.butter(2, 2500, 'high', fs=SR, output='sos'), click), 0, .5)
for i, n in enumerate(['D6', 'F#6', 'A6', 'E7']):
    place(mus, F_SUN + i * .06, bell(midi(n), 3.0, 1.4), -.3 + .2 * i, .09)
# the logotype draws on: low swell and a soft chord
tt = t[int(F_DUSK * SR):]
place(mus, F_DUSK, (np.sin(2 * np.pi * midi('D1') * tt) + .4 * np.sin(2 * np.pi * midi('D2') * tt)) * smooth(F_DUSK, F_DUSK + 1, tt + F_DUSK), 0, .12)
for i, n in enumerate(['A4', 'D5', 'F#5', 'A5']):
    place(mus, F_LOGO + 0.4 + i * .12, bell(midi(n), 2.6, 1.0), -.2 + .15 * i, .08)

L = int(2.6 * SR); tt = np.arange(L) / SR
out = mus.copy()
for c in (0, 1):
    ir = sg.sosfilt(sg.butter(2, 5000, 'low', fs=SR, output='sos'), rng.standard_normal(L) * np.exp(-6.9 * tt / 2.6))
    ir /= np.sqrt(np.sum(ir ** 2))
    out[:, c] = mus[:, c] * .6 + sg.fftconvolve(mus[:, c], ir)[:N] * .55 + sfx[:, c]
out *= (smooth(0, .4, t) * (1 - smooth(DUR - .8, DUR, t)))[:, None]
out *= 10 ** (-19 / 20) / np.sqrt(np.mean(out ** 2))
out = np.clip(out, -0.89, 0.89)
wavfile.write(sys.argv[1], SR, (out * 32767).astype(np.int16))
print('wrote', sys.argv[1])
