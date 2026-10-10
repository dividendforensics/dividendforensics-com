"""Soundtrack synthesized from the simulation's event log: a tension track whose tempo
rises as entries die, heartbeat in the final stretch, and hit/death/win sound effects."""
import json, os, sys, wave
import numpy as np
out = sys.argv[1]
L = json.load(open(os.path.join(out, 'log.json')))
SR = 44100
N = int(SR * (L['dur'] + 0.6))
mus = np.zeros((N, 2)); sfx = np.zeros((N, 2))
rng = np.random.default_rng(L['seed'])

def ts(d): return np.arange(int(d * SR)) / SR
def place(buf, t, sig, pan=0.0, amp=1.0):
    i = int(round(t * SR))
    if i >= N or i + len(sig) <= 0: return
    if i < 0: sig, i = sig[-i:], 0
    n = min(len(sig), N - i); pan = max(-1.0, min(1.0, pan))
    buf[i:i+n, 0] += sig[:n] * amp * np.cos((pan + 1) * np.pi / 4) * 1.4142
    buf[i:i+n, 1] += sig[:n] * amp * np.sin((pan + 1) * np.pi / 4) * 1.4142
def kick(d=0.4, f0=160, f1=42, dec=7.0):
    t = ts(d); f = f1 + (f0 - f1) * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * dec)
def noise(d, dec): t = ts(d); return rng.uniform(-1, 1, len(t)) * np.exp(-t * dec)
def hp(x): return np.diff(x, prepend=0.0)
def saw(f, d, harm, dec):
    t = ts(d); return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harm + 1)) * np.exp(-t * dec)
def tone(f, d, dec): t = ts(d); return (np.sin(2*np.pi*f*t) + 0.3*np.sin(4*np.pi*f*t)) * np.exp(-t * dec)

ev = L['events']
fr = L['frames']; ft = np.array([x['t'] for x in fr]); n_ent = L['n']
tension = np.interp(np.arange(N) / SR, ft, [1 - (x['alive'] - 1) / (n_ent - 1) for x in fr])

# --- music ---
t_all = np.arange(N) / SR
pad = sum(np.sin(2*np.pi*f*t_all) for f in (110, 130.81, 164.81, 220)) * (0.5 + 0.5*np.sin(2*np.pi*0.25*t_all))
mus[:, 0] += pad * (0.035 + 0.05 * tension); mus[:, 1] += pad * (0.035 + 0.05 * tension)
BASS = [55, 55, 65.41, 49.0]
for e in ev:
    if e['type'] != 'beat': continue
    t, i, T, d, fin = e['t'], e['i'], e['T'], e['dur'], e['final']
    if not fin: place(mus, t, kick(), 0, 0.95)
    note = BASS[(i // 4) % 4]; harm = 2 + int(T * 9)
    for q in (0, 0.5): place(mus, t + q * d + 0.02, saw(note, d * 0.46, harm, 5), 0, 0.33)
    if T > 0.25:
        for q in range(4): place(mus, t + q * d / 4, hp(noise(0.04, 90)), 0.35 if q % 2 else -0.35, 0.16 if q % 2 else 0.09)
    if T > 0.5 and i % 2 == 1 and not fin:
        place(mus, t, hp(noise(0.2, 18)), 0, 0.42); place(mus, t, tone(190, 0.12, 25), 0, 0.25)
fin_t = next((e['t'] for e in ev if e['type'] == 'final'), None)
win_t = next((e['t'] for e in ev if e['type'] == 'win'), None)
if fin_t is not None and win_t is not None and win_t > fin_t:
    d = win_t - fin_t; t = ts(d); ramp = (t / d) ** 2
    riser = hp(rng.uniform(-1, 1, len(t))) * ramp * 0.3 + np.sin(2*np.pi*np.cumsum(220 + 900*ramp)/SR) * ramp * 0.12
    place(mus, fin_t, riser)
# slow-motion: music goes "underwater" (low-pass) while time is slowed
mask = np.interp(t_all, ft, [1.0 if x['ts'] < 0.6 else 0.0 for x in fr])
mask = np.convolve(mask, np.ones(int(0.06*SR)) / int(0.06*SR), mode='same')
lp = np.zeros_like(mus); a = 0.04; yl = yr = 0.0
for k in range(N):
    yl += a * (mus[k, 0] - yl); yr += a * (mus[k, 1] - yr); lp[k, 0] = yl; lp[k, 1] = yr
mus = mus * (1 - mask[:, None]) + lp * mask[:, None] * 1.6

# --- sfx ---
PENT = [220, 261.63, 293.66, 329.63, 392, 440, 523.25, 587.33, 659.25, 784, 880, 1046.5]
last = {}
def ok(k, gap, t):
    if t - last.get(k, -9) < gap: return False
    last[k] = t; return True
for e in ev:
    t, k, x = e['t'], e['type'], e.get('x', 0.0)
    if k == 'bounce' and e.get('v', 0) > 4 and ok('b', 0.035, t):
        place(sfx, t, tone(PENT[e['i'] % len(PENT)], 0.3, 13), x, min(1, e['v'] / 14) * 0.22)
    elif k == 'clack' and ok('c', 0.04, t): place(sfx, t, hp(noise(0.03, 120)), x, 0.22)
    elif k == 'hit':
        place(sfx, t, kick(0.3, 120, 50, 10), x, 0.8); place(sfx, t, hp(noise(0.12, 35)), x, 0.55)
        place(sfx, t, tone(1250, 0.2, 18), x, 0.12)
    elif k == 'near' and ok('n', 0.4, t):
        d = 0.35; tt = ts(d); place(sfx, t - 0.1, hp(rng.uniform(-1, 1, len(tt))) * np.sin(np.pi * tt / d) ** 2, x, 0.3)
    elif k == 'die':
        place(sfx, t, kick(0.8, 140, 30, 4.5), 0, 1.0); place(sfx, t, hp(noise(0.7, 5)), x, 0.45)
        for j, f in enumerate((523.25, 392, 261.63)): place(sfx, t + 0.08 + 0.11 * j, tone(f, 0.3, 9), x, 0.25)
    elif k == 'heart':
        place(sfx, t, np.sin(2*np.pi*52*ts(0.16)) * np.exp(-ts(0.16)*22), 0, 0.9)
        place(sfx, t + 0.17, np.sin(2*np.pi*48*ts(0.16)) * np.exp(-ts(0.16)*22), 0, 0.6)
    elif k == 'final': place(sfx, t, kick(1.4, 90, 26, 2.2), 0, 1.0)
    elif k == 'count': place(sfx, t, tone(880, 0.18, 14), 0, 0.35)
    elif k == 'go':
        place(sfx, t, tone(1760, 0.35, 8), 0, 0.35); place(sfx, t, kick(0.5, 170, 40, 6), 0, 0.9)
    elif k == 'win':
        place(sfx, t, kick(0.9, 180, 35, 3.5), 0, 1.2); place(sfx, t, hp(noise(2.2, 2.0)), 0, 0.4)
        for f in (220, 277.18, 329.63, 440, 554.37): place(sfx, t + 0.05, saw(f, 3.2, 6, 1.2), 0, 0.09)
        for j, f in enumerate((880, 1108.73, 1318.51, 1760)): place(sfx, t + 0.15 + 0.12 * j, tone(f, 0.6, 5), (j - 1.5) / 3, 0.2)

mix = mus * 0.8 + sfx
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix = mix / (np.abs(mix).max() or 1) * 0.89
with wave.open(os.path.join(out, 'audio.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print(f'audio {N/SR:.1f}s, {len(ev)} events')
