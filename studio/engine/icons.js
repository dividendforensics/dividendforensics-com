// Hand-drawn food icons for dishes with no accurate emoji (gimbap, tteokbokki, jjajangmyeon,
// malatang, jokbal). Each painter returns a 256x256 canvas; configs refer to them as "@name".
const S = 256, C = 128;
function mk() { const c = document.createElement('canvas'); c.width = c.height = S; return [c, c.getContext('2d')]; }
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function circle(x, cx, cy, r, fill) { x.beginPath(); x.arc(cx, cy, r, 0, Math.PI * 2); x.fillStyle = fill; x.fill(); }
function radial(x, cx, cy, r, stops) { const g = x.createRadialGradient(cx, cy, 0, cx, cy, r); stops.forEach(([o, c]) => g.addColorStop(o, c)); return g; }
function gloss(x, cx, cy, rx, ry, a = 0.55) { x.save(); x.globalAlpha = a; x.fillStyle = '#fff'; x.beginPath(); x.ellipse(cx, cy, rx, ry, -0.5, 0, Math.PI * 2); x.fill(); x.restore(); }
function bowl(x, rim, inner) {
  circle(x, C, C + 4, 124, 'rgba(0,0,0,.35)');
  circle(x, C, C, 122, radial(x, C - 30, C - 30, 160, [[0, '#ffffff'], [1, '#cfcfd6']]));
  if (rim) { x.strokeStyle = rim; x.lineWidth = 5; x.beginPath(); x.arc(C, C, 113, 0, Math.PI * 2); x.stroke(); }
  circle(x, C, C, 104, inner);
}

const PAINT = {
  gimbap() { // one slice seen from the cut side: seaweed ring, rice, colored fillings
    const [c, x] = mk(), R = rng(7);
    circle(x, C, C + 4, 122, 'rgba(0,0,0,.35)');
    circle(x, C, C, 120, radial(x, C - 30, C - 40, 170, [[0, '#2f4636'], [1, '#0d1610']]));
    circle(x, C, C, 108, '#f6f3ea');
    for (let i = 0; i < 320; i++) { const a = R() * 6.283, d = 74 + R() * 32;
      x.fillStyle = R() < 0.5 ? '#ffffff' : '#e2dccd'; x.beginPath();
      x.ellipse(C + Math.cos(a) * d, C + Math.sin(a) * d, 6, 3.5, R() * 3, 0, 6.283); x.fill(); }
    const fill = [['#ffd23f', -24, -28, 30, 26], ['#ff7a1a', 10, -30, 24, 30], ['#2f8f2f', -38, 2, 26, 30],
      ['#ff9fb0', -6, -2, 32, 28], ['#8d5a2b', 28, 2, 24, 30], ['#ffe9a8', -18, 30, 34, 22], ['#4caf50', 18, 30, 24, 22]];
    for (const [col, dx0, dy0, w0, h0] of fill) { const k = 1.55, dx = dx0 * k, dy = dy0 * k, w = w0 * k, h = h0 * k; x.fillStyle = col; x.strokeStyle = 'rgba(0,0,0,.25)'; x.lineWidth = 2;
      x.beginPath(); x.roundRect(C + dx - w / 2, C + dy - h / 2, w, h, 7); x.fill(); x.stroke(); }
    x.fillStyle = '#f2e6c4'; for (let i = 0; i < 26; i++) { const a = R() * 6.283, d = 109 + R() * 8;
      x.beginPath(); x.ellipse(C + Math.cos(a) * d, C + Math.sin(a) * d, 3, 1.6, a, 0, 6.283); x.fill(); }
    gloss(x, C - 60, C - 70, 26, 10, 0.35);
    return c;
  },
  tteokbokki() { // rice-cake tubes in glossy red sauce on a plate
    const [c, x] = mk(), R = rng(11);
    bowl(x, null, radial(x, C - 20, C - 20, 120, [[0, '#ff6a3d'], [0.7, '#e0331a'], [1, '#b0200d']]));
    const cakes = [[-40, -35, 0.5], [10, -48, -0.3], [45, -10, 1.2], [-50, 15, -0.9], [-5, 5, 0.2], [30, 40, -0.6], [-25, 50, 0.9]];
    for (const [dx, dy, a] of cakes) { x.save(); x.translate(C + dx, C + dy); x.rotate(a);
      x.fillStyle = 'rgba(80,0,0,.35)'; x.beginPath(); x.roundRect(-37, -11, 76, 28, 14); x.fill();
      const g = x.createLinearGradient(0, -14, 0, 14); g.addColorStop(0, '#fff3ea'); g.addColorStop(0.55, '#f6c9b4'); g.addColorStop(1, '#e8735a');
      x.fillStyle = g; x.beginPath(); x.roundRect(-38, -14, 76, 28, 14); x.fill();
      x.fillStyle = 'rgba(230,40,20,.45)'; x.beginPath(); x.roundRect(-38, 2, 76, 12, 6); x.fill();
      x.fillStyle = 'rgba(255,255,255,.7)'; x.beginPath(); x.roundRect(-28, -10, 46, 5, 3); x.fill(); x.restore(); }
    x.fillStyle = '#e9b46a'; x.strokeStyle = '#b97a32'; x.lineWidth = 3;
    for (const [dx, dy, a] of [[40, -55, 0.4], [-60, -10, 2.2]]) { x.save(); x.translate(C + dx, C + dy); x.rotate(a);
      x.beginPath(); x.moveTo(-22, 14); x.lineTo(22, 14); x.lineTo(0, -22); x.closePath(); x.fill(); x.stroke(); x.restore(); }
    x.strokeStyle = '#3fae49'; x.lineWidth = 4;
    for (let i = 0; i < 8; i++) { x.beginPath(); x.arc(C + (R() - .5) * 150, C + (R() - .5) * 150, 6, 0, 6.283); x.stroke(); }
    for (let i = 0; i < 7; i++) gloss(x, C + (R() - .5) * 150, C + (R() - .5) * 150, 9, 4, 0.4);
    return c;
  },
  jjajang() { // yellow noodles under black-bean sauce, cucumber strips on top
    const [c, x] = mk(), R = rng(5);
    bowl(x, '#c62828', '#e8c25a');
    x.lineCap = 'round';
    for (let i = 0; i < 90; i++) { const a = R() * 6.283, d = R() * 80;
      x.strokeStyle = R() < 0.5 ? '#f6d977' : '#d9ae3f'; x.lineWidth = 6; x.beginPath();
      x.arc(C + Math.cos(a) * d, C + Math.sin(a) * d, 14 + R() * 20, R() * 6.283, R() * 6.283 + 1.6); x.stroke(); }
    x.fillStyle = '#2a170c';
    for (const [dx, dy, r] of [[0, 0, 52], [-28, -16, 34], [26, -20, 32], [-22, 26, 30], [24, 24, 32]]) {
      x.beginPath(); x.arc(C + dx, C + dy, r, 0, 6.283); x.fill(); }
    for (let i = 0; i < 16; i++) { const a = R() * 6.283, d = R() * 48;
      x.fillStyle = R() < 0.5 ? '#c9965c' : '#e8dcc0'; x.beginPath(); x.roundRect(C + Math.cos(a) * d - 6, C + Math.sin(a) * d - 6, 12, 12, 3); x.fill(); }
    for (let i = 0; i < 5; i++) gloss(x, C - 30 + R() * 50, C - 30 + R() * 50, 10, 4, 0.3);
    x.lineWidth = 6; for (let i = 0; i < 9; i++) { const ax = C - 30 + R() * 50, ay = C - 50 + R() * 20, a = 0.9 + R() * 0.6;
      x.strokeStyle = '#2e7d32'; x.beginPath(); x.moveTo(ax, ay); x.lineTo(ax + Math.cos(a) * 46, ay + Math.sin(a) * 46); x.stroke();
      x.strokeStyle = '#a5d66a'; x.lineWidth = 3; x.beginPath(); x.moveTo(ax, ay); x.lineTo(ax + Math.cos(a) * 46, ay + Math.sin(a) * 46); x.stroke(); x.lineWidth = 6; }
    return c;
  },
  malatang() { // red chili-oil soup with tofu, bok choy, lotus root, dried chilies
    const [c, x] = mk(), R = rng(9);
    bowl(x, '#8b8b8b', radial(x, C - 20, C - 20, 120, [[0, '#ff5a1f'], [0.75, '#c8260d'], [1, '#8f1407']]));
    x.fillStyle = 'rgba(255,170,40,.55)'; for (let i = 0; i < 40; i++) { x.beginPath(); x.arc(C + (R() - .5) * 180, C + (R() - .5) * 180, 3 + R() * 6, 0, 6.283); x.fill(); }
    x.save(); x.translate(C - 40, C - 30); x.rotate(-0.6); x.fillStyle = '#3c9a3c'; x.beginPath(); x.ellipse(0, 0, 44, 24, 0, 0, 6.283); x.fill();
    x.fillStyle = '#d9f2c4'; x.beginPath(); x.ellipse(18, 0, 24, 9, 0, 0, 6.283); x.fill(); x.restore();
    for (const [dx, dy] of [[30, -40], [48, -4], [22, 20]]) { x.fillStyle = '#f5e7c8'; x.strokeStyle = '#d6c29a'; x.lineWidth = 2;
      x.beginPath(); x.roundRect(C + dx - 16, C + dy - 16, 32, 32, 5); x.fill(); x.stroke(); }
    circle(x, C - 30, C + 42, 26, '#efe2c8'); for (const [dx, dy] of [[0, 0], [-11, -9], [11, -9], [-11, 9], [11, 9]]) circle(x, C - 30 + dx, C + 42 + dy, 4.5, '#c8573a');
    circle(x, C + 30, C + 60, 15, '#8a4a2a');
    x.fillStyle = '#b30000'; x.strokeStyle = '#5a0000'; x.lineWidth = 2;
    for (const [dx, dy, a] of [[-10, -62, 0.3], [62, 34, -1.1], [-66, 32, 1.3], [8, 64, 0.1]]) { x.save(); x.translate(C + dx, C + dy); x.rotate(a);
      x.beginPath(); x.ellipse(0, 0, 18, 6, 0, 0, 6.283); x.fill(); x.stroke(); x.restore(); }
    for (let i = 0; i < 6; i++) gloss(x, C + (R() - .5) * 150, C + (R() - .5) * 150, 8, 3, 0.35);
    return c;
  },
  jokbal() { // fanned slices of braised pork trotter: glossy dark skin rim, pale meat, on a lettuce leaf
    const [c, x] = mk();
    circle(x, C, C + 4, 120, 'rgba(0,0,0,.3)');
    x.fillStyle = '#4caf50'; x.beginPath(); x.ellipse(C, C + 6, 118, 100, 0.3, 0, 6.283); x.fill();
    x.fillStyle = '#7bd36b'; x.beginPath(); x.ellipse(C - 10, C + 2, 94, 78, 0.3, 0, 6.283); x.fill();
    const slices = [[-40, -40, -0.5], [-8, -6, -0.5], [26, 30, -0.5]];
    for (const [dx, dy, a] of slices) { x.save(); x.translate(C + dx, C + dy); x.rotate(a);
      x.fillStyle = 'rgba(0,0,0,.35)'; x.beginPath(); x.ellipse(4, 6, 70, 46, 0, 0, 6.283); x.fill();
      const skin = x.createLinearGradient(0, -38, 0, 38); skin.addColorStop(0, '#9a5a24'); skin.addColorStop(0.5, '#5a2c0e'); skin.addColorStop(1, '#3a1a06');
      x.fillStyle = skin; x.beginPath(); x.ellipse(0, 0, 70, 46, 0, 0, 6.283); x.fill();
      x.fillStyle = '#f0e2c8'; x.beginPath(); x.ellipse(2, 3, 58, 35, 0, 0, 6.283); x.fill();
      const meat = x.createRadialGradient(-8, -4, 2, 0, 0, 55); meat.addColorStop(0, '#f6d6c2'); meat.addColorStop(1, '#d99c80');
      x.fillStyle = meat; x.beginPath(); x.ellipse(6, 7, 44, 24, 0, 0, 6.283); x.fill();
      x.strokeStyle = 'rgba(160,90,60,.5)'; x.lineWidth = 2; x.beginPath(); x.ellipse(4, 5, 30, 10, 0, 0, 6.283); x.stroke();
      gloss(x, -30, -22, 22, 6, 0.55); x.restore(); }
    for (const [dx, dy] of [[-70, 40], [-55, 62]]) { circle(x, C + dx, C + dy, 10, '#f3ecd6'); circle(x, C + dx, C + dy, 4, '#e3d6b0'); }
    return c;
  },
};
export function buildIcons(names) { const out = {}; for (const n of names) if (PAINT[n]) out['@' + n] = PAINT[n](); return out; }
export const ICON_NAMES = Object.keys(PAINT);
