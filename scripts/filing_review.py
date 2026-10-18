"""Manual SEC submissions discovery. Never imports into the public site build.

Standard library only. Filing text is never executed, rendered, or auto-published.
State, raw cache and explicit snapshot exports must live outside the served repo.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

VERSION = '1.0.0'
PUBLIC_ROOT = Path(__file__).resolve().parents[1]
FORMS = {'10-K', '10-Q', '8-K', '10-K/A', '10-Q/A', '8-K/A'}
ACCESSION = re.compile(r'\d{10}-\d{2}-\d{6}\Z')
CIK = re.compile(r'\d{10}\Z')
MAX_BODY = 10 * 1024 * 1024


class ReviewError(ValueError):
    pass


def iso_time():
    return datetime.now(timezone.utc).isoformat()


def outside_public(path, public_root=PUBLIC_ROOT):
    path = Path(path).resolve()
    if path == public_root or public_root in path.parents:
        raise ReviewError('State and exports must be outside the public repository')
    return path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path, default=None):
    if not Path(path).exists():
        return default
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise ReviewError('Stored JSON is unreadable; preserve and investigate it') from exc


@contextmanager
def lock(path):
    """Fail closed. A crash lock requires manual process check before removal."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise ReviewError('Another process or stale lock exists; inspect before retrying') from exc
    try:
        (path / 'owner.json').write_text(json.dumps({'pid': os.getpid(), 'started': iso_time()}), encoding='utf-8')
        yield
    finally:
        (path / 'owner.json').unlink(missing_ok=True)
        path.rmdir()


def validate_config(config):
    if not isinstance(config, dict):
        raise ReviewError('Configuration must be a JSON object')
    ua = config.get('declaredUserAgent')
    if not isinstance(ua, str) or len(ua) > 240 or '\n' in ua or '\r' in ua or not re.search(r'\S+@\S+\.\S+', ua):
        raise ReviewError('Set an actual organization/application and contact email in declaredUserAgent')
    companies = config.get('companies')
    if not isinstance(companies, list):
        raise ReviewError('companies must be an explicit CIK allowlist')
    seen = set()
    for entry in companies:
        cik = entry.get('cik') if isinstance(entry, dict) else None
        if not isinstance(cik, str) or not CIK.fullmatch(cik) or int(cik) == 0 or cik in seen:
            raise ReviewError('CIKs must be unique, nonzero ten-digit strings; preserve leading zeros')
        seen.add(cik)
        if not entry.get('verificationSource') or not isinstance(entry.get('name'), str) or not entry['name'].strip():
            raise ReviewError('Record company name and CIK verificationSource')
        if not isinstance(entry.get('forms'), list) or not entry['forms'] or not set(entry['forms']) <= FORMS:
            raise ReviewError('Only explicitly configured supported forms may be collected')
        if not isinstance(entry.get('enabled'), bool):
            raise ReviewError('enabled must be an explicit boolean')
    return config


def date_string(value, allow_empty=False):
    if value == '' and allow_empty:
        return value
    if not isinstance(value, str):
        raise ReviewError('Invalid ISO calendar date')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ReviewError('Invalid ISO calendar date') from exc
    if parsed.isoformat() != value:
        raise ReviewError('Use YYYY-MM-DD dates')
    return value


def records(payload, company, since):
    """Validate complete recent arrays before admitting any candidate for a CIK."""
    if not isinstance(payload, dict) or str(payload.get('cik', '')).zfill(10) != company['cik']:
        raise ReviewError('Submissions CIK does not match the allowed company')
    try:
        recent = payload['filings']['recent']
        columns = ['accessionNumber', 'filingDate', 'reportDate', 'form', 'primaryDocument']
        arrays = [recent[name] for name in columns]
    except (KeyError, TypeError) as exc:
        raise ReviewError('Missing recent submissions arrays') from exc
    if not all(isinstance(x, list) for x in arrays) or len({len(x) for x in arrays}) != 1:
        raise ReviewError('Submissions arrays are incomplete or unequal')
    output = []
    for accession, filed, period, form, document in zip(*arrays):
        if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
            raise ReviewError('Invalid accession')
        date_string(filed)
        date_string(period, allow_empty=True)
        if not isinstance(form, str) or not isinstance(document, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', document) or '..' in document:
            raise ReviewError('Unsafe document path or invalid form')
        if filed < since or form not in company['forms']:
            continue
        cik = company['cik']
        url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{document}'
        output.append({'key': cik + ':' + accession, 'cik': cik, 'company': company['name'],
                       'accession': accession, 'form': form, 'filing_date': filed,
                       'report_period': period or None, 'source_url': url,
                       'source_kind': 'SEC submissions metadata', 'input_method': 'metadata_api',
                       'is_amendment': form.endswith('/A'), 'metrics': None,
                       'status': 'needs_review', 'primary_document_fetched': False})
    return output


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReviewError('Redirects are not allowed')


def http_get(url, user_agent):
    """Only internally constructed, allowlisted submissions URLs, never queue links."""
    if not re.fullmatch(r'https://data\.sec\.gov/submissions/CIK\d{10}\.json', url):
        raise ReviewError('Only SEC submissions URLs are fetched')
    request = Request(url, headers={'User-Agent': user_agent, 'Accept': 'application/json'})
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ReviewError('SEC response exceeds size limit')
        return body


class Pipeline:
    def __init__(self, state_dir, config, *, transport=http_get, clock=time.time,
                 sleep=time.sleep, gate_dir=None):
        self.root = outside_public(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = validate_config(config)
        self.transport, self.clock, self.sleep = transport, clock, sleep
        self.gate = outside_public(gate_dir or Path.home() / '.dfb-sec-gate')
        self.state_path = self.root / 'state.json'

    def state(self):
        state = read_json(self.state_path, {'version': VERSION, 'candidates': {}, 'runs': [],
                                          'last_success_at': None, 'review_events': []})
        if not isinstance(state, dict) or not isinstance(state.get('candidates'), dict):
            raise ReviewError('Invalid state schema; do not overwrite')
        return state

    def request(self, cik):
        # Shared gate covers separate state directories on this machine. It serializes
        # all requests and enforces at least one second between request starts.
        with lock(self.gate / 'request.lock'):
            timer_path = self.gate / 'timer.json'
            timer = read_json(timer_path, {'next_request': 0})
            self.sleep(max(0, timer['next_request'] - self.clock()))
            atomic_json(timer_path, {'next_request': self.clock() + 1})
            try:
                return self.transport(f'https://data.sec.gov/submissions/CIK{cik}.json', self.config['declaredUserAgent'])
            except HTTPError as exc:
                if exc.code in (403, 429):
                    retry = exc.headers.get('Retry-After', '') if exc.headers else ''
                    try:
                        delay = max(60, int(retry))
                    except (ValueError, TypeError):
                        try:
                            delay = max(60, parsedate_to_datetime(retry).timestamp() - self.clock())
                        except (ValueError, TypeError, AttributeError, OverflowError):
                            delay = 900
                    atomic_json(timer_path, {'next_request': self.clock() + delay})
                raise

    def collect(self, since, *, use_cache=False, max_age=86400):
        date_string(since)
        if not isinstance(max_age, int) or max_age < 0:
            raise ReviewError('Cache age must be a nonnegative integer')
        with lock(self.root / 'run.lock'):
            state = self.state()
            baseline = not state['runs']
            report = {'started_at': iso_time(), 'mode': 'baseline' if baseline else 'overlap_review',
                      'since': since, 'companies': [], 'created': 0, 'status': 'success'}
            enabled = [x for x in self.config['companies'] if x['enabled']]
            if not enabled:
                report['status'] = 'no_targets'
            failures = 0
            for company in enabled:
                cik = company['cik']
                cache_path = self.root / 'cache' / (cik + '.json')
                item = {'cik': cik, 'status': 'success', 'cache': False, 'stale': False}
                try:
                    cached = read_json(cache_path)
                    if use_cache:
                        if not cached:
                            raise ReviewError('No validated cache exists')
                        payload = cached['payload']
                        item.update(cache=True, stale=self.clock() - cached['fetched_epoch'] > max_age,
                                    source_fetched_at=cached['fetched_at'])
                        digest = cached['sha256']
                    else:
                        raw = self.request(cik)
                        if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
                            raise ReviewError('Invalid response body')
                        payload = json.loads(raw.decode('utf-8'))
                        digest = hashlib.sha256(raw).hexdigest()
                    incoming = records(payload, company, since)
                    # Reject conflicting duplicates without replacing old metadata.
                    staged = {}
                    for record in incoming:
                        old = staged.get(record['key']) or state['candidates'].get(record['key'])
                        if old and any(old.get(k) != record[k] for k in ('cik', 'accession', 'form', 'filing_date', 'report_period', 'source_url')):
                            raise ReviewError('Conflicting metadata for existing accession')
                        staged[record['key']] = record
                    fetched_at = cached['fetched_at'] if use_cache else iso_time()
                    if not use_cache:
                        atomic_json(cache_path, {'payload': payload, 'sha256': digest,
                                                'fetched_at': fetched_at, 'fetched_epoch': self.clock()})
                    new_count = 0
                    for key, record in staged.items():
                        if key not in state['candidates']:
                            record.update(discovered_at=iso_time(), source_fetched_at=fetched_at,
                                          metadata_sha256=digest, baseline=baseline)
                            state['candidates'][key] = record
                            new_count += 1
                    item.update(found=len(staged), created=new_count, source_fetched_at=fetched_at,
                                historical_files_not_fetched=bool(payload.get('filings', {}).get('files')))
                    report['created'] += new_count
                except (ReviewError, ValueError, KeyError, TypeError, UnicodeError, OSError, URLError) as exc:
                    failures += 1
                    # Never log remote body/exception text (may contain secrets/HTML).
                    code = f'http_{exc.code}' if isinstance(exc, HTTPError) else type(exc).__name__
                    item.update(status='fetch_failed' if isinstance(exc, (OSError, URLError)) else 'parse_failed', error=code)
                report['companies'].append(item)
                if item.get('error') in ('http_403', 'http_429'):
                    # Pause the whole run rather than hammering more issuers.
                    report['unattempted'] = [x['cik'] for x in enabled[len(report['companies']):]]
                    break
            # Relations are candidates, never a claim that a specific amendment
            # replaces one particular same-period original or its metrics.
            for record in state['candidates'].values():
                record['related_accessions'] = sorted(x['accession'] for x in state['candidates'].values()
                    if x['key'] != record['key'] and x['cik'] == record['cik']
                    and record['report_period'] is not None and x['report_period'] == record['report_period']
                    and x['form'].removesuffix('/A') == record['form'].removesuffix('/A'))
            if failures:
                report['status'] = 'partial_failure' if any(x['status'] == 'success' for x in report['companies']) else 'failed'
            fresh = enabled and not failures and not use_cache and not report.get('unattempted')
            if fresh:
                state['last_success_at'] = iso_time()
            report.update(finished_at=iso_time(), last_success_at=state['last_success_at'])
            state['runs'].append(report)
            atomic_json(self.state_path, state)
            return report

    def review(self, key, decision, record):
        if decision not in ('approved', 'review_rejected'):
            raise ReviewError('Decision must be approved or review_rejected')
        with lock(self.root / 'run.lock'):
            state = self.state()
            candidate = state['candidates'].get(key)
            if not candidate:
                raise ReviewError('Unknown candidate')
            validate_review(record, candidate, decision)
            event = {'candidate_key': key, 'decision': decision, 'recorded_at': iso_time(),
                     'record': record, 'record_sha256': hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(),
                     'provenance': 'operator_supplied_manual_record; not independent verification'}
            state['review_events'].append(event)
            candidate['status'] = decision
            atomic_json(self.state_path, state)
            return event

    def export(self, output):
        output = outside_public(output)
        if output == self.state_path or self.root in output.parents:
            raise ReviewError('Export must use a separate directory outside pipeline state')
        with lock(self.root / 'run.lock'):
            state = self.state()
            latest = {x['candidate_key']: x for x in state['review_events']}
            selected = []
            for key, event in latest.items():
                if event['decision'] == 'approved':
                    candidate = state['candidates'][key]
                    validate_review(event['record'], candidate, 'approved')
                    selected.append({'candidate': candidate, 'review': event})
            if not selected:
                raise ReviewError('No approved records; existing snapshot preserved')
            snapshot = {'version': VERSION, 'exported_at': iso_time(), 'publication_status': 'not_published',
                        'review_claim': 'operator-supplied records, not independent verification',
                        'records': sorted(selected, key=lambda x: x['candidate']['key'])}
            atomic_json(output, snapshot)
            return snapshot


def validate_review(record, candidate, decision):
    if not isinstance(record, dict):
        raise ReviewError('Review record must be an object')
    for name in ('reviewer', 'reviewed_at', 'notes'):
        if not isinstance(record.get(name), str) or not record[name].strip():
            raise ReviewError('Actual reviewer, timestamp and notes are required')
    try:
        timestamp = datetime.fromisoformat(record['reviewed_at'])
        if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
            raise ValueError()
    except ValueError as exc:
        raise ReviewError('Review timestamp must be a real past timezone-aware time') from exc
    if decision == 'review_rejected':
        return
    fields = record.get('fields')
    if not isinstance(fields, list) or not fields:
        raise ReviewError('Approval needs manually sourced field records')
    names = set()
    for field in fields:
        if not isinstance(field, dict):
            raise ReviewError('Each field must be an object')
        for name in ('name', 'source_url', 'document_location', 'period', 'unit', 'currency', 'basis', 'input_method'):
            if not isinstance(field.get(name), str) or not field[name].strip():
                raise ReviewError('Each field needs source/location/period/unit/currency/basis/method')
        if field['name'] in names or field['input_method'] != 'manual':
            raise ReviewError('Unique manual field records required')
        names.add(field['name'])
        source = urlsplit(field['source_url'])
        expected = urlsplit(candidate['source_url'])
        prefix = expected.path.rsplit('/', 1)[0] + '/'
        if source.scheme != 'https' or source.netloc != 'www.sec.gov' or not source.path.startswith(prefix) or '..' in source.path or source.query:
            raise ReviewError('Field source must be an SEC document from this accession')
        if 'value' not in field:
            raise ReviewError('Missing values must be explicit null, never implicitly zero')
        value = field['value']
        if value is None:
            if not isinstance(field.get('missing_reason'), str) or not field['missing_reason'].strip():
                raise ReviewError('Null needs missing_reason')
        elif not isinstance(value, str) or not re.fullmatch(r'-?\d+(?:\.\d+)?', value) or len(value) > 100:
            raise ReviewError('Use finite decimal strings (or explicit null); no float/coercion')
        else:
            try:
                if not Decimal(value).is_finite():
                    raise InvalidOperation()
            except InvalidOperation as exc:
                raise ReviewError('Invalid decimal') from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--state-dir', required=True, type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    collect = commands.add_parser('collect')
    collect.add_argument('--since', required=True)
    collect.add_argument('--cache-only', action='store_true')
    collect.add_argument('--max-cache-age', type=int, default=86400)
    review = commands.add_parser('review')
    review.add_argument('--key', required=True)
    review.add_argument('--decision', choices=['approved', 'review_rejected'], required=True)
    review.add_argument('--record', type=Path, required=True)
    export = commands.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    pipeline = Pipeline(args.state_dir, read_json(args.config))
    if args.command == 'collect':
        result = pipeline.collect(args.since, use_cache=args.cache_only, max_age=args.max_cache_age)
    elif args.command == 'review':
        event = pipeline.review(args.key, args.decision, read_json(args.record))
        result = {'candidate_key': event['candidate_key'], 'decision': event['decision']}
    else:
        snapshot = pipeline.export(args.output)
        result = {'records': len(snapshot['records']), 'publication_status': snapshot['publication_status']}
    print(json.dumps(result, ensure_ascii=False))
    if result.get('status') in ('failed', 'partial_failure'):
        return 2
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ReviewError as error:
        raise SystemExit(str(error))
