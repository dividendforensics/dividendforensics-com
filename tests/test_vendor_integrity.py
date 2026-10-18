from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VendorIntegrityTests(unittest.TestCase):
    def test_deployed_bytes_match_manifest_with_pinned_line_endings(self):
        entries = json.loads((ROOT / 'vendor/manifest.json').read_text(encoding='utf-8'))
        self.assertIn('vendor/decimal.js/* text eol=lf', (ROOT / '.gitattributes').read_text())
        for entry in entries:
            self.assertIn('LF', entry['files_hash_basis'])
            for name, expected in entry['files'].items():
                data = (ROOT / 'vendor' / entry['package'] / name).read_bytes()
                self.assertNotIn(b'\r\n', data, name)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected, name)
