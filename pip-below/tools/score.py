"""Scores one edit of PIP, BELOW Ep.1 (music + sound design, all synthesised).

usage: python3 tools/score.py <edit> <out.wav>      edit: main | shortA | shortB | shortC

Sound events are written in *story* time and mapped through the edit's clips
(edits.json), so a short gets the same moments at its own times, slow motion included.
Music follows the edit's own chord list, so each short starts on its first note and
resolves on its own ending instead of being a cut-down of the film's mix.
"""
import json
import os
import sys
import numpy as np
import scipy.signal as sg
from scipy.io import wavfile

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
EDITS = json.load(open(os.path.join(HERE, '..', 'edits.json')))
rng = np.random.default_rng(20261004)

T_FORM, T_DETACH, T_SURF, T_CROSS, T_POP = 9.2, 16.0, 45.6, 46.0, 47.4
AIR_CAMS = {'M12', 'C3'}
CLOSE_CAMS = {'M3', 'M4', 'M14', 'A1', 'A2', 'A3', 'A4', 'C5'}

CHORDS = {
    'Dmaj9': ['D2', 'A2', 'E3', 'F#3', 'A3', 'C#4'],
    'Bm11': ['B1', 'F#2', 'D3', 'E3', 'A3'],
    'Gmaj7#11': ['G1', 'D2', 'B2', 'F#3', 'C#4'],
    'Em9': ['E2', 'B2', 'D3', 'F#3', 'G3'],
    'F#m7': ['F#1', 'C#2', 'A2', 'E3', 'A3'],
    'Asus': ['A1', 'E2', 'B2', 'D3', 'E3'],
    'Dadd9': ['D2', 'A2', 'D3', 'F#3', 'A3', 'E4', 'F#4'],
}
# how busy the bells are at each story moment (0 = still, 1 = joyful)
ENERGY = [(0, 0.08), (9.2, 0.25), (16, 0.5), (25, 0.72), (29.5, 0.2), (33.6, 0.35), (34.4, 0.95), (38.5, 0.65), (46, 0.35), (50, 0.28), (54, 0.12), (60, 0.1)]


def smooth(a, b, x):
    k = np.clip((x - a) / (b - a), 0.0, 1.0)
    return k * k * (3 - 2 * k)


def midi(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return 440.0 * 2 ** ((names[name[:-1]] + 12 * (int(name[-1]) + 1) - 69) / 12)


def filt(x, kind, f, order=2):
    return sg.sosfilt(sg.butter(order, f, kind, fs=SR, output='sos'), x, axis=0)


def pink(n):
    return sg.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400], rng.standard_normal(n))


class Edit:
    def __init__(self, name):
        self.name = name
        self.E = EDITS[name]
        self.clips = []
        acc = 0.0
        for c in self.E['clips']:
            sp = c.get('speed', 1.0)
            d = (c['to'] - c['from']) / sp
            self.clips.append(dict(c, speed=sp, start=acc, end=acc + d))
            acc += d
        self.dur = acc
        self.N = int(np.ceil(acc * SR))
        self.t = np.arange(self.N) / SR
        self.buf = np.zeros((self.N, 2))      # under-water bus (gets muffled)
        self.air = np.zeros((self.N, 2))      # open-air bus
        self.music = np.zeros((self.N, 2))

    def out_times(self, s):
        """Every output time at which story time s is on screen, with that clip."""
        return [(c['start'] + (s - c['from']) / c['speed'], c) for c in self.clips if c['from'] <= s < c['to']]

    def story(self, o):
        for c in self.clips:
            if o < c['end'] or c is self.clips[-1]:
                return c['from'] + (o - c['start']) * c['speed'], c

    def place(self, bus, start, sig, pan=0.0, gain=1.0):
        i = int(round(start * SR))
        if i >= self.N or len(sig) == 0:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        j = min(self.N, i + len(sig))
        a = (pan + 1) * np.pi / 4
        bus[i:j, 0] += sig[: j - i] * gain * np.cos(a)
        bus[i:j, 1] += sig[: j - i] * gain * np.sin(a)

    def event(self, s, fn, pan=0.0, gain=1.0, bus=None):
        """Place a story-time sound wherever that moment appears in the edit."""
        for o, c in self.out_times(s):
            slow = c['speed'] < 0.99
            sig = fn(slow)
            g = gain * (1.25 if c['cam'] in CLOSE_CAMS else 1.0)
            target = self.air if (bus == 'auto' and c['cam'] in AIR_CAMS) else (self.buf if bus in (None, 'auto') else getattr(self, bus))
            self.place(target, o, sig, pan, g)

    def air_mask(self):
        m = np.zeros(self.N)
        for c in self.clips:
            if c['cam'] in AIR_CAMS:
                i, j = int(c['start'] * SR), int(c['end'] * SR)
                m[i:j] = 1
        return filt(m, 'lowpass', 20, 1).clip(0, 1)


# ─────────────────────────────── instruments
def bloop(f0, tau, chirp, length=0.25, slow=False):
    if slow:
        f0, tau, length, chirp = f0 * 0.62, tau * 2.6, length * 2.6, chirp / 2.6
    tt = np.arange(int(length * SR)) / SR
    ph = 2 * np.pi * np.cumsum(f0 * (1 + chirp * tt)) / SR
    return np.sin(ph) * np.exp(-tt / tau) * (1 - np.exp(-tt / 0.0006))


def bell(f, length=2.6, bright=1.0):
    tt = np.arange(int(length * SR)) / SR
    parts = [(1.0, 1.0, 2.2), (2.0, 0.3, 1.2), (3.01, 0.13 * bright, 0.6), (4.18, 0.07 * bright, 0.35)]
    return sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d) for r, a, d in parts) * (1 - np.exp(-tt / 0.004))


def swish(length, lo, hi, curve=1.0, slow=False):
    if slow:
        length *= 2.5
    L = int(length * SR)
    tt = np.arange(L) / SR
    x = filt(rng.standard_normal(L), 'bandpass', [lo, hi])
    return x * np.sin(np.pi * tt / length) ** (2 * curve)


def boop(slow=False):
    # Pip's nose meets the bubble: a soft rubbery note
    L = 0.22 * (2.5 if slow else 1)
    tt = np.arange(int(L * SR)) / SR
    f = (760 if not slow else 470) * (1 - 0.25 * tt / L)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (0.05 * (2.5 if slow else 1))) * (1 - np.exp(-tt / 0.002))


def query(slow=False):
    # a tiny rising two-note 'hm?'
    out = []
    for f0, f1, L in ((520, 560, 0.09), (600, 780, 0.12)):
        tt = np.arange(int(L * SR)) / SR
        f = f0 + (f1 - f0) * tt / L
        out.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / L) ** 2)
        out.append(np.zeros(int(0.03 * SR)))
    return np.concatenate(out)


def sparkle(slow=False, notes=('A5', 'D6', 'F#6', 'A6')):
    out = np.zeros(int(2.6 * SR))
    for i, n in enumerate(notes):
        b = bell(midi(n), 2.2, 1.4)
        k = int(i * 0.07 * SR)
        out[k:k + len(b)] += b[: len(out) - k]
    return out


# ─────────────────────────────── score
def score(name):
    ed = Edit(name)
    t = ed.t

    # sound design in story time
    s = 0.2
    while s < 60:
        close = 1.0 if (T_FORM - 1 < s < 17 or 54 < s) else 0.35
        f0 = rng.uniform(900, 2800)
        tau = rng.uniform(0.006, 0.016)
        ed.event(s, lambda slow, f0=f0, tau=tau: bloop(f0, tau, 8, 0.08, slow), pan=rng.uniform(-0.25, 0.25), gain=0.09 * close)
        s += rng.exponential(0.22 if close > 0.5 else 0.5)
    for s0 in np.arange(T_FORM, T_DETACH - 0.1, 0.5):           # the forming bubble gurgles
        ed.event(s0, lambda slow, k=(s0 - T_FORM) / 6.8: bloop(110 + 50 * k, 0.09, 0.4, 0.35, slow), gain=0.08 + 0.1 * (s0 - T_FORM) / 6.8)
    for s0, g in ((6.6, 0.05), (8.0, 0.05), (18.7, 0.06), (20.5, 0.05)):
        ed.event(s0, lambda slow: swish(0.35, 900, 3500, 1, slow), gain=g)
    ed.event(12.35, query, pan=0.3, gain=0.07)
    ed.event(15.9, boop, pan=0.2, gain=0.30)
    ed.event(T_DETACH, lambda slow: bloop(330, 0.07, 1.6, 0.5, slow), gain=0.5)
    ed.event(T_DETACH, lambda slow: bloop(62, 0.12, -0.3, 0.6, slow), gain=0.42)
    ed.event(T_DETACH + 0.05, lambda slow: swish(0.28, 1500, 6000, 0.6, slow), pan=0.4, gain=0.09)   # Pip startles
    ed.event(25.6, lambda slow: swish(3.6, 700, 3500, 0.5, slow), pan=-0.3, gain=0.07)              # the school
    ed.event(30.4, query, pan=-0.2, gain=0.07)
    ed.event(31.7, query, pan=0.25, gain=0.07)
    ed.event(32.27, lambda slow: swish(0.25, 1200, 5000, 0.6, slow), pan=0.3, gain=0.1)              # jelly dodge
    ed.event(33.5, lambda slow: sparkle(slow, ('E6', 'A6')), gain=0.06, bus='music')                 # there it is
    ed.event(34.4, lambda slow: swish(0.8, 500, 3000, 0.8, slow), gain=0.09)                          # dash
    ed.event(37.0, lambda slow: sparkle(slow, ('D6', 'F#6', 'A6', 'D7')), gain=0.07, bus='music')    # reunion
    for s0 in np.arange(16.5, 45.0, 2.3):
        ed.event(s0, lambda slow: bloop(rng.uniform(220, 300), 0.05, 0.8, 0.3, slow), pan=rng.uniform(-0.3, 0.3), gain=0.06)
    ed.event(45.6, lambda slow: bloop(180, 0.1, 0.5, 0.5, slow), gain=0.2)                            # bubble meets the ceiling
    ed.event(T_CROSS, lambda slow: swish(1.2, 400, 9000, 0.4, slow) * np.exp(-np.linspace(0, 5, int(1.2 * SR * (2.5 if slow else 1)))), gain=0.25, bus='air')
    ed.event(T_POP, lambda slow: bloop(3200, 0.006, 6, 0.06, slow), gain=0.28, bus='air')
    ed.event(T_POP + 0.03, lambda slow: sparkle(slow), gain=0.08, bus='music')
    ed.event(51.4, lambda slow: sparkle(slow, ('A5', 'E6')), gain=0.05, bus='music')                 # Pip's happy spin
    ed.event(57.4, lambda slow: bell(midi('F#5'), 2.5, 0.8), gain=0.06, bus='music')                  # Pip settles

    # riser toward the surface wherever 43–46 appears
    for o, c in ed.out_times(43.0):
        L = int(min(3.0, ed.dur - o) * SR)
        tt = np.arange(L) / SR
        k = (tt / (L / SR)) ** 2
        nz = rng.standard_normal(L)
        r = filt(nz, 'bandpass', [200, 900]) * (1 - k) + filt(nz, 'bandpass', [900, 4000]) * k
        ed.place(ed.buf, o, r * k * 0.6, gain=0.12)

    # music: pads on the edit's own chords, bells following story energy
    times = [m[0] for m in ed.E['music']] + [ed.dur + 0.5]
    for k, (a, ch) in enumerate(ed.E['music']):
        b = min(times[k + 1] + 1.0, ed.dur + 0.5)
        i0, i1 = int(max(a - 0.6, 0) * SR), min(ed.N, int(b * SR))
        tt = t[i0:i1]
        env = smooth(a - 0.6, a + 1.2, tt) * (1 - smooth(b - 1.4, b, tt))
        if a == 0:
            env = np.maximum(env, (tt < 1.2) * 1.0) * (1 - smooth(b - 1.4, b, tt))
        for n_i, nm in enumerate(CHORDS[ch]):
            f0 = midi(nm)
            for v, det in enumerate((-0.0016, 0.0, 0.0019)):
                ph = 2 * np.pi * f0 * (1 + det) * tt + rng.uniform(0, 6.28)
                sig = sum(np.sin(h * ph) * h ** -2.0 for h in range(1, 9) if f0 * h < 8000)
                a_ = ((n_i + v) % 3 - 1) * 0.45 * np.pi / 4 + np.pi / 4
                ed.music[i0:i1, 0] += sig * env * np.cos(a_) * 0.05 / len(CHORDS[ch])
                ed.music[i0:i1, 1] += sig * env * np.sin(a_) * 0.05 / len(CHORDS[ch])
    o, k = 0.0, 0
    while o < ed.dur - 0.8:
        s_, c = ed.story(o)
        e = np.interp(s_, [p[0] for p in ENERGY], [p[1] for p in ENERGY])
        ch = [m[1] for m in ed.E['music'] if m[0] <= o + 1e-6][-1]
        tones = [n[:-1] for n in CHORDS[ch]]
        octv = 4 + int(e * 2.2) + (k % 3 == 2)
        nm = tones[(k * 2 + (k // 3)) % len(tones)] + str(min(octv, 6))
        ed.place(ed.music, o, bell(midi(nm), 2.4, 0.7 + e), pan=0.5 * np.sin(k * 1.7), gain=0.05 + 0.06 * e)
        o += (1.25 - 0.8 * e) * (2.0 if c['speed'] < 0.99 else 1.0)
        k += 1
    # ending: a resolving chord in the last 1.6 s
    for i, nm in enumerate(['D5', 'F#5', 'A5', 'E6']):
        ed.place(ed.music, ed.dur - 1.9 + i * 0.09, bell(midi(nm), 2.0, 1.0), pan=-0.3 + i * 0.2, gain=0.07)

    # beds
    air = ed.air_mask()
    under_bed = np.stack([filt(pink(ed.N), 'lowpass', 380, 4) * 1.8 + filt(rng.standard_normal(ed.N), 'lowpass', 70) for _ in range(2)], 1)
    under_bed *= (0.15 * (1 - air) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.09 * t)))[:, None]
    sea = np.stack([filt(pink(ed.N), 'bandpass', [140, 2600]) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.16 * t + ch) ** 2) for ch in (0, 1)], 1)
    sea *= (0.11 * air)[:, None]

    muff = air[:, None]
    under_sfx = filt(ed.buf, 'lowpass', 2200)
    music = filt(ed.music, 'lowpass', 3600) * (1 - muff) + ed.music * muff

    def reverb(x, rt60, lp, wet):
        L = int(rt60 * SR)
        tt = np.arange(L) / SR
        y = np.zeros_like(x)
        for c_ in (0, 1):
            ir = filt(rng.standard_normal(L) * np.exp(-6.9 * tt / rt60), 'lowpass', lp)
            ir = np.concatenate([np.zeros(int(0.02 * SR)), ir])
            ir /= np.sqrt(np.sum(ir ** 2))
            y[:, c_] = sg.fftconvolve(x[:, c_], ir)[: len(x)]
        return x * (1 - wet) + y * wet * 1.4

    mix = reverb(music, 3.0, 5200, 0.42) + reverb(under_sfx, 1.6, 1800, 0.3) + under_bed + sea + reverb(ed.air, 1.1, 7000, 0.18)
    mix = filt(mix, 'highpass', 30)
    fi = ed.E['fadeIn']
    master = (smooth(0, fi, t) if fi > 0 else np.minimum(1, t / 0.01)) * (1 - smooth(ed.dur - max(ed.E['fadeOut'], 0.6), ed.dur, t))
    mix *= master[:, None]
    mix *= 10 ** (-19 / 20) / np.sqrt(np.mean(mix ** 2))
    a = np.abs(mix)
    mix = np.where(a < 0.6, mix, np.sign(mix) * (0.6 + 0.3 * np.tanh((a - 0.6) / 0.3)))
    mix *= min(1.0, 0.89 / np.max(np.abs(mix)))
    return ed, mix


if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    ed, mix = score(name)
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print(f'{name}: {ed.dur:.2f}s -> {out}, peak {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS')
