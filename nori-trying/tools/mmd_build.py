"""Builds an MMD (MikuMikuDance) project from the capture written by tools/mmd_capture.mjs:
three PMX 2.0 models (NORI, SUNNY, ROOM), one VMD motion per model, a camera + light VMD for the
main edit, the soundtrack as a 44.1 kHz WAV and the textures as PNG.

Conventions (checked against babylon-mmd, Blender mmd_tools, saba and three-mmd-loader sources):
  * MMD is left-handed: x_mmd = x, y_mmd = y, z_mmd = -z; quaternions become (-x, -y, z, w);
    triangles are written in reverse order.
  * 1 metre = 12.5 MMD units (1 unit ≈ 8 cm).
  * A camera key stores the look-at centre, the distance (negative = in front), Euler angles with
    the camera at centre + R_y(ry) R_x(rx) (0, 0, |distance|) (right-handed form), the vertical
    view angle in whole degrees and a perspective byte (0 = perspective on).
  * Every moving mesh gets its own bone under 全ての親; scale animation becomes vertex morphs,
    fading materials become material morphs, hidden objects drop far below the floor.
  * Each arm is a 17-bone chain fitted to the procedural tube (rings → joint frames).

usage: python3 tools/mmd_build.py <capture dir> <out dir> [soundtrack.wav]
"""
import base64
import json
import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from scipy.spatial.transform import Rotation

SCALE = 12.5
HIDE_Y = -80.0                      # metres below the floor for hidden objects
FAR = np.array([1.0, 1.0, -1.0])    # right → left handed
LINEAR_BONE = bytes(([20] * 8 + [107] * 8) * 1)
LINEAR_BONE = b''.join(LINEAR_BONE[k:] + bytes(k) for k in range(4))
LINEAR_CAM = bytes([20, 107, 20, 107] * 6)

CAP, OUT = sys.argv[1], sys.argv[2]
WAV = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)
scene = json.load(open(os.path.join(CAP, 'scene.json')))
F, J = scene['frames'], scene['joints']
b64 = lambda s, dt: np.frombuffer(base64.b64decode(s), dtype=dt)

# ───────────────────────────────────────────── tracks
rec = np.fromfile(os.path.join(CAP, 'tracks.bin'), dtype='<f8').reshape(-1, 20)
arms = np.fromfile(os.path.join(CAP, 'arms.bin'), dtype='<f4').reshape(F, 8, J, 10).astype(np.float64)
mids = np.fromfile(os.path.join(CAP, 'arms_mid.bin'), dtype='<f4').reshape(F, 8, J - 1, 3).astype(np.float64)
cam = np.fromfile(os.path.join(CAP, 'camera.bin'), dtype='<f4').reshape(F, 17).astype(np.float64)
frames = np.arange(F)


def track(mid):
    r = rec[rec[:, 1] == mid]
    i = np.searchsorted(r[:, 0], frames, side='right') - 1
    assert i[0] == 0, f'mesh {mid} has no frame-0 record'
    r = r[i]
    E = r[:, 4:20]
    A = np.stack([E[:, 0:3], E[:, 4:7], E[:, 8:11]], axis=2)       # columns
    T = E[:, 12:15].copy()
    s = np.linalg.norm(A, axis=1)
    det = np.linalg.det(A)
    s[:, 0] *= np.where(det < 0, -1, 1)
    safe = np.where(np.abs(s) < 1e-9, 1, s)
    R = A / safe[:, None, :]
    q = np.zeros((F, 4)); q[:, 3] = 1
    ok = np.abs(s).min(axis=1) > 1e-9
    q[ok] = Rotation.from_matrix(R[ok]).as_quat()
    # hold the last valid rotation through frames where the object is scaled to nothing
    last = q[0] if ok[0] else np.array([0, 0, 0, 1.0])
    for f in range(F):
        if ok[f]: last = q[f]
        else: q[f] = last
    return dict(T=T, q=q, s=s, vis=r[:, 2] > 0.5, op=r[:, 3], det0=det)


def lh(p):      # right-handed metres → MMD units
    return p * FAR * SCALE


def lhq(q):     # quaternion (x, y, z, w) right → left handed
    return q * np.array([-1, -1, 1, 1])


def continuous(q):
    q = q.copy()
    for f in range(1, len(q)):
        if np.dot(q[f], q[f - 1]) < 0: q[f] = -q[f]
    return q


def slerp(q0, q1, u):
    d = np.clip(np.sum(q0 * q1, axis=-1), -1, 1)
    q1 = np.where(d[..., None] < 0, -q1, q1); d = np.abs(d)
    th = np.arccos(np.clip(d, -1, 1))
    small = th < 1e-6
    st = np.where(small, 1, np.sin(th))
    a = np.where(small, 1 - u, np.sin((1 - u) * th) / st)
    b = np.where(small, u, np.sin(u * th) / st)
    return a[..., None] * q0 + b[..., None] * q1


def reduce_keys(chans, tol):
    """Greedy key reduction: keep a frame only where linear interpolation (slerp for 'q' channels)
    from the previous kept key would miss the true value by more than tol somewhere in between."""
    keys = [0]
    a = 0
    while a < F - 1:
        def fits(b):
            if b - a < 2: return True
            u = (np.arange(a + 1, b) - a) / (b - a)
            for kind, v, t in chans:
                if kind == 'q':
                    est = slerp(np.repeat(v[a][None], len(u), 0), np.repeat(v[b][None], len(u), 0), u)
                    err = 2 * np.arccos(np.clip(np.abs(np.sum(est * v[a + 1:b], axis=1)), -1, 1))
                else:
                    est = v[a] + (v[b] - v[a]) * u[:, None]
                    err = np.abs(est - v[a + 1:b]).max(axis=1)
                if err.max() > t: return False
            return True
        # gallop then bisect for the furthest frame that still fits
        step, b = 1, a + 1
        while b + step < F and fits(b + step): b += step; step *= 2
        lo, hi = b, min(F - 1, b + step)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fits(mid): lo = mid
            else: hi = mid - 1
        a = max(lo, a + 1)
        keys.append(a)
    return keys


# ───────────────────────────────────────────── binary writers
def text(s):
    b = s.encode('utf-16-le')
    return struct.pack('<i', len(b)) + b


def sjis(s, n):
    b = s.encode('shift_jis')
    assert len(b) <= n, f'name too long for VMD: {s}'
    return b.ljust(n, b'\0')


def idx_fmt(size, unsigned=False):
    return {1: 'B' if unsigned else 'b', 2: 'H' if unsigned else 'h', 4: 'i'}[size]


class Model:
    def __init__(self, name, comment):
        self.name, self.comment = name, comment
        self.pos, self.nor, self.uv, self.b1, self.b2, self.w = [], [], [], [], [], []
        self.faces = {}            # material key → list of index arrays
        self.mats = {}             # material key → dict
        self.bones = [dict(name='全ての親', en='ParentNode', pos=np.zeros(3), parent=-1, tail=None)]
        self.morphs = []           # dict(name, panel, kind='vertex'|'material', offsets)
        self.nv = 0
        self.textures = []

    def bone(self, name, pos, parent=0, tail=None):
        self.bones.append(dict(name=name, en=name, pos=pos, parent=parent, tail=tail))
        return len(self.bones) - 1

    def add(self, pos, nor, uv, idx, matkey, b1, b2=None, w=None):
        n = len(pos)
        self.pos.append(pos); self.nor.append(nor); self.uv.append(uv)
        self.b1.append(np.broadcast_to(b1, (n,)).astype(np.int32))
        self.b2.append(np.zeros(n, np.int32) if b2 is None else b2.astype(np.int32))
        self.w.append(np.ones(n) if w is None else w)
        self.faces.setdefault(matkey, []).append(idx + self.nv)
        base = self.nv
        self.nv += n
        return base

    def tex_index(self, file):
        if file is None: return -1
        if file not in self.textures: self.textures.append(file)
        return self.textures.index(file)

    def write(self, path):
        pos = np.concatenate(self.pos); nor = np.concatenate(self.nor); uv = np.concatenate(self.uv)
        b1 = np.concatenate(self.b1); b2 = np.concatenate(self.b2); w = np.concatenate(self.w)
        vsz = 2 if self.nv <= 65535 else 4
        order = sorted(self.mats, key=lambda k: (self.mats[k]['alpha_pass'], self.mats[k]['order']))
        mat_index = {k: i for i, k in enumerate(order)}
        out = bytearray(b'PMX ' + struct.pack('<f', 2.0) + bytes([8, 0, 0, vsz, 2, 2, 2, 2, 1]))
        out += text(self.name) + text(self.name) + text(self.comment) + text(self.comment)
        # vertices: all BDEF2 (rigid parts use weight 1 on their bone)
        vt = np.dtype([('p', '<f4', 3), ('n', '<f4', 3), ('uv', '<f4', 2), ('t', 'u1'), ('b1', '<i2'), ('b2', '<i2'), ('w', '<f4'), ('e', '<f4')])
        V = np.zeros(self.nv, vt)
        V['p'] = pos; V['n'] = nor; V['uv'] = uv; V['t'] = 1; V['b1'] = b1; V['b2'] = b2; V['w'] = w; V['e'] = 1
        out += struct.pack('<i', self.nv) + V.tobytes()
        tris = [np.concatenate(self.faces[k]).reshape(-1, 3)[:, ::-1].ravel() for k in order]
        allf = np.concatenate(tris)
        out += struct.pack('<i', len(allf)) + allf.astype('<u2' if vsz == 2 else '<i4').tobytes()
        out += struct.pack('<i', len(self.textures)) + b''.join(text(t) for t in self.textures)
        out += struct.pack('<i', len(order))
        for k, tri in zip(order, tris):
            m = self.mats[k]
            out += text(m['name']) + text(m['name'])
            out += struct.pack('<4f3ff3f', *m['diffuse'], *m['specular'], m['power'], *m['ambient'])
            out += struct.pack('<B4ff', m['flags'], *m['edge_color'], m['edge_size'])
            out += struct.pack('<hhB', m['tex'], -1, 0) + struct.pack('<BB', 1, m['toon'])
            out += text('') + struct.pack('<i', len(tri))
        out += struct.pack('<i', len(self.bones))
        for i, b in enumerate(self.bones):
            flags = 0x0002 | 0x0004 | 0x0008 | 0x0010 | (0x0001 if isinstance(b['tail'], int) else 0)
            out += text(b['name']) + text(b['en']) + struct.pack('<3fhiH', *b['pos'], b['parent'], 0, flags)
            out += struct.pack('<h', b['tail']) if isinstance(b['tail'], int) else struct.pack('<3f', *(b['tail'] if b['tail'] is not None else (0, 2.0, 0)))
        out += struct.pack('<i', len(self.morphs))
        for mo in self.morphs:
            out += text(mo['name']) + text(mo['name'])
            if mo['kind'] == 'vertex':
                vi, off = mo['offsets']
                rt = np.dtype([('i', '<u2' if vsz == 2 else '<i4'), ('o', '<f4', 3)])
                R = np.zeros(len(vi), rt); R['i'] = vi; R['o'] = off
                out += struct.pack('<BBi', mo['panel'], 1, len(vi)) + R.tobytes()
            else:   # material morph: multiply diffuse alpha by (1 - weight)
                out += struct.pack('<BBi', mo['panel'], 8, 1)
                out += struct.pack('<hB', mat_index[mo['mat']], 0)
                out += struct.pack('<28f', 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, *[1] * 12)
        # display frames: Root, 表情 (all morphs), then the bones in groups of their name prefix
        groups = {}
        for i, b in enumerate(self.bones[1:], 1): groups.setdefault(b['name'].rstrip('0123456789_').split('_')[0] or 'bones', []).append(i)
        frames = [('Root', 1, [(0, 0)]), ('表情', 1, [(1, i) for i in range(len(self.morphs))])] + [(g, 0, [(0, i) for i in v]) for g, v in groups.items()]
        out += struct.pack('<i', len(frames))
        for name, special, items in frames:
            out += text(name) + text(name) + struct.pack('<Bi', special, len(items))
            for kind, i in items: out += struct.pack('<Bh', kind, i)
        out += struct.pack('<ii', 0, 0)          # rigid bodies, joints
        open(path, 'wb').write(out)
        return dict(vertices=self.nv, faces=len(allf) // 3, materials=len(order), bones=len(self.bones), morphs=len(self.morphs), textures=len(self.textures), bytes=len(out))


def write_vmd(path, model_name, bone_keys=(), morph_keys=(), cam_keys=(), light_keys=()):
    out = bytearray(b'Vocaloid Motion Data 0002'.ljust(30, b'\0') + sjis(model_name, 20))
    out += struct.pack('<I', len(bone_keys))
    for name, f, p, q in bone_keys: out += sjis(name, 15) + struct.pack('<I3f4f', f, *p, *q) + LINEAR_BONE
    out += struct.pack('<I', len(morph_keys))
    for name, f, w in morph_keys: out += sjis(name, 15) + struct.pack('<If', f, w)
    out += struct.pack('<I', len(cam_keys))
    for f, d, c, r, fov in cam_keys: out += struct.pack('<If3f3f', f, d, *c, *r) + LINEAR_CAM + struct.pack('<IB', fov, 0)
    out += struct.pack('<I', len(light_keys))
    for f, col, d in light_keys: out += struct.pack('<I3f3f', f, *col, *d)
    out += struct.pack('<I', 0)                  # self-shadow keys
    open(path, 'wb').write(out)
    return len(out)


# ───────────────────────────────────────────── materials & textures
TEX = scene['textures']
for t in TEX:
    if t.get('file'): shutil.copy(os.path.join(CAP, 'tex', t['file']), os.path.join(OUT, f"tex{t['id']:02d}.png"))
MATS = scene['materials']
TEX_ALPHA = {}
for t in TEX:
    if t.get('file'):
        from PIL import Image
        im = Image.open(os.path.join(CAP, 'tex', t['file']))
        TEX_ALPHA[t['id']] = im.mode == 'RGBA' and im.getextrema()[3][0] < 250


def pmx_material(mat, group, castShadow, receiveShadow, order):
    c = np.array(mat['color'] or [1, 1, 1])
    alpha = mat['opacity'] if mat['transparent'] else 1.0
    if mat['transmission'] > 0.5: alpha = min(alpha, 0.25)
    # MMD blends texture alpha; a diffuse alpha just under 1 also tells loaders to draw it as transparent
    if alpha >= 1 and (mat['transparent'] or mat['alphaTest'] > 0 or (mat['map'] >= 0 and TEX_ALPHA.get(mat['map']))): alpha = 0.999
    em = np.array(mat['emissive'] or [0, 0, 0]) * min(1.0, mat['emissiveIntensity'])
    rough = mat['roughness']
    flags = (0x01 if mat['side'] == 2 or alpha < 1 else 0) | (0x02 | 0x04 if castShadow else 0) | (0x08 if receiveShadow else 0)
    edge = group != 'room' and alpha >= 1 and mat['type'] != 'MeshBasicMaterial'
    if edge: flags |= 0x10
    basic = mat['type'] == 'MeshBasicMaterial'
    return dict(name=f"{group}_{mat['id']:03d}", diffuse=[*c, alpha],
                specular=list(np.full(3, 0.12 * (1 - rough))), power=5 + 45 * (1 - rough),
                ambient=list(np.clip((c if basic else c * 0.5) + em, 0, 1)), flags=flags,
                edge_color=[0.22, 0.11, 0.07, 1.0], edge_size=0.55 if group == 'nori' else 0.45,
                toon=0, alpha_pass=1 if (alpha < 1 or mat['alphaTest'] > 0 or not mat['depthWrite']) else 0, order=order,
                tex_file=f"tex{mat['map']:02d}.png" if mat['map'] >= 0 and TEX[mat['map']].get('file') else None)


def mmd_uv(uv, mat):
    uv = uv.reshape(-1, 2).astype(np.float64).copy()
    if mat['map'] >= 0:
        t = TEX[mat['map']]
        assert abs(t['rotation']) < 1e-9, 'rotated texture'
        uv = uv * np.array(t['repeat']) + np.array(t['offset'])
        if t['flipY']: uv[:, 1] = 1 - uv[:, 1]
    else:
        uv[:, 1] = 1 - uv[:, 1]
    return uv


# ───────────────────────────────────────────── models
models = {g: Model(g.upper(), f'NORI, TRYING — Ep.1 "My Day Off" · {g} · generated by tools/mmd_build.py (previs export)') for g in ('nori', 'sunny', 'room')}
motion = {g: [] for g in models}          # (bone name, frames, positions LH, quats LH)
morph_tracks = {g: [] for g in models}    # (morph name, weights per frame)
used_names = set()


def unique(base):
    base = ''.join(ch for ch in base if ch.isascii() and (ch.isalnum() or ch == '_'))[:11] or 'obj'
    name, k = base, 1
    while name in used_names: name = f'{base}_{k}'; k += 1
    used_names.add(name)
    return name


stats = dict(static=0, dynamic=0, hidden=0, scale_morphs=0, material_morphs=0)
mat_opacity = {}
for m in scene['meshes']:
    if m['arm'] >= 0: continue
    g, M = m['group'], models[m['group']]
    tr = track(m['id'])
    if not tr['vis'].any():
        stats['hidden'] += 1; continue
    mat = MATS[m['mat']]
    key = mat['id']
    if key not in M.mats: M.mats[key] = pmx_material(mat, g, m['castShadow'], m['receiveShadow'], len(M.mats) + m['renderOrder'] * 1000)
    M.mats[key]['tex'] = M.tex_index(M.mats[key]['tex_file'])
    if np.ptp(tr['op'][tr['vis']]) > 1e-4: mat_opacity.setdefault((g, key), tr['op'])
    v = b64(m['pos'], '<f4').reshape(-1, 3).astype(np.float64)
    nl = b64(m['nor'], '<f4').reshape(-1, 3).astype(np.float64)
    uv = mmd_uv(b64(m['uv'], '<f4'), mat)
    idx = b64(m['idx'], '<u4').astype(np.int64).reshape(-1, 3)
    T, q, s, vis = tr['T'], tr['q'], tr['s'], tr['vis']
    dyn = (np.ptp(T, axis=0).max() > 1e-6 or np.ptp(s, axis=0).max() > 1e-6 or not vis.all()
           or np.abs(np.abs(np.sum(q * q[0], axis=1)) - 1).max() > 1e-9)
    r = int(np.argmax(vis))                          # rest frame: first frame it is seen
    smax = np.where(vis[:, None], s, -np.inf).max(axis=0)
    smin = np.where(vis[:, None], s, np.inf).min(axis=0)
    sref = smax if dyn else s[r]
    if np.abs(sref).min() < 1e-9:
        stats['hidden'] += 1; continue
    R0 = Rotation.from_quat(q[r]).as_matrix()
    p = (R0 @ (v * sref).T).T + T[r]
    n = (R0 @ (nl / sref).T).T; n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    if np.prod(np.sign(sref)) < 0: idx = idx[:, ::-1]
    if not dyn:
        stats['static'] += 1
        M.add(lh(p), n * FAR, uv, idx.ravel(), key, 0)
        continue
    stats['dynamic'] += 1
    bname = unique(m['name'] or f'm{m["id"]}')
    bi = M.bone(bname, lh(T[r]))
    base = M.add(lh(p), n * FAR, uv, idx.ravel(), key, bi)
    # bone track: rigid motion relative to the rest frame; hidden frames sink below the floor
    Tt, qt = T.copy(), q.copy()
    lastv = r
    for f in range(F):
        if vis[f]: lastv = f
        else: qt[f] = q[lastv]; Tt[f] = T[lastv] + np.array([0, HIDE_Y, 0])
    rel = (Rotation.from_quat(qt) * Rotation.from_quat(q[r]).inv()).as_quat()
    motion[g].append((bname, lh(Tt - T[r]), continuous(lhq(rel))))
    # scale animation → one vertex morph per independent axis (weight 0 = largest scale)
    span = smax - smin
    axes = [a for a in range(3) if abs(span[a]) > 1e-4 * max(1e-6, abs(smax[a]))]
    W = {}
    for a in axes:
        w = (smax[a] - np.where(vis, s[:, a], np.nan)) / span[a]
        for f in range(F):
            if np.isnan(w[f]): w[f] = w[f - 1] if f else 0
        W[a] = np.clip(w, 0, 1)
    groups_ = []
    for a in axes:
        for gr in groups_:
            if np.abs(W[gr[0]] - W[a]).max() < 1e-3: gr.append(a); break
        else: groups_.append([a])
    for gr in groups_:
        off = np.zeros_like(v)
        for a in gr: off[:, a] = v[:, a] * (smin[a] - smax[a])
        off = (R0 @ off.T).T
        keep = np.abs(off).max(axis=1) > 1e-7
        mname = unique(bname[:8] + '_s' + ''.join('xyz'[a] for a in gr))
        M.morphs.append(dict(name=mname, panel=3 if 'mouth' in bname else 4, kind='vertex', offsets=(np.nonzero(keep)[0] + base, lh(off[keep]))))
        morph_tracks[g].append((mname, W[gr[0]]))
        stats['scale_morphs'] += 1

for (g, key), op in mat_opacity.items():
    M = models[g]
    top = op.max()
    M.mats[key]['diffuse'][3] = float(top)
    mname = unique(f'fade{key}')
    M.morphs.append(dict(name=mname, panel=4, kind='material', mat=key))
    morph_tracks[g].append((mname, 1 - op / top))
    stats['material_morphs'] += 1

# ───────────────────────────────────────────── arms: 17-bone chains fitted to the tube
N = models['nori']
SEGS, RADIAL = 110, 22
arm_meshes = sorted([m for m in scene['meshes'] if m['arm'] >= 0], key=lambda m: m['arm'])


def frames_of(jt):            # (..., 10) → rotation matrices with columns normal, binormal, tangent
    Tg = jt[..., 6:9] / np.linalg.norm(jt[..., 6:9], axis=-1, keepdims=True)
    Nm = jt[..., 3:6] - np.sum(jt[..., 3:6] * Tg, axis=-1, keepdims=True) * Tg
    Nm /= np.linalg.norm(Nm, axis=-1, keepdims=True)
    B = np.cross(Tg, Nm)
    return np.stack([Nm, B, Tg], axis=-1)


arm_err = []
for m in arm_meshes:
    a = m['arm']
    mat = MATS[m['mat']]
    key = mat['id']
    if key not in N.mats: N.mats[key] = pmx_material(mat, 'nori', True, True, len(N.mats))
    N.mats[key]['tex'] = N.tex_index(N.mats[key]['tex_file'])
    v = b64(m['pos'], '<f4').reshape(-1, 3).astype(np.float64)
    nl = b64(m['nor'], '<f4').reshape(-1, 3).astype(np.float64)
    assert len(v) == (SEGS + 1) * (RADIAL + 1)
    ring0 = (v[0] + v[11]) / 2
    assert np.abs(ring0 - arms[0, a, 0, :3]).max() < 1e-5, 'arm geometry is not in world space'
    jt = arms[:, a]                                      # (F, J, 10)
    Fr = frames_of(jt)                                   # (F, J, 3, 3)
    Pj = jt[..., :3]
    Rw = np.einsum('fjab,jcb->fjac', Fr, Fr[0])          # world rotation of each joint vs rest
    bones = []
    for k in range(J):
        parent = 0 if k == 0 else bones[-1]
        bones.append(N.bone(f'arm{a}_{k:02d}', lh(Pj[0, k]), parent=parent))
    for k in range(J - 1): N.bones[bones[k]]['tail'] = bones[k + 1]
    N.bones[bones[-1]]['tail'] = tuple(lh(Pj[0, -1] - Pj[0, -2]))
    ring = np.arange(len(v)) // (RADIAL + 1)
    jt_ring = np.round(np.arange(J) * SEGS / (J - 1))      # the rings the capture sampled as joints
    sj = np.interp(ring, jt_ring, np.arange(J))
    k0 = np.minimum(np.floor(sj).astype(int), J - 2)
    fr = sj - k0
    uv = mmd_uv(b64(m['uv'], '<f4'), mat)
    idx = b64(m['idx'], '<u4').astype(np.int64)
    N.add(lh(v), nl * FAR, uv, idx, key, np.array(bones)[k0], np.array(bones)[k0 + 1], 1 - fr)
    # local transforms along the chain
    for k in range(J):
        if k == 0:
            rot = Rotation.from_matrix(Rw[:, 0]).as_quat()
            pos = Pj[:, 0] - Pj[0, 0]
        else:
            Rp = Rw[:, k - 1]
            rot = Rotation.from_matrix(np.einsum('fba,fbc->fac', Rp, Rw[:, k])).as_quat()
            pos = np.einsum('fba,fb->fa', Rp, Pj[:, k] - Pj[:, k - 1]) - (Pj[0, k] - Pj[0, k - 1])
        motion['nori'].append((f'arm{a}_{k:02d}', lh(pos), continuous(lhq(rot))))
    # how well the skinned chain reproduces the tube: skinned ring centres halfway between joints
    # against the engine's own ring centres there, every 10th frame
    mid_ring = np.round((np.arange(J - 1) + 0.5) * SEGS / (J - 1)).astype(int)
    c0 = (v[mid_ring * (RADIAL + 1)] + v[mid_ring * (RADIAL + 1) + 11]) / 2
    ka, wa = k0[mid_ring * (RADIAL + 1)], fr[mid_ring * (RADIAL + 1)]
    for f in range(0, F, 10):
        pa = Pj[f, ka] + np.einsum('rab,rb->ra', Rw[f, ka], c0 - Pj[0, ka])
        pb = Pj[f, ka + 1] + np.einsum('rab,rb->ra', Rw[f, ka + 1], c0 - Pj[0, ka + 1])
        skinned = (1 - wa)[:, None] * pa + wa[:, None] * pb
        arm_err.append(np.linalg.norm(skinned - mids[f, a], axis=1))

# ───────────────────────────────────────────── write models + motions
arm_err = np.concatenate(arm_err)
report = dict(stats=stats, models={}, motions={}, arm_fit_error_m=dict(median=float(np.median(arm_err)), p99=float(np.percentile(arm_err, 99)), max=float(arm_err.max())))
for g, M in models.items():
    report['models'][g] = M.write(os.path.join(OUT, f'{M.name}.pmx'))
    keys = []
    for name, P, Q in motion[g]:
        ks = reduce_keys([('v', P, 0.01), ('q', Q, 0.0015)], None)
        keys += [(name, f, P[f], Q[f]) for f in ks]
    mkeys = []
    for name, W in morph_tracks[g]:
        ks = reduce_keys([('v', W[:, None], 0.004)], None)
        mkeys += [(name, f, float(W[f])) for f in ks]
    # every bone and morph gets a key on frame 0 so the pose is fully defined
    keyed = {k[0] for k in keys}
    keys += [(b['name'], 0, (0, 0, 0), (0, 0, 0, 1)) for b in M.bones if b['name'] not in keyed]
    report['motions'][g] = dict(bone_keys=len(keys), morph_keys=len(mkeys), bytes=write_vmd(os.path.join(OUT, f'{M.name}.vmd'), M.name, keys, mkeys))

# ───────────────────────────────────────────── camera + light
E, Qc, fov, dist = cam[:, 0:3], cam[:, 3:7], cam[:, 7], cam[:, 8]
Rc = Rotation.from_quat(Qc)
fwd = Rc.apply([0, 0, -1])
C = E + fwd * dist[:, None]
rx = np.arcsin(np.clip(fwd[:, 1], -1, 1))
ry = np.unwrap(np.arctan2(-fwd[:, 0], -fwd[:, 2]))
# the stored angles must rebuild the engine camera exactly (no roll): eye = C + Ry Rx (0,0,d)
Rm = Rotation.from_euler('YX', np.stack([ry, rx], 1))
eye = C + Rm.apply([0, 0, 1]) * dist[:, None]
cam_err = dict(eye_m=float(np.abs(eye - E).max()), angle_deg=float(np.degrees((Rm.inv() * Rc).magnitude().max())))
CP, CD, CR = lh(C), -dist * SCALE, np.stack([rx, ry, np.zeros(F)], 1)
CF = np.round(fov).astype(int)
ks = reduce_keys([('v', CP, 0.01), ('v', CR, 0.0008), ('v', CD[:, None], 0.01), ('v', CF[:, None].astype(float), 0.4)], None)
cam_keys = [(f, float(CD[f]), CP[f], CR[f], int(CF[f])) for f in ks]
sunI = cam[:, 10:13]
light_col = np.clip(0.12 + 0.24 * sunI, 0, 1)
light_dir = -cam[:, 13:16] * FAR
lk = reduce_keys([('v', light_col, 0.004), ('v', light_dir, 0.004)], None)
light_keys = [(f, light_col[f], light_dir[f]) for f in lk]
report['camera'] = dict(keys=len(cam_keys), light_keys=len(light_keys), rebuild_error=cam_err, fov_range=[int(CF.min()), int(CF.max())],
                        bytes=write_vmd(os.path.join(OUT, 'CAMERA_main.vmd'), 'カメラ・照明', cam_keys=cam_keys, light_keys=light_keys))

# cut list for the previs sheet: MMD frame of every camera change
edits = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'edits.json')))[scene['edit']]
cuts, acc = [], 0.0
for c in edits['clips']:
    cuts.append(dict(frame=int(round(acc * 30)), cam=c['cam'], seconds=round((c['to'] - c['from']) / c.get('speed', 1), 2)))
    acc += (c['to'] - c['from']) / c.get('speed', 1)
report['cuts'] = cuts

if WAV:
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', WAV, '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', os.path.join(OUT, 'ep01-main.wav')], check=True)
json.dump(report, open(os.path.join(OUT, 'export_report.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in report.items() if k != 'cuts'}, indent=1, ensure_ascii=False))
