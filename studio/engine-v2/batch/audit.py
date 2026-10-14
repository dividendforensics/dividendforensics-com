#!/usr/bin/env python3
"""Audit one finished batch item: decode errors, resolution/fps, duration, true peak, LUFS.
With --fix, lowers the audio (video stream copied) until true peak <= -1.5 dBTP, then rewrites the meta.txt audio line.
usage: batch/audit.py <out_dir> [--fix]"""
import glob, json, os, re, subprocess, sys

def sh(args):
    return subprocess.run(args, capture_output=True, text=True)

def measure(mp4):
    e = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', mp4, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr
    tp = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', e)[-1]
    I = re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1]
    return float(tp), float(I)

def info(mp4):
    p = sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,duration', '-of', 'json', mp4])
    st = json.loads(p.stdout)['streams'][0]
    dec = sh(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'null', '-']).stderr.strip()
    return st['width'], st['height'], st['r_frame_rate'], float(st['duration']), len(dec.splitlines())

def main():
    d = sys.argv[1]; fix = '--fix' in sys.argv
    mp4 = glob.glob(os.path.join(d, '*.mp4'))[0]
    tp, I = measure(mp4)
    if fix and tp > -1.5:
        for _ in range(4):
            tmp = os.path.join(d, 'fix.mp4')
            g = -(tp + 2.5)
            sh(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-c:v', 'copy', '-af', f'volume={g:.2f}dB', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', tmp])
            os.replace(tmp, mp4)
            tp, I = measure(mp4)
            if tp <= -1.5: break
        meta = os.path.join(d, 'meta.txt')
        t = open(meta, encoding='utf8').read()
        t = re.sub(r'오디오\(최종 MP4 측정\): .*', f'오디오(최종 MP4 측정): true peak {tp} dBTP, {I} LUFS (재보정)', t)
        open(meta, 'w', encoding='utf8').write(t)
    w, h, fps, dur, errs = info(mp4)
    print(json.dumps({'dir': os.path.basename(d.rstrip('/')), 'res': f'{w}x{h}', 'fps': fps, 'dur': round(dur, 2), 'decode_errors': errs, 'tp': tp, 'lufs': I, 'mp4': mp4}, ensure_ascii=False))

main()
