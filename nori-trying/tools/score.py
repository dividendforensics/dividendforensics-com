"""Scores one edit of NORI, TRYING. Ep.1: music, sound effects and the recorded voices.

usage: python3 tools/score.py <edit> <out.wav>       edit: main | shortA | shortB | shortC

Sound effects and voices are written in story time and mapped through the edit's clips,
so a sped-up montage in a short keeps every cue on its picture. The music is played in
output time: at each beat the score asks which story moment is on screen and plays that
section's pattern, so a short gets a continuous groove instead of a time-squashed one.
"""
import json
import os
import sys
import numpy as np
import scipy.signal as sg
from scipy.io import wavfile

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
EDITS = json.load(open(os.path.join(ROOT, 'edits.json')))
LINES = json.load(open(os.path.join(ROOT, 'lines.json')))['lines']
VOICES = json.load(open(os.path.join(ROOT, 'voices.json')))
rng = np.random.default_rng(12)
BPM = 112
BEAT = 60 / BPM


def note(n):
    k = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
    return 440 * 2 ** ((k[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def smooth(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def filt(x, kind, f, order=2):
    return sg.sosfilt(sg.butter(order, f, kind, fs=SR, output='sos'), x)


def env(n, a=0.005, d=0.3):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / a)) * np.exp(-t / d)


# ───────────────────────── instruments
def pluck(f, dur=1.2, bright=0.5):
    """Karplus–Strong string: a ukulele-ish pluck."""
    n = int(dur * SR)
    N = max(2, int(SR / f))
    x = np.zeros(n)
    x[:N] = filt(rng.uniform(-1, 1, N), 'lowpass', 2000 + 6000 * bright) if N > 12 else rng.uniform(-1, 1, N)
    a = np.zeros(N + 2); a[0] = 1; a[N] = -0.497; a[N + 1] = -0.497
    y = sg.lfilter([1], a, x)
    return y * env(n, 0.002, dur * 0.6) * 0.6


def epiano(f, dur=1.6):
    t = np.arange(int(dur * SR)) / SR
    mod = 1.6 * np.exp(-t / 0.25) * np.sin(2 * np.pi * f * t)
    return np.sin(2 * np.pi * f * t + mod) * env(len(t), 0.004, dur * 0.45) * 0.5


def bell(f, dur=1.6, br=1.0):
    t = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in [(1, 1, dur * 0.5), (2.0, 0.3, dur * 0.25), (3.01, 0.15 * br, dur * 0.12)]) * (1 - np.exp(-t / 0.003)) * 0.4


def xylo(f, dur=0.35):
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.03)) * np.exp(-t / 0.09) * 0.5


def bass(f, dur=0.5):
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(len(t), 0.006, dur * 0.7) * 0.6


def shaker(dur=0.08, g=1.0):
    n = int(dur * SR)
    return filt(rng.standard_normal(n), 'bandpass', [5000, 11000]) * env(n, 0.004, 0.02) * 0.25 * g


def noise_burst(dur, lo, hi, a=0.01, d=0.1):
    n = int(dur * SR)
    return filt(rng.standard_normal(n), 'bandpass', [lo, hi]) * env(n, a, d)


def sweep(f0, f1, dur, wave='sine', vib=0.0):
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (f1 / f0) ** (t / dur) * (1 + vib * np.sin(2 * np.pi * 6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) if wave == 'sine' else sg.sawtooth(ph)
    return s * smooth(0, 0.02, t) * (1 - smooth(dur - 0.05, dur, t))


CHORDS = {
    'C': ['C3', 'E3', 'G3', 'C4'], 'G': ['G2', 'D3', 'G3', 'B3'], 'Am': ['A2', 'E3', 'A3', 'C4'], 'F': ['F2', 'C3', 'F3', 'A3'],
    'Cmaj7': ['C3', 'G3', 'B3', 'E4'], 'Fmaj7': ['F2', 'C3', 'E3', 'A3'], 'Dm7': ['D3', 'A3', 'C4', 'F4'], 'G7': ['G2', 'F3', 'B3', 'D4'],
}
PROG = {'bright': ['C', 'G', 'Am', 'F'], 'soft': ['Cmaj7', 'Fmaj7', 'Cmaj7', 'Fmaj7'], 'warm': ['F', 'C', 'Dm7', 'G7']}
# story-time sections → musical style
SECTIONS = [(0, 'morning'), (15, 'calm'), (20.5, 'montage'), (48.5, 'calm'), (55, 'none'), (73, 'clock'), (84, 'busy'), (124.5, 'timelapse'),
            (135, 'none'), (146, 'none'), (150.4, 'panic'), (157.4, 'none'), (171.5, 'warm'), (198.5, 'lullaby'), (224, 'end')]


def style_at(s):
    st = 'none'
    for t0, name in SECTIONS:
        if s >= t0:
            st = name
    return st


class Edit:
    def __init__(self, name):
        self.E = EDITS[name]
        acc, self.clips = 0.0, []
        for c in self.E['clips']:
            sp = c.get('speed', 1.0)
            d = (c['to'] - c['from']) / sp
            self.clips.append(dict(c, speed=sp, start=acc, end=acc + d))
            acc += d
        self.dur = acc
        self.N = int(np.ceil(acc * SR)) + SR // 10
        self.music = np.zeros((self.N, 2)); self.sfx = np.zeros((self.N, 2)); self.vox = np.zeros(self.N)

    def out_times(self, s):
        return [(c['start'] + (s - c['from']) / c['speed'], c) for c in self.clips if c['from'] <= s < c['to']]

    def story(self, o):
        for c in self.clips:
            if o < c['end'] or c is self.clips[-1]:
                return c['from'] + (o - c['start']) * c['speed']

    def put(self, buf, at, sig, pan=0.0, g=1.0):
        i = int(round(at * SR))
        if i < 0 or i >= len(buf):
            return
        j = min(len(buf), i + len(sig))
        if buf.ndim == 1:
            buf[i:j] += sig[: j - i] * g
            return
        a = (pan + 1) * np.pi / 4
        buf[i:j, 0] += sig[: j - i] * g * np.cos(a); buf[i:j, 1] += sig[: j - i] * g * np.sin(a)

    def at(self, s, sig, pan=0.0, g=1.0):
        for o, _ in self.out_times(s):
            self.put(self.sfx, o, sig, pan, g)


def score(name):
    ed = Edit(name)
    # ── voices
    for l in LINES:
        sr, x = wavfile.read(os.path.join(ROOT, 'audio', 'voice', f"{l['id']}.wav"))
        x = x.astype(np.float32) / 32768
        for o, _ in ed.out_times(l['at']):
            ed.put(ed.vox, o, x, g=1.0)
    # ── sound effects (story time)
    t_al = np.arange(int(1.6 * SR)) / SR
    alarm = np.sign(np.sin(2 * np.pi * 1250 * t_al)) * (np.sin(2 * np.pi * 22 * t_al) > 0) * 0.12
    ed.at(0.2, filt(alarm, 'bandpass', [600, 5000]), 0.2, 0.7)
    ed.at(2.9, noise_burst(0.12, 200, 2500, 0.002, 0.03), 0.2, 0.8)                     # slap!
    for k in range(9):                                                                   # morning birds
        s0 = 0.5 + k * 1.6 + rng.uniform(0, 0.6)
        ed.at(s0, sweep(2600, 4200, 0.09, vib=0.05) * 0.06, 0.6, 1.0)
        ed.at(s0 + 0.12, sweep(3800, 2900, 0.08) * 0.05, 0.6, 1.0)
    for k, s0 in enumerate([24.3, 28.3, 32.3, 36.3, 40.3, 44.3]):                        # checklist dings
        ed.at(s0, bell(note('E6') * 2 ** (k / 12), 0.6, 1.5), -0.2, 0.22)
    ed.at(23.6, noise_burst(1.0, 300, 3000, 0.1, 0.4) * 0.3, -0.3, 0.6)                  # pouring tea
    ed.at(35.0, noise_burst(0.15, 1500, 6000, 0.002, 0.05), 0.1, 0.4)                    # candle
    ed.at(44.2, noise_burst(0.03, 2000, 7000, 0.001, 0.01), -0.5, 0.8)                   # lamp click
    ed.at(55.6, sweep(420, 1700, 3.6, vib=0.02) * 0.18, 0.4, 1.0)                        # slide whistle stretch
    ed.at(61.0, sweep(160, 90, 0.25) * 0.4, 0.4, 1.0)                                    # boing back
    ed.at(62.3, noise_burst(0.03, 2000, 7000, 0.001, 0.01), 0, 0.8)                      # remote click
    ed.at(62.6, bell(note('C6'), 0.5) * 0.5 + 0, 0, 0.3)
    for k, (f0, f1, d) in enumerate([(466, 440, 0.45), (440, 415, 0.45), (415, 392, 0.45), (392, 330, 1.3)]):  # sad trombone
        ed.at(65.6 + k * 0.5, filt(sweep(f0 / 2, f1 / 2, d, 'saw', vib=0.012 if k == 3 else 0), 'lowpass', 900) * 0.16, 0, 1.0)
    for s0 in np.arange(72.0, 84.0, 1.0):                                                # the clock ticks
        ed.at(s0, noise_burst(0.02, 2500, 6000, 0.0005, 0.006), 0, 0.5)
    ed.at(82.2, noise_burst(0.1, 300, 2000, 0.005, 0.05), -0.4, 0.5)                     # frame nudged
    for s0 in np.arange(87.2, 100.0, 0.42):                                              # dusting swishes
        ed.at(s0, noise_burst(0.3, 1500, 7000, 0.05, 0.08) * 0.35, 0.5 * np.sin(s0), 0.6)
    ed.at(84.3, sweep(180, 420, 0.3) * 0.25, 0.2, 1.0)                                 # hop off the sofa
    for s0 in list(np.arange(84.95, 87.0, 0.11)) + list(np.arange(123.0, 124.5, 0.11)):  # squishy little steps
        ed.at(s0, filt(noise_burst(0.05, 150, 1200, 0.003, 0.02), 'lowpass', 900) * 0.6, 0.4, 0.7)
    for s0 in (85.0, 85.1, 85.2, 85.3):                                                  # cushions hit the floor
        ed.at(s0, filt(noise_burst(0.2, 60, 600, 0.002, 0.06), 'lowpass', 500), -0.2, 1.4)
    for k in range(12):                                                                  # books shuffle
        ed.at(101.8 + k * 0.55, noise_burst(0.06, 800, 4000, 0.001, 0.02), 0.5, 0.7)
    ed.at(109.0, sum(bell(note(n), 1.6, 1.2) for n in ['C6', 'E6', 'G6']) * 0.5, 0.3, 0.35)
    for k in range(3):                                                                   # three waterings
        ed.at(116.0 + k * 0.4, noise_burst(4.2, 400, 5000, 0.2, 2.5) * 0.25, -0.5 + k * 0.5, 0.6)
    for k in range(3):
        ed.at(120.8 + k * 0.2, bell(note('G6') * 2 ** (k * 4 / 12), 0.5, 1.4), -0.4 + k * 0.4, 0.2)
    for k, s0 in enumerate(np.cumsum(np.linspace(0.5, 0.06, 60)) + 124.8):               # time-lapse ticking
        if s0 < 135:
            ed.at(s0, noise_burst(0.015, 2500, 6000, 0.0005, 0.005), 0, 0.5)
    ed.at(135.2, sum(xylo(note(n)) for n in ['C5', 'E5', 'G5']) + xylo(note('C6')), 0, 0.5)   # ta-da
    for k in range(6):                                                                   # phone buzz
        n = int(0.16 * SR); tt = np.arange(n) / SR
        ed.at(138.0 + k * 0.22 if k < 3 else 138.9 + k * 0.22, np.sin(2 * np.pi * 150 * tt) * np.sin(np.pi * tt / 0.16) * 0.3, 0.3, 0.8)
    ed.at(146.0, sum(epiano(note(n), 1.5) for n in ['B3', 'F4', 'C5']) * 0.6, 0, 0.6)    # what time is it?!
    for s0 in np.arange(150.6, 157.0, 0.33):                                             # panic whooshes
        ed.at(s0, noise_burst(0.25, 600, 5000, 0.04, 0.06) * 0.4, rng.uniform(-0.6, 0.6), 0.7)
    for s0 in (153.2, 153.6, 153.8):
        ed.at(s0, filt(noise_burst(0.2, 60, 600, 0.002, 0.06), 'lowpass', 500), 0, 1.2)
    for k in range(3):                                                                   # knock knock knock
        ed.at(160.0 + k * 0.22, filt(noise_burst(0.12, 80, 900, 0.001, 0.03), 'lowpass', 700), -0.7, 1.6)
    ed.at(164.2, filt(sweep(300, 520, 1.2, 'saw') * 0.05, 'bandpass', [400, 2500]), -0.7, 1.0)  # door creak
    for s0 in np.arange(165.6, 170.2, 0.075):                                            # crab feet
        ed.at(s0, noise_burst(0.015, 3000, 8000, 0.0005, 0.004), -0.5 + (s0 - 165.6) / 5, 0.5)
    ed.at(170.4, sweep(200, 520, 0.35) * 0.25, 0.2, 1.0)                                 # hop
    ed.at(176.1, noise_burst(0.05, 1500, 5000, 0.002, 0.02), 0.2, 0.5)                   # mug handover
    ed.at(196.6, bell(note('E6'), 0.6) + np.concatenate([np.zeros(int(0.18 * SR)), bell(note('A6'), 0.8)])[:len(bell(note('E6'), 0.6))], 0, 0.3)  # update done
    ed.at(209.0, noise_burst(3.4, 300, 3000, 0.6, 2.0) * 0.25, 0.2, 0.6)                 # blanket
    ed.at(217.6, noise_burst(0.03, 2000, 7000, 0.001, 0.01), 0.2, 0.7)                   # TV off
    for s0 in np.arange(206.5, 232, 3.4):                                                # tiny snores
        n = int(1.4 * SR); tt = np.arange(n) / SR
        ed.at(s0, filt(rng.standard_normal(n), 'bandpass', [150, 900]) * np.sin(np.pi * tt / 1.4) ** 2 * 0.05, -0.1, 1.0)
    # ── music in output time
    o, beat = 0.0, 0
    while o < ed.dur - 0.05:
        s = ed.story(o)
        st = style_at(s)
        bar, b = beat // 4, beat % 4
        prog = PROG['soft'] if st in ('morning', 'calm', 'clock', 'lullaby') else PROG['warm'] if st in ('warm', 'end') else PROG['bright']
        ch = CHORDS[prog[bar % 4]]
        if st == 'morning' and b == 0 and bar % 2 == 0:
            for k, n in enumerate(ch):
                ed.put(ed.music, o + k * 0.06, epiano(note(n), 3.0), -0.3 + k * 0.2, 0.5)
        elif st == 'calm' and b in (0, 2):
            ed.put(ed.music, o, pluck(note(ch[(b // 2) + 1]) * 2, 1.4), 0.2, 0.7)
            if b == 0:
                ed.put(ed.music, o, bass(note(ch[0]) / 2, 1.2), 0, 0.5)
        elif st in ('montage', 'busy', 'end'):
            # strum: down on 1 and 3, up-strum on the 'and' of 2 and 4
            for sub, strength in ((0, 1.0), (0.5, 0.0), (1.0 if b % 2 == 0 else 0.5, 0.0)):
                pass
            strum = b in (0, 2) or st == 'busy'
            if strum:
                for k, n in enumerate(ch if b % 2 == 0 else ch[::-1]):
                    ed.put(ed.music, o + k * 0.012, pluck(note(n) * 2, 0.9, 0.6), -0.2 + k * 0.13, 0.42)
            ed.put(ed.music, o + BEAT / 2, sum(pluck(note(n) * 2, 0.5, 0.4) for n in ch[1:3]), 0.25, 0.25)
            if b in (0, 2):
                ed.put(ed.music, o, bass(note(ch[0]) / (1 if st == 'end' else 2), BEAT * 1.8), 0, 0.6)
            for q in range(2 if st != 'busy' else 4):
                ed.put(ed.music, o + q * BEAT / (2 if st != 'busy' else 4), shaker(g=0.7 if q % 2 else 1.0), 0.4, 1.0)
            if st == 'busy' and b == 3:
                ed.put(ed.music, o, xylo(note(ch[3]) * 2), -0.4, 0.4)
        elif st == 'clock' and b == 0:
            ed.put(ed.music, o, pluck(note(ch[2]) * 2, 1.8, 0.3), 0.3, 0.35)
        elif st == 'timelapse':
            for q in range(4):
                ed.put(ed.music, o + q * BEAT / 4, xylo(note(ch[q % 4]) * 2 * (2 if q == 3 else 1), 0.25), -0.3 + q * 0.2, 0.35)
        elif st == 'panic':
            for q in range(4):
                ed.put(ed.music, o + q * BEAT / 4, xylo(note(['C5', 'D#5', 'F#5', 'A5'][q]) * (1 + 0.06 * (beat % 2)), 0.2), 0.3 * (q - 1.5), 0.4)
        elif st == 'warm':
            if b == 0:
                for k, n in enumerate(ch):
                    ed.put(ed.music, o + k * 0.05, epiano(note(n), 2.4), -0.3 + k * 0.2, 0.32)
                ed.put(ed.music, o, bass(note(ch[0]) / 2, 1.6), 0, 0.45)
            ed.put(ed.music, o + BEAT * 0.5, pluck(note(ch[(b % 3) + 1]) * 2, 0.8, 0.4), 0.3, 0.35)
        elif st == 'lullaby' and b in (0, 2):
            ed.put(ed.music, o, bell(note(ch[(beat // 2) % 4]) * 4, 2.2, 0.8), -0.3 + 0.2 * (b // 2), 0.35)
            if b == 0:
                ed.put(ed.music, o, epiano(note(ch[0]), 3.0), 0, 0.25)
        o += BEAT * (1.25 if st == 'lullaby' else 1.0)
        beat += 1
    # title sting and the last chord
    for o, _ in ed.out_times(9.8):
        for k, n in enumerate(['C5', 'E5', 'G5', 'C6']):
            ed.put(ed.music, o + k * 0.07, pluck(note(n), 1.6, 0.7), -0.3 + 0.2 * k, 0.5)
    for k, n in enumerate(['F4', 'A4', 'C5', 'E5', 'G5']):
        ed.put(ed.music, ed.dur - 2.4 + k * 0.08, bell(note(n), 2.2), -0.3 + 0.15 * k, 0.4)

    # ── mix: duck music under the voices
    vox_env = np.convolve(np.abs(ed.vox), np.ones(SR // 20) / (SR // 20), 'same')
    duck = 1 - 0.55 * np.clip(vox_env / (np.max(vox_env) * 0.25 + 1e-9), 0, 1)
    duck = filt(duck, 'lowpass', 6, 1)
    room = np.stack([filt(rng.standard_normal(ed.N), 'lowpass', 300) * 0.006 for _ in range(2)], 1)

    def reverb(x, rt, wet):
        L = int(rt * SR); tt = np.arange(L) / SR; y = np.zeros_like(x)
        for c in (0, 1):
            ir = filt(rng.standard_normal(L) * np.exp(-6.9 * tt / rt), 'lowpass', 6000); ir /= np.sqrt(np.sum(ir ** 2))
            y[:, c] = sg.fftconvolve(x[:, c], ir)[: len(x)]
        return x * (1 - wet) + y * wet

    vox = np.stack([ed.vox, ed.vox], 1)
    vox = reverb(vox, 0.35, 0.08)
    mix = reverb(ed.music, 1.4, 0.22) * (0.55 * duck)[:, None] + reverb(ed.sfx, 0.5, 0.12) * 0.9 + vox * 1.25 + room
    mix = filt(mix.T, 'highpass', 35).T
    t = np.arange(ed.N) / SR
    fi = ed.E['fadeIn']
    master = (smooth(0, fi, t) if fi > 0 else 1.0) * (1 - smooth(ed.dur - max(ed.E['fadeOut'], 0.6), ed.dur, t))
    mix *= np.asarray(master)[:, None] if np.ndim(master) else master
    mix = mix[: int(ed.dur * SR)]
    mix *= 10 ** (-18 / 20) / (np.sqrt(np.mean(mix ** 2)) + 1e-9)
    a = np.abs(mix)
    mix = np.where(a < 0.6, mix, np.sign(mix) * (0.6 + 0.3 * np.tanh((a - 0.6) / 0.3)))
    mix *= min(1.0, 0.89 / np.max(np.abs(mix)))
    return ed, mix


if __name__ == '__main__':
    name, out = sys.argv[1], sys.argv[2]
    ed, mix = score(name)
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print(f'{name}: {ed.dur:.2f}s -> {out}')
