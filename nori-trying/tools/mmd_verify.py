"""Independent reader for the files tools/mmd_build.py writes: parses every PMX 2.0 and VMD field
from the published layouts, requires each file to be consumed exactly to its last byte and checks
indices, weights, names and key ranges.
usage: python3 tools/mmd_verify.py <mmd dir>
"""
import glob
import os
import struct
import sys

import numpy as np


class R:
    def __init__(self, b): self.b, self.o = b, 0
    def take(self, n): v = self.b[self.o:self.o + n]; assert len(v) == n, 'truncated'; self.o += n; return v
    def u(self, f): s = struct.calcsize('<' + f); return struct.unpack('<' + f, self.take(s))
    def text(self, enc): n, = self.u('i'); return self.take(n).decode(enc)
    def idx(self, size, unsigned=False): return self.u({1: 'B' if unsigned else 'b', 2: 'H' if unsigned else 'h', 4: 'i'}[size])[0]


def pmx(path):
    r = R(open(path, 'rb').read())
    assert r.take(4) == b'PMX ', 'magic'
    ver, = r.u('f'); n, = r.u('B'); g = r.u(f'{n}B')
    assert ver == 2.0 and n == 8
    enc = 'utf-16-le' if g[0] == 0 else 'utf-8'
    adduv, vs, ts, ms, bs, mos, rs = g[1:]
    info = [r.text(enc) for _ in range(4)]
    nv, = r.u('i')
    bones_used, weights = [], []
    for _ in range(nv):
        r.u('8f'); r.u(f'{4 * adduv}f')
        t, = r.u('B')
        if t == 0: bones_used.append(r.idx(bs))
        elif t == 1: bones_used += [r.idx(bs), r.idx(bs)]; weights.append(r.u('f')[0])
        elif t == 2: bones_used += [r.idx(bs) for _ in range(4)]; r.u('4f')
        elif t == 3: bones_used += [r.idx(bs), r.idx(bs)]; r.u('f'); r.u('9f')
        else: raise AssertionError('weight type')
        r.u('f')
    ni, = r.u('i'); assert ni % 3 == 0
    faces = np.array([r.idx(vs, unsigned=vs < 4) for _ in range(ni)])
    assert faces.min() >= 0 and faces.max() < nv, 'face index out of range'
    nt, = r.u('i'); textures = [r.text(enc) for _ in range(nt)]
    nm, = r.u('i'); total = 0; mats = []
    for _ in range(nm):
        name = r.text(enc); r.text(enc)
        diff = r.u('4f'); r.u('3ff3f'); flags, = r.u('B'); r.u('4ff')
        tex = r.idx(ts); sph = r.idx(ts); r.u('B'); shared, = r.u('B')
        toon = r.u('B')[0] if shared else r.idx(ts)
        r.text(enc); cnt, = r.u('i'); total += cnt
        assert -1 <= tex < nt and -1 <= sph < nt and cnt % 3 == 0 and 0 <= diff[3] <= 1
        mats.append(name)
    assert total == ni, 'material face counts do not add up'
    nb, = r.u('i'); bones = []
    for i in range(nb):
        name = r.text(enc); r.text(enc); r.u('3f'); parent = r.idx(bs); r.u('i'); fl, = r.u('H')
        if fl & 0x0001: assert 0 <= r.idx(bs) < nb
        else: r.u('3f')
        if fl & 0x0300: r.idx(bs); r.u('f')
        if fl & 0x0400: r.u('3f')
        if fl & 0x0800: r.u('6f')
        if fl & 0x2000: r.u('i')
        if fl & 0x0020:
            r.idx(bs); r.u('if'); nl, = r.u('i')
            for _ in range(nl):
                r.idx(bs)
                if r.u('B')[0]: r.u('6f')
        assert -1 <= parent < i, f'bone {name} parent must come first'
        assert len(name.encode('shift_jis')) <= 15, f'bone name {name} too long for VMD'
        bones.append(name)
    assert len(set(bones)) == nb, 'duplicate bone names'
    assert min(bones_used) >= 0 and max(bones_used) < nb, 'vertex bone index out of range'
    assert not weights or (min(weights) >= 0 and max(weights) <= 1)
    nmo, = r.u('i'); morphs = []
    for _ in range(nmo):
        name = r.text(enc); r.text(enc); r.u('B'); kind, = r.u('B'); cnt, = r.u('i')
        for _ in range(cnt):
            if kind == 1: assert 0 <= r.idx(vs, unsigned=vs < 4) < nv; r.u('3f')
            elif kind == 8: assert 0 <= r.idx(ms) < nm; r.u('B'); r.u('28f')
            else: raise AssertionError(f'morph type {kind} not expected')
        morphs.append(name)
    nd, = r.u('i')
    for _ in range(nd):
        r.text(enc); r.text(enc); r.u('B'); ne, = r.u('i')
        for _ in range(ne):
            k, = r.u('B'); i = r.idx(bs if k == 0 else mos)
            assert 0 <= i < (nb if k == 0 else nmo)
    nr, = r.u('i'); nj, = r.u('i')
    assert nr == 0 and nj == 0
    assert r.o == len(r.b), f'{len(r.b) - r.o} trailing bytes'
    return dict(name=info[0], vertices=nv, faces=ni // 3, materials=nm, textures=textures, bones=bones, morphs=morphs)


def vmd(path):
    r = R(open(path, 'rb').read())
    assert r.take(30).rstrip(b'\0') == b'Vocaloid Motion Data 0002'
    model = r.take(20).split(b'\0')[0].decode('shift_jis')
    out = dict(model=model, bones={}, morphs={}, cameras=[], lights=[])
    nb, = r.u('I')
    for _ in range(nb):
        name = r.take(15).split(b'\0')[0].decode('shift_jis'); f, = r.u('I'); p = r.u('3f'); q = r.u('4f'); r.take(64)
        assert abs(np.linalg.norm(q) - 1) < 1e-3, 'non-unit quaternion'
        assert np.isfinite(p).all()
        out['bones'].setdefault(name, []).append(f)
    nm, = r.u('I')
    for _ in range(nm):
        name = r.take(15).split(b'\0')[0].decode('shift_jis'); f, = r.u('I'); w, = r.u('f')
        assert -1e-6 <= w <= 1 + 1e-6, 'morph weight outside 0..1'
        out['morphs'].setdefault(name, []).append(f)
    nc, = r.u('I')
    for _ in range(nc):
        f, = r.u('I'); d, = r.u('f'); c = r.u('3f'); rot = r.u('3f'); r.take(24); fov, = r.u('I'); persp, = r.u('B')
        assert d < 0 and 1 <= fov <= 125 and persp == 0
        out['cameras'].append((f, d, c, rot, fov))
    nl, = r.u('I')
    for _ in range(nl):
        f, = r.u('I'); col = r.u('3f'); d = r.u('3f')
        assert all(0 <= x <= 1 for x in col)
        out['lights'].append(f)
    ns, = r.u('I')
    for _ in range(ns): r.u('IBf')
    assert r.o == len(r.b), f'{len(r.b) - r.o} trailing bytes'
    for k in ('bones', 'morphs'):
        for name, fs in out[k].items(): assert len(fs) == len(set(fs)), f'duplicate key frames on {name}'
    return out


if __name__ == '__main__':
    d = sys.argv[1]
    models = {}
    for p in sorted(glob.glob(os.path.join(d, '*.pmx'))):
        m = pmx(p); models[m['name']] = m
        missing = [t for t in m['textures'] if not os.path.exists(os.path.join(d, t))]
        assert not missing, f'missing textures {missing}'
        print(f"{os.path.basename(p)}: {m['vertices']} vertices, {m['faces']} faces, {m['materials']} materials, {len(m['bones'])} bones, {len(m['morphs'])} morphs, {len(m['textures'])} textures — OK")
    for p in sorted(glob.glob(os.path.join(d, '*.vmd'))):
        v = vmd(p)
        if v['model'] in models:
            m = models[v['model']]
            unknown = set(v['bones']) - set(m['bones']); unknown_m = set(v['morphs']) - set(m['morphs'])
            assert not unknown and not unknown_m, f'motion names not in model: {unknown} {unknown_m}'
            assert set(m['bones']) <= set(v['bones']), 'some bones have no key'
        last = max([max(fs) for fs in v['bones'].values()] + [c[0] for c in v['cameras']] + [0])
        print(f"{os.path.basename(p)}: model '{v['model']}', {sum(map(len, v['bones'].values()))} bone keys on {len(v['bones'])} bones, "
              f"{sum(map(len, v['morphs'].values()))} morph keys, {len(v['cameras'])} camera keys, {len(v['lights'])} light keys, last frame {last} — OK")
