// PIP, BELOW — Ep.1 "The Bubble".
// A reef fish called Pip meets a bubble, loses it, finds it, and lets it go.
// The world is a pure function of story time (0–60 s). Edits in edits.json cut that
// story into a 16:9 film and three 9:16 shorts, each filmed with its own cameras.

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const SURFACE = 40;              // water surface height (1 unit ≈ 10 cm)
const qs = new URLSearchParams(location.search);
const RENDER_MODE = qs.has('render');

// ───────────────────────────────────────────────────────── helpers
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(0xA5CE17);
const rr = (a, b) => a + (b - a) * rnd();
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeSine = (t) => -(Math.cos(Math.PI * clamp(t, 0, 1)) - 1) / 2;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

function hash3i(x, y, z) {
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263) ^ Math.imul(z | 0, 1274126177);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
function noise3(x, y, z) {
  const X = Math.floor(x), Y = Math.floor(y), Z = Math.floor(z);
  const fx = x - X, fy = y - Y, fz = z - Z;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = fz * fz * (3 - 2 * fz);
  const c = (i, j, k) => hash3i(X + i, Y + j, Z + k);
  return lerp(
    lerp(lerp(c(0, 0, 0), c(1, 0, 0), u), lerp(c(0, 1, 0), c(1, 1, 0), u), v),
    lerp(lerp(c(0, 0, 1), c(1, 0, 1), u), lerp(c(0, 1, 1), c(1, 1, 1), u), v), w);
}
function fbm3(x, y, z, oct = 4) {
  let s = 0, a = 0.5, f = 1;
  for (let i = 0; i < oct; i++) { s += a * noise3(x * f, y * f, z * f); f *= 2.03; a *= 0.5; }
  return s;
}

// ───────────────────────────────────────────────────────── light
// A low golden sun (10° above the horizon). Under water it is refracted by Snell's law
// and sits just inside the edge of Snell's window, so the light shafts lean at ~48°.
const SUN_ELEV = THREE.MathUtils.degToRad(10);
const SUN_AZ = new THREE.Vector2(-0.36, -0.93).normalize();
const SUN_ABOVE = V(SUN_AZ.x * Math.cos(SUN_ELEV), Math.sin(SUN_ELEV), SUN_AZ.y * Math.cos(SUN_ELEV)).normalize();
const SIN_R = Math.cos(SUN_ELEV) / 1.333;
const SUN_UNDER = V(SUN_AZ.x * SIN_R, Math.sqrt(1 - SIN_R * SIN_R), SUN_AZ.y * SIN_R).normalize();

const U = {
  uTime: { value: 0 },
  uSurfaceY: { value: SURFACE },
  uSunDir: { value: SUN_UNDER },
  uSunAbove: { value: SUN_ABOVE },
  uFogDensity: { value: 0.024 },
  uCamAbove: { value: 0 },
};

// ───────────────────────────────────────────────────────── shared GLSL
const COMMON = /* glsl */ `
uniform float uTime;
uniform float uSurfaceY;
uniform vec3 uSunDir;
uniform vec3 uSunAbove;
uniform float uFogDensity;
uniform float uCamAbove;

float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float vnoise(vec2 p){
  vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p){
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++){ s += a * vnoise(p); p = mat2(1.6, 1.2, -1.2, 1.6) * p; a *= 0.5; }
  return s;
}

// Tileable water caustics (after Dave Hoskins' classic iteration).
float caustics(vec2 uv, float t){
  vec2 p = mod(uv * 6.28318, 6.28318) - 250.0;
  vec2 i = p; float c = 1.0; float inten = 0.005;
  for (int n = 0; n < 5; n++){
    float tt = t * (1.0 - (3.5 / float(n + 1)));
    i = p + vec2(cos(tt - i.x) + sin(tt + i.y), sin(tt - i.y) + cos(tt + i.x));
    c += 1.0 / length(vec2(p.x / (sin(i.x + tt) / inten), p.y / (cos(i.y + tt) / inten)));
  }
  c /= 5.0;
  c = 1.17 - pow(c, 1.4);
  return clamp(pow(abs(c), 8.0), 0.0, 4.0);
}

// Golden-hour sky above the water.
vec3 skyColor(vec3 d){
  float y = max(d.y, 0.0);
  vec3 zen = vec3(0.018, 0.040, 0.120);
  vec3 mid = vec3(0.150, 0.110, 0.190);
  vec3 hor = vec3(0.620, 0.250, 0.100);
  vec3 c = mix(hor, mid, smoothstep(0.0, 0.22, y));
  c = mix(c, zen, smoothstep(0.15, 0.85, y));
  float s = max(dot(d, uSunAbove), 0.0);
  c += vec3(1.0, 0.45, 0.14) * pow(s, 6.0) * 0.38;
  c += vec3(1.0, 0.70, 0.40) * pow(s, 48.0) * 0.9;
  c += vec3(1.0, 0.90, 0.72) * smoothstep(0.99925, 0.99962, s) * 9.0;
  // thin evening cloud bands near the horizon
  vec2 cp = d.xz / (d.y + 0.06);
  float band = smoothstep(0.0, 0.05, y) * (1.0 - smoothstep(0.25, 0.6, y));
  if (band > 0.001) {
    float cl = smoothstep(0.52, 0.86, fbm(cp * vec2(0.35, 1.4) + vec2(uTime * 0.012, 3.0)));
    vec3 cloud = mix(vec3(0.20, 0.09, 0.12), vec3(0.95, 0.46, 0.22), pow(s, 3.0));
    c = mix(c, cloud, cl * band * 0.85);
  }
  return c;
}

// Colour of the water volume itself (in-scattering), seen from height y.
vec3 waterFog(vec3 dir, float y){
  float d01 = clamp((uSurfaceY - y) / uSurfaceY, 0.0, 1.0);
  vec3 deep = vec3(0.0012, 0.0085, 0.019);
  vec3 horizon = mix(vec3(0.020, 0.120, 0.150), vec3(0.0055, 0.045, 0.072), d01);
  vec3 up = mix(vec3(0.090, 0.330, 0.360), vec3(0.030, 0.150, 0.195), d01);
  float k = dir.y;
  vec3 c = k > 0.0 ? mix(horizon, up, smoothstep(0.0, 0.9, k)) : mix(horizon, deep, smoothstep(0.0, 0.75, -k));
  float s = max(dot(dir, uSunDir), 0.0);
  c += vec3(0.20, 0.42, 0.40) * pow(s, 4.0) * (0.55 - 0.3 * d01);
  return c;
}

// What you see looking in direction dir from height y under water: fog + Snell's window.
vec3 waterBackground(vec3 dir, float y, float sunAmt){
  vec3 c = waterFog(dir, y);
  float d01 = clamp((uSurfaceY - y) / uSurfaceY, 0.0, 1.0);
  float vis = mix(1.0, 0.16, pow(d01, 0.7));
  float wob = 0.022 * sin(dir.x * 23.0 + uTime * 1.7) * sin(dir.z * 19.0 - uTime * 1.3)
            + 0.012 * sin((dir.x - dir.z) * 47.0 + uTime * 2.3);
  float yy = dir.y + wob;
  float win = smoothstep(0.640 - d01 * 0.07, 0.675, yy);
  if (win > 0.001) {
    vec2 txz = (dir.xz + vec2(wob, -wob) * 0.5) * 1.333;
    vec3 T = vec3(txz.x, sqrt(max(1.0 - dot(txz, txz), 0.0)), txz.y);
    vec3 sky = skyColor(normalize(T)) * vec3(0.95, 1.55, 1.75);
    c = mix(c, sky * (0.22 + 0.78 * vis), win * (0.30 + 0.70 * vis));
  }
  float rim = exp(-pow((yy - 0.66) * 38.0, 2.0));
  c += rim * vis * vec3(0.30, 0.55, 0.55) * 0.5;
  float s = max(dot(dir, uSunDir), 0.0);
  c += vec3(1.0, 0.86, 0.62) * (pow(s, 28.0) * 1.4 + pow(s, 7.0) * 0.28) * vis * sunAmt;
  return c;
}

vec3 downwell(float y){
  float depth = max(uSurfaceY - y, 0.0);
  return vec3(1.0, 0.90, 0.78) * exp(-vec3(0.30, 0.085, 0.06) * depth * 0.22) * 2.4;
}

vec3 litSurface(vec3 albedo, vec3 n, vec3 p, float caus){
  vec3 L = downwell(p.y);
  float ndl = max(dot(n, uSunDir), 0.0);
  vec2 cuv = (p.xz + uSunDir.xz / uSunDir.y * (uSurfaceY - p.y) * 0.15) * 0.085;
  float c = caus > 0.0 ? caustics(cuv, uTime * 0.55 + 23.0) : 0.0;
  float cm = caus * (0.25 + 0.75 * smoothstep(-0.1, 0.7, n.y));
  vec3 direct = L * ndl * (0.42 + 2.6 * c * cm);
  vec3 amb = waterFog(n, p.y) * 1.7 + waterFog(-n, p.y) * 0.35;
  return albedo * (direct + amb);
}

vec3 applyWater(vec3 col, vec3 wpos){
  if (uCamAbove > 0.5) return col;
  vec3 v = wpos - cameraPosition; float d = length(v); vec3 dir = v / max(d, 1e-4);
  vec3 ext = exp(-vec3(0.30, 0.085, 0.06) * d * 0.25);
  float f = 1.0 - exp(-d * uFogDensity);
  return mix(col * ext, waterFog(dir, cameraPosition.y), f);
}
float waterFade(vec3 wpos){
  float d = distance(wpos, cameraPosition);
  return exp(-d * uFogDensity * 1.1);
}
`;

const STD_VERT = /* glsl */ `
varying vec3 vWorld; varying vec3 vNormalW; varying vec2 vUv;
void main(){
  vUv = uv;
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWorld = wp.xyz;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

function mat(vertexShader, fragmentShader, extra = {}) {
  const { uniforms = {}, ...rest } = extra;
  return new THREE.ShaderMaterial({
    uniforms: { ...U, ...uniforms },
    vertexShader: COMMON + vertexShader,
    fragmentShader: COMMON + fragmentShader,
    ...rest,
  });
}

// ───────────────────────────────────────────────────────── renderer & scenes
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({
  canvas, antialias: false, powerPreference: 'high-performance',
  preserveDrawingBuffer: RENDER_MODE,
});
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();          // opaque world + additive atmosphere
const bubbleScene = new THREE.Scene();    // refractive bubbles, drawn over a copy of the world
const camera = new THREE.PerspectiveCamera(45, 16 / 9, 0.05, 4000);
const under = new THREE.Group();          // everything that only exists below the surface
scene.add(under);

// ───────────────────────────────────────────────────────── sky / water dome
{
  const m = mat(
    `varying vec3 vWorld; void main(){ vec4 wp = modelMatrix * vec4(position,1.0); vWorld = wp.xyz; gl_Position = projectionMatrix * viewMatrix * wp; }`,
    `varying vec3 vWorld;
     void main(){
       vec3 dir = normalize(vWorld - cameraPosition);
       vec3 c = uCamAbove > 0.5 ? skyColor(dir) : waterBackground(dir, cameraPosition.y, 1.0);
       gl_FragColor = vec4(min(c, vec3(12.0)), 1.0);
     }`,
    { side: THREE.BackSide, depthWrite: false });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1800, 48, 24), m);
  dome.renderOrder = -10;
  dome.frustumCulled = false;
  dome.onBeforeRender = () => dome.position.copy(camera.position);
  scene.add(dome);
}

// ───────────────────────────────────────────────────────── seafloor
function terrainH(x, z) {
  let h = (fbm3(x * 0.03, 0.5, z * 0.03) - 0.5) * 3.2 + (fbm3(x * 0.13 + 5, 1.5, z * 0.13) - 0.5) * 0.7;
  h += Math.sin(x * 0.18 + z * 0.07 + fbm3(x * 0.05, 2.5, z * 0.05) * 3) * 0.25;
  const r = Math.hypot(x, z);
  h = lerp(-0.04, h, smooth(1.2, 9, r));
  h += smooth(55, 150, r) * 16 * fbm3(x * 0.02, 3.5, z * 0.02);
  return h;
}
{
  const g = new THREE.PlaneGeometry(340, 340, 260, 260);
  g.rotateX(-Math.PI / 2);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) p.setY(i, terrainH(p.getX(i), p.getZ(i)));
  g.computeVertexNormals();
  const m = mat(STD_VERT, `
    varying vec3 vWorld; varying vec3 vNormalW;
    void main(){
      vec3 p = vWorld;
      float dist = distance(p, cameraPosition);
      float fadeR = 1.0 - smoothstep(6.0, 28.0, dist);
      vec2 rd = normalize(vec2(0.92, 0.38));
      float ph = dot(p.xz, rd) * 5.5 + fbm(p.xz * 0.25) * 7.0;
      vec3 n = normalize(vNormalW - vec3(rd.x, 0.0, rd.y) * cos(ph) * 0.22 * fadeR);
      float m = fbm(p.xz * 0.6);
      vec3 sand = mix(vec3(0.50, 0.44, 0.33), vec3(0.80, 0.72, 0.56), m);
      float grain = hash12(floor(p.xz * 90.0));
      sand *= 0.9 + (0.22 * grain + 0.08 * sin(ph)) * fadeR;
      float pat = smoothstep(0.55, 0.72, fbm(p.xz * 0.15 + 4.0));
      sand = mix(sand, sand * vec3(0.50, 0.60, 0.46), pat * 0.65);
      vec3 col = litSurface(sand, n, p, 1.0);
      float sp = pow(hash12(floor(p.xz * 140.0) + floor(uTime * 6.0)), 70.0) * fadeR;
      col += downwell(p.y) * sp * 1.6 * max(dot(n, uSunDir), 0.0);
      gl_FragColor = vec4(applyWater(col, p), 1.0);
    }`);
  under.add(new THREE.Mesh(g, m));
}

// ───────────────────────────────────────────────────────── rocks
const VENT = V(0.02, 0.05, -0.02);
const rockMat = mat(STD_VERT, `
  varying vec3 vWorld; varying vec3 vNormalW;
  void main(){
    vec3 p = vWorld; vec3 n = normalize(vNormalW);
    float dist = distance(p, cameraPosition);
    float detail = 1.0 - smoothstep(3.0, 18.0, dist);
    vec2 q = p.xz * 7.0 + vec2(p.y * 5.3, -p.y * 3.1);
    float e = 0.06;
    float b0 = fbm(q), bx = fbm(q + vec2(e, 0.0)), bz = fbm(q + vec2(0.0, e));
    n = normalize(n - vec3(bx - b0, 0.0, bz - b0) / e * 0.10 * detail);
    float n1 = fbm(p.xz * 1.7 + p.y * 1.3);
    vec3 base = mix(vec3(0.16, 0.15, 0.14), vec3(0.36, 0.33, 0.29), n1);
    base *= 0.8 + 0.4 * b0;
    float moss = smoothstep(0.35, 0.9, n.y + (fbm(p.xz * 2.3 + p.y) - 0.5) * 1.1);
    vec3 algae = mix(vec3(0.21, 0.22, 0.11), vec3(0.34, 0.22, 0.12), fbm(p.xz * 3.0 + 9.0));
    base = mix(base, algae, moss * 0.75);
    float coral = smoothstep(0.62, 0.70, fbm(p.xz * 1.6 - p.y * 0.9 + 7.0));
    base = mix(base, vec3(0.78, 0.33, 0.40), coral * 0.8);
    float cav = smoothstep(0.38, 0.05, b0);
    base *= 1.0 - cav * 0.45;
    vec3 col = litSurface(base, n, p, 1.0);
    gl_FragColor = vec4(applyWater(col, p), 1.0);
  }`);
function makeRock(seed) {
  let g = new THREE.IcosahedronGeometry(1, 12);
  g.deleteAttribute('normal'); g.deleteAttribute('uv');
  g = mergeVertices(g);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const d = 1 + 0.42 * (fbm3(x * 1.2 + seed, y * 1.2, z * 1.2 - seed, 4) - 0.5) + 0.10 * (fbm3(x * 4 + seed, y * 4, z * 4, 3) - 0.5);
    let ny = y * d;
    if (ny < -0.25) ny = -0.25 + (ny + 0.25) * 0.25;
    p.setXYZ(i, x * d, ny, z * d);
  }
  g.computeVertexNormals();
  return g;
}
const rockGeos = [0, 1, 2, 3, 4, 5].map((i) => makeRock(i * 17.3 + 3));
function addRock(x, z, sx, sy, sz, ry, gi) {
  const m = new THREE.Mesh(rockGeos[gi % rockGeos.length], rockMat);
  m.position.set(x, terrainH(x, z) + sy * 0.12, z);
  m.scale.set(sx, sy, sz);
  m.rotation.y = ry;
  under.add(m);
}
// the crevice the bubble is born from
addRock(-0.40, 0.02, 0.30, 0.22, 0.28, 0.4, 0);
addRock(0.40, -0.12, 0.28, 0.19, 0.32, 1.3, 1);
addRock(0.05, -0.55, 0.36, 0.24, 0.26, 2.1, 2);
addRock(-0.95, 0.35, 0.16, 0.12, 0.15, 0.9, 5);
addRock(0.75, 0.45, 0.12, 0.09, 0.13, 2.4, 3);
addRock(-2.6, -3.4, 1.1, 0.7, 0.9, 0.2, 3);
addRock(2.9, -3.8, 1.4, 0.9, 1.1, 2.8, 4);
// the reef around it, kept clear of the opening camera path
const S1A = V(-15, 4.6, 24), S1B = V(-6.5, 2.1, 10.5);
function distToSeg2(px, pz, a, b) {
  const abx = b.x - a.x, abz = b.z - a.z;
  const t = clamp(((px - a.x) * abx + (pz - a.z) * abz) / (abx * abx + abz * abz), 0, 1);
  return Math.hypot(px - (a.x + abx * t), pz - (a.z + abz * t));
}
for (let i = 0, placed = 0; i < 400 && placed < 70; i++) {
  const ang = rnd() * Math.PI * 2, r = 4 + Math.pow(rnd(), 0.8) * 70;
  const x = Math.sin(ang) * r, z = Math.cos(ang) * r;
  const s = rr(0.5, 2.6) * (r > 25 ? 1.8 : 1);
  if (distToSeg2(x, z, S1A, S1B) < s + 3.0) continue;
  if (Math.hypot(x - 2.5, z - 2.5) < 3.5) continue;
  addRock(x, z, s * rr(0.8, 1.3), s * rr(0.5, 0.9), s * rr(0.8, 1.3), rnd() * 6.28, placed);
  placed++;
}

// ───────────────────────────────────────────────────────── sea grass
{
  const blade = new THREE.PlaneGeometry(1, 1, 1, 5);
  blade.translate(0, 0.5, 0);
  const N = 7000;
  const mesh = new THREE.InstancedMesh(blade, mat(`
    attribute vec4 aG;
    varying vec3 vWorld; varying vec3 vN; varying float vH; varying float vTint;
    void main(){
      vec3 p = position; float h = p.y;
      p.x *= (1.0 - h * 0.85);
      vec4 wp = modelMatrix * instanceMatrix * vec4(p, 1.0);
      float sway = sin(uTime * 1.1 + aG.x + wp.x * 0.3) * 0.5 + sin(uTime * 2.3 + aG.x * 2.0) * 0.15;
      vec2 dir = vec2(cos(aG.z), sin(aG.z));
      float bend = h * h * (0.35 + 0.3 * sway) * aG.w;
      wp.xz += dir * bend; wp.y -= bend * bend * 0.25;
      vWorld = wp.xyz; vH = h; vTint = aG.y;
      vN = normalize(mat3(modelMatrix * instanceMatrix) * vec3(0.0, 0.0, 1.0));
      gl_Position = projectionMatrix * viewMatrix * wp;
    }`, `
    varying vec3 vWorld; varying vec3 vN; varying float vH; varying float vTint;
    void main(){
      vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
      n = normalize(n + vec3(0.0, 0.6, 0.0));
      vec3 alb = mix(vec3(0.07, 0.11, 0.04), mix(vec3(0.30, 0.30, 0.10), vec3(0.40, 0.28, 0.12), vTint), vH);
      vec3 V = normalize(cameraPosition - vWorld);
      vec3 col = litSurface(alb, n, vWorld, 0.5);
      col += downwell(vWorld.y) * alb * pow(max(dot(-V, uSunDir), 0.0), 3.0) * vH * 0.5;
      gl_FragColor = vec4(applyWater(col, vWorld), 1.0);
    }`, { side: THREE.DoubleSide }), N);
  const aG = new Float32Array(N * 4);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  let n = 0;
  for (let i = 0; i < N * 6 && n < N; i++) {
    const x = rr(-30, 30), z = rr(-30, 30);
    const r = Math.hypot(x, z);
    if (r < 1.5) continue;
    const patch = fbm3(x * 0.12, 7.7, z * 0.12);
    if (patch < 0.5 + 0.1 * rnd()) continue;
    if (distToSeg2(x, z, S1A, S1B) < 1.5) continue;
    const h = rr(0.35, 1.1) * (0.6 + patch);
    e.set(0, rnd() * Math.PI, 0); q.setFromEuler(e);
    m4.compose(V(x, terrainH(x, z) - 0.03, z), q, V(rr(0.03, 0.06), h, 1));
    mesh.setMatrixAt(n, m4);
    aG.set([rnd() * 6.28, rnd(), rnd() * 6.28, h], n * 4);
    n++;
  }
  mesh.count = n;
  blade.setAttribute('aG', new THREE.InstancedBufferAttribute(aG, 4));
  mesh.frustumCulled = false;
  under.add(mesh);
}

// ───────────────────────────────────────────────────────── kelp forest
{
  const blade = new THREE.PlaneGeometry(1, 1, 1, 90);
  blade.translate(0, 0.5, 0);
  const mesh = new THREE.InstancedMesh(blade, mat(`
    attribute vec4 aK;
    varying vec3 vWorld; varying vec3 vN; varying vec2 vUv; varying vec4 vK;
    void main(){
      vUv = uv; vK = aK;
      vec4 wp = modelMatrix * instanceMatrix * vec4(position, 1.0);
      float h = position.y;
      float H = aK.y;
      vec2 sw = vec2(sin(uTime * 0.45 + aK.x + h * 2.6), cos(uTime * 0.38 + aK.x * 1.7 + h * 2.2)) * pow(h, 1.4) * (0.9 + 0.035 * H);
      sw += vec2(sin(uTime * 1.3 + h * 9.0 + aK.x), cos(uTime * 1.1 + h * 7.0)) * 0.08 * h;
      wp.xz += sw;
      vWorld = wp.xyz;
      vN = normalize(mat3(modelMatrix * instanceMatrix) * vec3(0.0, 0.0, 1.0));
      gl_Position = projectionMatrix * viewMatrix * wp;
    }`, `
    varying vec3 vWorld; varying vec3 vN; varying vec2 vUv; varying vec4 vK;
    void main(){
      float H = vK.y;
      float f = fract(vUv.y * H * 0.9 + vK.x);
      float w = 0.22 + 0.78 * pow(sin(3.14159 * f), 0.55);
      w *= 1.0 - smoothstep(0.92, 1.0, vUv.y) * 0.7;
      float ruff = 0.07 * sin(vUv.y * H * 22.0 + vK.x * 5.0);
      float across = abs(vUv.x - 0.5) * 2.0;
      if (across > w + ruff) discard;
      vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
      vec3 Vd = normalize(cameraPosition - vWorld);
      vec3 alb = mix(vec3(0.30, 0.22, 0.06), vec3(0.42, 0.30, 0.08), vK.z) * 0.8;
      alb *= 0.75 + 0.25 * smoothstep(0.0, 0.25, across) + 0.08 * sin(vUv.y * H * 40.0);
      alb *= mix(0.6, 1.0, smoothstep(0.0, 0.2, w - across));
      vec3 col = litSurface(alb, n, vWorld, 0.55);
      float back = pow(max(dot(-Vd, uSunDir), 0.0), 2.5);
      col += downwell(vWorld.y) * vec3(0.60, 0.42, 0.10) * back * 0.45;
      col *= 0.85 + 0.15 * vnoise(vec2(vUv.y * H * 3.0, vK.x * 10.0));
      gl_FragColor = vec4(applyWater(col, vWorld), 1.0);
    }`, { side: THREE.DoubleSide }), 70);
  const aK = new Float32Array(70 * 4);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  let n = 0;
  for (let i = 0; i < 4000 && n < 70; i++) {
    const ang = rnd() * Math.PI * 2, r = 1.8 + Math.pow(rnd(), 0.7) * 26;
    const x = Math.sin(ang) * r, z = Math.cos(ang) * r;
    // keep clear of the macro shot (camera sits towards +z of the vent) and the tracking orbit
    if (r < 3.2 && Math.cos(ang) > -0.2) continue;
    if (Math.abs(r - 3.3) < 0.7 && ang > 0.1 && ang < 1.3) continue;
    if (distToSeg2(x, z, S1A, S1B) < 2.5) continue;
    if (r < 1.8) continue;
    const H = rr(15, 33);
    for (let k = 0; k < 2 && n < 70; k++) {
      e.set(0, rnd() * Math.PI + k * 1.4, 0); q.setFromEuler(e);
      m4.compose(V(x + rr(-0.1, 0.1), terrainH(x, z) - 0.1, z + rr(-0.1, 0.1)), q, V(rr(0.35, 0.6), H * rr(0.8, 1), 1));
      mesh.setMatrixAt(n, m4);
      aK.set([rnd() * 6.28, H, rnd(), 0], n * 4);
      n++;
    }
  }
  mesh.count = n;
  blade.setAttribute('aK', new THREE.InstancedBufferAttribute(aK, 4));
  mesh.frustumCulled = false;
  under.add(mesh);
}

// ───────────────────────────────────────────────────────── story clock & bubble path
// Story time (seconds, 0–60) drives the whole world. Each edit (the 16:9 film and the
// 9:16 shorts) maps its own output time onto story time and films it with its own cameras.
export const STORY = 60;
const T_FORM = 9.2, T_DETACH = 16.0, T_SURF = 45.6, T_CROSS = 46.0, T_POP = 47.4, T_CODA = 54.0, T_FORM2 = 54.6;
const R0 = 0.15, R1 = 0.25;
const K_ACC = 1.1;
const Y_DETACH = VENT.y + R0 * (0.78 + 0.35);
const Y_TOUCH = SURFACE - R1 * 0.95;
const T_RISE = T_SURF - T_DETACH;
const VMAX = (Y_TOUCH - Y_DETACH) / (T_RISE - (1 - Math.exp(-K_ACC * T_RISE)) / K_ACC);
const riseY = (tau) => Y_DETACH + VMAX * (tau - (1 - Math.exp(-K_ACC * tau)) / K_ACC);
function zig(tau) {
  const A = 0.30 * (1 - Math.exp(-tau / 1.6)), w = 2.0;
  return [VENT.x + A * Math.sin(w * tau) + 0.04 * tau, VENT.z + A * 0.7 * (Math.cos(w * tau * 0.93) - 1) - 0.015 * tau];
}
function bubbleAt(t) {
  const s = { visible: true, pos: V(0, 0, 0), R: R0, neck: 0, wob: 0.04, flat: 0, tilt: new THREE.Quaternion(), surfaced: 0 };
  if (t >= T_CODA) {
    // a new bubble begins in the same crack
    const g = clamp((t - T_FORM2) / 7.0, 0, 1);
    s.visible = g > 0;
    s.R = Math.max(0.0001, R0 * 0.9 * Math.pow(g, 0.45));
    s.neck = 0.25 * g;
    s.pos.set(VENT.x, VENT.y + s.R * 0.78 + s.neck * s.R * 0.35, VENT.z);
    s.wob = 0.03 + 0.02 * g;
    return s;
  }
  if (t < T_FORM) { s.visible = false; s.R = 0.0001; s.pos.copy(VENT); return s; }
  if (t < T_DETACH) {
    const g = (t - T_FORM) / (T_DETACH - T_FORM);
    s.R = R0 * Math.pow(g, 0.42);
    s.neck = smooth(0.3, 1.0, g);
    s.pos.set(VENT.x, VENT.y + s.R * 0.78 + s.neck * s.R * 0.35, VENT.z);
    s.wob = 0.035 + 0.03 * g;
    return s;
  }
  const tau = Math.min(t, T_SURF) - T_DETACH;
  let y = riseY(tau);
  const [x, z] = zig(tau);
  s.R = lerp(R0, R1, clamp((y - Y_DETACH) / (Y_TOUCH - Y_DETACH), 0, 1));
  s.neck = Math.max(0, 1 - (t - T_DETACH) / 0.09);
  s.wob = 0.045 + 0.2 * Math.exp(-(t - T_DETACH) * 1.5);
  s.flat = 0.13 * (1 - Math.exp(-(t - T_DETACH) * 2.0));
  if (t >= T_SURF) {
    const u = Math.min(t, T_POP) - T_SURF;
    const k = smooth(0, 0.45, u);
    y = lerp(Y_TOUCH, SURFACE - R1 * 0.12 + swell(x, z, t), k) + 0.025 * Math.exp(-u * 3) * Math.sin(u * 18);
    s.flat = lerp(s.flat, 0.36, k);
    s.wob = 0.03 + 0.1 * Math.exp(-u * 4);
    s.surfaced = k;
    if (t > T_POP + 0.12) s.visible = false;
  }
  s.pos.set(x, y, z);
  if (t < T_SURF) {
    const [x2, z2] = zig(tau + 0.05);
    const vel = V(x2 - x, riseY(tau + 0.05) - y, z2 - z).normalize();
    s.tilt.setFromUnitVectors(V(0, 1, 0), V(0, 1, 0).lerp(vel, 0.7).normalize());
  }
  return s;
}
const Bc = (t) => bubbleAt(t).pos;

// ───────────────────────────────────────────────────────── bubbles (refractive)
const BUBBLE_VERT = /* glsl */ `
uniform float uWob; uniform float uNeck; uniform float uFlat; uniform float uBT;
#ifdef SMALL
attribute vec4 aB; attribute vec4 aB2;
#endif
varying vec3 vWorld; varying vec3 vN; varying vec3 vNView; varying vec3 vObj; varying float vSR;
void main(){
  vec3 p = position; vec3 n = normal;
  vec4 wp; vec3 nw; float scale;
#ifdef HERO
  float w = uWob * ( sin(uBT * 11.0) * (n.y * n.y - 0.333)
                   + 0.7 * sin(uBT * 15.3 + 1.3) * n.x * n.y
                   + 0.9 * sin(uBT * 17.7 + 2.1) * n.z * n.x
                   + 0.4 * sin(uBT * 21.0 + 0.7) * (n.y * n.y * n.y - 0.6 * n.y)
                   + 0.35 * sin(uBT * 9.1 + 0.4) * n.z * n.y );
  p *= 1.0 + w;
  vec3 sc = vec3(1.0 + uFlat * 0.45, 1.0 - uFlat, 1.0 + uFlat * 0.45);
  p *= sc;
  float wn = smoothstep(-0.15, -1.0, n.y) * uNeck;
  p.xz *= 1.0 - 0.62 * wn;
  p.y -= wn * 0.6;
  n = normalize(n / sc + vec3(0.0, wn * 0.8, 0.0));
  wp = modelMatrix * vec4(p, 1.0);
  nw = normalize(mat3(modelMatrix) * n);
  scale = length(modelMatrix[0].xyz);
#else
  // aB: source x, source z, phase, size   aB2: speed, source y, wobble, unused
  float H = uSurfaceY - aB2.y;
  float y = mod(aB.z * H + aB2.x * uTime, H);
  float r = aB.w * (1.0 + y / uSurfaceY * 0.7);
  r *= smoothstep(0.0, 0.25, y) * (1.0 - smoothstep(H - 0.4, H, y));
  float lift = smoothstep(0.0, 2.0, y);
  vec3 c = vec3(aB.x + sin(uTime * 3.1 + aB.z * 30.0) * aB2.z * lift + y * 0.03,
                aB2.y + y,
                aB.y + cos(uTime * 2.7 + aB.z * 20.0) * aB2.z * lift);
  p.y *= 0.85;
  wp = vec4(c + p * r, 1.0);
  nw = n;
  scale = r;
#endif
  vWorld = wp.xyz; vN = nw; vObj = p;
  vNView = normalize(mat3(viewMatrix) * nw);
  vec4 mv = viewMatrix * wp;
  vSR = scale * projectionMatrix[1][1] / max(-mv.z, 0.05) * 0.5;
  gl_Position = projectionMatrix * mv;
}`;
const BUBBLE_FRAG = /* glsl */ `
uniform sampler2D tScene; uniform vec2 uRes; uniform float uAspect;
uniform float uAboveMode; uniform float uPop;
varying vec3 vWorld; varying vec3 vN; varying vec3 vNView; varying vec3 vObj; varying float vSR;
void main(){
  vec3 n = normalize(vN);
  vec3 Vd = normalize(cameraPosition - vWorld);
  float cosi = clamp(dot(n, Vd), 0.0, 1.0);
  vec3 R = reflect(-Vd, n);
  vec2 suv = gl_FragCoord.xy / uRes;
  vec3 col;
  if (uAboveMode > 0.5) {
    // a surfaced bubble: a thin soap-like film with interference colours
    float hole = fbm(vObj.xz * 3.5 + 2.0) + vObj.y * 0.9;
    if (uPop > 0.0 && hole > 1.6 - uPop * 2.2) discard;
    float th = 0.35 + 0.9 * fbm(vObj.xz * 2.2 + vec2(vObj.y * 3.0 - uTime * 0.35, uTime * 0.2));
    vec3 film = 0.5 + 0.5 * cos(6.28318 * (th * 1.6 + vec3(0.0, 0.33, 0.67)) + cosi * 2.5);
    float Fs = 0.04 + 0.96 * pow(1.0 - cosi, 4.0);
    vec3 behind = texture2D(tScene, suv + vNView.xy * vec2(1.0 / uAspect, 1.0) * vSR * 0.08).rgb;
    col = behind * (0.93 - Fs * 0.3) + skyColor(normalize(vec3(R.x, abs(R.y), R.z))) * film * (0.18 + Fs * 1.1);
    col += vec3(1.0, 0.85, 0.6) * pow(max(dot(R, uSunAbove), 0.0), 400.0) * 6.0;
    gl_FragColor = vec4(col, 1.0);
    return;
  }
  // Air bubble in water: light goes from n=1.333 into n=1.0, so past ~48.6° the
  // surface reflects totally. That is the bright silver ring every bubble has.
  float eta = 1.333;
  float sint = eta * sqrt(max(1.0 - cosi * cosi, 0.0));
  float F;
  if (sint >= 1.0) F = 1.0;
  else {
    float cost = sqrt(1.0 - sint * sint);
    float rs = (eta * cosi - cost) / (eta * cosi + cost);
    float rp = (cosi - eta * cost) / (cosi + eta * cost);
    F = 0.5 * (rs * rs + rp * rp);
  }
  float fw = fwidth(sint) * 1.5 + 0.01;
  F = mix(F, 1.0, smoothstep(1.0 - fw, 1.0, sint));
  vec3 refl = waterBackground(R, vWorld.y, 1.0) * 1.15;
  // the air pocket acts as a diverging lens: it shows a shrunken view of the world behind it
  vec2 off = vNView.xy * vec2(1.0 / uAspect, 1.0) * vSR * 1.1;
  vec3 trans;
  trans.r = texture2D(tScene, suv + off * 1.00).r;
  trans.g = texture2D(tScene, suv + off * 1.05).g;
  trans.b = texture2D(tScene, suv + off * 1.10).b;
  trans *= 1.12;
  float inner = pow(max(dot(n, -uSunDir), 0.0), 5.0) * (1.0 - F);
  col = mix(trans, refl, F);
  col += downwell(vWorld.y) * inner * 0.22;
  col += vec3(1.0, 0.93, 0.80) * pow(max(dot(R, uSunDir), 0.0), 700.0) * 26.0 * mix(0.25, 1.0, smoothstep(0.0, 25.0, vWorld.y));
  gl_FragColor = vec4(min(applyWater(col, vWorld), vec3(12.0)), 1.0);
}`;
const bubbleUniforms = {
  tScene: { value: null }, uRes: { value: new THREE.Vector2(1, 1) }, uAspect: { value: 16 / 9 },
  uWob: { value: 0 }, uNeck: { value: 0 }, uFlat: { value: 0 }, uBT: { value: 0 },
  uAboveMode: { value: 0 }, uPop: { value: 0 },
};
const heroMat = mat(BUBBLE_VERT, BUBBLE_FRAG, { uniforms: bubbleUniforms, defines: { HERO: '' } });
const hero = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 96), heroMat);
hero.frustumCulled = false;
bubbleScene.add(hero);

// streams of small bubbles: the hero's own vent, plus seeps scattered over the reef
const smallBubbles = (() => {
  const base = new THREE.IcosahedronGeometry(1, 3);
  const g = new THREE.InstancedBufferGeometry().copy(base);
  const sources = [[VENT.x, VENT.z, 0.012, 0.028, 70]];
  for (let i = 0; i < 9; i++) {
    const a = rr(0, 6.28), r = rr(5, 26);
    sources.push([Math.sin(a) * r, Math.cos(a) * r, 0.02, 0.06, 18]);
  }
  const aB = [], aB2 = [];
  for (const [sx, sz, s0, s1, count] of sources) {
    const sy = terrainH(sx, sz) + 0.05;
    for (let i = 0; i < count; i++) {
      aB.push(sx + rr(-0.03, 0.03), sz + rr(-0.03, 0.03), rnd(), rr(s0, s1));
      aB2.push(rr(1.2, 2.4), sy, rr(0.02, 0.07), 0);
    }
  }
  g.instanceCount = aB.length / 4;
  g.setAttribute('aB', new THREE.InstancedBufferAttribute(new Float32Array(aB), 4));
  g.setAttribute('aB2', new THREE.InstancedBufferAttribute(new Float32Array(aB2), 4));
  const m = mat(BUBBLE_VERT, BUBBLE_FRAG, { uniforms: { ...bubbleUniforms, uAboveMode: { value: 0 } }, defines: { SMALL: '' } });
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false;
  bubbleScene.add(mesh);
  return mesh;
})();

// ───────────────────────────────────────────────────────── fish schools
function makeFishGeometry() {
  let body = new THREE.SphereGeometry(1, 16, 10);
  body.rotateZ(-Math.PI / 2);
  body.deleteAttribute('uv');
  const p = body.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i);
    const taper = x < 0 ? 1 - 0.6 * Math.pow(-x, 1.3) : 1 - 0.3 * x * x;
    p.setY(i, p.getY(i) * 0.30 * taper);
    p.setZ(i, p.getZ(i) * 0.11 * taper);
  }
  body = body.toNonIndexed();
  body.computeVertexNormals();
  const tri = (arr) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
    g.computeVertexNormals();
    return g;
  };
  const tail = tri([-0.80, 0, 0, -1.40, 0.32, 0, -1.22, 0, 0, -0.80, 0, 0, -1.22, 0, 0, -1.40, -0.32, 0]);
  const fin = tri([0.15, 0.24, 0, -0.35, 0.42, 0, -0.42, 0.18, 0]);
  return mergeGeometries([body, tail, fin]);
}
const fishBase = makeFishGeometry();
function makeSchool(count, spread, params) {
  const g = new THREE.InstancedBufferGeometry().copy(fishBase);
  g.instanceCount = count;
  const aF = new Float32Array(count * 4), aS = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const v = V(rr(-1, 1), rr(-1, 1), rr(-1, 1));
    if (v.length() > 1) { i--; continue; }
    v.multiply(V(1.4, 0.5, 1.0));
    aF.set([v.x, v.y, v.z, rnd()], i * 4);
    aS[i] = rr(0.32, 0.5);
  }
  g.setAttribute('aF', new THREE.InstancedBufferAttribute(aF, 4));
  g.setAttribute('aSize', new THREE.InstancedBufferAttribute(aS, 1));
  const uniforms = {
    uC: { value: params.c }, uVel: { value: params.vel || V(0, 0, 0) }, uR: { value: params.r },
    uW: { value: params.w }, uPh: { value: params.ph || 0 }, uAy: { value: params.ay || 0.5 }, uSpread: { value: spread },
  };
  const m = mat(`
    attribute vec4 aF; attribute float aSize;
    uniform vec3 uC; uniform vec3 uVel; uniform float uR; uniform float uW; uniform float uPh; uniform float uAy; uniform float uSpread;
    varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal;
    vec3 center(float t){ return uC + uVel * t + vec3(uR * cos(uW * t + uPh), uAy * sin(uW * 0.7 * t), uR * sin(uW * t + uPh)); }
    vec3 fishPos(float t){
      float s = aF.w * 6.283;
      vec3 wander = vec3(sin(t * 0.9 + s * 3.0), 0.5 * sin(t * 1.3 + s * 5.0), cos(t * 0.7 + s * 2.0)) * 0.3;
      return center(t - aF.w * 0.5) + (aF.xyz * (1.0 + 0.12 * sin(t * 0.5 + s)) + wander) * uSpread;
    }
    void main(){
      float t = uTime;
      vec3 P = fishPos(t);
      vec3 f = normalize(fishPos(t + 0.08) - P + vec3(1e-5, 0.0, 0.0));
      vec3 r = normalize(cross(f, vec3(0.0, 1.0, 0.0)));
      vec3 u = cross(r, f);
      vec3 lp = position;
      lp.z += sin(t * 13.0 + aF.w * 40.0 - lp.x * 3.5) * 0.13 * (0.25 + 0.75 * smoothstep(0.6, -1.4, lp.x));
      vLocal = position;
      vec3 wp = P + (f * lp.x + u * lp.y + r * lp.z) * aSize;
      vN = normalize(f * normal.x + u * normal.y + r * normal.z);
      vWorld = wp;
      gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
    }`, `
    varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal;
    void main(){
      vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
      float back = smoothstep(-0.04, 0.12, vLocal.y);
      vec3 alb = mix(vec3(0.72, 0.78, 0.80), vec3(0.07, 0.15, 0.21), back);
      alb *= 0.9 + 0.1 * sin(vLocal.x * 30.0);
      vec3 Vd = normalize(cameraPosition - vWorld);
      vec3 col = litSurface(alb, n, vWorld, 0.3);
      vec3 R = reflect(-Vd, n);
      float fr = pow(1.0 - abs(dot(n, Vd)), 3.0);
      col += waterFog(R, vWorld.y) * (1.5 + 3.0 * fr) * (1.0 - back * 0.7);
      col += vec3(1.0, 0.92, 0.8) * pow(max(dot(R, uSunDir), 0.0), 60.0) * 2.5 * (1.0 - back * 0.6);
      gl_FragColor = vec4(applyWater(col, vWorld), 1.0);
    }`, { uniforms, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false;
  under.add(mesh);
  return mesh;
}
// a school circling the reef (opening shot) …
makeSchool(170, 2.6, { c: V(4, 7.5, -12), r: 13, w: 0.16, ph: 2.6, ay: 1.0 });

// ───────────────────────────────────────────────────────── jellyfish
const jellies = [];
const bellGeo = new THREE.SphereGeometry(1, 48, 18, 0, Math.PI * 2, 0, Math.PI * 0.56);
function addJelly(x, y, z, s, ph) {
    const uniforms = { uPulse: { value: 0 } };
    const bell = new THREE.Mesh(bellGeo, mat(`
      uniform float uPulse;
      varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal;
      void main(){
        vec3 p = position;
        float rim = smoothstep(0.1, 1.0, 1.0 - p.y);
        p.xz *= 1.0 - 0.24 * uPulse * rim - 0.05 * uPulse;
        p.y *= 1.0 + 0.14 * uPulse;
        vLocal = p;
        vec4 wp = modelMatrix * vec4(p, 1.0);
        vWorld = wp.xyz;
        vN = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`, `
      varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal;
      void main(){
        vec3 n = normalize(vN);
        vec3 Vd = normalize(cameraPosition - vWorld);
        float fr = pow(1.0 - abs(dot(n, Vd)), 2.2);
        float ang = atan(vLocal.z, vLocal.x);
        float rib = pow(abs(sin(ang * 8.0)), 12.0) * smoothstep(0.95, 0.2, vLocal.y);
        float gon = smoothstep(0.35, 0.0, abs(length(vLocal.xz) - 0.35 - 0.08 * sin(ang * 4.0))) * smoothstep(0.55, 0.85, vLocal.y);
        vec3 c = vec3(0.50, 0.30, 1.00) * (0.06 + 1.5 * fr) + vec3(1.0, 0.55, 0.85) * (rib * 0.25 + gon * 0.55);
        c += vec3(0.6, 0.85, 1.0) * smoothstep(0.08, 0.0, vLocal.y) * 0.6;
        gl_FragColor = vec4(c * 0.7 * waterFade(vWorld) * smoothstep(0.4, 2.2, distance(vWorld, cameraPosition)), 1.0);
      }`, { uniforms, side: THREE.DoubleSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    bell.scale.setScalar(s);
    const tentacles = [];
    const lineMat = new THREE.LineBasicMaterial({ color: new THREE.Color(0.55, 0.40, 0.95), transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false });
    for (let j = 0; j < 14; j++) {
      const N = 48;
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
      const line = new THREE.Line(geo, lineMat);
      line.frustumCulled = false;
      tentacles.push({ line, a: (j / 14) * Math.PI * 2 + rr(-0.1, 0.1), len: s * rr(1.6, 3.0) * (j % 4 === 0 ? 1.4 : 1), N, oral: j % 4 === 0 });
      under.add(line);
    }
    under.add(bell);
    jellies.push({ bell, uniforms, tentacles, base: V(x, y, z), s, ph });
}
for (const sp of [
    [3.4, 21.5, -4.6, 0.75, 0.0], [-5.2, 25.5, -2.4, 1.0, 1.3], [2.3, 28.5, 5.2, 0.55, 2.2],
    [-10, 18.5, -9.5, 1.5, 0.6], [7.5, 31, -1.5, 0.8, 3.1],
  ]) addJelly(...sp);
function jellyPulse(t, ph) {
  const p = ((t * 0.42 + ph) % 1 + 1) % 1;
  return p < 0.28 ? smooth(0, 0.28, p) : 1 - smooth(0.28, 1.0, p);
}
function updateJellies(t) {
  for (const j of jellies) {
    const c = jellyPulse(t, j.ph);
    j.uniforms.uPulse.value = c;
    const pos = j.base.clone().add(V(Math.sin(t * 0.2 + j.ph) * 0.3, t * 0.22 + 0.25 * Math.sin((t * 0.42 + j.ph) * 6.283), Math.cos(t * 0.17 + j.ph) * 0.3));
    j.bell.position.copy(pos);
    j.bell.rotation.set(Math.sin(t * 0.3 + j.ph) * 0.15, t * 0.1, Math.cos(t * 0.25 + j.ph) * 0.12);
    j.bell.updateMatrixWorld();
    for (const tc of j.tentacles) {
      const arr = tc.line.geometry.attributes.position.array;
      const rad = (tc.oral ? 0.25 : 0.92) * j.s * (1 - 0.22 * c);
      const root = V(Math.cos(tc.a) * rad, 0.02 * j.s, Math.sin(tc.a) * rad).applyMatrix4(j.bell.matrixWorld);
      for (let k = 0; k < tc.N; k++) {
        const f = k / (tc.N - 1);
        const L = tc.len * f;
        arr[k * 3] = root.x + Math.sin(t * 1.1 + f * 5.0 + tc.a * 3) * 0.25 * f * j.s + Math.cos(tc.a) * f * 0.2 * j.s;
        arr[k * 3 + 1] = root.y - L;
        arr[k * 3 + 2] = root.z + Math.cos(t * 0.9 + f * 4.0 + tc.a * 2) * 0.25 * f * j.s + Math.sin(tc.a) * f * 0.2 * j.s;
      }
      tc.line.geometry.attributes.position.needsUpdate = true;
    }
  }
}

// ───────────────────────────────────────────────────────── light shafts
const RAY_SPECIAL = { value: 0 };
{
  const base = new THREE.PlaneGeometry(1, 1, 1, 10);
  const g = new THREE.InstancedBufferGeometry().copy(base);
  const N = 30;
  const aRay = new Float32Array(N * 4), aLen = new Float32Array(N), aGain = new Float32Array(N).fill(1);
  const hd = V(-SUN_UNDER.x, 0, -SUN_UNDER.z).normalize();
  const reach = SURFACE / SUN_UNDER.y;
  for (let i = 0; i < N; i++) {
    const cx = -hd.x * reach * 0.5 * SUN_UNDER.y * 1.2, cz = -hd.z * reach * 0.5 * SUN_UNDER.y * 1.2;
    aRay.set([cx + rr(-30, 30), cz + rr(-30, 30), rr(1.2, 5.0), rnd()], i * 4);
    aLen[i] = reach * rr(0.8, 1.05);
  }
  { // the shaft that lights the bubble when Pip finds it again
    const b = Bc(35.6), top = b.clone().addScaledVector(SUN_UNDER, (SURFACE - b.y) / SUN_UNDER.y);
    aRay.set([top.x, top.z, 1.5, 0.37], (N - 1) * 4);
    aLen[N - 1] = reach;
    aGain[N - 1] = 2.2;
  }
  g.instanceCount = N;
  g.setAttribute('aRay', new THREE.InstancedBufferAttribute(aRay, 4));
  g.setAttribute('aLen', new THREE.InstancedBufferAttribute(aLen, 1));
  g.setAttribute('aGain', new THREE.InstancedBufferAttribute(aGain, 1));
  const m = mat(`
    attribute vec4 aRay; attribute float aLen; attribute float aGain;
    varying vec2 vUv2; varying float vSeed; varying float vCamD; varying vec3 vWorld; varying float vGain;
    void main(){
      vUv2 = uv; vSeed = aRay.w; vGain = aGain;
      vec3 top = vec3(aRay.x, uSurfaceY, aRay.y);
      vec3 axis = -uSunDir;
      float along = (1.0 - uv.y) * aLen;
      vec3 P = top + axis * along;
      vec3 toCam = normalize(cameraPosition - P);
      vec3 side = normalize(cross(axis, toCam));
      P += side * (uv.x - 0.5) * aRay.z * (1.0 + (1.0 - uv.y) * 0.8);
      vWorld = P; vCamD = distance(P, cameraPosition);
      gl_Position = projectionMatrix * viewMatrix * vec4(P, 1.0);
    }`, `
    uniform float uRayStrength; uniform float uSpecial;
    varying vec2 vUv2; varying float vSeed; varying float vCamD; varying vec3 vWorld; varying float vGain;
    void main(){
      float edge = pow(max(1.0 - abs(vUv2.x - 0.5) * 2.0, 0.0), 1.8);
      float streak = 0.45 + 0.55 * vnoise(vec2(vUv2.x * 7.0 + vSeed * 13.0, uTime * 0.25 + vSeed * 5.0));
      float flick = 0.6 + 0.4 * sin(uTime * 0.9 + vSeed * 20.0);
      float fadeBot = smoothstep(0.0, 0.75, vUv2.y);
      float fadeTop = smoothstep(1.0, 0.97, vUv2.y);
      float nearF = smoothstep(0.8, 7.0, vCamD);
      float I = edge * streak * flick * fadeBot * fadeTop * nearF * exp(-vCamD * 0.016);
      gl_FragColor = vec4(vec3(0.55, 0.85, 0.78) * I * uRayStrength * (1.0 + (vGain - 1.0) * uSpecial), 1.0);
    }`, { uniforms: { uRayStrength: { value: 0.11 }, uSpecial: RAY_SPECIAL }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false;
  mesh.renderOrder = 5;
  under.add(mesh);
}

// ───────────────────────────────────────────────────────── marine snow
const snowUniforms = { uBox: { value: 22 }, uPx: { value: 800 } };
{
  const N = 5000;
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3), seed = new Float32Array(N * 4);
  for (let i = 0; i < N; i++) {
    pos.set([rr(-11, 11), rr(-11, 11), rr(-11, 11)], i * 3);
    seed.set([rnd(), rnd(), rnd(), rnd()], i * 4);
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
  const m = mat(`
    uniform float uBox; uniform float uPx;
    attribute vec4 aSeed;
    varying float vAlpha; varying float vBokeh;
    void main(){
      vec3 p = position + vec3(sin(uTime * 0.2 + aSeed.x * 6.3) * 0.3, -uTime * 0.05 * aSeed.y, cos(uTime * 0.17 + aSeed.z * 6.3) * 0.3);
      p = mod(p - cameraPosition + uBox * 0.5, uBox) - uBox * 0.5 + cameraPosition;
      vec4 mv = viewMatrix * vec4(p, 1.0);
      gl_Position = projectionMatrix * mv;
      float dist = -mv.z;
      gl_PointSize = clamp(uPx * (0.012 + aSeed.w * 0.02) / max(dist, 0.05), 1.0, 90.0);
      vAlpha = smoothstep(0.15, 0.8, dist) * (1.0 - smoothstep(uBox * 0.3, uBox * 0.5, dist)) * (0.4 + 0.6 * aSeed.y);
      vBokeh = smoothstep(2.2, 0.5, dist);
    }`, `
    varying float vAlpha; varying float vBokeh;
    void main(){
      float d = length(gl_PointCoord - 0.5) * 2.0;
      float hard = smoothstep(1.0, 0.0, d);
      float disc = smoothstep(1.0, 0.85, d) * 0.22 + smoothstep(0.98, 0.9, d) * smoothstep(0.75, 0.9, d) * 0.25;
      float a = mix(hard, disc, vBokeh) * vAlpha;
      vec3 c = downwell(cameraPosition.y) * vec3(0.55, 0.62, 0.55) * 0.35;
      gl_FragColor = vec4(c * a, 1.0);
    }`, { uniforms: snowUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const pts = new THREE.Points(g, m);
  pts.frustumCulled = false;
  pts.renderOrder = 6;
  under.add(pts);
}

// ───────────────────────────────────────────────────────── water surface
const surfUniforms = { uPopPos: { value: V(0, SURFACE, 0) }, uPopT: { value: -100 } };
function swell(x, z, t) {
  return 0.09 * Math.sin((x * 0.8 + z * 0.6) * 0.12 + t * 0.6) + 0.06 * Math.sin((x * -0.3 + z * 0.95) * 0.17 + t * 0.8);
}
{
  const g = new THREE.PlaneGeometry(3200, 3200, 320, 320);
  g.rotateX(-Math.PI / 2);
  const m = mat(`
    varying vec3 vWorld;
    void main(){
      vec4 wp = modelMatrix * vec4(position, 1.0);
      wp.y += 0.09 * sin((wp.x * 0.8 + wp.z * 0.6) * 0.12 + uTime * 0.6) + 0.06 * sin((wp.x * -0.3 + wp.z * 0.95) * 0.17 + uTime * 0.8);
      vWorld = wp.xyz;
      gl_Position = projectionMatrix * viewMatrix * wp;
    }`, `
    uniform vec3 uPopPos; uniform float uPopT;
    varying vec3 vWorld;
    vec2 waveGrad(vec2 p, float t){
      vec2 g = vec2(0.0);
      vec2 d; float k; float ph;
      d = normalize(vec2(1.0, 0.3));   k = 6.28318 / 7.0;  ph = dot(d, p) * k + t * 1.1; g += d * 0.035 * k * cos(ph);
      d = normalize(vec2(-0.4, 1.0));  k = 6.28318 / 4.3;  ph = dot(d, p) * k + t * 1.5; g += d * 0.022 * k * cos(ph);
      d = normalize(vec2(0.7, -0.8));  k = 6.28318 / 2.6;  ph = dot(d, p) * k + t * 2.0; g += d * 0.012 * k * cos(ph);
      d = normalize(vec2(-0.9, -0.2)); k = 6.28318 / 1.4;  ph = dot(d, p) * k + t * 2.8; g += d * 0.006 * k * cos(ph);
      d = normalize(vec2(0.2, 0.9));   k = 6.28318 / 0.8;  ph = dot(d, p) * k + t * 3.6; g += d * 0.003 * k * cos(ph);
      d = normalize(vec2(-0.6, 0.6));  k = 6.28318 / 0.45; ph = dot(d, p) * k + t * 4.6; g += d * 0.0016 * k * cos(ph);
      // concentric rings from the bubble that popped
      float tp = uTime - uPopT;
      if (tp > 0.0) {
        vec2 rv = p - uPopPos.xz; float r = length(rv) + 1e-4;
        float front = r - 0.9 * tp;
        float env = exp(-front * front * 6.0) * exp(-tp * 0.7) * smoothstep(0.0, 0.08, tp) + exp(-r * 6.0) * exp(-tp * 3.0) * 0.6;
        g += (rv / r) * 0.012 * 22.0 * cos(front * 22.0) * env;
      }
      return g;
    }
    void main(){
      vec3 I = normalize(vWorld - cameraPosition);
      float dist = distance(vWorld, cameraPosition);
      vec2 gr = waveGrad(vWorld.xz, uTime);
      gr *= 0.15 + 0.85 * exp(-dist * 0.06);
      vec3 n = normalize(vec3(-gr.x, 1.0, -gr.y));
      vec3 col;
      if (uCamAbove < 0.5) {
        vec3 nn = -n;
        float cosi = abs(dot(I, nn));
        float sint = 1.333 * sqrt(max(1.0 - cosi * cosi, 0.0));
        vec3 mirror = waterFog(reflect(I, nn), uSurfaceY - 0.5) * 1.05;   // total internal reflection
        vec3 T = refract(I, nn, 1.333);
        if (dot(T, T) < 1e-4) T = normalize(vec3(I.x, 0.02, I.z));
        T = normalize(T);
        float F = 0.02 + 0.98 * pow(1.0 - clamp(sqrt(max(1.0 - sint * sint, 0.0)), 0.0, 1.0), 5.0);
        F = max(F, smoothstep(0.93, 1.0, sint));
        vec3 sky = skyColor(T) * vec3(1.1, 1.6, 1.75);
        col = mix(sky, mirror, F);
        col += vec3(1.0, 0.9, 0.7) * pow(max(dot(T, uSunAbove), 0.0), 120.0) * 3.0 * (1.0 - F);
        gl_FragColor = vec4(applyWater(col, vWorld), 1.0);
        return;
      }
      vec3 R = reflect(I, n); R.y = abs(R.y);
      float cosi = max(dot(-I, n), 0.0);
      float F = 0.02 + 0.98 * pow(1.0 - cosi, 5.0);
      vec3 sky = skyColor(R);
      vec3 body = vec3(0.004, 0.030, 0.042) + vec3(0.02, 0.09, 0.075) * pow(max(dot(normalize(vec3(I.x, 0.0, I.z)), normalize(vec3(uSunAbove.x, 0.0, uSunAbove.z))), 0.0), 4.0);
      col = mix(body, sky, F);
      float s = max(dot(R, uSunAbove), 0.0);
      col += vec3(1.0, 0.72, 0.40) * (pow(s, 600.0) * 9.0 + pow(s, 60.0) * 0.45);
      col = mix(col, skyColor(normalize(vec3(I.x, 0.015, I.z))), smoothstep(120.0, 1500.0, dist));
      gl_FragColor = vec4(min(col, vec3(12.0)), 1.0);
    }`, { uniforms: surfUniforms, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(g, m);
  mesh.position.y = SURFACE;
  mesh.frustumCulled = false;
  scene.add(mesh);
}

// spray from the pop
const sprayUniforms = { uPopPos: surfUniforms.uPopPos, uPopT: surfUniforms.uPopT, uPx: snowUniforms.uPx };
const spray = (() => {
  const N = 60;
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3), vel = new Float32Array(N * 4);
  for (let i = 0; i < N; i++) {
    const a = rr(0, 6.28), sp = rr(0.2, 1.0), up = rr(0.9, 2.6);
    vel.set([Math.cos(a) * sp, up, Math.sin(a) * sp, rr(0.004, 0.012)], i * 4);
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aVel', new THREE.BufferAttribute(vel, 4));
  const m = mat(`
    uniform vec3 uPopPos; uniform float uPopT; uniform float uPx;
    attribute vec4 aVel; varying float vA;
    void main(){
      float tp = max(uTime - uPopT, 0.0);
      vec3 p = uPopPos + vec3(aVel.x * tp, aVel.y * tp - 4.9 * tp * tp, aVel.z * tp);
      vA = step(0.0, uTime - uPopT) * step(uPopPos.y - 0.02, p.y) * exp(-tp * 1.5);
      vec4 mv = viewMatrix * vec4(p, 1.0);
      gl_Position = projectionMatrix * mv;
      gl_PointSize = clamp(uPx * aVel.w / max(-mv.z, 0.05), 1.0, 30.0);
    }`, `
    varying float vA;
    void main(){
      float d = length(gl_PointCoord - 0.5) * 2.0;
      float a = smoothstep(1.0, 0.2, d) * vA;
      gl_FragColor = vec4(vec3(1.6, 1.2, 0.85) * a, 1.0);
    }`, { uniforms: sprayUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const pts = new THREE.Points(g, m);
  pts.frustumCulled = false;
  scene.add(pts);
  return pts;
})();

// ───────────────────────────────────────────────────────── post-processing
class BubblePass extends Pass {
  constructor() {
    super();
    this.needsSwap = false;
    this.copyRT = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
    this.copy = new FullScreenQuad(new THREE.ShaderMaterial({
      uniforms: { tDiffuse: { value: null } },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: 'uniform sampler2D tDiffuse; varying vec2 vUv; void main(){ gl_FragColor = texture2D(tDiffuse, vUv); }',
      depthTest: false, depthWrite: false,
    }));
  }
  setSize(w, h) { this.copyRT.setSize(w, h); bubbleUniforms.uRes.value.set(w, h); }
  render(r, writeBuffer, readBuffer) {
    this.copy.material.uniforms.tDiffuse.value = readBuffer.texture;
    r.setRenderTarget(this.copyRT);
    this.copy.render(r);
    bubbleUniforms.tScene.value = this.copyRT.texture;
    const ac = r.autoClear;
    r.autoClear = false;
    r.setRenderTarget(readBuffer);
    r.render(bubbleScene, camera);
    r.autoClear = ac;
  }
}

const FinalShader = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uFade: { value: 1 }, uWash: { value: 0 }, uDrops: { value: 0 },
    uAspect: { value: 16 / 9 }, uBar: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) }, uWarm: { value: 0 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse; uniform float uTime; uniform float uFade; uniform float uWash; uniform float uDrops;
    uniform float uAspect; uniform float uBar; uniform vec2 uRes; uniform float uWarm;
    varying vec2 vUv;
    float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
    vec2 drops(vec2 uv, float scale, float seed){
      vec2 st = uv * vec2(uAspect, 1.0) * scale;
      st.y += uTime * 0.25 * (0.5 + h21(floor(st) + seed));
      vec2 id = floor(st); vec2 f = fract(st) - 0.5;
      vec2 c = (vec2(h21(id + seed + 3.1), h21(id + seed + 7.7)) - 0.5) * 0.5;
      float r = 0.10 + 0.22 * h21(id + seed + 1.3);
      vec2 d = f - c;
      float m = smoothstep(r, r * 0.8, length(d)) * step(0.5, h21(id + seed));
      return d / r * m;
    }
    void main(){
      vec2 uv = vUv;
      vec2 off = vec2(0.0);
      if (uDrops > 0.001) off = (drops(uv, 6.0, 0.0) * 0.022 + drops(uv, 13.0, 4.0) * 0.010) * uDrops;
      uv += off;
      uv += vec2(sin(uv.y * 28.0 + uTime * 9.0), cos(uv.x * 24.0 + uTime * 7.0)) * 0.012 * uWash;
      vec2 dc = uv - 0.5;
      float ca = 0.0018 + 0.006 * uWash + length(off) * 0.3;
      vec3 col;
      col.r = texture2D(tDiffuse, uv - dc * ca).r;
      col.g = texture2D(tDiffuse, uv).g;
      col.b = texture2D(tDiffuse, uv + dc * ca).b;
      float l = dot(col, vec3(0.299, 0.587, 0.114));
      col = mix(col, col * col * (3.0 - 2.0 * col), 0.22);
      col += mix(vec3(-0.008, 0.004, 0.012), vec3(0.016, 0.006, -0.010), smoothstep(0.1, 0.8, l)) * (1.0 + uWarm);
      float v = smoothstep(1.25, 0.25, length(dc * vec2(uAspect, 1.0) * 0.75));
      col *= mix(0.5, 1.0, v);
      col = mix(col, vec3(0.80, 0.93, 0.97), uWash * 0.65);
      float g = h21(vUv * uRes + fract(uTime * 37.0) * vec2(113.0, 71.0)) - 0.5;
      col += g * 0.03 * (1.0 - l * 0.5);
      col *= 1.0 - uFade;
      if (vUv.y < uBar || vUv.y > 1.0 - uBar) col = vec3(0.0);
      gl_FragColor = vec4(col, 1.0);
    }`,
};

const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4 }));
composer.addPass(new RenderPass(scene, camera));
const bubblePass = new BubblePass();
composer.addPass(bubblePass);
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.6, 0.55, 0.78);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const finalPass = new ShaderPass(FinalShader);
composer.addPass(finalPass);

// ───────────────────────────────────────────────────────── Pip, the reef fish
const PIP_SCALE = 0.2;
const PIP_VERT = /* glsl */ `
attribute float aPart; attribute vec3 aC;
uniform vec3 uPos; uniform vec3 uF; uniform vec3 uU; uniform vec3 uR; uniform float uScale;
uniform float uSwim; uniform float uAmp; uniform float uFlap; uniform float uBlink; uniform float uBendY;
varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal; varying float vPart;
void main(){
  vec3 p = position; vec3 n = normal;
  vLocal = position; vPart = aPart;
  if (aPart > 2.5 && aPart < 4.5) {           // pectoral fins paddle
    float side = sign(aC.z);
    float ang = (0.45 + 0.5 * sin(uFlap + side)) * side;
    vec3 q = p - aC; float c = cos(ang), s = sin(ang);
    q = vec3(q.x, q.y * c - q.z * s, q.y * s + q.z * c);
    p = aC + q; n = vec3(n.x, n.y * c - n.z * s, n.y * s + n.z * c);
  }
  if (aPart > 4.5) p.y = aC.y + (p.y - aC.y) * mix(0.06, 1.0, uBlink);   // blink
  float k = smoothstep(0.5, -1.3, p.x);
  p.z += sin(uSwim - p.x * 2.6) * uAmp * k - sin(uSwim) * uAmp * 0.22 * smoothstep(-0.2, 1.0, p.x);
  p.z += uBendY * p.x * p.x * 0.5;
  vec3 wp = uPos + (uF * p.x + uU * p.y + uR * p.z) * uScale;
  vWorld = wp;
  vN = normalize(uF * n.x + uU * n.y + uR * n.z);
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}`;
const PIP_FRAG = /* glsl */ `
uniform float uKey;
varying vec3 vWorld; varying vec3 vN; varying vec3 vLocal; varying float vPart;
void main(){
  vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
  vec3 Vd = normalize(cameraPosition - vWorld);
  vec3 L = vLocal;
  vec3 alb;
  if (vPart < 0.5) {
    vec3 yellow = vec3(1.0, 0.70, 0.05), orange = vec3(1.0, 0.36, 0.03), belly = vec3(1.0, 0.92, 0.62);
    alb = mix(yellow, orange, smoothstep(0.10, 0.48, L.y));
    alb = mix(alb, belly, smoothstep(-0.05, -0.40, L.y));
    float d = min(abs(L.x - 0.20), abs(L.x + 0.40));
    float band = smoothstep(0.075, 0.06, d);
    float edge = smoothstep(0.10, 0.085, d) - band;
    alb = mix(alb, vec3(0.98, 0.97, 0.94), band);
    alb = mix(alb, vec3(0.07, 0.04, 0.02), edge * 0.9);
    float mouth = smoothstep(0.05, 0.02, length(vec2(L.x - 0.965, (L.y + 0.07) * 2.2)));
    alb = mix(alb, vec3(0.30, 0.07, 0.03), mouth);
    float cheek = smoothstep(0.15, 0.0, length(vec2(L.x - 0.66, L.y + 0.12))) * smoothstep(0.1, 0.22, abs(L.z));
    alb = mix(alb, vec3(1.0, 0.42, 0.34), cheek * 0.5);
  } else if (vPart < 4.5) {
    float ray = 0.82 + 0.18 * sin(atan(L.y, L.x + 0.8) * 36.0);
    alb = vec3(1.0, 0.50, 0.07) * ray;
    if (vPart < 1.5) alb = mix(alb, vec3(1.0, 0.86, 0.45), smoothstep(0.42, 0.64, length(L.xy - vec2(-0.8, 0.0))));
  } else {
    alb = vec3(0.01, 0.01, 0.018);
  }
  vec3 col = litSurface(alb, n, vWorld, 0.35);
  // the cinematographer's warm key light keeps Pip's colours readable at depth
  vec3 keyDir = normalize(Vd + vec3(0.0, 0.9, 0.0));
  col += alb * vec3(1.0, 0.86, 0.66) * (0.25 + 0.75 * max(dot(n, keyDir), 0.0)) * uKey;
  float rim = pow(1.0 - max(dot(n, Vd), 0.0), 3.0);
  col += vec3(0.55, 0.85, 1.0) * rim * 0.3 * uKey;
  if (vPart > 0.5 && vPart < 4.5) col += alb * downwell(vWorld.y) * pow(max(dot(-Vd, uSunDir), 0.0), 2.0) * 0.5;
  if (vPart > 4.5) {
    vec3 H = normalize(Vd + normalize(vec3(-0.35, 1.0, 0.25)));
    col += vec3(1.0) * pow(max(dot(n, H), 0.0), 140.0) * 5.0;
    col += vec3(0.75, 0.9, 1.0) * pow(max(dot(n, normalize(Vd + vec3(0.25, -0.5, 0.0))), 0.0), 50.0) * 0.5;
  }
  gl_FragColor = vec4(applyWater(col, vWorld), 1.0);
}`;
function makePipGeometry() {
  const parts = [];
  const add = (geo, part, center) => {
    geo = geo.index ? geo.toNonIndexed() : geo;
    if (geo.attributes.uv) geo.deleteAttribute('uv');
    if (!geo.attributes.normal) geo.computeVertexNormals();
    const n = geo.attributes.position.count;
    geo.setAttribute('aPart', new THREE.Float32BufferAttribute(new Float32Array(n).fill(part), 1));
    const c = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) c.set(center, i * 3);
    geo.setAttribute('aC', new THREE.Float32BufferAttribute(c, 3));
    parts.push(geo);
  };
  const tris = (arr) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3)); g.computeVertexNormals(); return g; };
  const taper = (x) => (x < 0 ? 1 - 0.5 * Math.pow(-x, 1.7) : 1 - 0.32 * x * x);
  // body: a plump lemon shape, nose to +x
  const body = new THREE.SphereGeometry(1, 48, 32);
  body.rotateZ(-Math.PI / 2);
  const p = body.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i); p.setY(i, p.getY(i) * 0.58 * taper(x)); p.setZ(i, p.getZ(i) * 0.34 * taper(x)); }
  body.computeVertexNormals();
  add(body, 0, [0, 0, 0]);
  // tail fan with a scalloped edge
  const tail = [], base = [-0.78, 0, 0];
  for (let k = 0; k < 14; k++) {
    const a0 = lerp(2.25, 4.03, k / 14), a1 = lerp(2.25, 4.03, (k + 1) / 14);
    const r = (a) => 0.66 + 0.07 * Math.cos((a - Math.PI) * 7);
    tail.push(...base, base[0] + r(a0) * Math.cos(a0), r(a0) * Math.sin(a0), 0, base[0] + r(a1) * Math.cos(a1), r(a1) * Math.sin(a1), 0);
  }
  add(tris(tail), 1, base);
  // dorsal and belly fins
  const fin = (x0, x1, sign, h) => {
    const out = [];
    for (let k = 0; k < 10; k++) {
      const xa = lerp(x0, x1, k / 10), xb = lerp(x0, x1, (k + 1) / 10);
      const ya = sign * 0.55 * taper(xa) * 0.95, yb = sign * 0.55 * taper(xb) * 0.95;
      const ha = sign * h * Math.sin(Math.PI * (k / 10)) ** 0.7, hb = sign * h * Math.sin(Math.PI * ((k + 1) / 10)) ** 0.7;
      out.push(xa, ya, 0, xb, yb, 0, xb, yb + hb, 0, xa, ya, 0, xb, yb + hb, 0, xa, ya + ha, 0);
    }
    return tris(out);
  };
  add(fin(-0.55, 0.25, 1, 0.32), 2, [0, 0.5, 0]);
  add(fin(-0.55, -0.05, -1, 0.18), 2, [0, -0.5, 0]);
  // pectoral fins (paddle while hovering)
  for (const side of [1, -1]) {
    const c = [0.18, -0.12, side * 0.28], arr = [];
    for (let k = 0; k < 8; k++) {
      const a0 = lerp(0.15, 1.3, k / 8), a1 = lerp(0.15, 1.3, (k + 1) / 8);
      arr.push(...c, c[0] - 0.34 * Math.cos(a0), c[1] - 0.06, c[2] + side * 0.34 * Math.sin(a0) * 0.6,
        c[0] - 0.34 * Math.cos(a1), c[1] - 0.06, c[2] + side * 0.34 * Math.sin(a1) * 0.6);
    }
    add(tris(arr), side > 0 ? 3 : 4, c);
  }
  // big round eyes
  for (const side of [1, -1]) {
    const e = new THREE.SphereGeometry(0.165, 28, 18);
    e.translate(0.52, 0.12, side * 0.235);
    add(e, 5, [0.52, 0.12, side * 0.235]);
  }
  return mergeGeometries(parts);
}
const pipU = {
  uPos: { value: V(0, -50, 0) }, uF: { value: V(1, 0, 0) }, uU: { value: V(0, 1, 0) }, uR: { value: V(0, 0, 1) },
  uScale: { value: PIP_SCALE }, uSwim: { value: 0 }, uAmp: { value: 0.1 }, uFlap: { value: 0 }, uBlink: { value: 1 },
  uBendY: { value: 0 }, uKey: { value: 0.48 },
};
const pip = new THREE.Mesh(makePipGeometry(), mat(PIP_VERT, PIP_FRAG, { uniforms: pipU, side: THREE.DoubleSide }));
pip.frustumCulled = false;
under.add(pip);

// ───────────────────────────────────────────────────────── Pip's performance (story time)
function catmull(keys, t) {
  const n = keys.length;
  if (t <= keys[0][0]) return keys[0][1].clone();
  if (t >= keys[n - 1][0]) return keys[n - 1][1].clone();
  let i = 0;
  while (t > keys[i + 1][0]) i++;
  const p0 = keys[Math.max(i - 1, 0)][1], p1 = keys[i][1], p2 = keys[i + 1][1], p3 = keys[Math.min(i + 2, n - 1)][1];
  const u = (t - keys[i][0]) / (keys[i + 1][0] - keys[i][0]), u2 = u * u, u3 = u2 * u;
  const f = (a, b, c, d) => 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3);
  return V(f(p0.x, p1.x, p2.x, p3.x), f(p0.y, p1.y, p2.y, p3.y), f(p0.z, p1.z, p2.z, p3.z));
}
const smoothKeys = (keys, t) => {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 0; i < keys.length - 1; i++) if (t <= keys[i + 1][0]) return lerp(keys[i][1], keys[i + 1][1], smooth(keys[i][0], keys[i + 1][0], t));
  return keys[keys.length - 1][1];
};
const easeOutCubic = (x) => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
const HOVER_DIR = V(0.86, 0.12, 0.30).normalize();          // Pip waits on the camera's right of the crack
const PERP = V(-HOVER_DIR.z, 0, HOVER_DIR.x).normalize();    // side view of the pair, toward +z
const D_KEYS = [[10.8, 0.64], [11.8, 0.54], [12.5, 0.42], [13.3, 0.57], [14.6, 0.50], [15.45, 0.62], [15.9, 0.355]];
const hoverPos = (t) => Bc(t).addScaledVector(HOVER_DIR, smoothKeys(D_KEYS, t)).add(V(0, 0.018 * Math.sin(t * 2.1), 0));
const SWIM_IN = [[5.2, V(5.0, 0.9, 3.9)], [6.5, V(3.4, 0.6, 3.1)], [7.7, V(2.1, 0.45, 2.6)], [8.9, V(1.35, 0.38, 1.55)], [9.9, V(0.95, 0.30, 0.75)], [10.8, hoverPos(10.8)]];
const P_ST0 = hoverPos(15.9);
const AWAY = HOVER_DIR.clone().add(V(0, 0.35, 0.1)).normalize();
const startlePos = (t) => {
  const s = Math.max(0, t - 15.95);
  const j = t > 15.95 ? Math.exp(-s * 4) : 0;
  return P_ST0.clone().addScaledVector(AWAY, 0.62 * (1 - Math.exp(-s * 7))).add(V(Math.sin(t * 70) * 0.012 * j, Math.sin(t * 53) * 0.01 * j, 0));
};
const helix = (t, r = 0.85, w = 1.6) => { const a = w * t; return Bc(t).add(V(r * Math.cos(a), -0.15 + 0.05 * Math.sin(t * 1.9), r * Math.sin(a))); };
// the school that sweeps Pip away
const SCHOOL_B = { vel: V(2.1, 0.6, 0.9), r: 0.8, w: 0.5, ay: 0.3 };
const schoolOff = (t) => V(SCHOOL_B.r * Math.cos(SCHOOL_B.w * t), SCHOOL_B.ay * Math.sin(SCHOOL_B.w * 0.7 * t), SCHOOL_B.r * Math.sin(SCHOOL_B.w * t));
SCHOOL_B.c = Bc(27).add(V(0.35, 0.05, 0.25)).sub(SCHOOL_B.vel.clone().multiplyScalar(27)).sub(schoolOff(27));
const schoolB = (t) => SCHOOL_B.c.clone().addScaledVector(SCHOOL_B.vel, t).add(schoolOff(t));
makeSchool(200, 1.6, { c: SCHOOL_B.c, vel: SCHOOL_B.vel, r: SCHOOL_B.r, w: SCHOOL_B.w, ay: SCHOOL_B.ay });
const CARRY = V(-0.3, 0.05, 0.25);
const REL = schoolB(29.0).add(CARRY);
const searchBase = (t) => {
  const s = t - 29.0;
  return REL.clone().addScaledVector(SCHOOL_B.vel, 0.45 * (1 - Math.exp(-s * 2.2)) / 2.2 - 0.12 * s).add(V(0.22 * Math.sin(s * 1.3), 0.22 * s, 0.22 * (Math.cos(s * 1.3) - 1)));
};
const JELLY_SPOT = searchBase(32.0).add(V(0, 0.75, 0)).addScaledVector(V(SCHOOL_B.vel.x, 0, SCHOOL_B.vel.z).normalize(), 1.4);
const DODGE = searchBase(32.3).sub(JELLY_SPOT).setY(-0.15).normalize();
const searchPos = (t) => searchBase(t).addScaledVector(DODGE, 0.75 * easeOutCubic((t - 32.25) / 0.4));
{ // a small jellyfish drifts into Pip's way
  const ph = 0.4, t = 32.0;
  const off = V(Math.sin(t * 0.2 + ph) * 0.3, t * 0.22 + 0.25 * Math.sin((t * 0.42 + ph) * 6.283), Math.cos(t * 0.17 + ph) * 0.3);
  const b = JELLY_SPOT.clone().sub(off);
  addJelly(b.x, b.y, b.z, 0.3, ph);
}
const orbitPos = (t) => { const a = 0.5 + 4.0 * (t - 37.0); return Bc(t).add(V(0.55 * Math.cos(a), -0.05, 0.55 * Math.sin(a))); };
const S_DASH = searchPos(34.4);
const dashPos = (t) => S_DASH.clone().lerp(orbitPos(t), easeInOut(clamp((t - 34.4) / 2.6, 0, 1)));
const BS = bubbleAt(T_SURF).pos;
const CAP = V(BS.x + 0.55, SURFACE - 0.95, BS.z + 0.35);
const capPos = (t) => CAP.clone().add(V(0.12 * Math.sin(t * 0.8), 0.03 * Math.sin(t * 1.7), 0.12 * (Math.cos(t * 0.8) - 1)));
const hover2 = (t) => Bc(t).addScaledVector(HOVER_DIR, 0.6).add(V(0, 0.018 * Math.sin(t * 2.1), 0));
const CODA = [[54.0, V(2.6, 1.0, 2.4)], [55.2, V(1.7, 0.6, 1.5)], [56.4, V(0.95, 0.34, 0.62)], [57.4, hover2(57.4)], [60.5, hover2(60.5)]];
const UP = V(0, 1, 0);

function pipPose(t) {
  let pos, look = null, spin = 0;
  if (t < 10.8) { pos = catmull(SWIM_IN, t); if (t > 10.0) look = Bc(t); }
  else if (t < 15.95) { pos = hoverPos(t); look = Bc(t); }
  else if (t < 18.6) { pos = startlePos(t); look = Bc(t); spin = Math.PI * 2 * easeOutCubic((t - 16.0) / 0.6); }
  else if (t < 20.6) { pos = startlePos(t).lerp(helix(t), easeInOut(smooth(18.6, 20.6, t))); if (t < 19.4) look = Bc(t); }
  else if (t < 25.8) pos = helix(t);
  else if (t < 29.0) pos = helix(t).lerp(schoolB(t).add(CARRY), smooth(25.8, 26.9, t));
  else if (t < 34.4) {
    pos = searchPos(t);
    const a = 3.0 * (t - 29.0);
    look = t > 33.4 ? Bc(t) : pos.clone().add(V(Math.cos(a), 0.1, Math.sin(a)));
  } else if (t < 37.0) { pos = dashPos(t); if (t < 35.0) look = Bc(t); }
  else if (t < 38.6) pos = orbitPos(t);
  else if (t < 43.0) pos = orbitPos(t).lerp(helix(t, 0.7, 1.4), smooth(38.6, 39.6, t));
  else if (t < 54.0) {
    pos = helix(t, 0.7, 1.4).lerp(capPos(t), smooth(43.0, 44.8, t));
    look = t < 45.7 ? Bc(t) : pos.clone().add(V(0.15, 1.0, 0.05));
    spin = Math.PI * 2 * easeInOut(smooth(51.4, 52.6, t));
  } else { pos = catmull(CODA, t); if (t > 56.6) look = Bc(t); }
  return { pos, look, spin };
}
const pipPos = (t) => pipPose(t).pos;
const pipSpeed = (t) => pipPos(t + 0.1).distanceTo(pipPos(t - 0.1)) / 0.2;
// swim phase is the integral of the tail-beat frequency, tabulated once
const PHASE_DT = 0.05;
const PHASE = (() => {
  const n = Math.ceil(STORY / PHASE_DT) + 2, out = new Float32Array(n);
  for (let i = 1; i < n; i++) {
    const s = (i - 1) * PHASE_DT;
    out[i] = out[i - 1] + (1.8 + Math.min(pipSpeed(s) * 2.2, 7)) * PHASE_DT * Math.PI * 2;
  }
  return out;
})();
const pipPhase = (t) => { const x = clamp(t / PHASE_DT, 0, PHASE.length - 2), i = Math.floor(x); return lerp(PHASE[i], PHASE[i + 1], x - i); };
const BLINKS = [11.0, 13.75, 17.9, 31.2, 33.55, 51.0, 57.9, 59.4];
const blinkAt = (t) => BLINKS.reduce((o, b) => Math.min(o, 1 - smooth(b - 0.07, b, t) * (1 - smooth(b + 0.02, b + 0.11, t))), 1);
function headingAt(t) {
  const p = pipPose(t);
  const vel = pipPos(t + 0.12).sub(pipPos(t - 0.12)).divideScalar(0.24);
  const speed = vel.length();
  let f = speed > 1e-4 ? vel.normalize() : HOVER_DIR.clone().negate();
  if (p.look) f = p.look.clone().sub(p.pos).normalize().lerp(f, smooth(0.35, 1.1, speed)).normalize();
  let h = V(f.x, 0, f.z);
  if (h.length() < 0.05) h = HOVER_DIR.clone().negate().setY(0);
  h.normalize();
  const y = clamp(f.y, -0.7, 0.78);
  f = h.multiplyScalar(Math.sqrt(1 - y * y)).setY(y);
  if (p.spin) f.applyAxisAngle(UP, p.spin);
  return { p, f, speed };
}
function updatePip(t) {
  pip.visible = t >= 5.2;
  if (!pip.visible) return;
  const { p, f, speed } = headingAt(t);
  const f0 = headingAt(t - 0.15).f, f1 = headingAt(t + 0.15).f;
  const r = f.clone().cross(UP).normalize();
  const u = r.clone().cross(f).normalize();
  pipU.uPos.value.copy(p.pos);
  pipU.uF.value.copy(f); pipU.uR.value.copy(r); pipU.uU.value.copy(u);
  pipU.uSwim.value = pipPhase(t);
  const startle = Math.exp(-Math.pow((t - 16.15) / 0.25, 2));
  pipU.uAmp.value = 0.07 + Math.min(speed * 0.06, 0.2) + startle * 0.25;
  pipU.uFlap.value = t * Math.PI * 2 * (speed < 0.4 ? 3.4 : 2.0);
  pipU.uBlink.value = blinkAt(t);
  pipU.uBendY.value = clamp(f0.clone().cross(f1).y * 1.2, -0.5, 0.5);
}

// ───────────────────────────────────────────────────────── cameras (one rig per shot)
const C = (pos, tgt, fov, o = {}) => ({ pos, tgt, fov, roll: 0, up: V(0, 1, 0), near: 0.03, shake: 0.008, ...o });
const P = pipPos;
const mid = (t, k = 0.5) => Bc(t).lerp(P(t), k);
const SUN_H = V(SUN_ABOVE.x, 0, SUN_ABOVE.z).normalize();
const SUN_UH = SUN_H.clone();
const SCHOOL_H = SCHOOL_B.vel.clone().setY(0).normalize();
const SCHOOL_P = V(-SCHOOL_H.z, 0, SCHOOL_H.x);
const DOME = () => { const d = BS.clone(); d.y = SURFACE; return d; };
const CAMS = {
  // ── Ep.1 main film, 16:9
  M1: (t) => { const e = easeSine(t / 6); return C(S1A.clone().lerp(S1B, e), V(3, 4.0, -8).lerp(V(0, 0.7, 0), e), 46, { shake: 0.02, near: 0.05 }); },
  M2: (t) => {
    const lag = P(t - 0.3), dir = P(t + 0.2).sub(P(t - 0.2)).setY(0).normalize();
    const side = V(-dir.z, 0, dir.x); if (side.z < 0) side.negate();
    return C(lag.addScaledVector(side, 1.5).add(V(0, 0.22, 0)), P(t).addScaledVector(dir, 0.35), 40, { shake: 0.012 });
  },
  M3: (t, u) => { const a = -0.30 + 0.12 * u, d = 1.55 - 0.1 * u; return C(VENT.clone().add(V(Math.sin(a) * d, 0.22, Math.cos(a) * d)), mid(t, 0.45).add(V(0, 0.04, 0)), 36, { near: 0.02, shake: 0.005 }); },
  M4: (t) => { const m = mid(Math.min(t, 16.3)); return C(m.clone().addScaledVector(PERP, 1.2).add(V(0, 0.07, 0)), m, 34, { near: 0.02, shake: 0.004 }); },
  M5: (t) => C(P_ST0.clone().addScaledVector(AWAY, 0.62).add(V(-0.7, -0.42, 1.8)), P(t).add(V(0, 0.5, 0)), 54, { near: 0.02 }),
  M6: (t, u) => {
    const b = Bc(t), bl = Bc(t - 0.35), a = 1.0 - 0.4 * u;
    return C(V(b.x + Math.sin(a) * 2.4, bl.y - 0.6, b.z + Math.cos(a) * 2.4), mid(t, 0.4).add(V(0, 0.25, 0)), 38);
  },
  M7: (t) => C(Bc(25).add(V(2.6, -1.4 + (Bc(t).y - Bc(25).y) * 0.45, 3.2)), Bc(t).lerp(P(t), smooth(25.6, 28.5, t)), 50),
  M8: (t, u) => { const o = SCHOOL_H.clone().multiplyScalar(-1.15).addScaledVector(SCHOOL_P, 0.45).add(V(0, 0.28, 0)).applyAxisAngle(UP, 0.25 * u); return C(P(t).add(o), P(t).add(V(0, 0.05, 0)), 42); },
  M9: (t) => C(P(t).add(V(-0.35, -0.8, 0.8)), P(t).lerp(Bc(t), 0.5), 56),
  M10: (t, u) => {
    const be = Bc(42.8), b = Bc(t), a = 0.4 + 0.5 * u;
    return C(V(be.x + 0.45, SURFACE - 1.0, be.z + 0.35), V(b.x + 0.1, b.y - 2.2, b.z + 0.05), 56, { up: V(Math.sin(a), 0, -Math.cos(a)) });
  },
  M11: (t, u) => C(V(BS.x + 1.5 * (1 - 0.3 * u), SURFACE - 0.85 + 0.9 * smooth(45.25, T_CROSS, t), BS.z + 1.15 * (1 - 0.3 * u)),
    mid(t, 0.4).lerp(Bc(t), smooth(44.4, 45.6, t)).add(V(0, 0.1, 0)), 40, { near: 0.02 }),
  M12: (t) => {
    const D = DOME(), k = Math.pow(smooth(T_POP, 50.0, t), 1.4);
    const pos = D.clone().add(V(1.25, 0.24, 0.62).lerp(V(2.4, 2.6, 9.0), k));
    pos.y = Math.max(pos.y, SURFACE + swell(pos.x, pos.z, t) + 0.16);
    return C(pos, D.clone().add(V(0, 0.08, 0).lerp(V(-1.6, 1.35, -7.0), k)), 38 + 6 * k, { near: 0.02, shake: 0.01 });
  },
  M13: (t) => C(P(t).addScaledVector(SUN_UH, -0.7).add(V(0, -1.15, 0)), P(t).addScaledVector(SUN_UNDER, 1.4), 58),
  M14: (t, u) => { const a = -0.36, d = 1.45 - 0.15 * u; return C(VENT.clone().add(V(Math.sin(a) * d, 0.2, Math.cos(a) * d)), mid(t, 0.45).add(V(0, 0.2, 0)), 34, { near: 0.02, shake: 0.004 }); },
  // ── Short A, 9:16
  A1: (t) => C(VENT.clone().add(V(Math.sin(-0.25) * 1.75, 0.34, Math.cos(-0.25) * 1.75)), VENT.clone().add(V(0.3, 0.24, 0.1)).lerp(mid(t), 0.5), 52, { near: 0.02, shake: 0.005 }),
  A2: (t) => C(P(t).addScaledVector(HOVER_DIR, 0.45).addScaledVector(PERP, 0.22).add(V(0, 0.12, 0)), Bc(t), 50, { near: 0.02, shake: 0.004 }),
  A3: (t) => { const c = Bc(Math.min(t, 16.0)).addScaledVector(HOVER_DIR, R0 + 0.08); return C(c.clone().addScaledVector(PERP, 0.85).add(V(0, 0.04, 0)), c, 50, { near: 0.02, shake: 0.002 }); },
  A4: (t) => C(P_ST0.clone().addScaledVector(PERP, 1.1).add(V(0, 0.15, 0)), P(t).lerp(Bc(t), 0.35), 58, { near: 0.02 }),
  A5: (t) => C(mid(t).add(V(1.3, -0.7, 1.7)), mid(t).add(V(0, 0.15, 0)), 62),
  // ── Short B
  B1: (t) => C(mid(t).add(V(1.6, -0.3, 1.4)), mid(t), 58),
  B2: (t) => C(Bc(25).add(V(2.2, -2.2 + (Bc(t).y - Bc(25).y) * 0.5, 2.6)), Bc(t).lerp(P(t), smooth(25.8, 28.4, t)), 64),
  B3: (t) => C(P(t).add(SCHOOL_H.clone().multiplyScalar(-1.2).addScaledVector(SCHOOL_P, 0.35).add(V(0, 0.1, 0))), P(t).add(V(0, 0.2, 0)), 56),
  B4: (t) => C(P(t).add(V(0.5, -1.1, 1.1)), P(t).lerp(Bc(t), 0.45), 64),
  // ── Short C
  C1: (t) => C(mid(t).add(V(0.7, -2.0, 0.9)), mid(t).add(V(0, 1.6, 0)), 62),
  C2: (t) => C(V(BS.x + 1.0, SURFACE - 1.0 + 1.05 * smooth(45.25, T_CROSS, t), BS.z + 0.75), mid(t).lerp(Bc(t), smooth(44.4, 45.6, t)).add(V(0, 0.1, 0)), 58, { near: 0.02 }),
  C3: (t) => {
    // look across the light, not into it, so the film of the dome stays visible; turn to the sun after the pop
    const D = DOME(), k = Math.pow(smooth(T_POP, 49.2, t), 1.3);
    const side = SUN_H.clone().applyAxisAngle(UP, 0.65).negate();
    const pos = D.clone().addScaledVector(side, 1.35 + 2.2 * k).add(V(0, 0.28 + 0.7 * k, 0));
    pos.y = Math.max(pos.y, SURFACE + swell(pos.x, pos.z, t) + 0.16);
    const tgt = D.clone().add(V(0, 0.12, 0)).lerp(pos.clone().addScaledVector(SUN_H, 10).add(V(0, 0.4, 0)), 0.75 * k);
    return C(pos, tgt, 60, { near: 0.02, shake: 0.01 });
  },
  C4: (t) => C(P(t).addScaledVector(SUN_UH, -0.55).add(V(0, -1.1, 0)), P(t).addScaledVector(SUN_UNDER, 1.2), 64),
  C5: (t) => C(VENT.clone().add(V(Math.sin(-0.1) * 1.9, 0.36, Math.cos(-0.1) * 1.9)), mid(t, 0.85).add(V(0, 0.22, 0)), 52, { near: 0.02, shake: 0.004 }),
};

// ───────────────────────────────────────────────────────── edits (edits.json)
export const EDITS = await (await fetch(new URL('./edits.json', import.meta.url))).json();
for (const E of Object.values(EDITS)) E.duration = E.clips.reduce((s, c) => s + (c.to - c.from) / (c.speed || 1), 0);
let edit = EDITS[qs.get('edit')] || EDITS.main;
export const currentEdit = () => edit;

const capRoot = document.getElementById('captions');
let capEls = [];
function buildCaptions() {
  if (!capRoot) return;
  capRoot.replaceChildren();
  capRoot.dataset.kind = edit.kind;
  capEls = edit.captions.map((c) => {
    const el = document.createElement('div');
    el.className = `c-${c.style}`;
    const main = document.createElement('div');
    main.className = 'c-main';
    main.textContent = c.text;
    el.append(main);
    if (c.sub) { const s = document.createElement('div'); s.className = 'c-sub'; s.textContent = c.sub; el.append(s); }
    el.style.opacity = '0';
    capRoot.append(el);
    const a = c.a < 0 ? edit.duration + c.a : c.a;
    return { el, a, b: Math.min(c.b, edit.duration + 1), style: c.style };
  });
}
function updateCaptions(outT) {
  for (const c of capEls) {
    const fin = c.style === 'hook' ? 0.25 : 0.7;
    const o = (c.a <= 0 ? 1 : smooth(c.a, c.a + fin, outT)) * (1 - smooth(c.b - 0.5, c.b, outT));
    c.el.style.opacity = o.toFixed(3);
    c.el.style.transform = `translateY(${((1 - smooth(c.a, c.a + 1.0, outT)) * (c.a <= 0 ? 0 : 10)).toFixed(2)}px)`;
  }
}

export function setEdit(name) {
  edit = EDITS[name] || EDITS.main;
  buildCaptions();
  applyLetterbox();
  return edit;
}
export function locate(outT) {
  outT = clamp(outT, 0, edit.duration - 1e-4);
  let acc = 0;
  for (let i = 0; i < edit.clips.length; i++) {
    const c = edit.clips[i], sp = c.speed || 1, d = (c.to - c.from) / sp;
    if (outT < acc + d || i === edit.clips.length - 1) return { clip: c, index: i, story: c.from + (outT - acc) * sp, u: clamp((outT - acc) / d, 0, 1) };
    acc += d;
  }
}

// ───────────────────────────────────────────────────────── frame
const shake = (t, s) => V(
  Math.sin(t * 0.71) * 0.6 + Math.sin(t * 1.93 + 1.2) * 0.3,
  Math.sin(t * 0.83 + 2.1) * 0.6 + Math.sin(t * 2.31) * 0.25,
  Math.sin(t * 0.57 + 4.2) * 0.5).multiplyScalar(s);
let viewH = 1, lastClip = -1;
export function frame(outT) {
  const loc = locate(outT);
  const t = loc.story;
  U.uTime.value = t;

  // camera first: whether we are above or below the water decides how the world is drawn
  const c = CAMS[loc.clip.cam](t, loc.u);
  camera.fov = c.fov;
  camera.near = c.near;
  camera.updateProjectionMatrix();
  camera.position.copy(c.pos);
  camera.up.copy(c.up);
  camera.lookAt(c.tgt.clone().add(shake(t, c.shake)));
  camera.rotateZ(c.roll);
  camera.up.set(0, 1, 0);
  const surfY = SURFACE + swell(camera.position.x, camera.position.z, t);
  const above = camera.position.y > surfY;
  U.uCamAbove.value = above ? 1 : 0;
  under.visible = !above;
  smallBubbles.visible = !above;
  snowUniforms.uPx.value = viewH * renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));

  // the bubble
  const b = bubbleAt(t);
  hero.visible = b.visible;
  hero.position.copy(b.pos);
  hero.quaternion.copy(b.tilt);
  hero.scale.setScalar(b.R);
  bubbleUniforms.uWob.value = b.wob;
  bubbleUniforms.uNeck.value = b.neck;
  bubbleUniforms.uFlat.value = b.flat;
  bubbleUniforms.uBT.value = t;
  heroMat.uniforms.uAboveMode.value = above ? 1 : 0;
  heroMat.uniforms.uPop.value = smooth(T_POP, T_POP + 0.1, t);
  surfUniforms.uPopPos.value.copy(BS).setY(SURFACE);
  surfUniforms.uPopT.value = T_POP;

  updateJellies(t);
  updatePip(t);
  RAY_SPECIAL.value = smooth(33.4, 34.6, t) * (1 - smooth(38.5, 40.5, t));

  // grade & transitions
  const fadeIn = edit.fadeIn > 0 ? 1 - smooth(0, edit.fadeIn, outT) : 0;
  const fadeOut = smooth(edit.duration - edit.fadeOut, edit.duration, outT);
  finalPass.uniforms.uFade.value = Math.max(fadeIn, fadeOut);
  finalPass.uniforms.uWash.value = Math.exp(-Math.pow((camera.position.y - surfY) / 0.07, 2));
  finalPass.uniforms.uDrops.value = above && t > T_CROSS ? Math.exp(-(t - T_CROSS) * 1.1) : 0;
  finalPass.uniforms.uTime.value = t;
  finalPass.uniforms.uWarm.value = above ? 1.5 : 0;
  renderer.toneMappingExposure = above ? 0.78 : 1.05;
  bloom.strength = above ? 0.32 : 0.6;
  bloom.threshold = above ? 0.95 : 0.78;
  bloom.radius = above ? 0.35 : 0.55;

  updateCaptions(outT);
  if (loc.index !== lastClip) { lastClip = loc.index; document.dispatchEvent(new CustomEvent('pip:clip', { detail: loc })); }
  composer.render();
  return loc;
}

// ───────────────────────────────────────────────────────── sizing
function applyLetterbox() {
  const aspect = camera.aspect;
  const bar = edit.letterbox && aspect >= 1.3 ? Math.max(0, (1 - aspect / 2.39) / 2) : 0;
  finalPass.uniforms.uBar.value = bar;
  document.documentElement.style.setProperty('--bar', `${(bar * 100).toFixed(3)}%`);
}
export function resize(w, h, pixelRatio) {
  viewH = h;
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(w, h, false);
  composer.setPixelRatio(pixelRatio);
  composer.setSize(w, h);
  camera.aspect = w / h;
  bubbleUniforms.uAspect.value = w / h;
  finalPass.uniforms.uAspect.value = w / h;
  finalPass.uniforms.uRes.value.set(w * pixelRatio, h * pixelRatio);
  applyLetterbox();
}

export const ready = (async () => {
  try { await document.fonts.ready; } catch { /* fonts are optional */ }
  setEdit(edit === EDITS.main ? 'main' : qs.get('edit'));
  if (RENDER_MODE) resize(window.innerWidth, window.innerHeight, 1);
  frame(0);
  return true;
})();

if (RENDER_MODE) window.__pip = { ready, frame, EDITS, setEdit, currentEdit };
