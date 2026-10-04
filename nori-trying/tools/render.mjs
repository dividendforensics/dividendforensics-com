// Renders one edit of nori-trying/index.html frame by frame in headless Chromium (PNG frames).
// usage: node tools/render.mjs --edit main|shortA|shortB|shortC --out <dir> [--from 0 --to <s>] [--times a,b,c]
//        --three <node_modules/three> --fonts <node_modules/@fontsource>
// Three.js is served from a local copy so the render works without CDN access.
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { extname, join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1]]] : a), []));
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const out = resolve(args.out || 'frames');
const EDIT = args.edit || 'main';
const edits = JSON.parse(await readFile(join(root, 'edits.json'), 'utf8'));
const E = edits[EDIT];
const W = +(args.w || E.w), H = +(args.h || E.h), FPS = +(args.fps || E.fps);
const only = args.times ? args.times.split(',').map(Number) : null;
const threeDir = resolve(args.three || 'node_modules/three');
const playwrightPath = args.playwright || '/opt/node22/lib/node_modules/playwright/index.mjs';
const { chromium } = await import(playwrightPath);

const types = { '.html': 'text/html', '.js': 'text/javascript', '.m4a': 'audio/mp4', '.json': 'application/json' };
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const file = join(root, path.endsWith('/') ? path + 'index.html' : path);
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': types[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
}).listen(0);
const port = server.address().port;

await mkdir(out, { recursive: true });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.route(/cdn\.jsdelivr\.net\/npm\/three@[^/]+\/(.*)$/, async (route) => {
  const rel = route.request().url().replace(/^.*three@[^/]+\//, '');
  route.fulfill({ body: await readFile(join(threeDir, rel)), contentType: 'text/javascript' });
});
// Google Fonts are swapped for the same faces from @fontsource when --fonts points at node_modules/@fontsource
if (args.fonts) {
  const faces = [['Cormorant Garamond', 'cormorant-garamond', [[300, 'normal'], [400, 'normal'], [300, 'italic'], [400, 'italic']]], ['Jost', 'jost', [[300, 'normal'], [400, 'normal'], [500, 'normal'], [600, 'normal']]], ['Fredoka', 'fredoka', [[500, 'normal'], [600, 'normal']]]];
  const css = faces.flatMap(([fam, dir, list]) => list.map(([w, st]) => `@font-face{font-family:'${fam}';font-style:${st};font-weight:${w};font-display:block;src:url(https://local.fonts/${dir}/files/${dir}-latin-${w}-${st}.woff2) format('woff2');}`)).join('\n');
  await page.route(/fonts\.googleapis\.com/, (route) => route.fulfill({ body: css, contentType: 'text/css' }));
  await page.route(/local\.fonts\//, async (route) => {
    const rel = route.request().url().replace('https://local.fonts/', '');
    route.fulfill({ body: await readFile(join(resolve(args.fonts), rel)), contentType: 'font/woff2' });
  });
}
await page.goto(`http://localhost:${port}/index.html?render&edit=${EDIT}`);
await page.waitForFunction(() => window.__nori, null, { timeout: 180000 });
await page.evaluate(() => window.__nori.ready);
const duration = await page.evaluate(() => window.__nori.currentEdit().duration);
const from = +(args.from ?? 0), to = Math.min(+(args.to ?? duration), duration);

const first = Math.round(from * FPS), last = Math.round(to * FPS);
const times = only || Array.from({ length: last - first }, (_, i) => (first + i) / FPS);
const t0 = Date.now();
for (let i = 0; i < times.length; i++) {
  const t = times[i];
  await page.evaluate((tt) => window.__nori.frame(tt), t);
  const idx = only ? i : Math.round(t * FPS);
  const name = only ? `${EDIT}_${t.toFixed(2)}.png` : `f_${String(idx).padStart(5, '0')}.png`;
  await page.screenshot({ path: join(out, name), type: 'png' });
  if (i % 10 === 0 || only) console.log(`frame ${i + 1}/${times.length} t=${t.toFixed(2)} ${((Date.now() - t0) / (i + 1) / 1000).toFixed(2)}s/frame`);
}
await browser.close();
server.close();
