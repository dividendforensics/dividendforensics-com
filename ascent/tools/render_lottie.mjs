// Renders lottie/ascent.json to PNG frames with lottie-web (SVG renderer) in headless Chromium.
// usage: node tools/render_lottie.mjs <node_modules dir> <out dir>
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const [nm, out] = process.argv.slice(2).map((p) => resolve(p));
await mkdir(out, { recursive: true });
const page = `<!doctype html><body style="margin:0;background:#000"><div id="a" style="width:1080px;height:1080px"></div>
<script src="/nm/lottie-web/build/player/lottie.min.js"></script><script>
fetch('/lottie/ascent.json').then(r => r.json()).then(d => { window.anim = lottie.loadAnimation({ container: document.getElementById('a'), renderer: 'svg', loop: false, autoplay: false, animationData: d }); window.ready = true; });
</script></body>`;
const srv = createServer(async (q, r) => {
  const p = new URL(q.url, 'http://x').pathname;
  try {
    if (p === '/') { r.writeHead(200, { 'content-type': 'text/html' }); return r.end(page); }
    const f = p.startsWith('/nm/') ? join(nm, p.slice(4)) : join(root, p);
    r.writeHead(200, { 'content-type': p.endsWith('.js') ? 'text/javascript' : 'application/json' }); r.end(await readFile(f));
  } catch { r.writeHead(404); r.end(); }
}).listen(0);
const b = await chromium.launch();
const pg = await b.newPage({ viewport: { width: 1080, height: 1080 } });
await pg.goto(`http://localhost:${srv.address().port}/`);
await pg.waitForFunction(() => window.ready);
const total = await pg.evaluate(() => window.anim.totalFrames);
for (let f = 0; f < total; f++) {
  await pg.evaluate((f) => window.anim.goToAndStop(f, true), f);
  await pg.screenshot({ path: join(out, `l_${String(f).padStart(4, '0')}.png`) });
}
console.log(`${total} frames`);
await b.close(); srv.close();
