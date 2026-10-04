"""Records every line in lines.json with Piper (offline neural TTS) and writes, per line,
a 48 kHz WAV plus its duration and a mouth-opening envelope at 24 fps for lip sync.

usage: python3 tools/voices.py <dir with piper .onnx voices> <out dir>
writes <out dir>/<id>.wav and voices.json next to lines.json
"""
import json
import os
import subprocess
import sys
import numpy as np
from scipy.io import wavfile
import scipy.signal as sg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
VOICE_DIR, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
spec = json.load(open(os.path.join(ROOT, 'lines.json')))
FPS, SR = 24, 48000
meta = {}
for ln in spec['lines']:
    v = spec['voices'][ln['who']]
    raw = os.path.join(OUT, f"{ln['id']}_raw.wav")
    subprocess.run([sys.executable, '-m', 'piper', '-m', os.path.join(VOICE_DIR, v['model'] + '.onnx'), '-f', raw,
                    '--length-scale', str(ln.get('length', v['length'])), '--noise-scale', str(v['noise'])],
                   input=ln['text'].encode(), check=True, capture_output=True)
    # pitch up without changing timing: resample, then stretch back
    f = 2 ** (v['pitch'] / 12)
    sr_in = int(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=sample_rate', '-of', 'csv=p=0', raw],
                               capture_output=True, text=True).stdout.strip())
    out = os.path.join(OUT, f"{ln['id']}.wav")
    af = f'asetrate={int(sr_in * f)},aresample={SR},atempo={1 / f:.5f},highpass=f=90,silenceremove=start_periods=1:start_threshold=-50dB'
    if ln.get('whisper'):
        af += ',volume=0.55,highpass=f=220'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', raw, '-af', af, '-ac', '1', '-ar', str(SR), out], check=True)
    os.remove(raw)
    sr, x = wavfile.read(out)
    x = x.astype(np.float32) / 32768
    # mouth envelope: band energy of the voice, smoothed, 24 per second
    band = sg.sosfilt(sg.butter(2, [250, 3000], 'bandpass', fs=sr, output='sos'), x)
    hop = sr // FPS
    env = np.array([np.sqrt(np.mean(band[i:i + hop] ** 2)) for i in range(0, len(band), hop)])
    env = np.clip(env / (np.percentile(env, 95) + 1e-6), 0, 1.2)
    meta[ln['id']] = {'dur': round(len(x) / sr, 3), 'mouth': [round(float(e), 2) for e in env]}
    print(f"{ln['id']} {ln['who']:5s} {len(x) / sr:5.2f}s  {ln['text']}")
json.dump(meta, open(os.path.join(ROOT, 'voices.json'), 'w'))
