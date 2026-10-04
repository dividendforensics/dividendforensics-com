"""Synthesises the 30-second score for ASCENT (no samples, everything is generated).

usage: python3 tools/score.py out.wav

Timeline (seconds) matches ascent.js:
  0.0  fade in, deep drone, distant seeps
  4.9  the bubble starts to form (close, tiny bubble clicks)
  8.3  release: a bubble 'bloop' (Minnaert resonance with upward chirp)
  8.6+ rising bell arpeggio that climbs with the bubble
  14.4 a fish school sweeps past
  23.5 riser toward the surface
  26.85 the camera breaks the surface: the muffled water opens into air
  27.75 the surfaced bubble pops; chime
  28.2 final chord under the title, fade to 30.0
"""
import sys
import numpy as np
import scipy.signal as sg
from scipy.io import wavfile

SR = 48000
DUR = 30.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(20261004)

T_FORM, T_DETACH, T_CROSS, T_POP = 4.9, 8.3, 26.85, 27.75
CUTS = [9.7, 13.9, 18.3, 22.7, 25.4]


def smooth(a, b, x):
    k = np.clip((x - a) / (b - a), 0.0, 1.0)
    return k * k * (3 - 2 * k)


def midi(name):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    n, o = (name[:-1], int(name[-1]))
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


def sos(kind, f, order=2):
    return sg.butter(order, f, kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return sg.sosfilt(sos(kind, f, order), x, axis=0)


def stereo():
    return np.zeros((N, 2))


def place(buf, start, sig, pan=0.0, gain=1.0):
    i = int(round(start * SR))
    if i >= N:
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    a = (pan + 1) * np.pi / 4
    buf[i:j, 0] += s * np.cos(a)
    buf[i:j, 1] += s * np.sin(a)


def pink(n):
    w = rng.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return sg.lfilter(b, a, w)


# ─────────────────────────────────────────── pad (additive, brightening as the bubble rises)
def pad():
    out = stereo()
    chords = [
        (0.0, 8.7, ['D2', 'A2', 'E3', 'F#3', 'A3']),          # Dmaj9 drone
        (8.0, 14.3, ['B1', 'F#2', 'D3', 'E3', 'A3']),          # Bm11
        (13.6, 18.7, ['G1', 'D2', 'B2', 'F#3', 'C#4']),        # Gmaj7#11
        (18.0, 23.1, ['E2', 'B2', 'D3', 'F#3', 'G3']),         # Em9
        (22.4, 27.1, ['A1', 'E2', 'B2', 'D3', 'F#3', 'A3']),   # A sus, leaning home
        (26.75, 30.0, ['D2', 'A2', 'D3', 'F#3', 'A3', 'E4', 'F#4']),  # D add9, open air
    ]
    # spectral tilt: dark and muffled below, open above the surface
    p = 2.6 - 0.9 * smooth(8.0, 26.0, t)
    p = np.where(t >= T_CROSS, 1.35 - 0.1 * smooth(T_CROSS, 29, t), p)
    for k_c, (a, b, notes) in enumerate(chords):
        i0, i1 = int(a * SR), min(N, int(b * SR))
        tt = t[i0:i1]
        env = smooth(a, a + 1.8, tt) * (1 - smooth(b - 1.5, b, tt)) if b < DUR else smooth(a, a + 0.5, tt)
        pp = p[i0:i1]
        for n_i, nm in enumerate(notes):
            f0 = midi(nm)
            for v, det in enumerate((-0.0016, 0.0, 0.0019)):
                f = f0 * (1 + det)
                vib = 1 + 0.0015 * np.sin(2 * np.pi * (0.13 + 0.05 * v) * tt + rng.uniform(0, 6.28))
                phase = 2 * np.pi * f * np.cumsum(vib) / SR + rng.uniform(0, 6.28)
                sig = np.zeros_like(tt)
                for h in range(1, 13):
                    if f * h > 9000:
                        break
                    sig += np.sin(h * phase) * h ** (-pp)
                pan = ((n_i + v) % 3 - 1) * 0.45
                place(out, a, sig * env / len(notes), pan)
    level = 0.09 + 0.15 * smooth(6, 26, t) + 0.12 * smooth(T_CROSS, 28.6, t)
    out *= level[:, None]
    return out


# ─────────────────────────────────────────── bells
def bell(f, length=3.0, bright=1.0):
    tt = np.arange(int(length * SR)) / SR
    partials = [(1.0, 1.0, 2.4), (2.0, 0.32, 1.3), (3.01, 0.14 * bright, 0.7), (4.18, 0.08 * bright, 0.4), (5.43, 0.04 * bright, 0.25)]
    s = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d) for r, a, d in partials)
    return s * (1 - np.exp(-tt / 0.004))


def bells():
    out = stereo()
    level = 0.26
    for when, nm, g in [(0.9, 'A3', 0.5), (3.0, 'F#4', 0.4), (5.7, 'E4', 0.45), (7.3, 'A4', 0.35)]:
        place(out, when, bell(midi(nm), 4.0, 0.6), pan=rng.uniform(-0.4, 0.4), gain=g)
    # the ascent: a pentatonic line that climbs and quickens with the bubble
    scale = ['D', 'E', 'F#', 'A', 'B']
    pitches = [f'{n}{o}' for o in (4, 5, 6) for n in scale] + ['D7']
    when, k = 8.65, 0
    while when < 26.6:
        prog = (when - 8.65) / (26.6 - 8.65)
        idx = min(len(pitches) - 1, int(prog * (len(pitches) - 1) + (k % 3 == 2) * 1))
        nm = pitches[idx]
        g = 0.22 + 0.18 * prog
        place(out, when, bell(midi(nm), 2.6, 0.8 + 0.6 * prog), pan=0.55 * np.sin(k * 1.7), gain=g)
        when += 1.05 - 0.62 * prog + rng.uniform(-0.04, 0.04)
        k += 1
    # pop: a small chime, then the closing chord's top notes
    for i, nm in enumerate(['D6', 'F#6', 'A6', 'E7']):
        place(out, T_POP + 0.03 + i * 0.045, bell(midi(nm), 3.5, 1.4), pan=-0.3 + i * 0.2, gain=0.22)
    for i, nm in enumerate(['A4', 'D5', 'F#5']):
        place(out, 28.2 + i * 0.12, bell(midi(nm), 2.4, 1.0), pan=-0.2 + i * 0.2, gain=0.18)
    return out * level


# ─────────────────────────────────────────── bubble acoustics
def bloop(f0, tau, chirp, length=0.25, amp=1.0):
    tt = np.arange(int(length * SR)) / SR
    f = f0 * (1 + chirp * tt)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * np.sin(ph) * np.exp(-tt / tau) * (1 - np.exp(-tt / 0.0006))


def bubbles_under():
    out = stereo()
    # tiny bubbles leaving the seep: louder once the camera is close (macro shot)
    when = 0.3
    while when < 12.5:
        close = 0.25 + 0.75 * smooth(4.4, 5.2, when) * (1 - smooth(9.6, 10.5, when))
        f0 = rng.uniform(900, 2800)
        place(out, when, bloop(f0, rng.uniform(0.006, 0.016), rng.uniform(4, 12), 0.08), pan=rng.uniform(-0.25, 0.25), gain=0.10 * close)
        when += rng.exponential(0.16)
    # the hero bubble forming: a low, stretching gurgle
    i0, i1 = int(T_FORM * SR), int(T_DETACH * SR)
    tt = t[i0:i1]
    g = smooth(T_FORM, T_DETACH, tt)
    f = 95 + 60 * g + 6 * np.sin(2 * np.pi * 7 * tt) * g
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.15 + 0.85 * g ** 2) * (1 - smooth(T_DETACH - 0.05, T_DETACH, tt))
    s += filt(rng.standard_normal(len(tt)), 'bandpass', [120, 500]) * 0.25 * g ** 3
    place(out, T_FORM, s, gain=0.18)
    # release: the bloop, a thump and a little second bubble
    place(out, T_DETACH, bloop(330, 0.07, 1.6, 0.5, 1.0), gain=0.55)
    place(out, T_DETACH, bloop(62, 0.12, -0.3, 0.6, 1.0), gain=0.45)
    place(out, T_DETACH + 0.07, bloop(690, 0.03, 2.5, 0.3), pan=0.15, gain=0.25)
    # the rising bubble wobbles: occasional soft low burbles
    for when in np.arange(9.0, 26.0, 1.9):
        place(out, when + rng.uniform(0, 0.4), bloop(rng.uniform(220, 300), 0.05, 0.8, 0.3), pan=rng.uniform(-0.3, 0.3), gain=0.10)
    # fish school sweep
    i0, i1 = int(14.3 * SR), int(18.0 * SR)
    tt = t[i0:i1]
    sw = filt(rng.standard_normal(len(tt)), 'bandpass', [700, 3500])
    flutter = 0.55 + 0.45 * np.sin(2 * np.pi * 11 * tt + 2 * np.sin(2 * np.pi * 0.7 * tt))
    env = smooth(14.3, 15.6, tt) * (1 - smooth(16.6, 18.0, tt))
    pan = np.clip((tt - 14.3) / 3.7 * 1.6 - 0.8, -0.8, 0.8)
    a = (pan + 1) * np.pi / 4
    out[i0:i1, 0] += sw * flutter * env * 0.07 * np.cos(a)
    out[i0:i1, 1] += sw * flutter * env * 0.07 * np.sin(a)
    # cut whooshes
    for c in CUTS:
        L = int(1.0 * SR)
        tt = np.arange(L) / SR
        w = filt(rng.standard_normal(L), 'bandpass', [150, 900]) * np.sin(np.pi * tt / 1.0) ** 3
        place(out, c - 0.6, w, gain=0.05)
    # riser toward the surface
    i0, i1 = int(23.4 * SR), int(T_CROSS * SR)
    tt = t[i0:i1]
    nz = rng.standard_normal(len(tt))
    k = smooth(23.4, T_CROSS, tt)
    r = filt(nz, 'bandpass', [200, 900]) * (1 - k) + filt(nz, 'bandpass', [900, 4000]) * k
    tone = np.sin(2 * np.pi * np.cumsum(midi('D3') * (1 + 0.5 * k ** 2)) / SR) * 0.3
    place(out, 23.4, (r * 0.6 + tone) * k ** 2, gain=0.16)
    return out


def ambience_under():
    out = stereo()
    for ch in (0, 1):
        x = filt(pink(N), 'lowpass', 380, 4) * 1.8
        x += filt(rng.standard_normal(N), 'lowpass', 70, 2) * 1.2
        swell = 0.75 + 0.25 * np.sin(2 * np.pi * 0.09 * t + ch * 1.3)
        out[:, ch] = x * swell
    gate = 1 - smooth(T_CROSS - 0.02, T_CROSS + 0.08, t)
    out *= (0.16 * gate)[:, None]
    return out


def air():
    out = stereo()
    # the breach: splash and a spray of droplets
    L = int(1.4 * SR)
    tt = np.arange(L) / SR
    sp = filt(rng.standard_normal(L), 'bandpass', [400, 9000]) * np.exp(-tt / 0.22) * (1 - np.exp(-tt / 0.008))
    place(out, T_CROSS - 0.03, sp, gain=0.32)
    for _ in range(26):
        when = T_CROSS + rng.uniform(0.05, 0.9)
        place(out, when, bloop(rng.uniform(1800, 5200), rng.uniform(0.004, 0.01), 8, 0.05), pan=rng.uniform(-0.6, 0.6), gain=0.06)
    # open sea at dusk
    for ch in (0, 1):
        x = filt(pink(N), 'bandpass', [140, 2600], 2)
        waves = 0.55 + 0.45 * np.sin(2 * np.pi * 0.16 * t + ch * 0.9) ** 2
        hiss = filt(rng.standard_normal(N), 'bandpass', [2500, 9000]) * 0.15 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + ch))
        out[:, ch] += (x * waves + hiss) * 0.12 * smooth(T_CROSS - 0.05, T_CROSS + 0.25, t)
    # the pop: click and a tiny bright resonance
    click = np.zeros(int(0.02 * SR))
    click[:96] = rng.standard_normal(96) * np.exp(-np.arange(96) / 20)
    place(out, T_POP, filt(click, 'highpass', 2500), gain=0.5)
    place(out, T_POP, bloop(3200, 0.006, 6, 0.06), gain=0.25)
    for _ in range(10):
        place(out, T_POP + rng.uniform(0.25, 0.9), bloop(rng.uniform(2500, 4800), 0.005, 6, 0.04), pan=rng.uniform(-0.4, 0.4), gain=0.05)
    # warm low swell under the title
    i0 = int(27.9 * SR)
    tt = t[i0:]
    sub = np.sin(2 * np.pi * midi('D1') * tt) + 0.4 * np.sin(2 * np.pi * midi('D2') * tt)
    place(out, 27.9, sub * smooth(27.9, 28.9, tt), gain=0.10)
    return out


def reverb(x, rt60, lp_hz, wet, predelay=0.02):
    L = int(rt60 * SR)
    tt = np.arange(L) / SR
    out = np.zeros_like(x)
    for ch in (0, 1):
        ir = rng.standard_normal(L) * np.exp(-6.9 * tt / rt60)
        ir = filt(ir, 'lowpass', lp_hz)
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] = sg.fftconvolve(x[:, ch], ir)[: len(x)]
    return x * (1 - wet) + out * wet * 1.4


def main(path):
    music = pad() + bells()
    under_sfx = bubbles_under()
    # under water everything above ~2 kHz is swallowed
    muffled = filt(under_sfx, 'lowpass', 2200, 2)
    muffle_mix = smooth(T_CROSS - 0.05, T_CROSS + 0.1, t)[:, None]
    music_dark = filt(music, 'lowpass', 3800, 2)
    music = music_dark * (1 - muffle_mix) + music * muffle_mix

    mix = reverb(music, 3.2, 5200, 0.42) + reverb(muffled, 1.6, 1800, 0.35) + ambience_under() + reverb(air(), 1.2, 7000, 0.18)
    mix = filt(mix, 'highpass', 28, 2)
    master = smooth(0.0, 1.6, t) * (1 - smooth(29.15, 30.0, t))
    mix *= master[:, None]
    # level to about -19 dBFS RMS, then a soft knee keeps transients under -1 dBFS
    mix *= 10 ** (-19 / 20) / np.sqrt(np.mean(mix ** 2))
    knee = 0.6
    a = np.abs(mix)
    mix = np.where(a < knee, mix, np.sign(mix) * (knee + 0.3 * np.tanh((a - knee) / 0.3)))
    mix *= min(1.0, 0.89 / np.max(np.abs(mix)))
    wavfile.write(path, SR, (mix * 32767).astype(np.int16))
    rms = np.sqrt(np.mean(mix ** 2))
    print(f'wrote {path}: {DUR:.1f}s, peak {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS, rms {20 * np.log10(rms):.1f} dBFS')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'ascent-score.wav')
