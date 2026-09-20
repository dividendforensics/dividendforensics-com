#!/usr/bin/env python3
"""Build DFB article listings and shared chrome from local, verified records.

`articles.json` is the canonical source. Never retrieve articles at build time.
Only published records are rendered. Missing local case files fall back to the
verified external article URL. Dates follow the newest dated public record,
not the first array entry, the build date, or a draft submission date.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
START, END = '<!-- ARTICLES:START -->', '<!-- ARTICLES:END -->'
HEADER_START, HEADER_END = '<!-- SITE:HEADER -->', '<!-- /SITE:HEADER -->'
FOOTER_START, FOOTER_END = '<!-- SITE:FOOTER -->', '<!-- /SITE:FOOTER -->'
REPORT_URL = ('https://dividendforensics.lemonsqueezy.com/checkout/buy/'
              '0417e6b9-d489-438e-9b2c-913437003238'
              '?utm_source=website&utm_medium=lead_magnet&utm_campaign=report001')
REQUIRED = ('url', 'title', 'blurb', 'date', 'group', 'label', 'case_key')
MONTHS = ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')

class BuildError(ValueError):
    pass

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)

def date_key(value: str) -> date:
    try:
        if re.fullmatch(r'\d{4}-\d{2}', value):
            return date.fromisoformat(value + '-01')
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise BuildError(f'Invalid publication date: {value!r}')

def display_date(value: str) -> str:
    d = date_key(value)
    return f'{d.day:02d} {MONTHS[d.month-1]} {d.year}' if len(value) == 10 else f'{MONTHS[d.month-1]} {d.year}'

def load(root: Path = ROOT):
    try:
        cfg = json.loads((root / 'articles.json').read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        raise BuildError(f'Cannot read articles.json: {e}') from e
    if not isinstance(cfg, dict) or not isinstance(cfg.get('articles'), list) or not cfg['articles']:
        raise BuildError('articles must be a non-empty array.')
    seen_urls, seen_slugs, public = set(), set(), []
    for i, a in enumerate(cfg['articles'], 1):
        if not isinstance(a, dict):
            raise BuildError(f'Article {i} must be an object.')
        for field in REQUIRED:
            if not isinstance(a.get(field), str) or not a[field].strip():
                raise BuildError(f'Article {i}: missing or invalid {field}.')
        url = urlsplit(a['url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password or any(c.isspace() for c in a['url']):
            raise BuildError(f'Article {i}: a public HTTPS URL is required.')
        if url.hostname == 'contributor.benzinga.com':
            raise BuildError('Contributor previews are not public article URLs.')
        if a['url'] in seen_urls:
            raise BuildError(f'Duplicate article URL: {a["url"]}')
        seen_urls.add(a['url'])
        date_key(a['date'])
        if a.get('case_slug'):
            slug = a['case_slug']
            if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
                raise BuildError(f'Article {i}: invalid case_slug.')
            if slug in seen_slugs:
                raise BuildError(f'Duplicate case_slug: {slug}')
            seen_slugs.add(slug)
        if 'home' in a and not isinstance(a['home'], bool):
            raise BuildError(f'Article {i}: home must be true or false.')
        status = a.get('status', 'published')
        if status not in ('published', 'draft', 'internal_review'):
            raise BuildError(f'Article {i}: invalid status.')
        if status == 'published':
            if date_key(a['date']) > date.today():
                raise BuildError(f'Future publication date: {a["date"]}')
            public.append(a)
    if not public:
        raise BuildError('At least one published article is required.')
    if not any(a.get('home', True) for a in public):
        raise BuildError('At least one published article must be shown on the home page.')
    return cfg, public

def destination(article: dict, root: Path = ROOT):
    slug = article.get('case_slug')
    if slug and (root / f'case-{slug}.html').is_file():
        return f'/case-{slug}.html', False
    return article['url'], True

def link_attrs(article: dict, root: Path = ROOT) -> tuple[str, bool]:
    url, external = destination(article, root)
    return f'href="{esc(url)}"' + (' target="_blank" rel="noopener"' if external else ''), external

def meta(article: dict) -> str:
    return (f'<div class="entry-meta"><span class="entry-key">{esc(article["case_key"])}</span>'
            f'<span>{esc(article["label"])}</span><time datetime="{esc(article["date"])}">{display_date(article["date"])}</time></div>')

def build_index(articles: list[dict], root: Path = ROOT) -> str:
    displayed = [a for a in articles if a.get('home', True)][:5]
    first, rest = displayed[0], displayed[1:]
    attrs, external = link_attrs(first, root)
    title = first.get('home_title') or first['title']
    arrow = '&nearr;' if external else '&rarr;'
    cta = 'Read on Benzinga' if external else 'Open research record'
    lead = (f'<article class="featured-research">{meta(first)}<h3><a {attrs}>{esc(title)}</a></h3>'
            f'<p>{esc(first["blurb"])}</p><a class="text-link" {attrs}>{cta} <span aria-hidden="true">{arrow}</span></a></article>')
    rows = []
    for a in rest:
        at, _ = link_attrs(a, root)
        rows.append(f'<article class="latest-item">{meta(a)}<h3><a {at}>{esc(a.get("home_title") or a["title"])}</a></h3></article>')
    return '\n<div class="home-research-grid">' + lead + '<div class="latest-list">' + ''.join(rows) + '</div></div>\n'

def build_research(articles: list[dict], root: Path = ROOT) -> str:
    out = []
    for a in articles:
        attrs, external = link_attrs(a, root)
        search = ' '.join(a[k] for k in ('title','blurb','group','label','case_key')).lower()
        source = 'Benzinga' if external else 'DFB record / Benzinga original'
        out.append(
            f'<article class="archive-entry" data-group="{esc(a["group"])}" data-search="{esc(search)}">'
            f'<time datetime="{esc(a["date"])}">{display_date(a["date"])}</time>'
            f'<span class="entry-category">{esc(a["group"])}</span><div class="entry-copy">'
            f'<h2><a {attrs}>{esc(a["title"])}</a></h2><p>{esc(a["blurb"])}</p>'
            f'<small>{esc(a["case_key"])} &nbsp; / &nbsp; {esc(a["label"])} &nbsp; / &nbsp; {source}</small></div>'
            f'<a class="entry-arrow" {attrs} aria-label="Read {esc(a["title"])}">{("&nearr;" if external else "&rarr;")}</a></article>'
        )
    return '\n' + '\n'.join(out) + '\n'

def header(page_name: str, root: Path = ROOT) -> str:
    nav = [('research.html','Research'),('learn.html','Field guides'),('membership.html','Membership'),('about.html','About'),('research-desk.html','Research Desk')]
    active = page_name
    if page_name.startswith('case-'): active = 'research.html'
    if page_name.endswith('-guide.html') or page_name.startswith('reit-'): active = 'learn.html'
    items = []
    for path, label in nav:
        current = ' aria-current="page"' if path == active else ''
        klass = ' class="desk-link"' if path == 'research-desk.html' else ''
        items.append(f'<li><a href="/{path}"{klass}{current}>{label}</a></li>')
    return (root / 'templates/header.html').read_text().replace('{{navigation}}','\n        '.join(items)).strip()

def footer(root: Path = ROOT) -> str:
    return (root / 'templates/footer.html').read_text().replace('{{report_url}}', esc(REPORT_URL)).strip()

def splice(text: str, inner: str, start: str = START, end: str = END) -> str:
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise BuildError(f'Missing, duplicate or reversed build markers: {start}')
    i, j = text.index(start) + len(start), text.index(end)
    return text[:i] + '\n' + inner.strip() + '\n' + text[j:]

def planned_outputs(root: Path = ROOT):
    _, articles = load(root)
    latest = max(articles, key=lambda a: date_key(a['date']))['date']
    planned = {}
    for path in root.glob('*.html'):
        text = path.read_text(encoding='utf-8')
        if HEADER_START not in text:
            continue  # verification files and retired redirects are intentionally unchanged
        text = splice(text, header(path.name, root), HEADER_START, HEADER_END)
        text = splice(text, footer(root), FOOTER_START, FOOTER_END)
        if path.name in ('index.html','research.html'):
            template = 'home.html' if path.name == 'index.html' else 'research.html'
            body = (root / 'templates' / template).read_text(encoding='utf-8').replace('{{report_url}}', esc(REPORT_URL))
            opening = '<main id="main" tabindex="-1">'
            text = splice(text, body, opening, '</main>')
            text = splice(text, build_index(articles, root) if path.name == 'index.html' else build_research(articles, root))
        text = re.sub(r'<time\b[^>]*data-dfb="updated"[^>]*>.*?</time>',
                      f'<time data-dfb="updated" datetime="{latest}">{display_date(latest)}</time>', text, flags=re.S)
        text = re.sub(r'(<(?:b|span)\b[^>]*data-dfb="selected-count"[^>]*>).*?(</(?:b|span)>)',
                      lambda m:m.group(1)+str(len(articles))+m.group(2), text, flags=re.S)
        planned[path] = text
    for required in ('index.html','research.html'):
        if root / required not in planned:
            raise BuildError(f'{required} does not contain the shared build markers.')
    return planned

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if generated markup needs updating; write nothing.')
    args = parser.parse_args(argv)
    try:
        planned = planned_outputs()
        changed = {p:t for p,t in planned.items() if p.read_text(encoding='utf-8') != t}
        if args.check:
            if changed:
                print('Needs rebuild: ' + ', '.join(p.name for p in changed))
                return 1
        else:
            # Validate every output first, then stage writes. Restore originals on OS failure.
            originals = {p:p.read_bytes() for p in changed}
            try:
                for p,t in changed.items():
                    p.with_suffix(p.suffix+'.tmp').write_text(t, encoding='utf-8')
                for p in changed:
                    p.with_suffix(p.suffix+'.tmp').replace(p)
            except OSError:
                for p,data in originals.items(): p.write_bytes(data)
                raise
            finally:
                for p in changed:
                    p.with_suffix(p.suffix+'.tmp').unlink(missing_ok=True)
        print(f'Validated {len(planned)} pages; ' + (f'updated {len(changed)}.' if changed else 'no changes.'))
        return 0
    except (BuildError, OSError) as e:
        print(f'Build stopped: {e}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
