// NORI, TRYING. — Ep.1 "My Day Off"
// An octopus plans the perfect rest and spends the whole day preparing for it.
// Everything on screen is a pure function of story time (0–232 s); edits.json cuts it
// into a 16:9 episode and three 9:16 shorts, each filmed with its own cameras.

import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

const qs = new URLSearchParams(location.search);
const RENDER = qs.has('render');
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const bump = (t, a, b, f = 0.15) => smooth(a, a + f, t) * (1 - smooth(b - f, b, t));
let seed = 11;
const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const rr = (a, b) => a + (b - a) * rnd();

export const STORY = 232;
const [LINES, VOICES, EDITS] = await Promise.all(['lines.json', 'voices.json', 'edits.json'].map((f) => fetch(new URL(`./${f}`, import.meta.url)).then((r) => r.json())));

// ───────────────────────────────────────────── renderer
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: RENDER, powerPreference: 'high-performance' });
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 16 / 9, 0.03, 60);

// ───────────────────────────────────────────── textures
function tex(w, h, draw, repeat = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.anisotropy = 8; t.colorSpace = THREE.SRGBColorSpace;
  t.userData.canvas = c;
  return t;
}
const speckle = (g, w, h, n, col, a, b) => { g.fillStyle = col; for (let i = 0; i < n; i++) { g.beginPath(); g.arc(rnd() * w, rnd() * h, lerp(a, b, rnd()), 0, 7); g.fill(); } };
const fabric = (base, line) => tex(256, 256, (g, w, h) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h); g.globalAlpha = 0.16; g.strokeStyle = line;
  for (let i = 0; i < w; i += 3) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, h); g.stroke(); g.beginPath(); g.moveTo(0, i); g.lineTo(w, i); g.stroke(); }
  g.globalAlpha = 0.07; speckle(g, w, h, 600, '#000', 0.5, 1.5);
}, [6, 6]);
const FONT = '"Jost", "DejaVu Sans", sans-serif';
const SERIF = '"DejaVu Serif", Georgia, serif';
const skinTex = tex(1024, 512, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#ff8a2a'); gr.addColorStop(1, '#f2681a');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 260; i++) {
    const x = rnd() * w, y = rnd() * h * 0.75;
    if (rnd() < Math.exp(-Math.pow((x / w - 0.25) / 0.08, 2)) * (y > h * 0.3 ? 1 : 0.2)) continue;
    g.fillStyle = `rgba(214, 84, 20, ${0.25 + rnd() * 0.35})`; g.beginPath(); g.ellipse(x, y, 3 + rnd() * 7, 2 + rnd() * 5, rnd() * 3, 0, 7); g.fill();
  }
});
const armTex = tex(1024, 128, (g, w, h) => {
  g.fillStyle = '#ff7a1c'; g.fillRect(0, 0, w, h);
  g.fillStyle = '#f9cfa0'; g.fillRect(0, h * 0.56, w, h * 0.36);
  for (let x = 7; x < w; x += 14.2) for (const y of [0.6, 0.88]) { g.fillStyle = '#fde7cc'; g.beginPath(); g.arc(x, h * y, 5.5, 0, 7); g.fill(); g.fillStyle = '#e5ad7c'; g.beginPath(); g.arc(x, h * y, 2.4, 0, 7); g.fill(); }
  for (let x = 14; x < w; x += 30) for (const y of [0.66, 0.82]) {
    g.fillStyle = '#e9b383'; g.beginPath(); g.arc(x + (y > 0.7 ? 15 : 0), h * y, 9, 0, 7); g.fill();
    g.fillStyle = '#fbe2c4'; g.beginPath(); g.arc(x + (y > 0.7 ? 15 : 0), h * y, 5, 0, 7); g.fill();
  }
});
const eyeTex = (iris1, iris2) => tex(1024, 512, (g, w, h) => {
  g.fillStyle = '#fbfbf7'; g.fillRect(0, 0, w, h);
  const cx = w * 0.25, cy = h * 0.5, R = h * 0.2;
  const ir = g.createRadialGradient(cx, cy, R * 0.2, cx, cy, R); ir.addColorStop(0, iris1); ir.addColorStop(0.7, iris2); ir.addColorStop(1, '#16263b');
  g.fillStyle = ir; g.beginPath(); g.arc(cx, cy, R, 0, 7); g.fill();
  g.fillStyle = '#05070b'; g.beginPath(); g.arc(cx, cy, R * 0.55, 0, 7); g.fill();
  g.fillStyle = '#fff'; g.beginPath(); g.arc(cx - R * 0.32, cy - R * 0.35, R * 0.2, 0, 7); g.fill(); g.beginPath(); g.arc(cx + R * 0.3, cy + R * 0.3, R * 0.08, 0, 7); g.fill();
});
const woodTex = tex(1024, 1024, (g, w, h) => {
  for (let i = 0; i < 8; i++) {
    const c = 150 + rnd() * 40; g.fillStyle = `rgb(${c}, ${c * 0.62}, ${c * 0.38})`; g.fillRect(0, i * h / 8, w, h / 8);
    g.globalAlpha = 0.25; g.strokeStyle = '#5a3418';
    for (let k = 0; k < 18; k++) { const y = i * h / 8 + rnd() * h / 8; g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(w * 0.3, y + 6, w * 0.7, y - 6, w, y + 2); g.stroke(); }
    g.globalAlpha = 1; g.fillStyle = '#4a2a14'; g.fillRect(0, i * h / 8, w, 3);
  }
}, [3, 3]);
const knitTex = tex(256, 256, (g, w, h) => { g.fillStyle = '#e2b13f'; g.fillRect(0, 0, w, h); g.strokeStyle = '#b8862a'; g.lineWidth = 3; for (let x = 0; x < w; x += 16) for (let y = 0; y < h; y += 12) { g.beginPath(); g.moveTo(x, y); g.lineTo(x + 8, y + 10); g.lineTo(x + 16, y); g.stroke(); } }, [3, 3]);
const creamKnit = tex(256, 256, (g, w, h) => { g.fillStyle = '#efe4cf'; g.fillRect(0, 0, w, h); g.strokeStyle = '#cdbb98'; g.lineWidth = 3; for (let x = 0; x < w; x += 16) for (let y = 0; y < h; y += 12) { g.beginPath(); g.moveTo(x, y); g.lineTo(x + 8, y + 10); g.lineTo(x + 16, y); g.stroke(); } }, [4, 4]);
const plaidTex = tex(256, 256, (g, w, h) => { g.fillStyle = '#f2efe6'; g.fillRect(0, 0, w, h); g.fillStyle = 'rgba(70, 100, 150, 0.55)'; for (let i = 0; i < w; i += 64) { g.fillRect(i, 0, 32, h); g.fillRect(0, i, w, 32); } }, [2, 2]);
const pillowTex = tex(512, 512, (g, w, h) => { g.fillStyle = '#f1e6cf'; g.fillRect(0, 0, w, h); g.globalAlpha = 0.1; speckle(g, w, h, 900, '#7a5a30', 0.5, 1.4); g.globalAlpha = 1; g.fillStyle = '#c4622b'; g.font = `bold 150px ${SERIF}`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('Nori', w / 2, h / 2); });
const calendarTex = tex(256, 320, (g, w, h) => {
  g.fillStyle = '#fbf6ea'; g.fillRect(0, 0, w, h); g.fillStyle = '#e0573a'; g.fillRect(0, 0, w, 70);
  g.fillStyle = '#fff'; g.font = `600 34px ${FONT}`; g.textAlign = 'center'; g.fillText('SATURDAY', w / 2, 48);
  g.fillStyle = '#3a2a20'; g.font = `600 120px ${FONT}`; g.fillText('12', w / 2, 190);
  g.fillStyle = '#e0573a'; g.font = `600 34px ${FONT}`; g.fillText('DAY OFF ♥', w / 2, 260);
});
const shellTex = tex(512, 256, (g, w, h) => { g.fillStyle = '#4fa3a0'; g.fillRect(0, 0, w, h); g.fillStyle = '#f4f0e4'; for (let y = 16; y < h; y += 40) for (let x = (y / 40) % 2 ? 0 : 20; x < w; x += 40) { g.beginPath(); g.arc(x, y, 7, 0, 7); g.fill(); } });
const pictureTex = (kind) => tex(256, 320, (g, w, h) => {
  g.fillStyle = '#f4ecdb'; g.fillRect(0, 0, w, h);
  if (kind === 'wave') { g.strokeStyle = '#3d7fa3'; g.lineWidth = 10; for (let k = 0; k < 3; k++) { g.beginPath(); for (let x = 20; x < 236; x += 4) g.lineTo(x, 150 + k * 40 + 18 * Math.sin(x / 22 + k)); g.stroke(); } }
  else { g.fillStyle = '#d9a441'; g.beginPath(); for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5 - Math.PI / 2, r = i % 2 ? 40 : 90; g.lineTo(128 + r * Math.cos(a), 160 + r * Math.sin(a)); } g.fill(); }
});
// dynamic screens: the TV, the phone, the plan, the clock
const tvTex = tex(512, 288, () => {}); const phoneTex = tex(256, 512, () => {}); const planTex = tex(256, 340, () => {});
function drawTV(state, p) {
  const g = tvTex.userData.canvas.getContext('2d'), w = 512, h = 288;
  g.fillStyle = state === 'off' ? '#0b0d10' : '#123a5c'; g.fillRect(0, 0, w, h);
  if (state === 'update' || state === 'done') {
    g.fillStyle = '#e8f1f7'; g.font = `500 34px ${FONT}`; g.textAlign = 'center';
    g.fillText(state === 'done' ? 'Update complete ✓' : 'Installing update…', w / 2, 120);
    g.fillStyle = 'rgba(255,255,255,0.25)'; g.fillRect(96, 150, 320, 14); g.fillStyle = '#7fd0ff'; g.fillRect(96, 150, 320 * p, 14);
    if (state === 'update') { g.fillStyle = '#b9cfdc'; g.font = `400 24px ${FONT}`; g.fillText('About 47 minutes remaining', w / 2, 210); }
  }
  tvTex.needsUpdate = true;
}
function drawPhone(state) {
  const g = phoneTex.userData.canvas.getContext('2d'), w = 256, h = 512;
  g.fillStyle = '#10141c'; g.fillRect(0, 0, w, h);
  if (state > 0) {
    g.fillStyle = '#1e2a3c'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#fff'; g.font = `600 30px ${FONT}`; g.textAlign = 'center'; g.fillText('4:58 PM', w / 2, 70);
    g.fillStyle = '#f2f2f2'; g.beginPath(); g.roundRect(18, 150, 220, 130, 22); g.fill();
    g.fillStyle = '#4fa3a0'; g.font = `600 22px ${FONT}`; g.textAlign = 'left'; g.fillText('Sunny 🦀', 36, 186);
    g.fillStyle = '#222'; g.font = `500 24px ${FONT}`; g.fillText('Coming over at 5!', 36, 226); g.fillText('Bringing cocoa ☕', 36, 260);
  }
  phoneTex.needsUpdate = true;
}
const PLAN = ['Tea', 'Snacks', 'Blanket', 'Candle', 'Book', 'Lamp'];
function drawPlan(done) {
  const g = planTex.userData.canvas.getContext('2d'), w = 256, h = 340;
  g.fillStyle = '#fffaf0'; g.fillRect(0, 0, w, h); g.strokeStyle = '#cfe0f0'; g.lineWidth = 2;
  for (let y = 70; y < h; y += 40) { g.beginPath(); g.moveTo(10, y + 8); g.lineTo(w - 10, y + 8); g.stroke(); }
  g.fillStyle = '#c4622b'; g.font = `600 30px ${FONT}`; g.textAlign = 'center'; g.fillText('REST PLAN', w / 2, 44);
  g.textAlign = 'left'; g.font = `500 26px ${FONT}`;
  PLAN.forEach((p, i) => {
    const y = 100 + i * 40; g.fillStyle = '#333'; g.fillText(p, 64, y);
    g.strokeStyle = '#333'; g.lineWidth = 2; g.strokeRect(24, y - 22, 24, 24);
    if (i < done) { g.strokeStyle = '#2f9a55'; g.lineWidth = 5; g.beginPath(); g.moveTo(26, y - 10); g.lineTo(35, y); g.lineTo(52, y - 28); g.stroke(); }
  });
  planTex.needsUpdate = true;
}
const clockTex = tex(256, 256, (g, w, h) => {
  g.fillStyle = '#fbf6ea'; g.beginPath(); g.arc(w / 2, h / 2, 124, 0, 7); g.fill();
  g.fillStyle = '#3a2a20'; for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; g.beginPath(); g.arc(w / 2 + 100 * Math.sin(a), h / 2 - 100 * Math.cos(a), i % 3 ? 4 : 8, 0, 7); g.fill(); }
});

// ───────────────────────────────────────────── materials
const phys = (o) => new THREE.MeshPhysicalMaterial(o), std = (o) => new THREE.MeshStandardMaterial(o);
const M = {
  skin: phys({ map: skinTex, roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.35, sheen: 0.4, sheenColor: new THREE.Color('#ffb070'), emissive: new THREE.Color('#ff5a10'), emissiveIntensity: 0.06 }),
  arm: phys({ map: armTex, roughness: 0.45, clearcoat: 0.3, clearcoatRoughness: 0.4, sheen: 0.4, sheenColor: new THREE.Color('#ffb070'), emissive: new THREE.Color('#ff5a10'), emissiveIntensity: 0.05 }),
  eye: phys({ map: eyeTex('#2c4a6e', '#3f6e9c'), roughness: 0.08, clearcoat: 1, clearcoatRoughness: 0.03 }),
  crabEye: phys({ map: eyeTex('#4a2a1a', '#7a4a2a'), roughness: 0.08, clearcoat: 1 }),
  mouth: std({ color: '#5b1d12', roughness: 0.5 }),
  tongue: std({ color: '#e0605a', roughness: 0.6 }),
  brow: std({ color: '#c94a14', roughness: 0.6 }),
  lid: phys({ color: '#f9782a', roughness: 0.4, clearcoat: 0.3, emissive: new THREE.Color('#ff5a10'), emissiveIntensity: 0.05 }),
  blush: std({ color: '#ff6a5a', roughness: 0.8, transparent: true, opacity: 0.0, depthWrite: false }),
  sofa: std({ map: fabric('#9aa98f', '#3f4a3a'), roughness: 0.95 }),
  knit: std({ map: knitTex, roughness: 1 }), plaid: std({ map: plaidTex, roughness: 0.95 }), pillow: std({ map: pillowTex, roughness: 0.95 }),
  blanket: std({ map: creamKnit, roughness: 1, side: THREE.DoubleSide }),
  wood: std({ map: woodTex, roughness: 0.55 }), woodDark: std({ color: '#8a5a32', roughness: 0.6 }),
  wall: std({ color: '#efe2c9', roughness: 0.95 }), wallSide: std({ color: '#e9d9bd', roughness: 0.95 }),
  ceramic: phys({ color: '#f6efe2', roughness: 0.25, clearcoat: 0.6 }), teal: phys({ map: shellTex, roughness: 0.25, clearcoat: 0.8 }),
  navy: std({ color: '#2b3e66', roughness: 0.3, metalness: 0.2 }), terracotta: std({ color: '#c9774a', roughness: 0.8 }), leaf: std({ color: '#5f8a4a', roughness: 0.7 }),
  bulb: std({ color: '#ffd38a', emissive: new THREE.Color('#ffb84a'), emissiveIntensity: 3.5 }),
  window: std({ color: '#fff6e2', emissive: new THREE.Color('#fff1d6'), emissiveIntensity: 0.85 }),
  black: std({ color: '#1a1c20', roughness: 0.4 }), metal: std({ color: '#b9b4ab', roughness: 0.3, metalness: 0.8 }),
  tv: std({ map: tvTex, emissive: new THREE.Color('#ffffff'), emissiveMap: tvTex, emissiveIntensity: 0.9 }),
  phone: std({ map: phoneTex, emissive: new THREE.Color('#ffffff'), emissiveMap: phoneTex, emissiveIntensity: 0.0 }),
  paper: std({ map: planTex, roughness: 0.9 }), cal: std({ map: calendarTex, roughness: 0.9 }), clock: std({ map: clockTex, roughness: 0.6 }),
  crab: phys({ color: '#e8553a', roughness: 0.45, clearcoat: 0.4 }), cocoa: std({ color: '#5a3018', roughness: 0.15 }),
  water: phys({ color: '#9fd8ff', roughness: 0.05, transmission: 0.0, transparent: true, opacity: 0.55, depthWrite: false }),
  flame: std({ color: '#ffd27a', emissive: new THREE.Color('#ffae3a'), emissiveIntensity: 5 }),
  shade: std({ color: '#f3e3c3', emissive: new THREE.Color('#ffcf8a'), emissiveIntensity: 0, side: THREE.DoubleSide, roughness: 0.9 }),
  steam: new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.15, depthWrite: false }),
  dust: new THREE.MeshBasicMaterial({ color: '#fff5d8', transparent: true, opacity: 0.8, depthWrite: false }),
};
const RB = (w, h, d, r = 0.05, s = 4) => new RoundedBoxGeometry(w, h, d, s, r);
function mesh(geo, mat, p = [0, 0, 0], r = [0, 0, 0], parent = scene, shadow = true) {
  const m = new THREE.Mesh(geo, mat); m.position.set(...p); m.rotation.set(...r);
  m.castShadow = shadow; m.receiveShadow = true; parent.add(m); return m;
}

// ───────────────────────────────────────────── the living room (fixed set)
mesh(new THREE.PlaneGeometry(12, 12), M.wood, [0, 0, 0], [-Math.PI / 2, 0, 0], scene, false);
mesh(new THREE.PlaneGeometry(12, 5), M.wall, [0, 2.5, -1.25], [0, 0, 0], scene, false);
mesh(new THREE.PlaneGeometry(8, 5), M.wallSide, [-2.6, 2.5, 1.5], [0, Math.PI / 2, 0], scene, false);
mesh(new THREE.PlaneGeometry(8, 5), M.wallSide, [2.6, 2.5, 1.5], [0, -Math.PI / 2, 0], scene, false);
mesh(new THREE.PlaneGeometry(12, 5), M.wallSide, [0, 2.5, 3.4], [0, Math.PI, 0], scene, false);
const windowPane = mesh(new THREE.PlaneGeometry(0.9, 1.3), M.window, [1.45, 1.75, -1.24], [0, 0, 0], scene, false);
for (const x of [0.92, 1.98]) mesh(new THREE.PlaneGeometry(0.32, 1.6), std({ color: '#fbf5ea', roughness: 1, side: THREE.DoubleSide }), [x, 1.7, -1.2]);
// pictures; the right one hangs crooked until Pip… until Nori fixes it
const frames = [];
for (const [x, y, k] of [[-1.55, 1.85, 'wave'], [-1.05, 1.95, 'star']]) {
  const f = new THREE.Group(); f.position.set(x, y, -1.22); scene.add(f);
  mesh(RB(0.32, 0.38, 0.03, 0.01), M.woodDark, [0, 0, 0], [0, 0, 0], f); mesh(new THREE.PlaneGeometry(0.26, 0.32), std({ map: pictureTex(k), roughness: 0.9 }), [0, 0, 0.017], [0, 0, 0], f, false);
  frames.push(f);
}
mesh(new THREE.PlaneGeometry(0.22, 0.28), M.cal, [-0.62, 1.62, -1.235], [0, 0, 0], scene, false);
// wall clock
const clock = new THREE.Group(); clock.position.set(0.05, 2.12, -1.22); scene.add(clock);
mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.03, 48), M.woodDark, [0, 0, 0], [Math.PI / 2, 0, 0], clock);
mesh(new THREE.CircleGeometry(0.15, 48), M.clock, [0, 0, 0.017], [0, 0, 0], clock, false);
const hourHand = mesh(new THREE.BoxGeometry(0.012, 0.08, 0.004), M.black, [0, 0, 0.022], [0, 0, 0], clock, false); hourHand.geometry.translate(0, 0.035, 0);
const minHand = mesh(new THREE.BoxGeometry(0.008, 0.12, 0.004), M.black, [0, 0, 0.026], [0, 0, 0], clock, false); minHand.geometry.translate(0, 0.055, 0);
// shelf, plants, fairy lights
for (const y of [0.55, 0.95, 1.35]) mesh(RB(0.95, 0.04, 0.32, 0.01), M.woodDark, [1.55, y, -1.05]);
for (const x of [1.08, 2.02]) mesh(RB(0.04, 1.4, 0.32, 0.01), M.woodDark, [x, 0.7, -1.05]);
const plantAt = (x, y, z, s) => {
  const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g);
  mesh(new THREE.CylinderGeometry(0.07 * s, 0.055 * s, 0.12 * s, 20), M.terracotta, [0, 0.06 * s, 0], [0, 0, 0], g);
  for (let i = 0; i < 9; i++) mesh(new THREE.ConeGeometry(0.018 * s, 0.22 * s, 8), M.leaf, [(rnd() - 0.5) * 0.08 * s, 0.2 * s, (rnd() - 0.5) * 0.08 * s], [(rnd() - 0.5) * 0.6, 0, (rnd() - 0.5) * 0.6], g);
  return g;
};
const PLANTS = [plantAt(-1.75, 0, -0.9, 3.0), plantAt(1.28, 1.37, -1.0, 1), plantAt(1.78, 1.37, -1.0, 1.2)];
const PLANT_TOP = [V(-1.75, 0.75, -0.9), V(1.28, 1.62, -1.0), V(1.78, 1.68, -1.0)];
const bulbs = [];
for (let i = 0; i <= 18; i++) { const u = i / 18; bulbs.push(mesh(new THREE.SphereGeometry(0.014, 10, 8), M.bulb, [lerp(0.95, 2.1, u), 1.32 - Math.sin(u * Math.PI) * 0.12 + 0.06 * Math.sin(u * 18), -0.9], [0, 0, 0], scene, false)); }
for (let i = 0; i <= 26; i++) { const u = i / 26; mesh(new THREE.SphereGeometry(0.013, 10, 8), M.bulb, [lerp(-2.2, 0.9, u), 2.45 - Math.sin(u * Math.PI) * 0.28, -1.2], [0, 0, 0], scene, false); }
// books: two shelves of them; Nori sorts the top row by colour
const BOOKS = [];
{
  const hues = [0.02, 0.58, 0.12, 0.33, 0.85, 0.07, 0.5, 0.15, 0.95, 0.62, 0.28, 0.75];
  let x = 1.18;
  hues.forEach((hue, i) => {
    const bw = 0.045 + (i % 3) * 0.012, bh = 0.22 + ((i * 7) % 5) * 0.025;
    const m = mesh(RB(bw, bh, 0.2, 0.005, 1), std({ color: new THREE.Color().setHSL(hue, 0.5, 0.55), roughness: 0.8 }), [x, 0.97 + bh / 2 + 0.02, -1.02]);
    BOOKS.push({ m, hue, w: bw, h: bh, x0: x });
    x += bw + 0.012;
  });
  // sorted slots by hue
  const sorted = [...BOOKS].sort((a, b) => a.hue - b.hue);
  let sx = 1.18; for (const b of sorted) { b.x1 = sx; sx += b.w + 0.012; }
  let x2 = 1.2; while (x2 < 1.95) { const bw = 0.03 + rnd() * 0.04, bh = 0.2 + rnd() * 0.12; mesh(RB(bw, bh, 0.22, 0.005, 1), std({ color: new THREE.Color().setHSL(rnd(), 0.35, 0.55), roughness: 0.8 }), [x2, 0.57 + bh / 2 + 0.02, -1.02]); x2 += bw + 0.008; }
}
// floor lamp (Nori switches it on)
mesh(new THREE.CylinderGeometry(0.16, 0.18, 0.03, 32), M.black, [-1.55, 0.015, -0.55]);
mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.45, 12), M.black, [-1.55, 0.74, -0.55]);
const shade = mesh(new THREE.CylinderGeometry(0.14, 0.22, 0.26, 32, 1, true), M.shade, [-1.55, 1.5, -0.55]);
const lampLight = new THREE.PointLight('#ffc27a', 0, 4, 2); lampLight.position.set(-1.55, 1.42, -0.55); scene.add(lampLight);
// sofa
mesh(RB(2.3, 0.36, 0.95, 0.06), M.sofa, [0, 0.24, -0.35]);
mesh(RB(1.08, 0.17, 0.8, 0.07), M.sofa, [-0.55, 0.5, -0.28]); mesh(RB(1.08, 0.17, 0.8, 0.07), M.sofa, [0.55, 0.5, -0.28]);
mesh(RB(2.3, 0.62, 0.26, 0.1), M.sofa, [0, 0.78, -0.72], [-0.12, 0, 0]);
for (const x of [-1.2, 1.2]) mesh(RB(0.26, 0.62, 0.95, 0.11), M.sofa, [x, 0.48, -0.33]);
// coffee table & side table
mesh(RB(1.7, 0.06, 0.75, 0.02), M.wood, [0, 0.42, 0.85]);
for (const [x, z] of [[-0.75, 0.55], [0.75, 0.55], [-0.75, 1.15], [0.75, 1.15]]) mesh(new THREE.CylinderGeometry(0.025, 0.02, 0.4, 10), M.woodDark, [x, 0.2, z]);
mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.04, 40), M.wood, [-1.55, 0.56, 0.3]); mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.54, 12), M.woodDark, [-1.55, 0.27, 0.3]);
// TV across the room, the door on the left wall
mesh(RB(1.4, 0.45, 0.4, 0.03), M.woodDark, [0, 0.23, 3.1]);
mesh(RB(1.1, 0.64, 0.05, 0.02), M.black, [0, 0.82, 3.12]);
const tvScreen = mesh(new THREE.PlaneGeometry(1.02, 0.574), M.tv, [0, 0.82, 3.09], [0, Math.PI, 0], scene, false);
const tvLight = new THREE.PointLight('#8fc6ff', 0, 3.5, 2); tvLight.position.set(0, 0.9, 2.8); scene.add(tvLight);
const doorPivot = new THREE.Group(); doorPivot.position.set(-2.58, 0, 0.15); scene.add(doorPivot);
mesh(RB(0.06, 2.0, 0.9, 0.01), std({ color: '#c08a5a', roughness: 0.6 }), [0, 1.0, 0.45], [0, 0, 0], doorPivot);
mesh(new THREE.SphereGeometry(0.03, 16, 12), M.metal, [0.05, 0.95, 0.82], [0, 0, 0], doorPivot);
const doorway = mesh(new THREE.PlaneGeometry(0.9, 2.0), std({ color: '#ffe9c4', emissive: new THREE.Color('#ffd9a0'), emissiveIntensity: 1.2 }), [-2.62, 1.0, 0.6], [0, Math.PI / 2, 0], scene, false);


// ───────────────────────────────────────────── set dressing (the cosy clutter of a lived-in room)
const leafTex = tex(256, 256, (g, w, h) => {
  g.clearRect(0, 0, w, h);
  g.fillStyle = '#3f7a3a'; g.beginPath(); g.ellipse(w / 2, h / 2, w * 0.42, h * 0.46, 0, 0, 7); g.fill();
  g.globalCompositeOperation = 'destination-out';
  for (let k = 0; k < 6; k++) { const y = h * (0.22 + k * 0.11); for (const s of [-1, 1]) { g.beginPath(); g.ellipse(w / 2 + s * w * 0.3, y, w * 0.1, h * 0.025, s * 0.4, 0, 7); g.fill(); } }
  g.globalCompositeOperation = 'source-over';
  g.strokeStyle = '#2e5a2a'; g.lineWidth = 4; g.beginPath(); g.moveTo(w / 2, h * 0.06); g.lineTo(w / 2, h * 0.94); g.stroke();
});
const leafMat = std({ map: leafTex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.6 });
const smallLeafTex = tex(64, 64, (g, w, h) => { g.clearRect(0, 0, w, h); g.fillStyle = '#5e9a4a'; g.beginPath(); g.moveTo(w / 2, 2); g.quadraticCurveTo(w - 4, h / 2, w / 2, h - 2); g.quadraticCurveTo(4, h / 2, w / 2, 2); g.fill(); });
const smallLeafMat = std({ map: smallLeafTex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.6 });
const rugTex = tex(512, 512, (g, w, h) => {
  for (let r = 256; r > 0; r -= 6) { g.fillStyle = r % 36 < 6 ? '#b88a55' : r % 18 < 6 ? '#d8b98a' : '#cda673'; g.beginPath(); g.arc(256, 256, r, 0, 7); g.fill(); }
  g.globalAlpha = 0.15; speckle(g, w, h, 3000, '#5a3a1a', 0.5, 1.2);
});
const wickerTex = tex(256, 256, (g, w, h) => { g.fillStyle = '#c99a5e'; g.fillRect(0, 0, w, h); g.strokeStyle = '#8a6234'; g.lineWidth = 3; for (let y = 0; y < h; y += 10) for (let x = (y / 10) % 2 * 10; x < w; x += 20) { g.beginPath(); g.ellipse(x, y, 9, 4, 0, 0, 7); g.stroke(); } }, [3, 2]);
const sketchTex = tex(512, 256, (g, w, h) => {
  g.fillStyle = '#fbf7ec'; g.fillRect(0, 0, w, h); g.fillStyle = '#e6dcc8'; g.fillRect(w / 2 - 2, 0, 4, h);
  g.strokeStyle = '#5a6a8a'; g.lineWidth = 3;
  g.beginPath(); g.arc(120, 110, 40, Math.PI, 0); g.stroke();                                // a little octopus doodle
  for (let k = 0; k < 6; k++) { g.beginPath(); g.moveTo(85 + k * 14, 110); g.quadraticCurveTo(80 + k * 14, 160, 95 + k * 14, 175); g.stroke(); }
  g.fillStyle = '#5a6a8a'; g.beginPath(); g.arc(106, 100, 4, 0, 7); g.arc(134, 100, 4, 0, 7); g.fill();
  g.font = `500 22px ${FONT}`; g.fillText('rest = ?', 300, 70);
  for (let k = 0; k < 5; k++) { g.beginPath(); g.moveTo(300, 110 + k * 24); g.lineTo(460 - k * 20, 110 + k * 24); g.stroke(); }
});
const octoMugTex = tex(256, 128, (g, w, h) => {
  g.fillStyle = '#f6efe2'; g.fillRect(0, 0, w, h); g.fillStyle = '#ff7a1c';
  g.beginPath(); g.arc(64, 52, 22, Math.PI, 0); g.fill(); g.fillRect(42, 52, 44, 8);
  for (let k = 0; k < 5; k++) { g.beginPath(); g.ellipse(46 + k * 9, 72, 4, 14, 0, 0, 7); g.fill(); }
  g.fillStyle = '#222'; g.beginPath(); g.arc(57, 46, 3, 0, 7); g.arc(71, 46, 3, 0, 7); g.fill();
});
const outsideTex = tex(256, 256, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#cfe6f5'); gr.addColorStop(0.6, '#eef3e2'); gr.addColorStop(1, '#a9c48a');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  for (let k = 0; k < 14; k++) { g.fillStyle = `rgba(${80 + rnd() * 40}, ${130 + rnd() * 50}, ${70 + rnd() * 30}, 0.85)`; g.beginPath(); g.arc(rnd() * w, h * (0.55 + rnd() * 0.3), 20 + rnd() * 40, 0, 7); g.fill(); }
});
const blobTex = tex(128, 128, (g, w, h) => { const gr = g.createRadialGradient(64, 64, 4, 64, 64, 64); gr.addColorStop(0, 'rgba(40,22,10,0.55)'); gr.addColorStop(1, 'rgba(40,22,10,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
const blobMat = new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false });
const contact = (x, z, sx, sz, y = 0.006) => { const m = mesh(new THREE.PlaneGeometry(1, 1), blobMat, [x, y, z], [-Math.PI / 2, 0, 0], scene, false); m.scale.set(sx, sz, 1); m.renderOrder = 1; return m; };
const spineTex = (hue) => tex(64, 256, (g, w, h) => {
  const c = new THREE.Color().setHSL(hue, 0.45, 0.5); g.fillStyle = `#${c.getHexString()}`; g.fillRect(0, 0, w, h);
  g.fillStyle = 'rgba(255,240,210,0.75)'; g.fillRect(0, h * 0.12, w, 6); g.fillRect(0, h * 0.82, w, 6);
  g.fillRect(w * 0.3, h * 0.35, w * 0.4, h * 0.3);
});
const starShape = (() => { const s = new THREE.Shape(); for (let i = 0; i < 10; i++) { const a = i * Math.PI / 5 + Math.PI / 2, r = i % 2 ? 0.4 : 1; const x = Math.cos(a) * r, y = Math.sin(a) * r; if (i) s.lineTo(x, y); else s.moveTo(x, y); } s.closePath(); return s; })();
const starGeo = new THREE.ExtrudeGeometry(starShape, { depth: 0.3, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.08, bevelSegments: 2 }); starGeo.scale(0.035, 0.035, 0.035);
function succulent(g, x, y, z, s, kind) {
  mesh(new THREE.CylinderGeometry(0.06 * s, 0.045 * s, 0.09 * s, 20), kind % 2 ? M.terracotta : std({ color: '#e8dccb', roughness: 0.5 }), [x, y + 0.045 * s, z], [0, 0, 0], g);
  if (kind === 0) { for (let i = 0; i < 12; i++) { const a = i * 2.4, r = 0.02 + i * 0.003; mesh(new THREE.SphereGeometry(0.018 * s, 10, 8), std({ color: '#7fa86a', roughness: 0.6 }), [x + Math.cos(a) * r * s, y + 0.1 * s + i * 0.002, z + Math.sin(a) * r * s], [0.6, a, 0], g).scale.set(1, 0.6, 1.8); } }
  else if (kind === 1) { mesh(new THREE.CapsuleGeometry(0.03 * s, 0.1 * s, 6, 12), std({ color: '#5b8f4a', roughness: 0.7 }), [x, y + 0.15 * s, z], [0, 0, 0], g); mesh(new THREE.CapsuleGeometry(0.018 * s, 0.05 * s, 6, 10), std({ color: '#5b8f4a', roughness: 0.7 }), [x + 0.035 * s, y + 0.16 * s, z], [0, 0, -0.9], g); }
  else { for (let i = 0; i < 7; i++) mesh(new THREE.ConeGeometry(0.012 * s, 0.13 * s, 6), std({ color: '#6f9a55', roughness: 0.7 }), [x + (rnd() - 0.5) * 0.04 * s, y + 0.13 * s, z + (rnd() - 0.5) * 0.04 * s], [(rnd() - 0.5) * 0.7, 0, (rnd() - 0.5) * 0.7], g); }
}
{
  const g = new THREE.Group(); scene.add(g);
  // a proper window: frame, mullions, sill, the garden beyond
  M.window.map = outsideTex; M.window.emissiveMap = outsideTex; M.window.needsUpdate = true;
  for (const [x, y, w, h] of [[1.45, 2.42, 1.0, 0.06], [1.45, 1.08, 1.0, 0.06], [0.97, 1.75, 0.06, 1.4], [1.93, 1.75, 0.06, 1.4], [1.45, 1.75, 0.03, 1.3], [1.45, 1.78, 0.9, 0.03]]) mesh(RB(w, h, 0.06, 0.01), std({ color: '#f3ead9', roughness: 0.6 }), [x, y, -1.21], [0, 0, 0], g);
  mesh(RB(1.1, 0.04, 0.2, 0.01), std({ color: '#f3ead9', roughness: 0.6 }), [1.45, 1.07, -1.15], [0, 0, 0], g);
  succulent(g, 1.12, 1.09, -1.13, 1.0, 0); succulent(g, 1.3, 1.09, -1.12, 1.2, 1); succulent(g, 1.62, 1.09, -1.13, 0.9, 2); succulent(g, 1.8, 1.09, -1.12, 1.1, 0);
  // more frames and a floating shelf above the sofa's left arm
  for (const [x, y, w, h, k] of [[-1.95, 1.55, 0.26, 0.32, 'star'], [-0.3, 1.95, 0.22, 0.22, 'wave']]) { mesh(RB(w + 0.04, h + 0.04, 0.03, 0.01), M.woodDark, [x, y, -1.225], [0, 0, 0], g); mesh(new THREE.PlaneGeometry(w, h), std({ map: pictureTex(k), roughness: 0.9 }), [x, y, -1.205], [0, 0, 0], g, false); }
  mesh(RB(0.6, 0.03, 0.16, 0.01), M.woodDark, [-1.55, 1.4, -1.16], [0, 0, 0], g);
  succulent(g, -1.75, 1.415, -1.14, 0.9, 1); succulent(g, -1.38, 1.415, -1.14, 0.8, 2);
  for (let k = 0; k < 4; k++) mesh(RB(0.035, 0.18 + k * 0.01, 0.12, 0.004, 1), std({ map: spineTex(rnd()), roughness: 0.8 }), [-1.6 + k * 0.04, 1.51 + k * 0.005, -1.15], [0, 0, 0], g);
  // the bookshelf: spines with titles, stars, jars, baskets, a trailing pothos
  for (const [x, y] of [[1.25, 1.4], [1.85, 1.4], [1.6, 0.6]]) mesh(starGeo, M.gold, [x, y + 0.04, -0.94], [0, 0.3, 0], g);
  for (const [x, y] of [[1.92, 0.6], [1.22, 0.6]]) { mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.11, 20), phys({ color: '#dff0f0', roughness: 0.05, transparent: true, opacity: 0.5 }), [x, y + 0.055, -1.0], [0, 0, 0], g); mesh(new THREE.CylinderGeometry(0.042, 0.042, 0.02, 20), M.woodDark, [x, y + 0.12, -1.0], [0, 0, 0], g); }
  for (const x of [1.3, 1.8]) mesh(RB(0.36, 0.22, 0.26, 0.04), std({ map: wickerTex, roughness: 0.9 }), [x, 0.13, -1.0], [0, 0, 0], g);
  for (let k = 0; k < 16; k++) { const u = k / 15; const lf = mesh(new THREE.PlaneGeometry(0.06, 0.06), smallLeafMat, [1.95 + Math.sin(u * 5) * 0.03, 1.45 - u * 0.55, -0.92 + Math.cos(u * 4) * 0.03], [0.3, rnd() * 3, rnd() * 3], g, false); lf.castShadow = true; }
  // big monstera in the left corner
  mesh(new THREE.CylinderGeometry(0.17, 0.13, 0.32, 28), std({ color: '#d9cbb3', roughness: 0.7 }), [-2.15, 0.16, -0.75], [0, 0, 0], g);
  for (let k = 0; k < 9; k++) {
    const a = k * 0.7 + 0.3, len = 0.5 + rnd() * 0.5;
    const stem = new THREE.Group(); stem.position.set(-2.15, 0.3, -0.75); stem.rotation.set(Math.cos(a) * 0.5, a, Math.sin(a) * 0.5); g.add(stem);
    mesh(new THREE.CylinderGeometry(0.007, 0.009, len, 6), M.leaf, [0, len / 2, 0], [0, 0, 0], stem);
    const lf = mesh(new THREE.PlaneGeometry(0.42, 0.42), leafMat, [0, len + 0.12, 0.05], [-0.7, 0, 0], stem, false); lf.castShadow = true;
  }
  // rug, floor clutter, the knitting basket
  mesh(new THREE.CircleGeometry(1.25, 64), std({ map: rugTex, roughness: 1 }), [0.1, 0.005, 0.95], [-Math.PI / 2, 0, 0], g, false);
  for (let k = 0; k < 9; k++) {
    const x = rr(-1.8, 1.9), z = rr(1.4, 2.6);
    const sh = mesh(new THREE.ConeGeometry(0.025, 0.05, 12), std({ color: ['#f2d6c4', '#e9c2a8', '#f7e9da'][k % 3], roughness: 0.5 }), [x, 0.018, z], [Math.PI / 2, rnd() * 6, 0], g); sh.scale.set(1, 1, 0.7);
  }
  mesh(new THREE.SphereGeometry(0.07, 20, 14), std({ color: '#d9765a', roughness: 1 }), [1.05, 0.07, 1.5], [0, 0, 0], g);
  for (const s of [-1, 1]) mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.3, 6), M.woodDark, [1.05 + s * 0.03, 0.12, 1.5], [0.4 * s, 0, 0.9], g);
  mesh(RB(0.42, 0.26, 0.32, 0.05), std({ map: wickerTex, roughness: 0.9 }), [-2.2, 0.13, 0.75], [0, 0.6, 0], g);
  for (let k = 0; k < 2; k++) mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.36, 20), M.blanket, [-2.2 + k * 0.1, 0.3, 0.75], [Math.PI / 2, 0.6, 0], g);
  // sketchbook, stacked books on the table
  mesh(RB(0.36, 0.01, 0.24, 0.004, 1), std({ map: sketchTex, roughness: 0.9 }), [0.02, 0.456, 0.95], [0, -0.12, 0], g);
  for (let k = 0; k < 3; k++) mesh(RB(0.22 - k * 0.02, 0.035, 0.16, 0.006, 1), std({ map: spineTex(0.05 + k * 0.3), roughness: 0.8 }), [-0.68, 0.468 + k * 0.036, 0.62], [0, 0.2 * k, 0], g);
  // soft contact shadows where things meet the floor
  contact(0, -0.3, 2.6, 1.3); contact(0, 0.85, 2.0, 1.0); contact(-1.55, 0.3, 0.7, 0.7); contact(1.55, -1.0, 1.2, 0.5); contact(-2.15, -0.75, 0.6, 0.6); contact(-1.55, -0.55, 0.5, 0.5); contact(0, 3.05, 1.7, 0.6); contact(-2.2, 0.75, 0.7, 0.55);
}

// ───────────────────────────────────────────── props (move on keyframes)
const PROPS = {};
function prop(name, obj, keys) { PROPS[name] = { obj, keys: keys.map(([t, p, r = [0, 0, 0], lift = 0]) => ({ t, p: V(...p), r: new THREE.Euler(...r), lift })) }; scene.add(obj); return obj; }
function group(build) { const g = new THREE.Group(); build(g); g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; }
function propAt(name, t) {
  const k = PROPS[name].keys;
  if (t <= k[0].t) return { p: k[0].p.clone(), r: k[0].r };
  for (let i = 0; i < k.length - 1; i++) {
    if (t <= k[i + 1].t) {
      const u = ease((t - k[i].t) / (k[i + 1].t - k[i].t));
      const p = k[i].p.clone().lerp(k[i + 1].p, u); p.y += Math.sin(Math.PI * u) * k[i + 1].lift;
      const r = new THREE.Euler(lerp(k[i].r.x, k[i + 1].r.x, u), lerp(k[i].r.y, k[i + 1].r.y, u), lerp(k[i].r.z, k[i + 1].r.z, u));
      return { p, r };
    }
  }
  return { p: k[k.length - 1].p.clone(), r: k[k.length - 1].r };
}
const pp = (name, t) => propAt(name, t).p;

const mugG = (cocoa = true, mat = M.ceramic) => group((g) => {
  mesh(new THREE.CylinderGeometry(0.05, 0.045, 0.11, 28, 1, true), mat, [0, 0.055, 0], [0, 0, 0], g);
  mesh(new THREE.CircleGeometry(0.045, 20), mat, [0, 0.001, 0], [Math.PI / 2, 0, 0], g);
  if (cocoa) mesh(new THREE.CircleGeometry(0.047, 24), M.cocoa, [0, 0.095, 0], [-Math.PI / 2, 0, 0], g);
  mesh(new THREE.TorusGeometry(0.028, 0.008, 10, 24), mat, [0.055, 0.055, 0], [0, 0, Math.PI / 2], g);
});
// rest set-up
prop('kettle', group((g) => {
  mesh(new THREE.SphereGeometry(0.09, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.62), M.teal, [0, 0.07, 0], [0, 0, 0], g);
  mesh(new THREE.CylinderGeometry(0.012, 0.02, 0.12, 12), M.teal, [0.1, 0.1, 0], [0, 0, -0.9], g);
  mesh(new THREE.TorusGeometry(0.06, 0.01, 8, 24, Math.PI), M.black, [0, 0.16, 0], [0, 0, 0], g);
}), [[0, [-1.5, 0.58, 0.22]], [21.5, [-1.5, 0.58, 0.22]], [23.0, [-0.62, 0.85, 0.75], [0, Math.PI, 0], 0.25], [24.6, [-0.62, 0.85, 0.75], [0, Math.PI, 0.9]], [25.6, [-1.5, 0.58, 0.22], [0, 0, 0], 0.25],
  [151.0, [-1.5, 0.58, 0.22]], [151.8, [-0.62, 0.85, 0.75], [0, Math.PI, 0.9], 0.2], [152.6, [-1.5, 0.58, 0.22], [0, 0, 0], 0.2]]);
prop('teacup', mugG(true, std({ map: octoMugTex, roughness: 0.3 })), [[0, [-1.62, 0.58, 0.38]], [22.0, [-1.62, 0.58, 0.38]], [23.2, [-0.5, 0.455, 0.75], [0, 0, 0], 0.25]]);
prop('snacks', group((g) => { mesh(new THREE.CylinderGeometry(0.1, 0.07, 0.06, 32), M.ceramic, [0, 0.03, 0], [0, 0, 0], g); for (let i = 0; i < 7; i++) mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.012, 16), std({ color: '#c58a4a' }), [(rnd() - 0.5) * 0.1, 0.06 + i * 0.004, (rnd() - 0.5) * 0.1], [0.3, 0, 0.2], g); }),
  [[0, [-1.45, 0.58, 0.42]], [26.0, [-1.45, 0.58, 0.42]], [27.6, [-0.55, 0.45, 0.95], [0, 0, 0], 0.35]]);
prop('blanket', group((g) => { mesh(RB(0.5, 0.12, 0.35, 0.06, 5), M.blanket, [0, 0.06, 0], [0, 0, 0], g); }),
  [[0, [0.55, 0.45, 0.86], [0, 0.3, 0]], [30.0, [0.55, 0.45, 0.86], [0, 0.3, 0]], [31.8, [0.02, 0.62, 0.02], [0.05, 0, 0], 0.3],
  [84.3, [0.02, 0.62, 0.02], [0.05, 0, 0]], [85.1, [0.4, 0.0, 0.45], [0.2, 0.8, 0.3], 0.15],
  [154.0, [0.4, 0.0, 0.45], [0.2, 0.8, 0.3]], [155.0, [1.2, 0.82, -0.3], [0, 0.2, 0], 0.4],
  [209.0, [1.2, 0.82, -0.3], [0, 0.2, 0]], [212.5, [0.0, 0.66, 0.0], [0.15, 0, 0.0], 0.3]]);
prop('candle', group((g) => { mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.09, 24), std({ color: '#f5ede0', roughness: 0.7 }), [0, 0.045, 0], [0, 0, 0], g); }), [[0, [0.25, 0.45, 1.0]]]);
const flame = mesh(new THREE.SphereGeometry(0.012, 12, 8), M.flame, [0.25, 0.555, 1.0], [0, 0, 0], scene, false); flame.scale.set(1, 1.8, 1);
const candleLight = new THREE.PointLight('#ffb35a', 0, 2.2, 2); candleLight.position.set(0.25, 0.6, 1.0); scene.add(candleLight);
prop('book', group((g) => { mesh(RB(0.16, 0.025, 0.22, 0.004, 1), std({ color: '#c45a4a' }), [0, 0.012, 0], [0, 0, 0], g); }), [[0, [1.92, 0.585, -1.0], [0, 0, Math.PI / 2]], [37.6, [1.92, 0.585, -1.0], [0, 0, Math.PI / 2]], [39.6, [-0.25, 0.455, 0.78], [0, 0.3, 0], 0.4]]);
prop('plan', group((g) => { mesh(new THREE.PlaneGeometry(0.16, 0.21), M.paper, [0, 0, 0], [0, 0, 0], g, false); }), [[0, [-0.3, 0.46, 1.05], [-Math.PI / 2, 0, 0.2]], [19.8, [-0.3, 0.46, 1.05], [-Math.PI / 2, 0, 0.2]], [21.0, [-0.36, 1.05, 0.38], [-0.25, 0.25, 0], 0.15], [48.2, [-0.36, 1.05, 0.38], [-0.25, 0.25, 0]], [49.4, [-0.3, 0.46, 1.05], [-Math.PI / 2, 0, 0.2], 0.15]]);
prop('remote', group((g) => { mesh(RB(0.05, 0.02, 0.16, 0.008, 2), M.black, [0, 0.01, 0], [0, 0, 0], g); mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.005, 12), std({ color: '#d33', emissive: new THREE.Color('#a11'), emissiveIntensity: 0.4 }), [0, 0.022, -0.05], [0, 0, 0], g); }),
  [[0, [1.85, 0.97, -0.9], [0, 0.4, 0]], [58.4, [1.85, 0.97, -0.9], [0, 0.4, 0]], [61.0, [0.42, 0.95, 0.15], [0.9, 0, 0], 0.2], [70.5, [0.42, 0.95, 0.15], [0.9, 0, 0]], [71.6, [0.35, 0.6, -0.05], [0, 0.6, 0], 0.1],
    [214.6, [0.35, 0.6, -0.05], [0, 0.6, 0]], [215.4, [0.5, 0.72, 0.05], [0.7, 0, 0], 0.08], [217.6, [0.5, 0.72, 0.05], [0.7, 0, 0]], [218.2, [0.42, 0.6, -0.02], [0, 0.6, 0], 0.05]]);
prop('phone', group((g) => { mesh(RB(0.075, 0.012, 0.15, 0.01, 2), M.black, [0, 0.006, 0], [0, 0, 0], g); mesh(new THREE.PlaneGeometry(0.066, 0.135), M.phone, [0, 0.0125, 0], [-Math.PI / 2, 0, 0], g, false); }),
  [[0, [0.38, 0.455, 0.72], [0, -0.3, 0]], [139.2, [0.38, 0.455, 0.72], [0, -0.3, 0]], [140.6, [0.3, 1.0, 0.32], [1.25, 0, 0], 0.15], [148.2, [0.3, 1.0, 0.32], [1.25, 0, 0]], [149.0, [0.38, 0.455, 0.72], [0, -0.3, 0], 0.1]]);
// the cleaning kit and the three waterers
prop('duster', group((g) => { mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.3, 8), M.woodDark, [0, -0.15, 0], [0, 0, 0], g); mesh(new THREE.SphereGeometry(0.07, 16, 12), std({ color: '#f0a9c4', roughness: 1 }), [0, 0.02, 0], [0, 0, 0], g); }),
  [[0, [1.65, 0.06, 0.45], [Math.PI / 2, 0, 0]], [84.0, [1.65, 0.06, 0.45], [Math.PI / 2, 0, 0]], [85.0, [1.55, 1.2, -0.75], [0, 0, 0.3], 0.3], [100.0, [1.55, 1.2, -0.75], [0, 0, 0.3]], [101.0, [1.65, 0.06, 0.45], [Math.PI / 2, 0, 0], 0.3]]);
prop('can', group((g) => { mesh(new THREE.CylinderGeometry(0.07, 0.08, 0.14, 24), std({ color: '#5aa16e', roughness: 0.5, metalness: 0.3 }), [0, 0.07, 0], [0, 0, 0], g); mesh(new THREE.CylinderGeometry(0.008, 0.014, 0.18, 10), std({ color: '#5aa16e', metalness: 0.3 }), [0.1, 0.12, 0], [0, 0, -0.9], g); }),
  [[0, [-1.3, 0.0, 0.3]], [113.0, [-1.3, 0.0, 0.3]], [114.4, [-1.55, 0.95, -0.82], [0, 0, -0.7], 0.3], [121.0, [-1.55, 0.95, -0.82], [0, 0, -0.7]], [122.2, [-1.3, 0.0, 0.3], [0, 0, 0], 0.3]]);
prop('glass', group((g) => { mesh(new THREE.CylinderGeometry(0.035, 0.03, 0.1, 20, 1, true), phys({ color: '#dff3ff', roughness: 0.05, transparent: true, opacity: 0.45 }), [0, 0.05, 0], [0, 0, 0], g); }),
  [[0, [0.62, 0.455, 0.6]], [113.6, [0.62, 0.455, 0.6]], [115.0, [1.22, 1.78, -0.95], [0, 0, -1.1], 0.3], [121.0, [1.22, 1.78, -0.95], [0, 0, -1.1]], [122.4, [0.62, 0.455, 0.6], [0, 0, 0], 0.3]]);
prop('mugB', mugG(false, std({ color: '#e0573a', roughness: 0.4 })), [[0, [-0.62, 0.455, 0.98]], [114.0, [-0.62, 0.455, 0.98]], [115.4, [1.72, 1.85, -0.92], [0, 0, -1.1], 0.3], [121.0, [1.72, 1.85, -0.92], [0, 0, -1.1]], [122.6, [-0.62, 0.455, 0.98], [0, 0, 0], 0.3]]);
// cushions get knocked off by the dusting and thrown back during the panic
const cushion = (mat, w = 0.5) => group((g) => mesh(RB(w, w * 0.9, 0.16, 0.07, 5), mat, [0, 0, 0], [0, 0, 0], g));
prop('cushKnit', cushion(M.knit), [[0, [-0.82, 0.78, -0.42], [-0.25, 0.25, 0.12]], [84.4, [-0.82, 0.78, -0.42], [-0.25, 0.25, 0.12]], [85.2, [-0.9, 0.08, 0.55], [-1.5, 0.6, 0.3], 0.3], [152.4, [-0.9, 0.08, 0.55], [-1.5, 0.6, 0.3]], [153.2, [-0.82, 0.78, -0.42], [-0.25, 0.25, 0.12], 0.5]]);
prop('cushPlaid', cushion(M.plaid, 0.42), [[0, [-1.02, 0.72, -0.18], [-0.2, 0.6, 0.2]], [84.5, [-1.02, 0.72, -0.18], [-0.2, 0.6, 0.2]], [85.3, [-1.5, 0.07, 0.35], [-1.55, 1.2, 0], 0.3], [152.8, [-1.5, 0.07, 0.35], [-1.55, 1.2, 0]], [153.6, [-1.02, 0.72, -0.18], [-0.2, 0.6, 0.2], 0.5]]);
prop('cushPlaid2', cushion(M.plaid, 0.4), [[0, [0.75, 0.86, -0.55], [-0.2, -0.1, -0.08]]]);
prop('cushNori', cushion(M.pillow), [[0, [0.66, 0.73, -0.2], [-0.22, -0.22, -0.12]], [84.3, [0.66, 0.73, -0.2], [-0.22, -0.22, -0.12]], [85.0, [0.35, 0.08, 0.95], [-1.5, -0.4, 0], 0.3], [153.0, [1.0, 0.08, 0.5], [-1.5, -0.4, 0]], [153.8, [0.66, 0.73, -0.2], [-0.22, -0.22, -0.12], 0.5]]);
// cocoa that Sunny brings
prop('cocoaS', mugG(true, std({ color: '#f2c94c', roughness: 0.35 })), [[0, [-3.4, 0.2, 0.6]]]);
prop('cocoaN', mugG(true, std({ color: '#7fb6d9', roughness: 0.35 })), [[0, [-3.4, 0.2, 0.6]]]);
// steam, water, dust: simple particle meshes
const steam = []; for (let i = 0; i < 10; i++) steam.push(mesh(new THREE.SphereGeometry(0.02, 8, 6), M.steam, [0, -5, 0], [0, 0, 0], scene, false));
const streams = [0, 1, 2].map(() => mesh(new THREE.CylinderGeometry(0.006, 0.01, 1, 8, 1, true), M.water, [0, -5, 0], [0, 0, 0], scene, false));
const dust = []; for (let i = 0; i < 40; i++) dust.push(mesh(new THREE.SphereGeometry(0.006, 6, 4), M.dust, [0, -5, 0], [0, 0, 0], scene, false));
const zzz = [];

// ───────────────────────────────────────────── Nori
const HEAD0 = V(0, 1.02, -0.18), HR = 0.34;
const nori = new THREE.Group(); scene.add(nori);
const SHELF_SPOT = V(1.95, 0.6, -0.42);
const HEADPATH = [[0, HEAD0, 0], [84.25, HEAD0, 0], [84.95, V(0.7, 0.64, 0.4), 0.35], [85.6, V(1.25, 0.6, 0.8), 0.05], [86.3, V(2.12, 0.6, 0.3), 0.05], [87.0, SHELF_SPOT, 0.05],
  [123.0, SHELF_SPOT, 0], [123.5, V(2.12, 0.6, 0.3), 0.05], [124.0, V(1.25, 0.6, 0.8), 0.05], [124.4, V(0.7, 0.64, 0.4), 0.05], [124.95, HEAD0, 0.35]];
function headPath(t) {
  let i = 0; while (i < HEADPATH.length - 2 && t > HEADPATH[i + 1][0]) i++;
  const [ta, a] = HEADPATH[i], [tb, b, lift] = HEADPATH[i + 1], u = ease(clamp((t - ta) / (tb - ta), 0, 1));
  const p = a.clone().lerp(b, u); p.y += Math.sin(Math.PI * u) * lift;
  p.moving = t > ta && t < tb && a.distanceTo(b) > 0.01 ? 1 : 0;
  return p;
}
const headPivot = new THREE.Group(); headPivot.position.copy(HEAD0); nori.add(headPivot);
const head = mesh(new THREE.SphereGeometry(HR, 96, 64), M.skin, [0, 0, 0], [0, 0, 0], headPivot);
const web = mesh(new THREE.SphereGeometry(0.27, 48, 24), M.skin, [0, -0.25, 0.01], [0, 0, 0], headPivot); web.scale.set(1.05, 0.42, 0.85);
const face = new THREE.Group(); headPivot.add(face);
const eyes = [], lids = [], lowLids = [], brows = [], blushes = [];
for (const s of [-1, 1]) {
  const n = V(s * 0.36, -0.06, 0.93).normalize();
  const e = mesh(new THREE.SphereGeometry(0.092, 48, 32), M.eye, n.clone().multiplyScalar(HR * 0.8).toArray(), [0, 0, 0], face);
  const lid = mesh(new THREE.SphereGeometry(0.099, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.5), M.lid, e.position.toArray(), [0, 0, 0], face);
  const low = mesh(new THREE.SphereGeometry(0.096, 48, 24, 0, Math.PI * 2, Math.PI * 0.5, Math.PI * 0.5), M.lid, e.position.toArray(), [0, 0, 0], face);
  const brow = mesh(new THREE.CapsuleGeometry(0.017, 0.085, 6, 12), M.brow, V(s * 0.34, 0.27, 0.9).normalize().multiplyScalar(HR * 1.01).toArray(), [0, 0, 0], face);
  const bl = mesh(new THREE.CircleGeometry(0.04, 24), M.blush, V(s * 0.55, -0.32, 0.77).normalize().multiplyScalar(HR * 1.005).toArray(), [0, 0, 0], face, false);
  bl.lookAt(bl.position.clone().multiplyScalar(2)); bl.scale.set(1.3, 0.8, 1);
  eyes.push(e); lids.push(lid); lowLids.push(low); brows.push({ m: brow, s, base: brow.position.clone() }); blushes.push(bl);
}
const mouthG = new THREE.Group(); mouthG.position.copy(V(0, -0.36, 0.93).normalize().multiplyScalar(HR * 0.99)); mouthG.rotation.x = 0.36; face.add(mouthG);
const smileLine = mesh(new THREE.TorusGeometry(0.035, 0.009, 10, 32, Math.PI * 0.85), M.mouth, [0, 0, 0.004], [0, 0, Math.PI + Math.PI * 0.075], mouthG);
const mouthOpen = mesh(new THREE.SphereGeometry(0.04, 24, 16), M.mouth, [0, -0.012, 0], [0, 0, 0], mouthG); mouthOpen.scale.set(1, 0.1, 0.35);
const tongue = mesh(new THREE.SphereGeometry(0.022, 16, 12), M.tongue, [0, -0.025, 0.006], [0, 0, 0], mouthG); tongue.scale.set(1, 0.5, 0.4);

// arms
const ARM_ANG = [-2.9, -2.2, -1.35, -0.45, 0.45, 1.35, 2.2, 2.9].map((a) => a * 0.55 + Math.PI / 2);
function surfaceY(x, z) {
  if (Math.abs(x) < 1.07 && z > -0.68 && z < 0.12) return 0.585;
  if (Math.abs(x) < 1.15 && z <= -0.68) return 1.05;
  if (Math.abs(x) >= 1.07 && Math.abs(x) < 1.33 && z > -0.8 && z < 0.15) return 0.79;
  return 0.0;
}
function legPoints(i, t, head, moving) {
  const a = (i / 8) * Math.PI * 2 + 0.4;
  const base = head.clone().add(V(Math.cos(a) * 0.2, -0.27, Math.sin(a) * 0.17));
  const phase = t * 9 + (i % 2) * Math.PI;
  const step = moving ? Math.max(0, Math.sin(phase)) * 0.09 : 0;
  const foot = V(head.x + Math.cos(a) * (0.46 + 0.04 * Math.sin(t * 1.1 + i)), 0.035 + step, head.z + Math.sin(a) * 0.42);
  const pts = [];
  for (let k = 0; k <= 10; k++) {
    const s = k / 10;
    const p = base.clone().lerp(foot, Math.min(1, s * 1.35));
    p.y = lerp(base.y, foot.y, smooth(0, 0.75, s)) + Math.sin(Math.PI * Math.min(1, s * 1.35)) * 0.06;
    if (s > 0.74) { const c = (s - 0.74) / 0.26; p.add(V(Math.cos(a) * 0.14 * c, 0.05 * c * c, Math.sin(a) * 0.14 * c)); }
    pts.push(p);
  }
  return pts;
}
function restPoints(i, t, head) {
  const standing = smooth(0.8, 0.68, head.y);
  if (standing > 0.99) return legPoints(i, t, head, head.moving);
  if (standing > 0.01) { const a = restSofa(i, t, head), b = legPoints(i, t, head, head.moving); return a.map((p, k) => p.lerp(b[k], standing)); }
  return restSofa(i, t, head);
}
function restSofa(i, t, head) {
  const a = ARM_ANG[i];
  const dir = V(Math.cos(a) * 1.2, 0, Math.sin(a) * 0.34);
  const base = head.clone().add(V(Math.cos(a) * 0.2, -0.27, Math.sin(a) * 0.16));
  const L = 0.5 + 0.2 * Math.abs(Math.cos(a));
  const pts = [];
  for (let k = 0; k <= 10; k++) {
    const s = k / 10, sway = Math.sin(t * 1.3 + i * 0.8 + s * 3.0) * 0.05 * s;
    const p = base.clone().addScaledVector(dir, s * L).add(V(-dir.z * sway, 0, dir.x * sway));
    const r = lerp(0.09, 0.025, s), ground = surfaceY(p.x, p.z) + r;
    p.y = lerp(base.y, Math.max(ground, base.y - 0.6), smooth(0, 0.45, s));
    if (p.z > 0.12 && ground < 0.2) p.y = Math.max(p.y - (p.z - 0.12) * 1.1, 0.46);
    if (s > 0.72) { const c = (s - 0.72) / 0.28; p.add(V(-dir.x * 0.09 * c * c, 0.07 * c * c, -dir.z * 0.09 * c * c + 0.02 * c)); }
    pts.push(p);
  }
  return pts;
}
function reachPoints(i, target, head, t) {
  const a = ARM_ANG[i];
  const base = head.clone().add(V(Math.cos(a) * 0.2, -0.27, Math.sin(a) * 0.16));
  const out = V(Math.cos(a), 0, Math.sin(a)).normalize();
  const d = target.distanceTo(base);
  const p1 = base.clone().addScaledVector(out, 0.18 + d * 0.15).add(V(0, 0.05 + d * 0.08, 0));
  const p2 = target.clone().add(V(0, 0.12 + d * 0.08, 0)).addScaledVector(out, -0.05);
  const pts = [];
  for (let k = 0; k <= 10; k++) {
    const s = k / 10, q = 1 - s;
    const p = base.clone().multiplyScalar(q * q * q).addScaledVector(p1, 3 * q * q * s).addScaledVector(p2, 3 * q * s * s).addScaledVector(target, s * s * s);
    const wig = Math.sin(t * 2.0 + i + s * 5) * 0.012 * Math.sin(Math.PI * s);
    pts.push(p.add(V(wig, wig * 0.6, -wig)));
  }
  return pts;
}
function taperTube(pts, segs = 64, radial = 16, r0 = 0.095, r1 = 0.016, thin = 1) {
  const curve = new THREE.CatmullRomCurve3(pts);
  const pos = [], nor = [], uv = [], idx = [], up = V(0, 1, 0);
  for (let i = 0; i <= segs; i++) {
    const u = i / segs, P = curve.getPointAt(u), T = curve.getTangentAt(u);
    let N = V().crossVectors(T, up); if (N.lengthSq() < 1e-4) N.set(1, 0, 0); N.normalize();
    const B = V().crossVectors(N, T).normalize();
    const r = lerp(r0, r1, Math.pow(u, 0.85)) * thin * (u > 0.97 ? Math.sqrt(Math.max(0, 1 - (u - 0.97) / 0.03)) * 0.9 + 0.1 : 1);
    const cups = Math.pow(Math.max(0, Math.sin(u * 72 * Math.PI)), 3) * (u > 0.06 && u < 0.95 ? 1 : 0);
    for (let j = 0; j <= radial; j++) {
      const v = (j / radial) * Math.PI * 2;
      const n = N.clone().multiplyScalar(Math.cos(v)).addScaledVector(B, Math.sin(v));
      const under = Math.max(0, -Math.sin(v) - 0.55) / 0.45;              // only the cups on the underside
      const side = Math.exp(-Math.pow((Math.abs(Math.cos(v)) - 0.62) / 0.18, 2));
      const rr2 = r * (1 + 0.16 * cups * (under * 0.6 + side * Math.max(0, -Math.sin(v) + 0.2)));
      pos.push(P.x + n.x * rr2, P.y + n.y * rr2, P.z + n.z * rr2); nor.push(n.x, n.y, n.z); uv.push(u * 4, 1.01 - j / radial);
    }
  }
  for (let i = 0; i < segs; i++) for (let j = 0; j < radial; j++) { const a = i * (radial + 1) + j, b = a + radial + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  return g;
}
const arms = ARM_ANG.map(() => { const m = new THREE.Mesh(new THREE.BufferGeometry(), M.arm); m.castShadow = m.receiveShadow = true; nori.add(m); return m; });

// ───────────────────────────────────────────── Sunny the hermit crab (teapot shell)
const sunny = new THREE.Group(); scene.add(sunny);
const sunnyBody = new THREE.Group(); sunny.add(sunnyBody);
const shellG = new THREE.Group(); sunnyBody.add(shellG);
mesh(new THREE.SphereGeometry(0.13, 40, 28), M.teal, [0, 0.15, -0.03], [0, 0, 0], shellG).scale.set(1, 0.85, 1);
mesh(new THREE.CylinderGeometry(0.014, 0.024, 0.13, 12), M.teal, [0.13, 0.17, -0.03], [0, 0, -0.95], shellG);
mesh(new THREE.TorusGeometry(0.055, 0.013, 10, 24, Math.PI * 1.2), M.teal, [-0.13, 0.16, -0.03], [0, 0, Math.PI * 0.4], shellG);
const shellLid = mesh(new THREE.SphereGeometry(0.07, 24, 12, 0, Math.PI * 2, 0, Math.PI * 0.5), M.teal, [0, 0.255, -0.03], [0, 0, 0], shellG);
mesh(new THREE.SphereGeometry(0.018, 12, 8), M.teal, [0, 0.07, 0], [0, 0, 0], shellLid);
mesh(new THREE.SphereGeometry(0.075, 24, 16), M.crab, [0, 0.085, 0.07], [0, 0, 0], sunnyBody).scale.set(1.2, 0.8, 0.9);
const crabEyes = [], crabStalks = [];
for (const s of [-1, 1]) {
  const st = new THREE.Group(); st.position.set(s * 0.035, 0.12, 0.1); sunnyBody.add(st);
  mesh(new THREE.CylinderGeometry(0.007, 0.009, 0.08, 8), M.crab, [0, 0.04, 0], [0, 0, 0], st);
  const e = mesh(new THREE.SphereGeometry(0.026, 24, 16), M.crabEye, [0, 0.09, 0.005], [0, 0, 0], st);
  crabStalks.push(st); crabEyes.push(e);
}
const crabMouth = mesh(new THREE.TorusGeometry(0.014, 0.004, 8, 16, Math.PI), M.mouth, [0, 0.07, 0.135], [0, 0, Math.PI], sunnyBody);
const claws = [];
for (const s of [-1, 1]) {
  const c = new THREE.Group(); c.position.set(s * 0.085, 0.08, 0.1); sunnyBody.add(c);
  mesh(new THREE.CapsuleGeometry(0.012, 0.06, 4, 8), M.crab, [s * 0.02, 0, 0.03], [Math.PI / 2, 0, s * 0.6], c);
  const pinch = mesh(new THREE.SphereGeometry(s > 0 ? 0.035 : 0.028, 16, 12), M.crab, [s * 0.03, 0.01, 0.08], [0, 0, 0], c); pinch.scale.set(1, 0.7, 1.3);
  claws.push(c);
}
const legs = [];
for (const s of [-1, 1]) for (let k = 0; k < 3; k++) {
  const l = new THREE.Group(); l.position.set(s * 0.07, 0.07, 0.04 - k * 0.04); sunnyBody.add(l);
  mesh(new THREE.CapsuleGeometry(0.008, 0.07, 4, 8), M.crab, [s * 0.04, -0.03, 0], [0, 0, s * 1.0], l);
  legs.push({ l, s, k });
}

// ───────────────────────────────────────────── lights (time of day)
const hemi = new THREE.HemisphereLight('#fff1dc', '#8a5a34', 0.6); scene.add(hemi);
const sun = new THREE.DirectionalLight('#ffe2b8', 2.6); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -3, right: 3, top: 3, bottom: -2 }); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02; sun.shadow.radius = 3;
scene.add(sun); scene.add(sun.target);
const fill = new THREE.PointLight('#ffd0a0', 1.1, 7, 2); fill.position.set(-1.6, 1.5, 2.0); scene.add(fill);
const rim = new THREE.PointLight('#fff2d8', 2.0, 5, 2); rim.position.set(1.2, 1.9, -0.9); scene.add(rim);
const fairy = new THREE.PointLight('#ffb35a', 0.6, 2.5, 2); fairy.position.set(1.5, 1.25, -0.8); scene.add(fairy);
// story time → light: [t, sun colour, sun intensity, hemi intensity, window colour, window emissive, sun direction (azimuth, elevation)]
const DAY = [
  [0, '#dfe8ff', 1.1, 0.45, '#e6f0ff', 0.27, 0.9, 0.35], [15, '#fff3e0', 1.8, 0.55, '#fff6e2', 0.33, 0.7, 0.55], [75, '#fffaf0', 2.0, 0.6, '#ffffff', 0.36, 0.4, 0.75],
  [125, '#fffaf0', 2.0, 0.6, '#ffffff', 0.36, 0.4, 0.75], [135, '#ffd29a', 2.1, 0.5, '#ffe2b0', 0.39, -0.2, 0.35], [160, '#ffb27a', 1.7, 0.45, '#ffc38a', 0.36, -0.4, 0.22],
  [195, '#ff8a5a', 1.1, 0.38, '#ff9a6a', 0.3, -0.55, 0.1], [215, '#7a8ab8', 0.3, 0.25, '#3a4a7a', 0.18, -0.6, 0.05], [232, '#6a7ab0', 0.25, 0.22, '#33406e', 0.15, -0.6, 0.05],
];
const cA = new THREE.Color(), cB = new THREE.Color();
function dayAt(t) {
  let i = 0; while (i < DAY.length - 2 && t > DAY[i + 1][0]) i++;
  const a = DAY[i], b = DAY[i + 1], u = smooth(a[0], b[0], t);
  return { sun: cA.set(a[1]).clone().lerp(cB.set(b[1]), u), sunI: lerp(a[2], b[2], u), hemi: lerp(a[3], b[3], u), win: new THREE.Color(a[4]).lerp(new THREE.Color(b[4]), u), winI: lerp(a[5], b[5], u), az: lerp(a[6], b[6], u), el: lerp(a[7], b[7], u) };
}

// ───────────────────────────────────────────── the story: Nori's actions
// arm actions: [arm, t0, t1, target(t) → Vector3, in, out]
const P = (name) => (t) => pp(name, t).add(V(0, 0.06, 0));
const at = (x, y, z) => () => V(x, y, z);
const wob = (base, f = 9, a = 0.06) => (t) => base(t).add(V(Math.sin(t * f) * a, Math.abs(Math.sin(t * f * 0.7)) * a * 0.6, Math.cos(t * f * 1.3) * a * 0.5));
const ACTIONS = [
  // cold open: slap the alarm off, then a big stretch
  [7, 1.6, 3.4, at(-0.95, 0.66, 0.05), 0.35, 0.5],
  [1, 5.0, 7.0, (t) => V(0.55, 1.75 + 0.05 * Math.sin(t * 6), -0.05), 0.5, 0.6], [6, 5.1, 7.0, (t) => V(-0.55, 1.75 + 0.05 * Math.sin(t * 6 + 1), -0.05), 0.5, 0.6],
  // the plan, then six jobs at once
  [4, 19.4, 49.8, P('plan'), 0.5, 0.6],
  [7, 21.0, 25.9, P('kettle'), 0.5, 0.4], [6, 21.6, 23.6, P('teacup'), 0.4, 0.4],
  [5, 25.6, 28.0, P('snacks'), 0.5, 0.4],
  [5, 29.6, 32.2, P('blanket'), 0.5, 0.4], [6, 30.0, 32.2, (t) => pp('blanket', t).add(V(-0.2, 0.06, 0)), 0.5, 0.4],
  [2, 33.6, 35.6, wob(at(0.25, 0.6, 1.0), 6, 0.02), 0.5, 0.5],
  [3, 37.0, 40.0, P('book'), 0.6, 0.4],
  [7, 41.6, 44.4, at(-1.5, 1.45, -0.45), 0.6, 0.5],
  // the long, long stretch for the remote
  [1, 55.2, 70.8, P('remote'), 2.4, 0.5],
  // incident two: frame, duster, books, plants
  [6, 80.6, 84.0, (t) => V(-1.05 + Math.sin(t * 3) * 0.02 * smooth(81.8, 82.6, t), 1.85, -1.18), 1.0, 0.6],
  [0, 84.2, 101.0, (t) => (t < 85 ? pp('duster', t) : pp('duster', t).add(V(Math.sin(t * 7) * 0.25, Math.sin(t * 5) * 0.12, 0.05))), 0.5, 0.5],
  [2, 86.8, 97.0, wob(at(1.35, 1.12, -0.9), 11, 0.16), 0.4, 0.4], [3, 87.2, 97.0, wob(at(1.75, 0.75, -0.9), 10, 0.16), 0.4, 0.4],
  [1, 101.5, 108.6, (t) => booksTarget(t, 0), 0.4, 0.4], [2, 101.7, 108.6, (t) => booksTarget(t, 1), 0.4, 0.4], [3, 101.9, 108.6, (t) => booksTarget(t, 2), 0.4, 0.4],
  [5, 113.0, 122.2, P('can'), 0.5, 0.4], [2, 113.6, 122.4, P('glass'), 0.5, 0.4], [3, 114.0, 122.6, P('mugB'), 0.5, 0.4],
  [3, 138.8, 149.0, P('phone'), 0.5, 0.4],
  // panic: everything back in place
  [7, 152.2, 153.4, P('cushKnit'), 0.25, 0.25], [6, 152.6, 153.8, P('cushPlaid'), 0.25, 0.25], [1, 152.8, 154.0, P('cushNori'), 0.25, 0.25],
  [4, 150.6, 152.8, P('kettle'), 0.3, 0.3], [5, 153.8, 155.2, P('blanket'), 0.25, 0.3], [2, 155.0, 156.4, wob(at(0.25, 0.6, 1.0), 9, 0.02), 0.3, 0.3],
  // the door
  [7, 163.0, 166.0, (t) => doorHandle(t), 0.7, 0.6],
  // taking the cocoa, holding it
  [3, 175.6, 224.0, P('cocoaN'), 0.6, 0.6],
  // asleep, one arm curls around Sunny
  [2, 220.5, 232.0, (t) => sunnyPos(t).add(V(0.02, 0.22, -0.05)), 1.6, 0.1],
];
function booksTarget(t, j) {
  // three arms leapfrog through the twelve books
  const per = 7.0 / 4, k = Math.floor((t - 101.6) / per) * 3 + j;
  const b = BOOKS[clamp(k, 0, BOOKS.length - 1)];
  return bookPos(b, t).add(V(0, b.h / 2 + 0.03, 0.05));
}
function bookPos(b, t) {
  const idx = BOOKS.indexOf(b), start = 101.8 + idx * 0.55, u = smooth(start, start + 0.6, t);
  return V(lerp(b.x0, b.x1, u), 0.97 + b.h / 2 + 0.02 + Math.sin(Math.PI * u) * 0.12, -1.02 + Math.sin(Math.PI * u) * 0.12);
}
const doorAngle = (t) => -1.35 * smooth(164.2, 165.4, t) * (1 - smooth(172.5, 173.6, t));
const doorHandle = (t) => V(-2.58 + Math.sin(-doorAngle(t)) * 0.82, 0.95, 0.15 + Math.cos(-doorAngle(t)) * 0.82);

// face & body: [t, {lid, brow, smile, open, look:[x,y,z]|null, blush, tilt, turn, lift, squash}]
const FACE = [
  [0, { lid: 0.0, brow: 0, smile: 0.2, look: null, tilt: 0.15, lift: -0.1, squash: 0.1 }],
  [4, { lid: 0.35, brow: -0.2, smile: 0.4, tilt: 0.1, lift: -0.06, squash: 0.06 }],
  [5.2, { lid: 0.05, brow: 0.6, smile: 0, open: 1.0, tilt: -0.15, lift: 0.04, squash: -0.08 }],
  [6.6, { lid: 0.1, brow: 0.5, smile: 0.1, open: 0.9, tilt: -0.15, lift: 0.04, squash: -0.08 }],
  [7.4, { lid: 0.4, brow: -0.1, smile: 0.5, open: 0, tilt: 0.05, lift: -0.02, squash: 0.03 }],
  [9, { lid: 0.55, brow: 0, smile: 0.6, tilt: 0.0, lift: 0, squash: 0 }],
  [15.5, { lid: 0.85, brow: 0.6, smile: 0.7, look: [0, 1.0, 2.5] }],
  [20, { lid: 0.9, brow: 0.5, smile: 0.8, look: [-0.36, 1.05, 0.38] }],
  [48, { lid: 0.9, brow: 0.5, smile: 0.8, look: [-0.36, 1.05, 0.38] }],
  [50, { lid: 0.5, brow: -0.1, smile: 0.9, look: [0, 1.0, 2.5], lift: -0.05, squash: 0.06 }],
  [54, { lid: 0.6, brow: 0, smile: 0.5, look: [1.85, 0.97, -0.9], turn: -0.5 }],
  [57, { lid: 0.6, brow: 0.2, smile: 0.4, look: [1.85, 0.97, -0.9], turn: -0.6 }],
  [61.5, { lid: 0.8, brow: 0.5, smile: 0.8, look: [0, 0.82, 3.1], turn: 0 }],
  [65.0, { lid: 0.95, brow: 0.9, smile: -0.2, look: [0, 0.82, 3.1], open: 0.3 }],
  [68.0, { lid: 0.45, brow: -0.7, smile: -0.3, look: [0, 0.82, 3.1], open: 0 }],
  [73, { lid: 0.5, brow: -0.5, smile: 0, look: [0, 1, 2.5] }],
  [76, { lid: 0.8, brow: 0.3, smile: 0.1, look: [-1.05, 1.95, -1.22], turn: 0.9, tilt: -0.2 }],
  [80.5, { lid: 0.85, brow: 0.6, smile: 0.5, look: [-1.05, 1.95, -1.22], turn: 0.9 }],
  [84.3, { lid: 1.0, brow: 0.9, smile: 0.9, look: [1.3, 0.8, -0.4], turn: -0.5, tilt: 0 }],
  [87, { lid: 0.9, brow: 0.6, smile: 0.8, look: [1.55, 1.2, -1.0], turn: -0.1, tilt: -0.15 }],
  [101, { lid: 0.9, brow: 0.7, smile: 0.9, look: [1.5, 1.1, -1.02], turn: -0.1, tilt: -0.1 }],
  [109, { lid: 1.0, brow: 1.0, smile: 1.0, open: 0.4, look: [1.5, 1.1, -1.02], turn: -0.1, tilt: -0.1 }],
  [111, { lid: 0.9, brow: 0.6, smile: 0.9, open: 0, look: [0, 1.2, 0.5], turn: 0 }],
  [114, { lid: 0.85, brow: 0.5, smile: 0.9, look: [0.2, 1.3, -0.9], turn: 0 }],
  [124, { lid: 0.8, brow: 0.4, smile: 0.8, look: [0, 1, 2.5], turn: 0 }],
  [135.5, { lid: 0.9, brow: 0.8, smile: 1.0, look: [0, 1, 2.5], lift: 0.03 }],
  [138.5, { lid: 0.9, brow: 0.3, smile: 0.5, look: [0.38, 0.46, 0.72], lift: 0 }],
  [141, { lid: 0.9, brow: 0.3, smile: 0.5, look: [0.3, 1.0, 0.32] }],
  [144.5, { lid: 1.0, brow: 0.8, smile: -0.1, open: 0.2, look: [0.3, 1.0, 0.32] }],
  [146, { lid: 1.0, brow: 1.0, smile: -0.4, open: 0.6, look: [0.05, 2.12, -1.22], turn: 3.14, tilt: -0.35, lift: 0.05 }],
  [149.8, { lid: 1.0, brow: 1.0, smile: -0.4, open: 0.6, look: [0.05, 2.12, -1.22], turn: 3.14, tilt: -0.35 }],
  [150.6, { lid: 1.0, brow: 0.9, smile: -0.2, open: 0.2, look: [0, 1, 2.5], turn: 0, tilt: 0, lift: 0 }],
  [157, { lid: 0.9, brow: 0.5, smile: 0.3, open: 0, look: [0, 1, 2.5] }],
  [161, { lid: 1.0, brow: 0.8, smile: 0.6, look: [-2.5, 1.0, 0.6], turn: 0.9 }],
  [170, { lid: 0.95, brow: 0.6, smile: 0.9, look: [0.7, 0.75, -0.1], turn: -0.25 }],
  [176, { lid: 0.9, brow: 0.4, smile: 0.9, look: [0.7, 0.75, -0.1], turn: -0.25, blush: 0.2 }],
  [183, { lid: 0.95, brow: 0.2, smile: 0.4, look: [0.7, 0.75, -0.1], turn: -0.25, blush: 0.6 }],
  [186, { lid: 1.0, brow: 0.9, smile: 0.6, look: [0.7, 0.75, -0.1], turn: -0.2, blush: 0.9 }],
  [190.5, { lid: 0.6, brow: -0.6, smile: 0.2, look: [0, 1, 2.5], turn: 0, blush: 0.8 }],
  [192.6, { lid: 0.3, brow: 0.8, smile: 1.0, open: 0.5, look: [0.7, 0.75, -0.1], turn: -0.2, blush: 0.7, lift: 0.04 }],
  [195, { lid: 0.7, brow: 0.4, smile: 0.9, open: 0, look: [0, 0.82, 3.1], turn: 0, blush: 0.4, lift: 0 }],
  [199, { lid: 0.6, brow: 0.1, smile: 0.6, look: [0, 0.82, 3.1], blush: 0.3 }],
  [203, { lid: 0.25, brow: -0.2, smile: 0.5, look: [0, 0.82, 3.1], lift: -0.06, squash: 0.08, tilt: 0.12 }],
  [206, { lid: 0.0, brow: -0.1, smile: 0.6, lift: -0.12, squash: 0.12, tilt: 0.22 }],
  [232, { lid: 0.0, brow: 0.1, smile: 0.9, lift: -0.13, squash: 0.12, tilt: 0.25 }],
];
const FACE_DEF = { lid: 0.8, brow: 0, smile: 0.5, open: 0, look: null, blush: 0, tilt: 0, turn: 0, lift: 0, squash: 0 };
const faceKeys = [];
{ let cur = { ...FACE_DEF }; for (const [t, k] of FACE) { cur = { ...cur, ...k }; faceKeys.push([t, { ...cur }]); } }
function faceAt(t) {
  let i = 0; while (i < faceKeys.length - 2 && t > faceKeys[i + 1][0]) i++;
  const [ta, a] = faceKeys[i], [tb, b] = faceKeys[i + 1], u = ease(clamp((t - ta) / Math.max(tb - ta, 1e-3), 0, 1));
  const out = {};
  for (const key of Object.keys(FACE_DEF)) {
    if (key === 'look') {
      const la = a.look ? V(...a.look) : null, lb = b.look ? V(...b.look) : null;
      out.look = la && lb ? la.lerp(lb, u) : (u < 0.5 ? la : lb);
    } else out[key] = lerp(a[key], b[key], u);
  }
  return out;
}
const BLINKS = [12.2, 17.8, 33.0, 46.0, 59.0, 63.6, 79.0, 95.0, 117.0, 131.0, 143.0, 158.0, 168.0, 179.0, 188.0, 197.0];
const blinkAt = (t) => BLINKS.reduce((o, b) => Math.min(o, 1 - smooth(b - 0.07, b, t) * (1 - smooth(b + 0.02, b + 0.11, t))), 1);
// speech → mouth
const SPEECH = LINES.lines.map((l) => ({ ...l, ...VOICES[l.id] }));
function mouthAt(who, t) {
  for (const l of SPEECH) {
    if (l.who !== who || t < l.at || t > l.at + l.dur) continue;
    const f = (t - l.at) * 24, i = Math.floor(f), m = l.mouth;
    return lerp(m[i] || 0, m[i + 1] || 0, f - i);
  }
  return 0;
}
// Sunny's path: [t, pos, yaw]
const SUNNY = [
  [0, [-3.4, 0, 0.6], 1.57], [164.6, [-3.4, 0, 0.6], 1.57], [166.0, [-2.2, 0, 0.6], 1.57], [167.6, [-1.2, 0, 1.55], 0.6], [169.4, [0.9, 0, 1.45], 1.2],
  [170.2, [1.0, 0, 0.45], 3.4], [171.2, [0.62, 0.585, -0.08], 3.3], [232, [0.62, 0.585, -0.08], 3.3],
];
function sunnyPos(t) {
  let i = 0; while (i < SUNNY.length - 2 && t > SUNNY[i + 1][0]) i++;
  const [ta, a, ya] = SUNNY[i], [tb, b, yb] = SUNNY[i + 1], u = ease(clamp((t - ta) / (tb - ta), 0, 1));
  const p = V(...a).lerp(V(...b), u);
  if (i === 5) p.y += Math.sin(Math.PI * u) * 0.35;                    // the hop up onto the sofa
  p.yaw = lerp(ya, yb, u);
  p.moving = t > ta && t < tb && i > 0 ? 1 : 0;
  return p;
}
function sunnyAnim(t) {
  const p = sunnyPos(t);
  sunny.visible = t > 164;
  sunny.position.copy(p); sunny.rotation.y = Math.PI / 2 - p.yaw + Math.PI / 2;
  // turn toward Nori once seated
  if (t > 171.2) sunny.rotation.y = lerp(sunny.rotation.y, -0.9, smooth(171.2, 172.0, t)) + 0.2 * bump(t, 182.0, 185.5, 0.4);
  const walk = p.moving ? 1 : 0;
  for (const { l, s, k } of legs) l.rotation.set(Math.sin(t * 22 + k * 2 + (s > 0 ? Math.PI : 0)) * 0.5 * walk, 0, 0);
  sunnyBody.position.y = Math.abs(Math.sin(t * 22)) * 0.012 * walk;
  const talk = mouthAt('sunny', t);
  shellLid.position.y = 0.255 + talk * 0.03 + 0.04 * bump(t, 192.6, 193.6, 0.1) * Math.abs(Math.sin(t * 30));
  crabMouth.scale.set(1, 1 + talk * 1.5, 1);
  const blink = 1 - smooth(186.9, 187.0, t) * (1 - smooth(187.05, 187.15, t)) - smooth(209.9, 210, t) * (1 - smooth(210.05, 210.15, t));
  crabEyes.forEach((e) => e.scale.set(1, Math.max(blink, 0.1), 1));
  // eye stalks look around the tidy room
  const look = bump(t, 181.5, 186.0, 0.5);
  crabStalks.forEach((st, k) => { st.rotation.set(-0.2 * look, (k ? -1 : 1) * 0.1 + Math.sin(t * 1.5) * 0.6 * look, (k ? -1 : 1) * 0.15); });
  // claws: carry mugs in, hand one over, pull the blanket, press the remote
  const carry = t < 176.0;
  claws.forEach((c, k) => c.rotation.set(carry ? -0.5 : -0.2 - 0.6 * bump(t, 209.0, 213.0, 0.4) - 0.5 * bump(t, 214.8, 218.0, 0.3), 0, 0));
  return p;
}
// cocoa mugs follow Sunny's claws until handed over
function updateCocoa(t) {
  const claw = (k) => { claws[k].updateWorldMatrix(true, false); return V(k ? 0.03 : -0.03, 0.02, 0.1).applyMatrix4(claws[k].matrixWorld); };
  const S = PROPS.cocoaS.obj, N = PROPS.cocoaN.obj;
  S.position.copy(claw(0)).add(V(0, -0.02, 0)); S.visible = t > 164;
  if (t < 176.0) N.position.copy(claw(1)).add(V(0, -0.02, 0));
  else if (t < 176.6) N.position.copy(claw(1)).lerp(V(-0.42, 0.92, 0.25), smooth(176.0, 176.6, t));
  else N.position.copy(tipOf(3)).add(V(0, -0.05, 0));
  N.visible = t > 164;
  // Sunny sips at the end
  if (t > 221.5) S.position.add(V(0, 0.04 * bump(t, 221.5, 223.5, 0.4), 0));
}
const tips = [];
const tipOf = (i) => tips[i] ? tips[i].clone() : V();

// ───────────────────────────────────────────── post
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bokeh = new BokehPass(scene, camera, { focus: 2.5, aperture: 0.002, maxblur: 0.008 });
composer.addPass(bokeh);
const bloom = new UnrealBloomPass(new THREE.Vector2(512, 512), 0.3, 0.45, 1.15);
composer.addPass(bloom);
composer.addPass(new OutputPass());
// a warm, soft grade: lifted shadows, gentle vignette, a little film grain
const grade = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uAspect: { value: 16 / 9 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime; uniform float uAspect; varying vec2 vUv;
    float h(vec2 p){ vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float l = dot(c, vec3(0.299, 0.587, 0.114));
      c = mix(c, c * vec3(1.04, 1.0, 0.93) + vec3(0.025, 0.012, 0.0), 0.8);
      c = mix(vec3(l), c, 1.06);
      vec2 d = (vUv - 0.5) * vec2(uAspect, 1.0);
      c *= mix(0.78, 1.0, smoothstep(1.05, 0.35, length(d)));
      c += (h(vUv * 1000.0 + uTime) - 0.5) * 0.018;
      gl_FragColor = vec4(c, 1.0);
    }`,
});
composer.addPass(grade);

// ───────────────────────────────────────────── world at story time t
let lastTV = '', lastPhone = -1, lastPlan = -1;
function world(t) {
  // light
  const d = dayAt(t);
  sun.color.copy(d.sun); sun.intensity = d.sunI; hemi.intensity = d.hemi;
  sun.position.set(1.45 + Math.sin(d.az) * 3, 1.0 + d.el * 4.5, -1.2 - 3.0); sun.target.position.set(0, 0.6, 0.6);
  M.window.emissive.copy(d.win); M.window.emissiveIntensity = d.winI;
  const evening = smooth(185, 215, t);
  const lampOn = smooth(43.6, 44.2, t);
  lampLight.intensity = lampOn * (0.9 + 2.2 * evening); M.shade.emissiveIntensity = lampOn * (0.5 + 1.2 * evening);
  const candleOn = smooth(35.0, 35.4, t) * (1 - smooth(88.0, 88.3, t)) + smooth(155.8, 156.2, t);
  flame.visible = candleOn > 0.01; flame.scale.set(1, 1.6 + 0.3 * Math.sin(t * 13), 1); candleLight.intensity = candleOn * (0.35 + 0.6 * evening) * (0.9 + 0.1 * Math.sin(t * 17));
  fairy.intensity = 0.4 + 1.0 * evening; M.bulb.emissiveIntensity = 3 + 2 * evening;
  fill.intensity = lerp(0.8, 0.4, evening); rim.intensity = lerp(1.4, 0.5, evening);
  renderer.toneMappingExposure = lerp(0.95, 1.2, evening);
  scene.background = null;
  // clock: 7:00 at t=0 … 9:05 at 15, 11:40 at 125, spins to 4:58 at 135, 5:00 at 160, 7:10 at 232
  const CLOCK = [[0, 7.0], [3, 7.02], [15, 9.08], [75, 10.3], [125, 11.65], [135, 16.97], [146, 16.99], [160, 17.0], [232, 19.17]];
  let i = 0; while (i < CLOCK.length - 2 && t > CLOCK[i + 1][0]) i++;
  const hrs = lerp(CLOCK[i][1], CLOCK[i + 1][1], clamp((t - CLOCK[i][0]) / (CLOCK[i + 1][0] - CLOCK[i][0]), 0, 1));
  hourHand.rotation.z = -((hrs % 12) / 12) * Math.PI * 2; minHand.rotation.z = -(hrs % 1) * Math.PI * 2;
  // TV and phone and plan
  const tvState = t < 62.6 ? 'off' : t < 196.5 ? 'update' : t < 217.6 ? 'done' : 'off';
  const prog = tvState === 'update' ? clamp((t - 62.6) / 160, 0.02, 0.86) : 1;
  const key = tvState + Math.round(prog * 50);
  if (key !== lastTV) { drawTV(tvState, prog); lastTV = key; }
  M.tv.emissiveIntensity = tvState === 'off' ? 0 : 0.95; tvLight.intensity = tvState === 'off' ? 0 : 0.9;
  const ph = t > 138.0 && t < 149.5 ? 1 : 0;
  if (ph !== lastPhone) { drawPhone(ph); lastPhone = ph; }
  M.phone.emissiveIntensity = ph ? 1.0 : 0;
  const done = [24.3, 28.3, 32.3, 36.3, 40.3, 44.3].filter((x) => t > x).length;
  if (done !== lastPlan) { drawPlan(done); lastPlan = done; }
  // the phone buzzes on the table
  if (t > 138 && t < 139.2) PROPS.phone.obj.position.x += Math.sin(t * 90) * 0.004;
  frames[1].rotation.z = 0.2 * (1 - smooth(81.8, 82.8, t));
  doorPivot.rotation.y = doorAngle(t); doorway.visible = doorAngle(t) < -0.05;
  // props
  for (const [name, { obj }] of Object.entries(PROPS)) { const { p, r } = propAt(name, t); obj.position.copy(p); obj.rotation.copy(r); }
  BOOKS.forEach((b) => b.m.position.copy(bookPos(b, t)));
  // steam over the tea, water pouring, dust
  steam.forEach((s, k) => {
    const life = ((t * 0.6 + k / steam.length) % 1), on = smooth(24.4, 25.4, t) * (1 - smooth(80, 84, t)) + smooth(152.6, 153.6, t) * (1 - smooth(166, 170, t));
    const cup = pp('teacup', t); s.position.set(cup.x + Math.sin(k * 3 + t) * 0.02, cup.y + 0.12 + life * 0.25, cup.z); s.scale.setScalar((0.4 + life * 1.1) * on * (1 - life)); s.material.opacity = 0.08;
  });
  [['can', 0, PLANT_TOP[0]], ['glass', 1, PLANT_TOP[1]], ['mugB', 2, PLANT_TOP[2]]].forEach(([n, k, top]) => {
    const on = bump(t, 116.0 + k * 0.4, 120.6, 0.3), from = pp(n, t).add(V(0.06, 0.06, 0));
    streams[k].visible = on > 0.02;
    const len = Math.max(from.y - top.y, 0.05);
    streams[k].position.set(lerp(from.x, top.x, 0.5), from.y - len / 2, lerp(from.z, top.z, 0.5)); streams[k].scale.set(on, len, on);
  });
  dust.forEach((p, k) => {
    const on = bump(t, 85.5, 100, 0.5), life = (t * 0.7 + k * 0.137) % 1;
    p.visible = on > 0.02;
    p.position.set(1.55 + Math.sin(k * 7.1) * 0.45 + Math.sin(t + k) * 0.05, 1.0 + life * 0.6, -0.95 + Math.cos(k * 3.3) * 0.12 + life * 0.25); p.scale.setScalar((1 - life) * on);
  });
  PLANTS.forEach((pl, k) => pl.scale.setScalar(1 + 0.03 * bump(t, 120.6 + k * 0.2, 123.0, 0.4)));
  // Nori
  const f = faceAt(t);
  const breathe = 1 + 0.015 * Math.sin(t * 2.0) * (t > 205 ? 1.6 : 1);
  const laugh = bump(t, 192.6, 195.0, 0.2) * Math.abs(Math.sin(t * 16)) * 0.03;
  const panic = bump(t, 150.4, 157.2, 0.3);
  const hpath = headPath(t);
  headPivot.position.copy(hpath).add(V(Math.sin(t * 31) * 0.01 * panic, f.lift + laugh + (hpath.moving ? Math.abs(Math.sin(t * 9)) * 0.03 : 0), 0));
  headPivot.rotation.set(f.tilt * 0.5, f.turn * 0.35, f.tilt * 0.3 + Math.sin(t * 25) * 0.04 * panic);
  head.scale.set(breathe * (1 + f.squash * 0.5), (0.98 / breathe) * (1 - f.squash), 0.92 * breathe);
  const blink = blinkAt(t), open = clamp(f.lid * blink, 0, 1);
  lids.forEach((l) => l.rotation.set(lerp(1.05, -0.62, open), 0, 0));
  lowLids.forEach((l) => l.rotation.set(lerp(0.05, 0.78, Math.max(open, 0.35)), 0, 0));
  headPivot.updateMatrixWorld(true);
  eyes.forEach((e) => {
    if (f.look) { const lp = f.look.clone(); e.parent.worldToLocal(lp); const dir = lp.sub(e.position).normalize(); e.rotation.set(-clamp(Math.asin(dir.y), -0.5, 0.5), clamp(Math.atan2(dir.x, dir.z), -0.6, 0.6), 0); }
    else e.rotation.set(0.1, 0, 0);
  });
  brows.forEach(({ m, s, base }) => { m.position.copy(base).add(V(0, 0.02 * f.brow, 0)); m.rotation.set(0, 0, Math.PI / 2 - s * 0.32 * (0.4 - f.brow)); });
  M.blush.opacity = 0.45 * f.blush + 0.12;
  const talk = mouthAt('nori', t);
  const mo = clamp(f.open + talk * 0.9, 0, 1.2);
  mouthOpen.scale.set(1 + 0.2 * mo, 0.1 + 0.9 * mo, 0.35); tongue.visible = mo > 0.15;
  smileLine.scale.set(1, f.smile >= 0 ? 0.4 + 0.6 * f.smile : 0.4 + 0.6 * -f.smile, 1);
  smileLine.rotation.z = f.smile >= 0 ? Math.PI + Math.PI * 0.075 : Math.PI * 0.075;
  smileLine.visible = mo < 0.6;
  // arms
  const hp = headPivot.position.clone(); hp.moving = hpath.moving;
  for (let i = 0; i < 8; i++) {
    let pts = restPoints(i, t, hp), w = 0, tgt = null;
    for (const [arm, t0, t1, fn, inD, outD] of ACTIONS) {
      if (arm !== i || t < t0 || t > t1) continue;
      w = smooth(t0, t0 + inD, t) * (1 - smooth(t1 - outD, t1, t)); tgt = fn(t);
    }
    if (tgt && w > 0) {
      const rp = reachPoints(i, tgt, hp, t);
      pts = pts.map((p, k) => p.lerp(rp[k], ease(w)));
    }
    if (t > 150.4 && t < 157.2) pts = pts.map((p, k) => p.add(V(Math.sin(t * 20 + i + k) * 0.015 * panic, 0, 0)));
    let len = 0; for (let k = 1; k < pts.length; k++) len += pts[k].distanceTo(pts[k - 1]);
    const thin = clamp(Math.sqrt(0.75 / len), 0.42, 1);
    arms[i].geometry.dispose(); arms[i].geometry = taperTube(pts, 110, 22, 0.1, 0.016, thin);
    tips[i] = pts[pts.length - 1];
  }
  sunnyAnim(t);
  updateCocoa(t);
}

// ───────────────────────────────────────────── cameras
const HEADP = () => headPivot.position.clone();
const STAND = () => smooth(0.8, 0.68, headPivot.position.y);
const C = (pos, tgt, fov, o = {}) => ({ pos, tgt, fov, focus: o.focus ?? pos.distanceTo(tgt), aperture: o.aperture ?? 0.0018, shake: o.shake ?? 0.004 });
const drift = (t, a = 0.03) => V(Math.sin(t * 0.21) * a, Math.sin(t * 0.17 + 1) * a * 0.5, Math.cos(t * 0.13) * a);
const CAMS = {
  // ── 16:9
  WIDE: (t) => C(V(0.1, 1.35, 3.35).add(drift(t, 0.05)), V(0.05, 0.95, -0.4), 46, { aperture: 0.001 }),
  MED: (t) => C(V(0.05, 1.15, 2.45).add(drift(t)), V(0, 0.86, -0.2), 34),
  MEDL: (t) => C(V(-0.55, 1.1, 2.3).add(drift(t)), V(0.15, 0.85, -0.2), 34),
  CU: (t) => C(HEADP().add(V(0.05, 0.08, 1.8).lerp(V(0.3, 0.12, 1.25), STAND())).add(drift(t, 0.015)), HEADP().add(V(0, -0.06, 0)), 30 + 6 * STAND(), { aperture: 0.0025 }),
  CUSLOW: (t, u) => C(V(0.05, 1.1, 1.8 - 0.3 * u), HEADP().add(V(0, -0.06, 0)), 30, { aperture: 0.0025 }),
  PLAN: (t) => C(V(-0.15, 1.15, 1.05), V(-0.36, 1.03, 0.38), 32, { aperture: 0.003 }),
  RIGHT: (t) => C(V(2.25, 1.25, 1.35).add(drift(t)), V(0.2, 0.85, -0.45), 42),
  LEFT: (t) => C(V(-2.15, 1.2, 1.45).add(drift(t)), V(0.2, 0.85, -0.4), 42),
  STRETCH: (t, u) => C(V(0.9 + 0.4 * u, 1.3, 2.4), V(0.9 - 0.2 * u, 0.95, -0.5), 48, { aperture: 0.001 }),
  TV: (t) => C(V(0.55, 1.4, -0.95), V(0, 0.82, 3.1), 40, { focus: 3.0 }),
  TVCU: (t) => C(V(0.1, 0.9, 2.2), V(0, 0.82, 3.1), 44, { focus: 0.9 }),
  FRAME: (t) => C(V(-0.75, 1.75, 0.35), V(-1.05, 1.9, -1.22), 38, { focus: 1.6 }),
  SHELF: (t) => C(V(0.85, 1.2, 1.2).add(drift(t, 0.02)), V(1.85, 0.82, -0.7), 40, { focus: 2.0 }),
  SHELFW: (t) => C(V(0.35, 1.45, 1.75).add(drift(t, 0.02)), V(1.7, 0.9, -0.65), 44, { focus: 2.4, aperture: 0.0012 }),
  PLANTS: (t) => C(V(0.1, 1.35, 2.2).add(drift(t)), V(0.05, 1.05, -0.6), 50, { aperture: 0.001 }),
  CLOCK: (t) => C(V(0.05, 1.75, 0.6), V(0.05, 2.08, -1.22), 34, { focus: 1.9 }),
  PHONE: (t) => C(V(0.35, 1.1, 0.75), pp('phone', t), 34, { focus: 0.45, aperture: 0.004 }),
  DOOR: (t) => C(V(-0.6, 1.0, 2.2), V(-2.1, 0.5, 0.7), 44),
  SUNNYWALK: (t) => C(V(-0.2, 0.55, 2.6).add(drift(t, 0.02)), sunnyPos(t).add(V(0, 0.15, 0)), 40),
  TWO: (t) => C(V(0.3, 1.1, 2.15).add(drift(t)), V(0.3, 0.86, -0.15), 34),
  TWOCU: (t) => C(V(0.35, 1.02, 1.45).add(drift(t, 0.015)), V(0.32, 0.86, -0.15), 32, { aperture: 0.0025 }),
  SUNNYCU: (t) => C(V(0.25, 0.85, 0.85), sunnyPos(t).add(V(0, 0.18, 0)), 30, { aperture: 0.003 }),
  END: (t, u) => C(V(0.25, 1.15 + 0.15 * u, 2.1 + 0.6 * u), V(0.25, 0.85, -0.2), 34),
  // ── 9:16
  V_MED: (t) => C(V(0.05, 1.25, 2.6).add(drift(t)), V(0, 0.95, -0.2), 52),
  V_CU: (t) => C(HEADP().add(V(0.05, 0.08, 1.93).lerp(V(0.3, 0.12, 1.3), STAND())).add(drift(t, 0.015)), HEADP().add(V(0, -0.12, 0)), 44 + 6 * STAND(), { aperture: 0.0025 }),
  V_PLAN: (t) => C(V(-0.1, 1.15, 1.25), V(-0.25, 0.98, 0.2), 50),
  V_STRETCH: (t, u) => C(V(2.2, 1.45, 1.6), V(0.9 + 0.3 * u, 0.95, -0.45), 66, { aperture: 0.001 }),
  V_TV: (t) => C(V(0.55, 1.35, -0.85), V(0, 0.82, 3.1), 58, { focus: 3.0 }),
  V_FRAME: (t) => C(V(-0.6, 1.5, 0.6), V(-0.8, 1.55, -1.0), 56, { focus: 1.6 }),
  V_SHELF: (t) => C(V(1.25, 1.15, 1.3), V(1.85, 0.85, -0.7), 58, { focus: 2.0 }),
  V_PLANTS: (t) => C(V(0.7, 1.45, 2.75), V(0.55, 1.0, -0.6), 70, { aperture: 0.001 }),
  V_CLOCK: (t) => C(V(0.25, 1.95, 0.35), V(0.05, 2.0, -1.22), 52, { focus: 1.6 }),
  V_PHONE: (t) => C(V(0.32, 1.12, 0.85), pp('phone', t).add(V(0, -0.02, 0)), 44, { focus: 0.55, aperture: 0.004 }),
  V_DOOR: (t) => C(V(-0.75, 1.1, 2.1), V(-2.5, 0.8, 0.55), 60),
  V_TWO: (t) => C(V(0.3, 1.2, 2.3).add(drift(t)), V(0.3, 0.9, -0.15), 52),
  V_TWOCU: (t) => C(V(0.32, 1.05, 1.6).add(drift(t, 0.015)), V(0.32, 0.88, -0.15), 46, { aperture: 0.0025 }),
  V_END: (t, u) => C(V(0.25, 1.2 + 0.1 * u, 2.2 + 0.4 * u), V(0.25, 0.88, -0.2), 52),
};

// ───────────────────────────────────────────── edits & captions
for (const E of Object.values(EDITS)) E.duration = E.clips.reduce((s, c) => s + (c.to - c.from) / (c.speed || 1), 0);
let edit = EDITS[qs.get('edit')] || EDITS.main;
export const currentEdit = () => edit;
export function locate(outT) {
  outT = clamp(outT, 0, edit.duration - 1e-4);
  let acc = 0;
  for (let i = 0; i < edit.clips.length; i++) {
    const c = edit.clips[i], sp = c.speed || 1, d = (c.to - c.from) / sp;
    if (outT < acc + d || i === edit.clips.length - 1) return { clip: c, index: i, story: c.from + (outT - acc) * sp, u: clamp((outT - acc) / d, 0, 1), start: acc };
    acc += d;
  }
}
const subEl = document.getElementById('sub'), titleEl = document.getElementById('titlecard'), cardEl = document.getElementById('endcard');
function captions(outT, loc) {
  // subtitles follow the voice: a line shows while it is heard in this edit
  let text = '';
  for (const l of SPEECH) {
    const s = loc.story;
    if (s >= l.at - 0.05 && s <= l.at + l.dur + 0.5) text = l.text;
  }
  if (subEl) { subEl.textContent = text; subEl.style.opacity = text ? '1' : '0'; }
  const tc = edit.title ? bump(outT, edit.title[0], edit.title[1], 0.5) : 0;
  if (titleEl) titleEl.style.opacity = tc.toFixed(3);
  const ec = bump(outT, edit.duration - (edit.endCard || 0), edit.duration + 1, 0.5);
  if (cardEl) cardEl.style.opacity = (edit.endCard ? ec : 0).toFixed(3);
}
export function setEdit(name) {
  edit = EDITS[name] || EDITS.main;
  document.documentElement.dataset.kind = edit.kind;
  return edit;
}
let lastClip = -1;
export function frame(outT) {
  const loc = locate(outT);
  const t = loc.story;
  world(t);
  const c = CAMS[loc.clip.cam](t, loc.u);
  camera.fov = c.fov; camera.updateProjectionMatrix();
  camera.position.copy(c.pos);
  camera.lookAt(c.tgt.clone().add(V(Math.sin(t * 0.9) * c.shake, Math.sin(t * 1.3) * c.shake, 0)));
  bokeh.uniforms.focus.value = c.focus; bokeh.uniforms.aperture.value = c.aperture;
  grade.uniforms.uTime.value = outT % 10; grade.uniforms.uAspect.value = camera.aspect;
  const fi = edit.fadeIn > 0 ? 1 - smooth(0, edit.fadeIn, outT) : 0, fo = smooth(edit.duration - edit.fadeOut, edit.duration, outT);
  renderer.toneMappingExposure *= 1 - Math.max(fi, fo) * 0.98;
  captions(outT, loc);
  if (loc.index !== lastClip) { lastClip = loc.index; document.dispatchEvent(new CustomEvent('nori:clip', { detail: loc })); }
  composer.render();
  return loc;
}
export function resize(w, h, pr = 1) {
  renderer.setPixelRatio(pr); renderer.setSize(w, h, false); composer.setPixelRatio(pr); composer.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
export const ready = (async () => {
  try { await document.fonts.ready; } catch { /* optional */ }
  setEdit(qs.get('edit') || 'main');
  if (RENDER) resize(innerWidth, innerHeight, 1);
  frame(0);
  return true;
})();
if (RENDER) window.__nori = { ready, frame, currentEdit, setEdit, EDITS, debug: { scene, camera, THREE } };
