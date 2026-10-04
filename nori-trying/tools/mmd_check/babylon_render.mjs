// Renders MMD frames of the exported package with the babylon-mmd bundle (index.html + bundle.js next to this file).
// usage: node babylon_render.mjs <mmd dir> <out dir> <frame,frame,...>
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname } from 'node:path';
const [,, mmdDir, outDir, framesArg] = process.argv;
const www = new URL('./', import.meta.url).pathname;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png' };
const server = createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = p.startsWith('/mmd/') ? join(mmdDir, p.slice(5)) : join(www, p === '/' ? 'index.html' : p);
  try { const b = await readFile(file); res.writeHead(200, { 'content-type': types[extname(file)] || 'application/octet-stream' }); res.end(b); }
  catch { res.writeHead(404); res.end(); }
}).listen(0);
const { chromium } = await import('/opt/node22/lib/node_modules/playwright/index.mjs');
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text().slice(0, 300)); });
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.goto(`http://localhost:${server.address().port}/`);
await page.waitForFunction(() => window.start);
console.log(JSON.stringify(await page.evaluate(() => window.start('/mmd/'))));
const out = [];
for (const f of framesArg.split(',').map(Number)) {
  const cam = await page.evaluate((f) => window.seek(f), f);
  await page.screenshot({ path: join(outDir, `mmd_${String(f).padStart(5, '0')}.png`) });
  out.push({ frame: f, ...cam });
}
console.log('CAMS ' + JSON.stringify(out));
await browser.close(); server.close();
