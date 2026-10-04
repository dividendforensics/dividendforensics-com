// Captures the main edit of NORI, TRYING for the MMD export (tools/mmd_build.py): every mesh's
// geometry and material, every moving object's world transform at 30 fps (MMD's frame rate), the
// eight procedural arms as joint frames, the camera and the sun. Nothing is rendered: the engine
// is served with two small patches so frame() only poses the world.
// usage: node tools/mmd_capture.mjs --out <dir> --three <node_modules/three> [--edit main] [--frames n] [--textime 63]
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, open } from 'node:fs/promises';
import { extname, join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1]]] : a), []));
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const out = resolve(args.out || 'mmd_capture');
const EDIT = args.edit || 'main';
const FPS = 30, JOINTS = 17, CHUNK = 240;
const threeDir = resolve(args.three || 'node_modules/three');
const { chromium } = await import(args.playwright || '/opt/node22/lib/node_modules/playwright/index.mjs');

// the engine, posed but not drawn, with its module-level objects handed to the page
const PATCHES = [
  ['const c = CAMS[loc.clip.cam](t, loc.u);', 'const c = CAMS[loc.clip.cam](t, loc.u); window.__lastCam = c;'],
  ['  composer.render();\n  return loc;', '  if (!window.__noRender) composer.render();\n  return loc;'],
];
const NAMED = ['nori', 'sunny', 'headPivot', 'head', 'web', 'face', 'mouthG', 'smileLine', 'mouthOpen', 'tongue', 'eyes', 'lids', 'lowLids', 'brows', 'blushes',
  'sunnyBody', 'shellG', 'shellLid', 'crabEyes', 'crabStalks', 'crabMouth', 'claws', 'legs', 'doorPivot', 'clock', 'hourHand', 'minHand', 'flame', 'steam', 'streams',
  'dust', 'zzz', 'PLANTS', 'BOOKS', 'tvScreen', 'doorway', 'windowPane', 'shade', 'frames', 'bulbs'];
const EXPOSE = `\nwindow.__mmd = { arms, sun, hemi, PROPS, named: { ${NAMED.map((n) => `${n}: (typeof ${n} !== 'undefined' ? ${n} : null)`).join(', ')} } };\n`;

const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const file = join(root, path.endsWith('/') ? path + 'index.html' : path);
    let body = await readFile(file);
    if (path === '/engine.js') {
      let src = body.toString();
      for (const [a, b] of PATCHES) { if (!src.includes(a)) throw new Error('engine patch failed: ' + a); src = src.replace(a, b); }
      body = src + EXPOSE;
    }
    res.writeHead(200, { 'content-type': types[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch (e) { console.error(String(e)); res.writeHead(404); res.end(); }
}).listen(0);

await mkdir(join(out, 'tex'), { recursive: true });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
page.on('console', (m) => { if (m.type() === 'error') console.log('[page]', m.text()); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.route(/cdn\.jsdelivr\.net\/npm\/three@[^/]+\/(.*)$/, async (route) => {
  route.fulfill({ body: await readFile(join(threeDir, route.request().url().replace(/^.*three@[^/]+\//, ''))), contentType: 'text/javascript' });
});
await page.route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.fulfill({ body: '', contentType: 'text/css' }));
await page.goto(`http://localhost:${server.address().port}/index.html?render&edit=${EDIT}`);
await page.waitForFunction(() => window.__nori && window.__mmd, null, { timeout: 180000 });
await page.evaluate(() => window.__nori.ready);

// ── scene inventory at frame 0: meshes, materials, textures, names
const inv = await page.evaluate(({ EDIT }) => {
  const { scene, THREE } = window.__nori.debug;
  window.__noRender = true;
  window.__nori.setEdit(EDIT);
  window.__nori.frame(0);
  scene.updateMatrixWorld(true);
  const { arms, named, PROPS } = window.__mmd;
  // readable names for the objects the engine keeps in variables
  const label = (o, n) => { if (o && o.isObject3D && !o.userData.mmdName) o.userData.mmdName = n; };
  for (const [n, v] of Object.entries(named)) {
    if (!v) continue;
    if (v.isObject3D) label(v, n);
    else if (Array.isArray(v)) v.forEach((x, i) => label(x && (x.isObject3D ? x : x.m || x.l || x.obj), n + i));
  }
  for (const [n, p] of Object.entries(PROPS)) label(p.obj, n);
  arms.forEach((a, i) => label(a, 'arm' + i));
  const groupOf = (o) => { for (let p = o; p; p = p.parent) { if (p === named.nori) return 'nori'; if (p === named.sunny) return 'sunny'; } return 'room'; };
  const nameOf = (o) => { const parts = []; for (let p = o; p && p !== scene; p = p.parent) if (p.userData.mmdName) { parts.push(p.userData.mmdName); break; } return parts[0] || ''; };

  const meshes = [], mats = new Map(), texs = new Map();
  const b64 = (arr) => { const u8 = new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  const texId = (t) => {
    if (!t) return -1;
    if (!texs.has(t.uuid)) {
      const img = t.image; let data = null;
      try {
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        c.getContext('2d').drawImage(img, 0, 0); data = c.toDataURL('image/png');
      } catch (e) { data = null; }
      texs.set(t.uuid, { id: texs.size, uuid: t.uuid, data, flipY: t.flipY, repeat: [t.repeat.x, t.repeat.y], offset: [t.offset.x, t.offset.y], rotation: t.rotation, w: img.width, h: img.height });
    }
    return texs.get(t.uuid).id;
  };
  const matId = (m) => {
    if (!mats.has(m.uuid)) {
      const col = (c) => (c ? [c.r, c.g, c.b] : null);
      mats.set(m.uuid, {
        id: mats.size, type: m.type, name: m.name, color: col(m.color), opacity: m.opacity, transparent: m.transparent, alphaTest: m.alphaTest,
        side: m.side, emissive: col(m.emissive), emissiveIntensity: m.emissiveIntensity ?? 0, roughness: m.roughness ?? 1, metalness: m.metalness ?? 0,
        transmission: m.transmission ?? 0, map: texId(m.map), depthWrite: m.depthWrite,
      });
    }
    return mats.get(m.uuid).id;
  };
  let skipped = [];
  scene.traverse((o) => {
    if (!o.isMesh) { if (o.isPoints || o.isLine || o.isSprite) skipped.push(o.type); return; }
    if (Array.isArray(o.material)) { skipped.push('multi-material ' + nameOf(o)); return; }
    const g = o.geometry;
    if (!g.attributes.normal) g.computeVertexNormals();
    const n = g.attributes.position.count;
    const idx = g.index ? Uint32Array.from(g.index.array) : Uint32Array.from({ length: n }, (_, i) => i);
    const pos = Float32Array.from(g.attributes.position.array), nor = Float32Array.from(g.attributes.normal.array);
    const uv = g.attributes.uv ? Float32Array.from(g.attributes.uv.array) : new Float32Array(n * 2);
    meshes.push({
      id: meshes.length, name: nameOf(o), group: groupOf(o), arm: arms.indexOf(o), mat: matId(o.material),
      castShadow: o.castShadow, receiveShadow: o.receiveShadow, renderOrder: o.renderOrder, frustumCulled: o.frustumCulled,
      n, pos: b64(pos), nor: b64(nor), uv: b64(uv), idx: b64(idx),
    });
    o.userData.mmdId = meshes.length - 1;
    if (arms.includes(o)) o.userData.mmdArm = true;
  });
  window.__mmdMeshes = []; scene.traverse((o) => { if (o.isMesh && o.userData.mmdId !== undefined) window.__mmdMeshes[o.userData.mmdId] = o; });
  return { meshes, materials: [...mats.values()], textures: [...texs.values()], skipped, duration: window.__nori.currentEdit().duration };
}, { EDIT });

for (const t of inv.textures) {
  if (t.data) { await writeFile(join(out, 'tex', `t${t.id}.png`), Buffer.from(t.data.split(',')[1], 'base64')); t.file = `t${t.id}.png`; }
  delete t.data;
}
const nFrames = Math.min(+(args.frames || Infinity), Math.floor(inv.duration * FPS));
console.log(`${inv.meshes.length} meshes, ${inv.materials.length} materials, ${inv.textures.length} textures, ${nFrames} frames; skipped: ${inv.skipped.join(', ') || 'none'}`);

// ── per frame: changed mesh transforms, arm joints, camera, light
const tracks = await open(join(out, 'tracks.bin'), 'w'), armsF = await open(join(out, 'arms.bin'), 'w'), midF = await open(join(out, 'arms_mid.bin'), 'w'), camF = await open(join(out, 'camera.bin'), 'w');
const t0 = Date.now();
for (let f0 = 0; f0 < nFrames; f0 += CHUNK) {
  const res = await page.evaluate(({ f0, f1, FPS, JOINTS }) => {
    const { scene, camera, THREE } = window.__nori.debug;
    const { arms, sun, hemi } = window.__mmd;
    const meshes = window.__mmdMeshes;
    const prev = window.__mmdPrev || (window.__mmdPrev = meshes.map(() => null));
    const rec = [], armOut = [], midOut = [], camOut = [];
    const P = new THREE.Vector3(), Q = new THREE.Quaternion(), S = new THREE.Vector3();
    const visible = (o) => { for (let p = o; p; p = p.parent) if (!p.visible) return 0; return 1; };
    for (let f = f0; f < f1; f++) {
      window.__nori.frame(f / FPS);
      scene.updateMatrixWorld(true);
      for (let i = 0; i < meshes.length; i++) {
        const o = meshes[i]; if (o.userData.mmdArm) continue;
        const e = o.matrixWorld.elements, v = visible(o), op = o.material.opacity;
        const p = prev[i];
        let changed = !p || p[0] !== v || p[1] !== op;
        if (!changed) for (let k = 0; k < 16; k++) if (Math.abs(p[2 + k] - e[k]) > 1e-7) { changed = true; break; }
        if (changed) { const r = [f, i, v, op, ...e]; prev[i] = [v, op, ...e]; rec.push(...r); }
      }
      // arms: centre, normal, tangent and radius of the tube at evenly spaced rings (segs = 110, radial = 22)
      for (const a of arms) {
        const pos = a.geometry.attributes.position.array, R = 23, segs = 110;
        const ring = (i) => { const a0 = i * R * 3, a1 = (i * R + 11) * 3; return [(pos[a0] + pos[a1]) / 2, (pos[a0 + 1] + pos[a1 + 1]) / 2, (pos[a0 + 2] + pos[a1 + 2]) / 2, pos[a0] - pos[a1], pos[a0 + 1] - pos[a1 + 1], pos[a0 + 2] - pos[a1 + 2]]; };
        a.updateMatrixWorld();
        const m = a.matrixWorld;
        for (let k = 0; k < JOINTS; k++) {
          const i = Math.round((k * segs) / (JOINTS - 1));
          const c = ring(i), lo = ring(Math.max(0, i - 1)), hi = ring(Math.min(segs, i + 1));
          const cw = new THREE.Vector3(c[0], c[1], c[2]).applyMatrix4(m);
          const nw = new THREE.Vector3(c[3], c[4], c[5]).transformDirection(m);
          const tw = new THREE.Vector3(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]).transformDirection(m);
          const rad = Math.hypot(c[3], c[4], c[5]) / 2;
          armOut.push(cw.x, cw.y, cw.z, nw.x, nw.y, nw.z, tw.x, tw.y, tw.z, rad);
        }
        // ring centres halfway between joints, only used to measure how well the bone chain fits
        for (let k = 0; k < JOINTS - 1; k++) {
          const c = ring(Math.round(((k + 0.5) * segs) / (JOINTS - 1)));
          const cw = new THREE.Vector3(c[0], c[1], c[2]).applyMatrix4(m);
          midOut.push(cw.x, cw.y, cw.z);
        }
      }
      camera.updateMatrixWorld();
      camera.matrixWorld.decompose(P, Q, S);
      const c = window.__lastCam;
      const dir = new THREE.Vector3().subVectors(sun.position, sun.target.position).normalize();
      camOut.push(P.x, P.y, P.z, Q.x, Q.y, Q.z, Q.w, camera.fov, c.pos.distanceTo(c.tgt), c.focus, sun.color.r * sun.intensity, sun.color.g * sun.intensity, sun.color.b * sun.intensity, dir.x, dir.y, dir.z, hemi.intensity);
    }
    const b64 = (arr) => { const u8 = new Uint8Array(arr.buffer); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
    return { rec: b64(Float64Array.from(rec)), arms: b64(Float32Array.from(armOut)), mid: b64(Float32Array.from(midOut)), cam: b64(Float32Array.from(camOut)) };
  }, { f0, f1: Math.min(nFrames, f0 + CHUNK), FPS, JOINTS });
  await tracks.write(Buffer.from(res.rec, 'base64'));
  await armsF.write(Buffer.from(res.arms, 'base64'));
  await midF.write(Buffer.from(res.mid, 'base64'));
  await camF.write(Buffer.from(res.cam, 'base64'));
  const done = Math.min(nFrames, f0 + CHUNK);
  console.log(`frames ${done}/${nFrames}  ${((Date.now() - t0) / done).toFixed(1)} ms/frame`);
}
await Promise.all([tracks.close(), armsF.close(), midF.close(), camF.close()]);
// screens drawn at run time (TV, phone, plan) are blank on frame 0: export every texture again at
// a moment when they show their story content
const TEX_T = +(args.textime ?? 63);
const redrawn = await page.evaluate((t) => {
  const { scene } = window.__nori.debug;
  window.__nori.frame(t);
  const seen = new Map();
  scene.traverse((o) => { if (o.isMesh && o.material.map && o.material.map.image instanceof HTMLCanvasElement) seen.set(o.material.map.uuid, o.material.map); });
  const out = {};
  for (const [uuid, tx] of seen) {
    const c = document.createElement('canvas'); c.width = tx.image.width; c.height = tx.image.height;
    c.getContext('2d').drawImage(tx.image, 0, 0); out[uuid] = c.toDataURL('image/png');
  }
  return out;
}, TEX_T);
for (const t of inv.textures) if (redrawn[t.uuid]) await writeFile(join(out, 'tex', `t${t.id}.png`), Buffer.from(redrawn[t.uuid].split(',')[1], 'base64'));
await writeFile(join(out, 'scene.json'), JSON.stringify({ edit: EDIT, fps: FPS, frames: nFrames, joints: JOINTS, ...inv }));
await browser.close();
server.close();
