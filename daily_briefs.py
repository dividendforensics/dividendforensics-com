"""Offline, fail-closed filing briefs. Review evidence is required, never generated here."""
from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from education import E, shell

KST = ZoneInfo('Asia/Seoul')
CHECKS = ('sources', 'arithmetic', 'periods_units', 'english', 'neutrality', 'freshness')


def require(ok, message):
    if not ok:
        raise ValueError('Daily brief: ' + message)


def digest(record):
    return sha256(json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def stamp(raw):
    value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    require(value.tzinfo is not None, 'timestamp needs timezone')
    return value


def decimal(raw):
    require(isinstance(raw, str) and re.fullmatch(r'-?\d+(?:\.\d+)?', raw), 'numbers must be finite decimal strings')
    return Decimal(raw)


def calculations(brief):
    values = {k: decimal(v['value']) for k, v in brief['facts'].items()}
    result = {}
    units_by_id = {k: v['unit'] for k, v in brief['facts'].items()}
    periods_by_id = {k: {(v['period']['start'], v['period']['end'])} for k, v in brief['facts'].items()}
    with localcontext() as ctx:
        ctx.prec = 40
        for item in brief['calculations']:
            args = item['inputs']
            require(args and all(k in values for k in args), 'unknown calculation input')
            units = {units_by_id[k] for k in args}
            require(len(units) == 1, 'mixed calculation units')
            periods = set().union(*(periods_by_id[k] for k in args))
            require(len(periods) == 1 or len(item.get('comparison_basis', '').strip()) >= 20, 'cross-period calculation requires explicit comparison basis')
            op = item['operation']
            if op == 'sum':
                value = sum((values[k] for k in args), Decimal(0))
                require(item['unit'] in units, 'sum unit mismatch')
            elif op == 'subtract':
                require(len(args) == 2, 'subtraction requires two inputs')
                value = values[args[0]] - values[args[1]]
                require(item['unit'] in units, 'subtraction unit mismatch')
            elif op in ('ratio', 'ratio_percent', 'percent_change'):
                require(len(args) == 2 and values[args[1]] > 0, 'invalid ratio denominator')
                require(item['unit'] == ('times' if op == 'ratio' else 'percent'), 'ratio unit mismatch')
                value = (values[args[0]] / values[args[1]] - (1 if op == 'percent_change' else 0)) * (1 if op == 'ratio' else 100)
            else:
                raise ValueError('Daily brief: unsupported calculation')
            places = item['decimal_places']
            require(type(places) is int and 0 <= places <= 6, 'invalid decimal places')
            raw_value = value
            value = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
            require(value == decimal(item['expected']), 'independent arithmetic mismatch')
            require(item.get('precision_note'), 'calculation precision disclosure missing')
            require(item['id'] not in values, 'duplicate calculation id')
            # Derived calculations use the full-precision intermediate, not its display rounding.
            values[item['id']] = raw_value
            units_by_id[item['id']] = item['unit']
            periods_by_id[item['id']] = periods
            result[item['id']] = format(value, f'.{places}f')
    return result


def validate(brief, review, now):
    require(brief['status'] == 'approved', 'non-approved brief in public catalog')
    require(brief.get('category') in ('REITs', 'BDCs', 'Operating Companies'), 'invalid editorial category')
    require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', brief['slug']), 'invalid slug')
    published = stamp(brief['published_at'])
    checked = stamp(brief['source_checked_at'])
    reviewed = stamp(review['reviewed_at'])
    require(checked <= reviewed <= now and checked <= published <= now, 'invalid check/review/publication chronology')
    event = date.fromisoformat(brief['event_date'])
    start, end = (date.fromisoformat(brief['reporting_period'][x]) for x in ('start','end'))
    require(start <= end <= event <= checked.date(), 'invalid event/reporting chronology')
    require(brief.get('author') and review.get('reviewer') and brief['author'] != review['reviewer'], 'independent reviewer required')
    require(review.get('brief_sha256') == digest(brief), 'review does not match exact brief')
    require(review.get('decision') == 'pass', 'review did not pass')
    for check in CHECKS:
        evidence = review['checks'].get(check, {})
        require(evidence.get('result') == 'pass' and len(evidence.get('evidence', '').strip()) >= 20, f'{check} review evidence missing')
    sources = brief['sources']
    require(sources and brief['facts'] and brief['calculations'], 'missing evidence ledger')
    event_source = sources.get(brief.get('event_source_id'))
    require(event_source is not None and event_source['kind'] == 'sec', 'event requires a primary SEC filing')
    for source in sources.values():
        u = urlsplit(source['url'])
        require(u.scheme == 'https' and u.hostname and not u.username and not u.password, 'direct HTTPS source required')
        require(not any(c.isspace() for c in source['url']) and '\\' not in source['url'], 'invalid source URL characters')
        require(re.fullmatch(r'[0-9a-f]{64}', source.get('content_sha256', '')), 'source bytes SHA256 evidence missing')
        if source['kind'] == 'sec':
            match = re.fullmatch(r'/Archives/edgar/data/[0-9]+/([0-9]{18})/[A-Za-z0-9_.-]+', u.path)
            require(u.hostname in ('www.sec.gov', 'sec.gov') and u.port in (None, 443) and not u.query and not u.fragment and match is not None, 'SEC source requires official Archives filing URL')
            if source is event_source:
                require(brief.get('event_key') == 'sec:' + match.group(1), 'event key must match primary SEC accession')
        require(source['kind'] in ('sec', 'issuer') and source.get('title') and source.get('locator'), 'primary source and locator required')
        source_check = stamp(source['checked_at'])
        require(source_check <= checked, 'invalid source check chronology')
        if source.get('publication_precision') == 'date':
            require('published_at' not in source, 'date-only source must not invent publication timestamp')
            require(date.fromisoformat(source['published_date']) <= source_check.date(), 'invalid source publication date')
        else:
            require(source.get('publication_precision', 'timestamp') == 'timestamp' and source_check >= stamp(source['published_at']), 'invalid source chronology')
        if source.get('accepted_at'):
            require(source.get('accepted_at_kind') == 'SEC acceptance, not public availability', 'acceptance timestamp must not imply publication')
            stamp(source['accepted_at'])
    for fact in brief['facts'].values():
        decimal(fact['value'])
        require(fact['source_id'] in sources and fact.get('unit') and fact.get('basis') and fact.get('locator'), 'fact provenance missing')
        require(fact['period'] in [brief['reporting_period']] + brief.get('comparison_periods', []), 'fact period mismatch')
        require(date.fromisoformat(fact['period']['start']) <= date.fromisoformat(fact['period']['end']) <= event, 'invalid fact reporting period')
    require(brief.get('title') and brief.get('summary') and brief.get('limitations'), 'missing editorial fields')
    require(brief.get('sections') and 3 <= len(brief['sections']) <= 4, 'newsletter requires three or four paragraphs')
    require({'fact','inference','open_question'} <= {s['type'] for s in brief['sections']}, 'separate fact/inference/open question required')
    for section in brief['sections']:
        require(section['type'] in ('fact','inference','open_question') and section.get('heading') and section.get('text'), 'invalid section')
        require(section.get('source_ids') and all(s in sources for s in section['source_ids']), 'section source trail missing')
    calculations(brief)
    return published.astimezone(KST).date().isoformat()


def load(root, now=None):
    cfg = json.loads((root/'content/daily-briefs/catalog.json').read_text())
    require(cfg.get('schema_version') == 1, 'unsupported schema')
    now = now or datetime.now(timezone.utc)
    days, slugs, events, records = set(), set(), set(), []
    reviews = cfg['reviews']
    for brief in cfg['briefs']:
        matches = [r for r in reviews if r.get('brief_sha256') == digest(brief)]
        require(len(matches) == 1, 'exactly one matching independent review required')
        day = validate(brief, matches[0], now)
        require(day not in days, 'more than one brief on a KST publication date')
        require(brief['slug'] not in slugs, 'duplicate slug')
        require(brief['event_key'] not in events, 'same SEC event already published')
        events.add(brief['event_key'])
        days.add(day); slugs.add(brief['slug']); records.append(brief)
    return sorted(records, key=lambda b: stamp(b['published_at']), reverse=True)


def publication_label(brief):
    return str(stamp(brief['published_at']).astimezone(KST).date()) + ' KST' if brief.get('published_at') else 'Unpublished review preview'


def cards(records):
    if not records:
        return ''
    rows = ''.join(f'<article class="lesson-card"><span class="kicker">{E(b["category"])}</span><time datetime="{E(str(stamp(b["published_at"]).astimezone(KST).date()) if b.get("published_at") else "")}">{E(publication_label(b))}</time><h3><a href="/brief-{E(b["slug"])}.html">{E(b["title"])}</a></h3><p>{E(b["summary"])}</p></article>' for b in records[:3])
    return '<section class="wrap education-section" aria-labelledby="brief-title"><h2 id="brief-title">Daily Brief</h2><p>A short read on company filings, with the facts checked before publication.</p><div class="lesson-grid">'+rows+'</div><a href="/daily-briefs.html">All daily briefs →</a></section>'


def outputs(root):
    records = load(root)
    output = {}
    if not records:
        # Do not silently orphan previously published pages by deleting their records.
        require(not list(root.glob('brief-*.html')) and not (root/'daily-briefs.html').exists(), 'published brief records removed; restore catalog or use explicit retirement process')
        return output, records
    known = {f'brief-{b["slug"]}.html' for b in records}
    require(not {p.name for p in root.glob('brief-*.html')} - known, 'previously published brief removed')
    for b in records:
        name = f'brief-{b["slug"]}.html'
        pub = (f'<time datetime="{E(stamp(b["published_at"]).astimezone(KST).date())}">{E(stamp(b["published_at"]).astimezone(KST).strftime("%d %B %Y"))} · KST</time>' if b.get('published_at') else 'Unpublished review preview')
        intro = f'<header class="wrap page-heading daily-brief-heading" style="max-width:800px"><span class="kicker">Daily Brief · {E(b["category"])}</span><h1>{E(b["title"])}</h1><div class="article-meta"><span>By <a href="/editorial-policy.html" rel="author">{E(b["author"])}</a></span>{pub}</div></header>'
        # The public format is a short newsletter, not a second copy of the machine ledger.
        # Claims, periods, exact inputs and independently checked calculations remain in JSON.
        paragraphs = ''.join(f'<p>{E(section["text"])}</p>' for section in b['sections'])
        sources = ' · '.join(f'<a href="{E(source["url"])}">{E(source["title"])}</a>' for source in b['sources'].values())
        body = intro+'<article class="wrap education-section lesson-body daily-newsletter" style="max-width:800px"><div class="newsletter-copy">'+paragraphs+'</div><p class="small-note">Sources: '+sources+'.</p><p class="small-note">Structural research, not investment advice.</p><p><a href="/daily-briefs.html">All daily briefs</a> · <a href="/research-desk.html#inquiries">Report a factual correction</a></p></article>'
        output[root/name] = shell(root,name,b['title'],b['summary'],body,'Article',article={'published':str(stamp(b['published_at']).astimezone(KST).date()),'updated':str(stamp(b['published_at']).astimezone(KST).date()),'author_name':b['author']})
    archive = '<header class="wrap page-heading"><h1>Daily Brief</h1><p>A short read on what changed in company filings. New notes appear only when the evidence clears review.</p></header>'
    archive += '<section class="wrap education-section"><ul>'+''.join(f'<li><time datetime="{E(str(stamp(b["published_at"]).astimezone(KST).date()) if b.get("published_at") else "")}">{E(publication_label(b))}</time> · <a href="/brief-{E(b["slug"])}.html">{E(b["title"])}</a></li>' for b in records)+'</ul></section>'
    output[root/'daily-briefs.html'] = shell(root,'daily-briefs.html','Daily Brief','Short, source-checked notes on company filings.',archive)
    return output, records
