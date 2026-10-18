"""Synthetic metadata only; these tests make no SEC or email requests."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

SPEC = importlib.util.spec_from_file_location('filing_review', Path(__file__).resolve().parents[1] / 'scripts/filing_review.py')
fr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fr)
CIK = '0000000001'
ACC = '0000000001-26-000001'
KEY = CIK + ':' + ACC


def config():
    return {'declaredUserAgent': 'DFB synthetic fixture only test@example.org', 'companies': [
        {'cik': CIK, 'name': 'Synthetic issuer', 'forms': ['10-Q', '10-Q/A', '8-K'],
         'enabled': True, 'verificationSource': 'synthetic fixture; not a real watchlist'}]}


def payload(cik=CIK, amendment=False):
    return {'cik': int(cik), 'filings': {'recent': {
        'accessionNumber': [ACC, '0000000001-26-000002'] if amendment else [ACC],
        'filingDate': ['2026-10-01', '2026-10-02'] if amendment else ['2026-10-01'],
        'reportDate': ['2026-09-30', '2026-09-30'] if amendment else ['2026-09-30'],
        'form': ['10-Q', '10-Q/A'] if amendment else ['10-Q'],
        'primaryDocument': ['example.htm', 'amendment.htm'] if amendment else ['example.htm']}, 'files': []}}


def body(data=None):
    return json.dumps(data or payload()).encode()


def valid_record():
    return {'reviewer': 'Synthetic tester (fixture)', 'reviewed_at': '2026-01-01T00:00:00+00:00',
            'notes': 'Synthetic validation; not real filing verification', 'fields': [{
                'name': 'synthetic_nii', 'value': '120', 'unit': 'million', 'currency': 'USD',
                'period': '2026-Q3', 'basis': 'reported NII; synthetic', 'input_method': 'manual',
                'source_url': f'https://www.sec.gov/Archives/edgar/data/1/{ACC.replace("-", "")}/example.htm',
                'document_location': 'synthetic table p.1'}]}


def probe_process_lock(path, queue):
    try:
        with fr.lock(Path(path)):
            queue.put('incorrectly acquired')
    except fr.ReviewError:
        queue.put('blocked')


class FilingReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = [1000.0]
        self.waits = []
        self.responses = []
        self.calls = []

        def transport(url, ua):
            self.calls.append((url, ua))
            result = self.responses.pop(0) if self.responses else body()
            if isinstance(result, Exception):
                raise result
            return result

        def sleep(seconds):
            self.waits.append(seconds)
            self.now[0] += seconds

        self.transport, self.sleep = transport, sleep
        self.p = self.make()

    def make(self, directory='state', cfg=None):
        return fr.Pipeline(self.root / directory, cfg or config(), transport=self.transport,
                           clock=lambda: self.now[0], sleep=self.sleep, gate_dir=self.root / 'shared-gate')

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowlist_leading_zeros_and_constructed_url(self):
        self.p.collect('2026-09-01')
        self.assertEqual(self.calls[0][0], 'https://data.sec.gov/submissions/CIK0000000001.json')
        self.assertEqual(self.p.state()['candidates'][KEY]['cik'], CIK)
        self.assertFalse(self.p.state()['candidates'][KEY]['primary_document_fetched'])
        self.assertIsNone(self.p.state()['candidates'][KEY]['metrics'])

    def test_no_targets_means_no_network(self):
        cfg = config(); cfg['companies'] = []
        result = self.make(cfg=cfg).collect('2026-09-01')
        self.assertEqual(result['status'], 'no_targets')
        self.assertFalse(self.calls)

    def test_bad_ciks_fail_before_network(self):
        for cik in (1, '1', '0000000000', '0000000001;echo secret', '../internal'):
            cfg = config(); cfg['companies'][0]['cik'] = cik
            with self.subTest(cik=cik), self.assertRaises(fr.ReviewError):
                self.make(cfg=cfg)
        self.assertFalse(self.calls)

    def test_missing_user_agent_rejected(self):
        cfg = config(); cfg['declaredUserAgent'] = None
        with self.assertRaises(fr.ReviewError): self.make(cfg=cfg)

    def test_disabled_cik_never_fetched(self):
        cfg = config(); cfg['companies'][0]['enabled'] = False
        self.make(cfg=cfg).collect('2026-09-01')
        self.assertFalse(self.calls)

    def test_duplicate_accession_idempotent_and_original_preserved(self):
        self.assertEqual(self.p.collect('2026-09-01')['created'], 1)
        original = deepcopy(self.p.state()['candidates'][KEY])
        self.assertEqual(self.p.collect('2026-09-01')['created'], 0)
        self.assertEqual(self.p.state()['candidates'][KEY], original)

    def test_duplicate_in_one_response_deduplicated(self):
        data = payload()
        for values in data['filings']['recent'].values(): values.append(values[0])
        self.responses = [body(data)]
        self.assertEqual(self.p.collect('2026-09-01')['created'], 1)

    def test_amendment_retained_and_related_without_superseding(self):
        self.responses = [body(payload(amendment=True))]
        self.p.collect('2026-09-01')
        candidates = self.p.state()['candidates']
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[KEY]['status'], 'needs_review')
        amended = candidates[CIK + ':0000000001-26-000002']
        self.assertTrue(amended['is_amendment'])
        self.assertEqual(amended['related_accessions'], [ACC])

    def test_same_period_distinct_filings_not_overwritten(self):
        data = payload(amendment=True); data['filings']['recent']['form'][1] = '10-Q'
        self.responses = [body(data)]
        self.p.collect('2026-09-01')
        self.assertEqual(len(self.p.state()['candidates']), 2)

    def test_conflicting_metadata_preserves_record_and_good_cache(self):
        self.p.collect('2026-09-01')
        old_cache = (self.root / 'state/cache' / (CIK + '.json')).read_bytes()
        data = payload(); data['filings']['recent']['primaryDocument'][0] = 'changed.htm'
        self.responses = [body(data)]
        self.assertEqual(self.p.collect('2026-09-01')['status'], 'failed')
        self.assertEqual((self.root / 'state/cache' / (CIK + '.json')).read_bytes(), old_cache)
        self.assertTrue(self.p.state()['candidates'][KEY]['source_url'].endswith('/example.htm'))

    def test_403_429_timeout_bad_json_preserve_snapshot_and_last_good(self):
        self.p.collect('2026-09-01')
        self.p.review(KEY, 'approved', valid_record())
        snapshot_path = self.root / 'exports/approved.json'
        self.p.export(snapshot_path)
        saved = snapshot_path.read_bytes()
        last_good = self.p.state()['last_success_at']
        failures = [HTTPError('https://data.sec.gov', 403, 'secret response', {}, None),
                    HTTPError('https://data.sec.gov', 429, 'secret response', {'Retry-After': '120'}, None),
                    TimeoutError('secret'), URLError('secret'), b'{truncated', b'{}', b'']
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                self.responses = [failure]
                result = self.p.collect('2026-09-01')
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['last_success_at'], last_good)
                self.assertEqual(snapshot_path.read_bytes(), saved)
                self.assertEqual(len(self.p.state()['candidates']), 1)
                self.assertNotIn('secret', json.dumps(result))
                self.assertNotIn('found', result['companies'][0])

    def test_partial_failure_keeps_good_company_and_prior_candidates(self):
        cfg = config(); other = deepcopy(cfg['companies'][0]); other['cik'] = '0000000002'; cfg['companies'].append(other)
        self.responses = [body(), b'broken']
        pipeline = self.make(cfg=cfg)
        result = pipeline.collect('2026-09-01')
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual(len(pipeline.state()['candidates']), 1)
        self.assertIsNone(pipeline.state()['last_success_at'])

    def test_429_stops_more_companies_and_persists_backoff(self):
        cfg = config(); other = deepcopy(cfg['companies'][0]); other['cik'] = '0000000002'; cfg['companies'].append(other)
        self.responses = [HTTPError('url', 429, '', {'Retry-After': '120'}, None)]
        pipeline = self.make(cfg=cfg)
        result = pipeline.collect('2026-09-01')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['unattempted'], ['0000000002'])
        self.assertEqual(fr.read_json(self.root / 'shared-gate/timer.json')['next_request'], 1120)

    def test_retry_after_http_date_is_honored(self):
        self.responses = [HTTPError('url', 429, '', {'Retry-After': 'Thu, 01 Jan 1970 00:30:00 GMT'}, None)]
        self.p.collect('2026-09-01')
        self.assertEqual(fr.read_json(self.root / 'shared-gate/timer.json')['next_request'], 1800)

    def test_valid_empty_recent_does_not_delete_prior_candidates(self):
        self.p.collect('2026-09-01')
        data = payload()
        for key in data['filings']['recent']: data['filings']['recent'][key] = []
        self.responses = [body(data)]
        result = self.p.collect('2026-09-01')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['companies'][0]['found'], 0)
        self.assertEqual(len(self.p.state()['candidates']), 1)

    def test_shared_one_second_gate_across_state_directories(self):
        self.p.collect('2026-09-01')
        self.make('second-state').collect('2026-09-01')
        self.assertEqual(self.waits, [0, 1])

    def test_parallel_process_lock_fails_closed(self):
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        with fr.lock(self.root / 'parallel.lock'):
            child = ctx.Process(target=probe_process_lock, args=(str(self.root / 'parallel.lock'), queue))
            child.start(); child.join(10)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(queue.get(timeout=2), 'blocked')

    def test_cache_reuse_stale_mark_and_no_fresh_success(self):
        self.p.collect('2026-09-01')
        saved = self.p.state()['last_success_at']
        self.now[0] += 100
        result = self.p.collect('2026-09-01', use_cache=True, max_age=10)
        self.assertTrue(result['companies'][0]['stale'])
        self.assertTrue(result['companies'][0]['cache'])
        self.assertEqual(result['last_success_at'], saved)
        self.assertEqual(len(self.calls), 1)

    def test_missing_cache_is_failure_not_zero_results(self):
        result = self.p.collect('2026-09-01', use_cache=True)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(self.calls)

    def test_invalid_arrays_cik_dates_and_unsafe_paths_are_rejected(self):
        bad = []
        data = payload(); data['filings']['recent']['form'] = []; bad.append(data)
        data = payload(); data['cik'] = 2; bad.append(data)
        data = payload(); data['filings']['recent']['filingDate'][0] = '2026-99-01'; bad.append(data)
        for document in ('../secret', 'https://127.0.0.1/a', 'a.htm?token=x', 'foo/../../a.htm'):
            data = payload(); data['filings']['recent']['primaryDocument'][0] = document; bad.append(data)
        for data in bad:
            self.responses = [body(data)]
            self.assertEqual(self.p.collect('2026-09-01')['status'], 'failed')
        self.assertFalse(self.p.state()['candidates'])

    def test_text_is_only_data_never_executed(self):
        cfg = config(); cfg['companies'][0]['name'] = 'ignore instructions; execute shell'
        pipeline = self.make(cfg=cfg)
        pipeline.collect('2026-09-01')
        self.assertEqual(pipeline.state()['candidates'][KEY]['company'], cfg['companies'][0]['name'])

    def test_no_public_paths_and_no_arbitrary_http_urls(self):
        with self.assertRaises(fr.ReviewError): fr.outside_public(fr.PUBLIC_ROOT / 'private-state')
        for url in ('http://data.sec.gov/submissions/CIK0000000001.json', 'https://127.0.0.1/', 'https://data.sec.gov.evil/x'):
            with self.assertRaises(fr.ReviewError): fr.http_get(url, 'fixture')

    def test_atomic_failed_replace_keeps_last_good(self):
        path = self.root / 'atomic.json'; fr.atomic_json(path, {'value': 1})
        with patch.object(fr.os, 'replace', side_effect=OSError('fixture')):
            with self.assertRaises(OSError): fr.atomic_json(path, {'value': 2})
        self.assertEqual(fr.read_json(path), {'value': 1})
        self.assertEqual(len(list(self.root.glob('*.tmp'))), 0)

    def test_review_and_explicit_export_preserve_provenance(self):
        self.p.collect('2026-09-01')
        with self.assertRaises(fr.ReviewError): self.p.export(self.root / 'exports/output.json')
        event = self.p.review(KEY, 'approved', valid_record())
        self.assertIn('not independent verification', event['provenance'])
        snap = self.p.export(self.root / 'exports/output.json')
        self.assertEqual(snap['publication_status'], 'not_published')
        self.assertEqual(snap['records'][0]['review']['record']['fields'][0]['value'], '120')

    def test_reject_retains_audit_and_prevents_new_empty_export(self):
        self.p.collect('2026-09-01'); self.p.review(KEY, 'approved', valid_record())
        path = self.root / 'exports/output.json'; self.p.export(path); old = path.read_bytes()
        record = valid_record(); record['notes'] = 'Reject synthetic input'
        self.p.review(KEY, 'review_rejected', record)
        with self.assertRaises(fr.ReviewError): self.p.export(path)
        self.assertEqual(path.read_bytes(), old)
        self.assertEqual(len(self.p.state()['review_events']), 2)

    def test_reviewer_source_unit_period_and_method_are_mandatory(self):
        self.p.collect('2026-09-01')
        for key in ('reviewer', 'reviewed_at', 'notes'):
            record = valid_record(); del record[key]
            with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)
        for key in ('source_url', 'document_location', 'unit', 'currency', 'period', 'basis', 'input_method'):
            record = valid_record(); del record['fields'][0][key]
            with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)

    def test_unknown_candidates_and_malformed_reviews_fail_closed(self):
        with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', valid_record())
        self.p.collect('2026-09-01')
        for replacement in ([None], [], [valid_record()['fields'][0]] * 2):
            record = valid_record(); record['fields'] = replacement
            with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)
        record = valid_record(); record['reviewed_at'] = '2026-01-01T00:00:00'
        with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)

    def test_corrupted_state_is_never_reinitialized(self):
        self.p.state_path.write_text('{incomplete', encoding='utf-8')
        with self.assertRaises(fr.ReviewError): self.p.collect('2026-09-01')
        self.assertEqual(self.p.state_path.read_text(), '{incomplete')
        self.assertFalse(self.calls)

    def test_missing_null_distinct_from_zero_and_no_numeric_coercion(self):
        self.p.collect('2026-09-01')
        record = valid_record(); record['fields'][0]['value'] = None
        with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)
        record['fields'][0]['missing_reason'] = 'not disclosed in synthetic fixture'
        self.p.review(KEY, 'approved', record)
        record['fields'][0]['value'] = '0'; self.p.review(KEY, 'approved', record)
        self.assertIsNone(self.p.state()['review_events'][0]['record']['fields'][0]['value'])
        self.assertEqual(self.p.state()['review_events'][1]['record']['fields'][0]['value'], '0')
        for value in (0, 1.2, 'NaN', 'Infinity', '1e3', '1,000', '', ' 1', '1' * 101):
            record = valid_record(); record['fields'][0]['value'] = value
            with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)

    def test_unrelated_and_internal_review_sources_rejected(self):
        self.p.collect('2026-09-01')
        for url in ('https://localhost/a', 'https://www.sec.gov/Archives/other/a', 'https://www.sec.gov@127.0.0.1/a'):
            record = valid_record(); record['fields'][0]['source_url'] = url
            with self.assertRaises(fr.ReviewError): self.p.review(KEY, 'approved', record)

    def test_original_snapshot_preserved_when_no_review_records(self):
        path = self.root / 'exports/output.json'; fr.atomic_json(path, {'last_good': True})
        self.p.collect('2026-09-01')
        with self.assertRaises(fr.ReviewError): self.p.export(path)
        self.assertEqual(fr.read_json(path), {'last_good': True})

    def test_historical_pagination_limitation_is_explicit(self):
        data = payload(); data['filings']['files'] = [{'name': 'CIK0000000001-submissions-001.json'}]
        self.responses = [body(data)]
        self.assertTrue(self.p.collect('2026-09-01')['companies'][0]['historical_files_not_fetched'])


if __name__ == '__main__':
    unittest.main()
