#!/usr/bin/env python3
"""Render DFB's own HTML typesetting to social PNGs. No external imagery."""
from pathlib import Path
from html import escape
import argparse, os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SPECS={
 'og.png':('The publication','A dividend is the last<br>line of the <em>investigation.</em>','Filing-anchored research on dividends, REITs &amp; BDCs.'),
 'og-research.png':('Research archive','The findings.<br><em>The figures behind them.</em>','Company filings. Verified arithmetic. Visible limitations.'),
 'og-learn.png':('The reading room','Before the ratio,<br><em>understand the business.</em>','Field guides to real estate, private credit and cash flow.'),
 'og-tools.png':('Working papers & tools','The work behind<br><em>the conclusion.</em>','Original reports, reconciliations and research checklists.'),
}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true');args=ap.parse_args()
 font='' if args.offline else '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Inter:wght@400;500&display=swap">'
 with sync_playwright() as p:
  exe=os.environ.get('CHROMIUM_PATH');browser=p.chromium.launch(**({'executable_path':exe} if exe else {}),args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1200,'height':630},device_scale_factor=1)
  for name,(label,headline,description) in SPECS.items():
   page.set_content(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">{font}<style>
   *{{box-sizing:border-box}}body{{margin:0;width:1200px;height:630px;background:#f3f0e8;color:#242925;padding:42px 64px;font-family:Inter,Arial,sans-serif}}
   header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #c8c1b4;padding-bottom:25px}}.mark{{font:500 45px/1 'EB Garamond',Georgia,serif;letter-spacing:-3px}}.name{{font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-left:22px;border-left:1px solid #c8c1b4;padding-left:22px}}.identity{{display:flex;align-items:center}}.label{{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#653239}}
   h1{{font:400 82px/1.03 'EB Garamond',Georgia,serif;letter-spacing:-2px;margin:65px 0 27px}}em{{font-weight:400;color:#653239}}p{{font-size:15px;color:#64675d;margin:0}}footer{{position:absolute;bottom:42px;left:64px;right:64px;display:flex;justify-content:space-between;border-top:1px solid #c8c1b4;padding-top:21px;font-size:10px;letter-spacing:1px}}aside{{position:absolute;right:64px;top:178px;width:8px;height:234px;background:#653239}}
   </style></head><body><header><div class="identity"><span class="mark">DFB</span><span class="name">Dividend Forensics<br>Bureau</span></div><span class="label">{escape(label)}</span></header><h1>{headline}</h1><p>{description}</p><aside aria-hidden="true"></aside><footer><span>INDEPENDENT STRUCTURAL RESEARCH</span><span>dividendforensics.com</span></footer></body></html>''',wait_until='load')
   page.evaluate('document.fonts.ready');page.screenshot(path=str(ROOT/'img'/name))
  browser.close()
 print('Rendered four 1200x630 social-preview PNGs. No font files are bundled.')
if __name__=='__main__':main()
