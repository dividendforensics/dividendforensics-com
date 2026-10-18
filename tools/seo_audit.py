#!/usr/bin/env python3
"""Offline checks of crawlable static output; never claims Google indexing/rank.

By default inspect build_site.planned_outputs, so generated disk files can be
stale without producing false failures. No network, account or submission calls.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'https://dividendforensics.com'
sys.path.insert(0, str(ROOT))


def clean(text):
    return ' '.join(text.split())


def page_url(name):
    path = '/' + name
    if path.endswith('/index.html'): path = path[:-10]
    return DOMAIN + path


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.title, self.h1, self.description, self.canonical = [], [], [], []
        self.links, self.robots, self.schema_raw, self.text, self.alternates = [], [], [], [], []
        self.language = None
        self.redirect, self.active = False, False
        self.in_title, self.in_h1, self.json_buffer = False, None, None
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.language = a.get('lang')
        if tag == 'title':
            self.in_title = True
            self.title.append('')
        if tag == 'h1':
            self.h1.append('')
            self.in_h1 = len(self.h1) - 1
        if tag == 'br':
            self.handle_data(' ')
        if tag == 'meta':
            name, content = a.get('name', '').lower(), a.get('content', '')
            if name == 'description': self.description.append(clean(content))
            if name in ('robots', 'googlebot'): self.robots.append(content.lower())
            if name == 'dfb-design': self.active = True
            if a.get('http-equiv', '').lower() == 'refresh': self.redirect = True
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonical.append(a.get('href', ''))
        if tag == 'link' and 'alternate' in a.get('rel', '').lower().split() and a.get('hreflang'):
            self.alternates.append((a['hreflang'], a.get('href', '')))
        if tag == 'a' and a.get('href') and 'nofollow' not in a.get('rel', '').lower().split():
            self.links.append(a['href'])
        if tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self.json_buffer = ''

    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
        if tag == 'h1': self.in_h1 = None
        if tag == 'script' and self.json_buffer is not None:
            self.schema_raw.append(self.json_buffer)
            self.json_buffer = None

    def handle_data(self, data):
        if self.json_buffer is not None:
            self.json_buffer += data
            return
        if self.in_title: self.title[-1] += data
        if self.in_h1 is not None: self.h1[self.in_h1] += data
        self.text.append(data)

    @property
    def indexable(self):
        directives = {x.strip() for value in self.robots for x in value.split(',')}
        return self.active and not self.redirect and not directives.intersection({'noindex', 'none'})


def schema_nodes(value):
    if isinstance(value, list):
        for item in value: yield from schema_nodes(item)
    elif isinstance(value, dict):
        yield value
        if '@graph' in value: yield from schema_nodes(value['@graph'])


def day(value):
    if not isinstance(value, str): raise ValueError('Date must be text')
    if len(value) == 10: return date.fromisoformat(value)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).date()


def internal_url(href, base):
    resolved = urlsplit(urljoin(base, href))
    if resolved.scheme not in ('https', 'http') or resolved.netloc != urlsplit(DOMAIN).netloc:
        return None
    path = resolved.path or '/'
    if path.endswith('/index.html'): path = path[:-10]
    return urlunsplit(('https', resolved.netloc, path, '', ''))


def audit(pages, sitemap_text, bdc_articles=()):
    """pages maps repository-relative HTML names to source strings."""
    parsed = {name: Page(raw) for name, raw in pages.items() if name.endswith('.html')}
    errors, warnings = [], []
    excluded = sorted(name for name, page in parsed.items() if page.active and not page.indexable)
    selected = {name: page for name, page in parsed.items() if page.indexable}
    records, canonical_pages, schemas = [], {}, {}
    for name, page in selected.items():
        expected = page_url(name)
        for label, values in [('title', page.title), ('description', page.description), ('canonical', page.canonical), ('h1', page.h1)]:
            if len(values) != 1 or not clean(values[0]):
                errors.append(f'{name}: expected one nonempty {label}')
        if page.canonical != [expected]: errors.append(f'{name}: canonical does not identify its own HTTPS URL')
        if expected in canonical_pages: errors.append(f'{name}: duplicate canonical {expected}')
        canonical_pages[expected] = name
        title = clean(page.title[0]) if page.title else ''
        description = page.description[0] if page.description else ''
        if len(title) > 85: warnings.append(f'{name}: long descriptive title ({len(title)} characters); review presentation, not a ranking error')
        if len(description) > 190: warnings.append(f'{name}: long description ({len(description)} characters); Google may choose another snippet')
        nodes = []
        for raw in page.schema_raw:
            try: nodes.extend(schema_nodes(json.loads(raw)))
            except (ValueError, TypeError): errors.append(f'{name}: invalid JSON-LD')
        schemas[name] = nodes
        records.append({'file': name, 'url': expected, 'title': title, 'description': description,
                        'h1': clean(page.h1[0]) if page.h1 else '', 'language': page.language,
                        'inbound_pages': 0, 'lastmod': None})
    for field in ('title', 'description', 'h1'):
        groups = defaultdict(list)
        for record in records:
            if record[field]: groups[record[field].casefold()].append(record['file'])
        for value, names in groups.items():
            if len(names) > 1: errors.append(f'duplicate {field}: ' + ', '.join(sorted(names)))

    sitemap, lastmods = [], {}
    try:
        tree = ET.fromstring(sitemap_text)
        namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        if tree.tag != namespace + 'urlset': raise ValueError('Expected sitemap urlset')
        for item in tree.findall(namespace + 'url'):
            loc = item.findtext(namespace + 'loc')
            if not loc: raise ValueError('Missing sitemap loc')
            sitemap.append(loc)
            modified = item.findtext(namespace + 'lastmod')
            if modified is not None:
                day(modified)
                lastmods[loc] = modified
    except (ET.ParseError, ValueError, TypeError):
        errors.append('sitemap.xml: invalid sitemap or lastmod date')
    if len(sitemap) != len(set(sitemap)): errors.append('sitemap.xml: duplicate URL')
    for url in sorted(set(sitemap) - set(canonical_pages)):
        errors.append('sitemap.xml: target is not a canonical indexable page: ' + url)
    for url in sorted(set(canonical_pages) - set(sitemap)):
        errors.append('sitemap.xml: missing indexable page: ' + url)

    incoming = defaultdict(set)
    graph = defaultdict(set)
    for name, page in selected.items():
        source = page_url(name)
        for href in page.links:
            destination = internal_url(href, source)
            if destination in canonical_pages and destination != source:
                incoming[destination].add(source)
                graph[source].add(destination)
    reached, queue = set(), deque([DOMAIN + '/'])
    while queue:
        source = queue.popleft()
        if source in reached: continue
        reached.add(source)
        queue.extend(graph[source] - reached)
    for record in records:
        name, url = record['file'], record['url']
        page = selected[name]
        record['inbound_pages'] = len(incoming[url])
        record['lastmod'] = lastmods.get(url)
        if url != DOMAIN + '/' and not incoming[url]: errors.append(f'{name}: no crawlable inbound link from another indexable page')
        if url not in reached: errors.append(f'{name}: not reachable from home through crawlable static links')
        if name.startswith('es/') and page.language != 'es':
            errors.append(f'{name}: Spanish page must declare html lang="es"')
        if page.alternates:
            alternate = dict(page.alternates)
            if len(alternate) != len(page.alternates): errors.append(f'{name}: duplicate hreflang language')
            for language, destination in page.alternates:
                if destination not in canonical_pages:
                    errors.append(f'{name}: hreflang target is not a canonical indexable page: {destination}')
                    continue
                target = selected[canonical_pages[destination]]
                if language != 'x-default' and target.language != language:
                    errors.append(f'{name}: hreflang language differs from target html lang')
                if language != 'x-default' and dict(target.alternates).get(page.language) != url:
                    errors.append(f'{name}: hreflang target does not link back')
            if page.language not in alternate or alternate[page.language] != url:
                errors.append(f'{name}: hreflang set must include its self canonical')
            if 'en' in alternate and alternate.get('x-default') != alternate['en']:
                errors.append(f'{name}: x-default must identify the paired English canonical')
        article_nodes = [n for n in schemas[name] if n.get('@type') == 'Article'
                         or isinstance(n.get('@type'), list) and 'Article' in n['@type']]
        for article in article_nodes:
            try:
                published, modified = day(article['datePublished']), day(article['dateModified'])
                if modified < published: raise ValueError('Modification before publication')
            except (KeyError, ValueError, TypeError):
                errors.append(f'{name}: invalid or missing Article publication/modification dates')
                continue
            if url not in lastmods or day(lastmods[url]) != modified:
                errors.append(f'{name}: sitemap lastmod does not match Article dateModified')
        if url in lastmods and not article_nodes:
            warnings.append(f'{name}: lastmod has no Article dateModified reference; verify the actual update record')

    bdc_checked = []
    for source in bdc_articles:
        name = source['slug'] + '.html'
        page = selected.get(name)
        if not page:
            errors.append(f'{name}: expected BDC article is not indexable')
            continue
        nodes = [n for n in schemas[name] if n.get('@type') == 'Article']
        if len(nodes) != 1:
            errors.append(f'{name}: expected one BDC Article schema')
            continue
        schema = nodes[0]
        expected = DOMAIN + '/' + name
        entity = schema.get('mainEntityOfPage')
        if isinstance(entity, dict): entity = entity.get('@id')
        if entity != expected or schema.get('headline') != source['title']:
            errors.append(f'{name}: BDC schema headline or entity URL differs from content source')
        if schema.get('datePublished') != source['published'] or schema.get('dateModified') != source['updated']:
            errors.append(f'{name}: BDC schema dates differ from article content source')
        text = clean(' '.join(page.text))
        if 'US BDC education.' not in text or 'This guide focuses on US REITs.' in text:
            errors.append(f'{name}: missing or incorrect BDC scope statement')
        bdc_checked.append(name)

    errors = sorted(set(errors))
    return {'audit_kind': 'offline static output; not Google index or ranking evidence',
            'status': 'fail' if errors else 'pass', 'indexable_pages': len(selected),
            'sitemap_urls': len(sitemap), 'bdc_articles_checked': len(bdc_checked),
            'excluded_active_pages': excluded, 'errors': errors, 'warnings': sorted(set(warnings)),
            'pages': sorted(records, key=lambda item: item['url'])}


def site_audit(root=ROOT, *, planned=True):
    root = Path(root).resolve()
    excluded_directories = {'node_modules', 'vendor', '_legacy'}
    pages = {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8')
             for p in root.rglob('*.html')
             if not any(part.startswith('.') or part in excluded_directories
                        for part in p.relative_to(root).parts[:-1])}
    sitemap = (root / 'sitemap.xml').read_text(encoding='utf-8')
    if planned:
        from build_site import planned_outputs
        for path, text in planned_outputs(root).items():
            if path.suffix == '.html': pages[path.relative_to(root).as_posix()] = text
            elif path.name == 'sitemap.xml': sitemap = text
    source = root / 'content/bdc.json'
    articles = json.loads(source.read_text(encoding='utf-8')) if source.exists() else []
    report = audit(pages, sitemap, articles)
    report['input'] = 'planned_outputs' if planned else 'saved_files'
    robots_path = root / 'robots.txt'
    if not robots_path.exists() or DOMAIN + '/sitemap.xml' not in robots_path.read_text(encoding='utf-8'):
        report['errors'].append('robots.txt: missing public sitemap declaration')
        report['status'] = 'fail'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--saved-files', action='store_true', help='Audit saved HTML instead of the planned build')
    parser.add_argument('--output', type=Path, help='Optional local JSON report, normally .qa/seo-audit.json')
    args = parser.parse_args(argv)
    report = site_audit(args.root, planned=not args.saved_files)
    if args.output:
        destination = args.output.resolve()
        qa = args.root.resolve() / '.qa'
        if qa not in destination.parents: raise SystemExit('Audit reports must be inside the local .qa directory')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{report["status"].upper()}: {report["indexable_pages"]} indexable static pages; '
          f'{report["sitemap_urls"]} sitemap URLs; {report["bdc_articles_checked"]} BDC article schemas; '
          f'{len(report["errors"])} errors; {len(report["warnings"])} advisory warnings. '
          'Google indexing/ranking not checked.')
    for error in report['errors']: print(error)
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
