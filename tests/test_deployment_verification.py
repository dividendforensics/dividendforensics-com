from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
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
