"""Read-only release check: ordinary public URLs must match the saved site.

A cache-busted response is diagnostic evidence only; it can never make a stale
canonical response pass. Does not purge caches, submit forms or change hosting.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import argparse
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[1]


def normalized(data):
    return data.replace(b'\r\n', b'\n').strip()


def targets(root=ROOT):
    pages = sorted(p.relative_to(root).as_posix() for p in root.rglob('*.html')
                   if '.qa' not in p.parts and 'name="dfb-design"' in p.read_text(encoding='utf-8'))
    assets = ['bureau.css', 'education.js', 'bdc-calculators.js',
              'capital-calculators.js', 'proposal.js', 'calculators.js',
              'vendor/decimal.js/decimal.js', 'vendor/decimal.js/LICENCE.md',
              'vendor/decimal.js/package.json', 'vendor/manifest.json',
              'research-desk.css', 'spanish-calculators.js', 'sitemap.xml', 'robots.txt', 'Refund.html', 'ads.txt']
    return pages + assets


def fetch(url):
    request = Request(url, headers={'User-Agent': 'DFB-release-verification/1.1'})
    with urlopen(request, timeout=25) as response:
        return response.status, response.read(), dict(response.headers.items())


def check(path, base, root=ROOT, fetcher=fetch):
    expected = normalized((root / path).read_bytes())
    url = base.rstrip('/') + ('/' if path == 'index.html' else '/'+path[:-10] if path.endswith('/index.html') else '/' + path)
    row = {'path': path, 'url': url, 'matches': False}
    try:
        status, body, headers = fetcher(url)
        row.update(status=status, matches=status == 200 and normalized(body) == expected,
                   response_sha256=hashlib.sha256(normalized(body)).hexdigest(),
                   expected_sha256=hashlib.sha256(expected).hexdigest(),
                   headers={k.lower(): v for k, v in headers.items()
                            if k.lower() in {'cache-control', 'age', 'etag',
                                             'last-modified', 'x-cache', 'date'}})
        if not row['matches']:
            # Never promote this diagnostic to the canonical URL's result.
            fresh_status, fresh_body, _ = fetcher(url + '?dfb_review=' + str(time.time_ns()))
            row['cache_busted_matches'] = fresh_status == 200 and normalized(fresh_body) == expected
    except (OSError, HTTPError, ValueError) as error:
        row['error'] = str(error)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://dividendforensics.com')
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--output', type=Path, default=ROOT / '.qa/live-verification.json')
    args = parser.parse_args()
    if not 1 <= args.attempts <= 21 or not 1 <= args.interval <= 60:
        parser.error('Use 1–21 attempts and a 1–60 second retry interval.')
    pending = targets()
    results = {}
    history = []
    for attempt in range(args.attempts):
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda path: check(path, args.base), pending))
        results.update({row['path']: row for row in rows})
        pending = [row['path'] for row in rows if not row['matches']]
        history.append({'attempt': attempt + 1, 'remaining': pending})
        if not pending:
            break
        if attempt + 1 < args.attempts:
            time.sleep(args.interval)
    report = {'passed': not pending, 'checked': len(results),
              'matched': sum(row['matches'] for row in results.values()),
              'failures': [results[path] for path in pending],
              'history': history, 'responses': list(results.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'responses'}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
