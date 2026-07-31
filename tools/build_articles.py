#!/usr/bin/env python3
"""Regenerate the article lists on index.html and research.html from data/articles.json.

The JSON is the single source of truth for titles, dates, links and summaries.
HTML is generated rather than fetched at runtime so the text stays in the page
for crawlers. Run from the repository root:  python3 tools/build_articles.py
"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTS = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
GROUP_ORDER = ["REIT", "Industrials", "Telecom", "BDC"]

def row(a, home=False):
    title = a.get("home_title", a["title"]) if home else a["title"]
    meta = f'{a["date"]} &middot; {a["sector"]}' if home else f'{a["date"]} &middot; {a["tag"]} &middot; Read on Benzinga &rarr;'
    return (f'    <a class="row" href="{a["url"]}" target="_blank" rel="noopener">\n'
            f'      <span class="rt">{title}</span>\n'
            f'      <span class="rd">{a["summary"]}</span>\n'
            f'      <span class="rmeta">{meta}</span>\n'
            f'    </a>\n')

def home_block():
    picked = [a for a in ARTS if a.get("home")]
    picked.sort(key=lambda a: a["date"], reverse=True)
    return '  <div class="rows">\n' + "".join(row(a, home=True) for a in picked) + '  </div>'

def research_block():
    out = []
    for g in GROUP_ORDER:
        items = [a for a in ARTS if a["group"] == g]
        if not items:
            continue
        items.sort(key=lambda a: a["date"], reverse=True)
        out.append(f'  <div class="grp"><div class="grp-h">{g}</div>\n  <div class="rows">\n'
                   + "".join(row(a) for a in items) + '  </div></div>\n')
    return "\n".join(out)

def splice(path, block):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    new = re.sub(r'(<!-- ARTICLES:START -->\n).*?(\s*<!-- ARTICLES:END -->)',
                 lambda m: m.group(1) + block + m.group(2), s, flags=re.S)
    if new == s and "ARTICLES:START" not in s:
        raise SystemExit(f"{path}: markers missing")
    p.write_text(new, encoding="utf-8")
    print(f"{path}: rebuilt")

splice("index.html", home_block())
splice("research.html", research_block())
