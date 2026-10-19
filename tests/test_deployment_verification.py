from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('live_check', ROOT / 'tools/verify_deployment.py')
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class DeploymentVerificationTests(unittest.TestCase):
    def test_stale_plain_response_cannot_pass_with_a_fresh_query(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sitemap.xml').write_bytes(b'current')
            urls = []
            def fetcher(url):
                urls.append(url)
                return 200, b'current' if '?' in url else b'old', {'Cache-Control': 'max-age=600'}
            result = live.check('sitemap.xml', 'https://example.com', root, fetcher)
            self.assertFalse(result['matches'])
            self.assertTrue(result['cache_busted_matches'])
            self.assertEqual(urls[0], 'https://example.com/sitemap.xml')
            self.assertEqual(result['headers']['cache-control'], 'max-age=600')

    def test_home_checks_its_canonical_root_and_no_diagnostic_when_matching(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_bytes(b'current\n')
            urls = []
            def fetcher(url):
                urls.append(url)
                return 200, b'current\r\n', {'ETag': 'example'}
            self.assertTrue(live.check('index.html', 'https://example.com/', root, fetcher)['matches'])
            self.assertEqual(urls, ['https://example.com/'])

    def test_fetch_error_is_a_failed_check(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'robots.txt').write_bytes(b'current')
            def fetcher(url):
                raise OSError('unavailable')
            result = live.check('robots.txt', 'https://example.com', root, fetcher)
            self.assertFalse(result['matches'])
            self.assertIn('unavailable', result['error'])

    def test_report_exists_before_requests_and_only_finishes_passed_after_all_results(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'report.json'
            (root / 'index.html').write_bytes(b'current')
            def fetcher(url):
                initial = json.loads(output.read_text())
                self.assertFalse(initial['passed'])
                self.assertFalse(initial['complete'])
                self.assertEqual(initial['unchecked'], ['index.html'])
                return 200, b'current', {}
            report = live.verify(['index.html'], 'https://example.com', output,
                                 root=root, fetcher=fetcher)
            saved = json.loads(output.read_text())
            self.assertTrue(saved['passed'])
            self.assertTrue(saved['complete'])
            self.assertEqual(saved['checked'], 1)
            self.assertEqual(saved['unchecked'], [])
            self.assertEqual(saved, report)
            self.assertTrue(saved['completed_at'].endswith('+00:00'))

    def test_completed_response_survives_a_later_worker_failure_without_passing(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'report.json'
            for name in ('first.html', 'second.html'):
                (root / name).write_bytes(b'current')
            first_saved = Event()
            original_save = live.save_report
            def save(report, destination):
                original_save(report, destination)
                if report['checked'] == 1:
                    first_saved.set()
            def fetcher(url):
                if url.endswith('second.html'):
                    self.assertTrue(first_saved.wait(5), 'First response was not persisted.')
                    partial = json.loads(output.read_text())
                    self.assertEqual(partial['responses'][0]['path'], 'first.html')
                    self.assertFalse(partial['passed'])
                    self.assertFalse(partial['complete'])
                    raise RuntimeError('simulated interruption')
                return 200, b'current', {}
            with patch.object(live, 'save_report', side_effect=save):
                live.verify(['first.html', 'second.html'], 'https://example.com', output,
                            root=root, fetcher=fetcher)
            saved = json.loads(output.read_text())
            self.assertFalse(saved['passed'])
            self.assertFalse(saved['complete'])
            self.assertEqual(saved['checked'], 1)
            self.assertEqual(saved['unchecked'], ['second.html'])
            self.assertIn('simulated interruption', saved['error'])

    def test_exhausted_retries_keep_canonical_mismatch_failed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'report.json'
            (root / 'index.html').write_bytes(b'current')
            urls = []
            def fetcher(url):
                urls.append(url)
                return 200, b'current' if '?' in url else b'old', {}
            with patch.object(live.time, 'sleep') as sleep:
                report = live.verify(['index.html'], 'https://example.com', output,
                                     attempts=2, interval=1, root=root, fetcher=fetcher)
            self.assertTrue(report['complete'])
            self.assertFalse(report['passed'])
            self.assertTrue(report['failures'][0]['cache_busted_matches'])
            self.assertEqual(urls.count('https://example.com/'), 2)
            self.assertEqual(len(report['history']), 2)
            sleep.assert_called_once_with(1)

    def test_provenance_includes_revisions_and_only_allowlisted_environment(self):
        environment = {'GITHUB_REPOSITORY': 'owner/site', 'GITHUB_RUN_ID': '123',
                       'DFB_PAGES_SHA': 'a' * 40, 'GH_TOKEN': 'never-save-this',
                       'PRODUCT_SECRET': 'never-save-this-either'}
        with patch.dict(live.os.environ, environment, clear=True), \
                patch.object(live.subprocess, 'check_output', side_effect=['a' * 40, 'b' * 40]):
            evidence = live.provenance()
        self.assertEqual(evidence['source_commit'], 'a' * 40)
        self.assertEqual(evidence['source_tree'], 'b' * 40)
        self.assertEqual(evidence['provenance']['GITHUB_RUN_ID'], '123')
        self.assertNotIn('never-save', json.dumps(evidence))

    def test_missing_local_file_is_recorded_as_failed_evidence(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            report = live.verify(['missing.html'], 'https://example.com', root / 'report.json',
                                 root=root)
            self.assertFalse(report['passed'])
            self.assertTrue(report['complete'])
            self.assertEqual(report['checked'], 1)
            self.assertIn('error', report['failures'][0])
