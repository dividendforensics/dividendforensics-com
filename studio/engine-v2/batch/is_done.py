#!/usr/bin/env python3
"""Exit 0 if this batch config already has a finished, checked MP4 (so a restarted run can skip it).
usage: batch/is_done.py <config.json>"""
import glob, json, os, re, subprocess, sys
c = json.load(open(sys.argv[1]))
name = os.path.splitext(os.path.basename(sys.argv[1]))[0] + f"-s{c['seed']}-v3d-nebula"
d = os.path.join('out', name)
mp4 = os.path.join(d, name + '.mp4'); meta = os.path.join(d, 'meta.txt')
if not (os.path.exists(mp4) and os.path.exists(meta)): sys.exit(1)
if subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'null', '-'], capture_output=True, text=True).stderr.strip(): sys.exit(1)
m = re.search(r'true peak (-?[\d.]+) dBTP', open(meta, encoding='utf8').read())
sys.exit(0 if m and float(m.group(1)) <= -1.5 else 1)
