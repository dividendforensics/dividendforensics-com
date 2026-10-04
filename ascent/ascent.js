// ASCENT — a 30-second journey of one air bubble from the seafloor to the light.
// Every frame is a pure function of time t (0..30 s), so the film can be played
// live in the browser or rendered frame-by-frame into a video (see tools/render.mjs).

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

export const DURATION = 30;
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

// ───────────────────────────────────────────────────────── bubble path
const T_FORM = 4.9, T_DETACH = 8.3, T_SURF = 26.45, T_CROSS = 26.85, T_POP = 27.75;
const R0 = 0.15, R1 = 0.25;
const K_ACC = 1.15;
const Y_DETACH = VENT.y + R0 * (0.78 + 0.35);
const Y_TOUCH = SURFACE - R1 * 0.95;
const T_RISE = T_SURF - T_DETACH;
const VMAX = (Y_TOUCH - Y_DETACH) / (T_RISE - (1 - Math.exp(-K_ACC * T_RISE)) / K_ACC);
const riseY = (tau) => Y_DETACH + VMAX * (tau - (1 - Math.exp(-K_ACC * tau)) / K_ACC);
function zig(tau) {
  const A = 0.30 * (1 - Math.exp(-tau / 1.6)), w = 2.3;
  return [VENT.x + A * Math.sin(w * tau) + 0.06 * tau, VENT.z + A * 0.7 * (Math.cos(w * tau * 0.93) - 1) - 0.02 * tau];
}
function bubbleAt(t) {
  const s = { visible: true, pos: V(0, 0, 0), R: R0, neck: 0, wob: 0.04, flat: 0, tilt: new THREE.Quaternion(), surfaced: 0 };
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
    const u = t - T_SURF;
    const k = smooth(0, 0.45, u);
    y = lerp(Y_TOUCH, SURFACE - R1 * 0.12 + swell(x, z, t), k) + 0.025 * Math.exp(-u * 3) * Math.sin(u * 18);
    s.flat = lerp(s.flat, 0.36, k);
    s.wob = 0.03 + 0.1 * Math.exp(-u * 4);
    s.surfaced = k;
  }
  s.pos.set(x, y, z);
  // flatten across the direction of travel (rising bubbles are oblate and tilt as they zig-zag)
  if (t < T_SURF) {
    const [x2, z2] = zig(tau + 0.05);
    const vel = V(x2 - x, riseY(tau + 0.05) - y, z2 - z).normalize();
    s.tilt.setFromUnitVectors(V(0, 1, 0), V(0, 1, 0).lerp(vel, 0.7).normalize());
  }
  return s;
}

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
// … and one that sweeps over the bubble as it climbs toward the light
{
  const vel = V(2.4, 0, 1.0);
  const c = bubbleAt(16).pos.clone().add(V(0, 5.5, 0)).sub(vel.clone().multiplyScalar(16));
  makeSchool(220, 1.9, { c, vel, r: 0.8, w: 0.5, ay: 0.3 });
}

// ───────────────────────────────────────────────────────── jellyfish
const jellies = [];
{
  const bellGeo = new THREE.SphereGeometry(1, 48, 18, 0, Math.PI * 2, 0, Math.PI * 0.56);
  const spots = [
    [3.4, 21.5, -4.6, 0.75, 0.0], [-5.2, 25.5, -2.4, 1.0, 1.3], [2.3, 28.5, 5.2, 0.55, 2.2],
    [-10, 18.5, -9.5, 1.5, 0.6], [7.5, 31, -1.5, 0.8, 3.1],
  ];
  for (const [x, y, z, s, ph] of spots) {
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
        gl_FragColor = vec4(c * waterFade(vWorld), 1.0);
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
}
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
{
  const base = new THREE.PlaneGeometry(1, 1, 1, 10);
  const g = new THREE.InstancedBufferGeometry().copy(base);
  const N = 30;
  const aRay = new Float32Array(N * 4), aLen = new Float32Array(N);
  const hd = V(-SUN_UNDER.x, 0, -SUN_UNDER.z).normalize();
  const reach = SURFACE / SUN_UNDER.y;
  for (let i = 0; i < N; i++) {
    const cx = -hd.x * reach * 0.5 * SUN_UNDER.y * 1.2, cz = -hd.z * reach * 0.5 * SUN_UNDER.y * 1.2;
    aRay.set([cx + rr(-30, 30), cz + rr(-30, 30), rr(1.2, 5.0), rnd()], i * 4);
    aLen[i] = reach * rr(0.8, 1.05);
  }
  g.instanceCount = N;
  g.setAttribute('aRay', new THREE.InstancedBufferAttribute(aRay, 4));
  g.setAttribute('aLen', new THREE.InstancedBufferAttribute(aLen, 1));
  const m = mat(`
    attribute vec4 aRay; attribute float aLen;
    varying vec2 vUv2; varying float vSeed; varying float vCamD; varying vec3 vWorld;
    void main(){
      vUv2 = uv; vSeed = aRay.w;
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
    uniform float uRayStrength;
    varying vec2 vUv2; varying float vSeed; varying float vCamD; varying vec3 vWorld;
    void main(){
      float edge = pow(max(1.0 - abs(vUv2.x - 0.5) * 2.0, 0.0), 1.8);
      float streak = 0.45 + 0.55 * vnoise(vec2(vUv2.x * 7.0 + vSeed * 13.0, uTime * 0.25 + vSeed * 5.0));
      float flick = 0.6 + 0.4 * sin(uTime * 0.9 + vSeed * 20.0);
      float fadeBot = smoothstep(0.0, 0.75, vUv2.y);
      float fadeTop = smoothstep(1.0, 0.97, vUv2.y);
      float nearF = smoothstep(0.8, 7.0, vCamD);
      float I = edge * streak * flick * fadeBot * fadeTop * nearF * exp(-vCamD * 0.016);
      gl_FragColor = vec4(vec3(0.55, 0.85, 0.78) * I * uRayStrength, 1.0);
    }`, { uniforms: { uRayStrength: { value: 0.11 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
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

// ───────────────────────────────────────────────────────── camera choreography
const shake = (t, s) => V(
  Math.sin(t * 0.71) * 0.6 + Math.sin(t * 1.93 + 1.2) * 0.3,
  Math.sin(t * 0.83 + 2.1) * 0.6 + Math.sin(t * 2.31) * 0.25,
  Math.sin(t * 0.57 + 4.2) * 0.5).multiplyScalar(s);
const B = (t) => bubbleAt(t).pos;

export const SHOTS = [
  { name: 'The reef', start: 0 },
  { name: 'A breath is born', start: T_FORM },
  { name: 'Through the kelp', start: 9.7 },
  { name: 'Toward the light', start: 13.9 },
  { name: 'Orbit', start: 18.3 },
  { name: 'Below the mirror', start: 22.7 },
  { name: 'Surface', start: 25.4 },
  { name: 'Open air', start: T_CROSS },
];

function cameraAt(t) {
  const c = { pos: V(0, 0, 0), tgt: V(0, 0, 0), fov: 45, roll: 0, up: V(0, 1, 0), near: 0.05, shake: 0.012 };
  if (t < T_FORM) {
    const e = easeSine(t / T_FORM);
    c.pos.lerpVectors(S1A, S1B, e);
    c.tgt.lerpVectors(V(3, 4.0, -8), V(0, 0.7, 0), e);
    c.fov = 46; c.shake = 0.02;
  } else if (t < 9.7) {
    const u = (t - T_FORM) / (9.7 - T_FORM);
    const ang = -0.55 + 0.32 * u, dist = 1.02 - 0.1 * u;
    const b = bubbleAt(t);
    c.pos.set(VENT.x + Math.sin(ang) * dist, VENT.y + 0.13 + 0.06 * u, VENT.z + Math.cos(ang) * dist);
    const by = b.visible ? b.pos.y : VENT.y + 0.1;
    c.pos.y += Math.max(0, by - 0.45) * 0.3;
    c.tgt.set(b.pos.x, VENT.y + 0.17 + Math.max(0, by - VENT.y - 0.17) * 0.55, b.pos.z);
    c.fov = 30; c.near = 0.02; c.shake = 0.006;
  } else if (t < 13.9) {
    const u = (t - 9.7) / 4.2;
    const ang = 0.95 - 0.55 * u, dist = 3.3;
    const b = B(t), bl = B(t - 0.35);
    c.pos.set(b.x + Math.sin(ang) * dist, bl.y - 0.9 + 0.3 * u, b.z + Math.cos(ang) * dist);
    c.tgt.copy(b).add(V(0, 0.45, 0));
    c.fov = 34;
  } else if (t < 18.3) {
    const u = (t - 13.9) / 4.4;
    const b0 = B(13.9), b = B(t);
    c.pos.set(b0.x + 0.9, b0.y - 2.2 + (b.y - b0.y) * 0.55, b0.z + 1.2);
    c.tgt.copy(b).add(V(-0.25, 0.6, -0.35));
    c.roll = 0.05 + 0.3 * easeSine(u);
    c.fov = 52;
  } else if (t < 22.7) {
    const u = (t - 18.3) / 4.4;
    const b = B(t);
    const ang = 2.2 + 1.7 * easeSine(u) + 0.25 * u, r = 1.35 - 0.25 * u;
    c.pos.set(b.x + Math.sin(ang) * r, b.y + 0.18 - 0.35 * u, b.z + Math.cos(ang) * r);
    c.tgt.copy(b);
    c.fov = 36; c.shake = 0.008;
  } else if (t < 25.4) {
    const u = (t - 22.7) / 2.7;
    const be = B(25.4), b = B(t);
    c.pos.set(be.x + 0.5, SURFACE - 1.1 - 0.15 * u, be.z + 0.35);
    c.tgt.set(b.x + 0.12, b.y - 2.5, b.z + 0.08);
    const a = 0.4 + 0.5 * u;
    c.up.set(Math.sin(a), 0, -Math.cos(a));
    c.fov = 56; c.shake = 0.006;
  } else if (t < T_CROSS) {
    const u = (t - 25.4) / (T_CROSS - 25.4);
    const bs = B(T_SURF), b = B(t);
    c.pos.set(bs.x + 1.5 * (1 - 0.3 * u), SURFACE - 0.75 + 0.8 * smooth(25.95, T_CROSS, t), bs.z + 1.1 * (1 - 0.3 * u));
    c.tgt.copy(b).add(V(0, 0.12, 0));
    c.fov = 40; c.near = 0.02; c.shake = 0.008;
  } else {
    const D = B(T_SURF).clone(); D.y = SURFACE;
    const k = Math.pow(smooth(27.75, 30.0, t), 1.4);
    c.pos.copy(D).add(V(1.25, 0.24, 0.62).lerp(V(2.4, 2.6, 9.0), k));
    c.pos.y = Math.max(c.pos.y, SURFACE + swell(c.pos.x, c.pos.z, t) + 0.16);
    c.tgt.copy(D).add(V(0, 0.08, 0).lerp(V(-1.6, 1.35, -7.0), k));
    c.fov = 38 + 6 * k; c.near = 0.02; c.shake = 0.01;
  }
  return c;
}

// ───────────────────────────────────────────────────────── captions
const CAPTIONS = [
  { el: 'cap-1', a: 0.9, b: 4.3 },
  { el: 'cap-2', a: 5.6, b: 8.6 },
  { el: 'cap-3', a: 22.95, b: 25.2 },
  { el: 'title', a: 28.15, b: 31 },
];
const capEls = CAPTIONS.map((c) => ({ ...c, node: document.getElementById(c.el) }));

// ───────────────────────────────────────────────────────── frame
let viewW = 1, viewH = 1, lastShot = -1;
export function frame(t) {
  t = clamp(t, 0, DURATION);
  U.uTime.value = t;
  const above = t >= T_CROSS;
  U.uCamAbove.value = above ? 1 : 0;
  under.visible = !above;
  smallBubbles.visible = !above;

  // bubble
  const b = bubbleAt(t);
  hero.visible = b.visible && !(t > T_POP + 0.12);
  hero.position.copy(b.pos);
  hero.quaternion.copy(b.tilt);
  hero.scale.setScalar(b.R);
  bubbleUniforms.uWob.value = b.wob;
  bubbleUniforms.uNeck.value = b.neck;
  bubbleUniforms.uFlat.value = b.flat;
  bubbleUniforms.uBT.value = t;
  heroMat.uniforms.uAboveMode.value = above ? 1 : 0;
  heroMat.uniforms.uPop.value = smooth(T_POP, T_POP + 0.1, t);
  surfUniforms.uPopPos.value.copy(b.pos).setY(SURFACE);
  surfUniforms.uPopT.value = T_POP;

  updateJellies(t);

  // camera
  const c = cameraAt(t);
  camera.fov = c.fov;
  camera.near = c.near;
  camera.updateProjectionMatrix();
  camera.position.copy(c.pos);
  const sh = shake(t, c.shake);
  camera.up.copy(c.up);
  camera.lookAt(c.tgt.clone().add(sh));
  camera.rotateZ(c.roll);
  camera.up.set(0, 1, 0);
  snowUniforms.uPx.value = viewH * renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));

  // grade & transitions
  const fadeIn = 1 - smooth(0.0, 1.9, t);
  const fadeOut = smooth(29.25, 30.0, t);
  finalPass.uniforms.uFade.value = Math.max(fadeIn, fadeOut);
  finalPass.uniforms.uWash.value = Math.exp(-Math.pow((t - T_CROSS) / 0.11, 2));
  finalPass.uniforms.uDrops.value = t > T_CROSS ? Math.exp(-(t - T_CROSS) * 1.1) : 0;
  finalPass.uniforms.uTime.value = t;
  finalPass.uniforms.uWarm.value = above ? 1.5 : 0;
  renderer.toneMappingExposure = above ? 0.78 : 1.05;
  bloom.strength = above ? 0.32 : 0.6;
  bloom.threshold = above ? 0.95 : 0.78;
  bloom.radius = above ? 0.35 : 0.55;

  for (const c2 of capEls) {
    if (!c2.node) continue;
    const o = smooth(c2.a, c2.a + 0.7, t) * (1 - smooth(c2.b - 0.7, c2.b, t)) * (1 - fadeOut * 0.0);
    c2.node.style.opacity = o.toFixed(3);
    c2.node.style.transform = `translateY(${((1 - smooth(c2.a, c2.a + 1.2, t)) * 8).toFixed(2)}px)`;
  }
  const shot = SHOTS.reduce((i, s, k) => (t >= s.start ? k : i), 0);
  if (shot !== lastShot) { lastShot = shot; document.dispatchEvent(new CustomEvent('ascent:shot', { detail: shot })); }

  composer.render();
}

// ───────────────────────────────────────────────────────── sizing
export function resize(w, h, pixelRatio) {
  viewW = w; viewH = h;
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(w, h, false);
  composer.setPixelRatio(pixelRatio);
  composer.setSize(w, h);
  const aspect = w / h;
  camera.aspect = aspect;
  bubbleUniforms.uAspect.value = aspect;
  finalPass.uniforms.uAspect.value = aspect;
  finalPass.uniforms.uRes.value.set(w * pixelRatio, h * pixelRatio);
  // 2.39:1 letterbox when the screen is wide enough to carry it
  const bar = aspect >= 1.3 ? Math.max(0, (1 - aspect / 2.39) / 2) : 0;
  finalPass.uniforms.uBar.value = bar;
  document.documentElement.style.setProperty('--bar', `${(bar * 100).toFixed(3)}%`);
}

export const ready = (async () => {
  try { await document.fonts.ready; } catch { /* fonts are optional */ }
  resize(window.innerWidth, window.innerHeight, RENDER_MODE ? 1 : Math.min(window.devicePixelRatio || 1, 1.5));
  frame(0.0);
  return true;
})();

if (RENDER_MODE) window.__ascent = { ready, frame, DURATION, debug: { renderer, bloom, finalPass, scene, under, U } };
