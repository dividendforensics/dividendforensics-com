"""Read-only release check: ordinary public URLs must match the saved site.

A cache-busted response is diagnostic evidence only; it can never make a stale
canonical response pass. Does not purge caches, submit forms or change hosting.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import argparse
import hashlib
import json
import os
import subprocess
import time
from time import sleep as retry_sleep

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
              'research-desk.css', 'spanish-calculators.js', 'sitemap.xml', 'robots.txt', 'Refund.html', 'ads.txt', 'research-resources.css', 'research-worksheet.js', 'lesson-formats.css']
    return pages + assets + ['international.css', 'international-calculators.js', 'content/filing-labs.json',
                             'operating-companies.css', 'operating-calculators.js', 'content/operating-company-lab.json']


def fetch(url):
    request = Request(url, headers={'User-Agent': 'DFB-release-verification/1.1'})
    with urlopen(request, timeout=25) as response:
        return response.status, response.read(), dict(response.headers.items())


def check(path, base, root=ROOT, fetcher=fetch):
    url = base.rstrip('/') + ('/' if path == 'index.html' else '/'+path[:-10] if path.endswith('/index.html') else '/' + path)
    row = {'path': path, 'url': url, 'matches': False}
    try:
        expected = normalized((root / path).read_bytes())
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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def provenance(root=ROOT):
    def revision(ref):
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', ref], cwd=root, text=True,
                stderr=subprocess.DEVNULL, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            return None

    # Only public run identifiers are saved; never serialize the environment.
    keys = ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
            'GITHUB_EVENT_NAME', 'DFB_PAGES_RUN_ID', 'DFB_PAGES_RUN_URL',
            'DFB_PAGES_SHA')
    return {'source_commit': revision('HEAD'), 'source_tree': revision('HEAD^{tree}'),
            'normalization': 'CRLF to LF, then strip leading and trailing whitespace',
            'provenance': {key: os.environ[key] for key in keys if os.environ.get(key)}}


def save_report(report, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report['updated_at'] = utc_now()
    temporary = output.with_suffix(output.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    temporary.replace(output)


def verify(paths, base, output, attempts=1, interval=30, root=ROOT, fetcher=fetch):
    paths = list(dict.fromkeys(paths))
    pending = paths[:]
    results = {}
    report = {'passed': False, 'complete': False, 'expected': len(paths),
              'checked': 0, 'matched': 0, 'unchecked': paths[:], 'failures': [],
              'history': [], 'responses': [], 'base': base,
              'started_at': utc_now(), **provenance(root)}
    save_report(report, output)

    def persist():
        report.update(checked=len(results),
                      matched=sum(row['matches'] for row in results.values()),
                      unchecked=[path for path in paths if path not in results],
                      failures=[results[path] for path in paths
                                if path in results and not results[path]['matches']],
                      responses=[results[path] for path in paths if path in results])
        save_report(report, output)

    try:
        for attempt in range(attempts):
            history = {'attempt': attempt + 1, 'complete': False, 'remaining': pending[:]}
            report['history'].append(history)
            persist()
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(check, path, base, root, fetcher) for path in pending]
                for future in as_completed(futures):
                    row = future.result()
                    results[row['path']] = row
                    history['remaining'] = [path for path in pending
                                            if path not in results or not results[path]['matches']]
                    # A killed/timed-out process leaves an explicitly incomplete report.
                    persist()
            pending = history['remaining'][:]
            history['complete'] = True
            persist()
            if not pending:
                break
            if attempt + 1 < attempts:
                retry_sleep(interval)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        persist()
        return report

    report['complete'] = bool(paths) and len(results) == len(paths)
    report['passed'] = report['complete'] and not pending
    report['completed_at'] = utc_now()
    persist()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://dividendforensics.com')
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--output', type=Path, default=ROOT / '.qa/live-verification.json')
    args = parser.parse_args()
    if not 1 <= args.attempts <= 21 or not 1 <= args.interval <= 60:
        parser.error('Use 1–21 attempts and a 1–60 second retry interval.')
    report = verify(targets(), args.base, args.output, args.attempts, args.interval)
    print(json.dumps({k: v for k, v in report.items() if k != 'responses'}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
