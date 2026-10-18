"""Reader-visible attribution and source parity across the published editions."""
import json
from pathlib import Path
import unittest
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import build_site
from international import LOCALES, PAGES, PROSPECT_FILING, PROSPECT_POLICY, path_for
from localized import PAIRS, url

ROOT = Path(__file__).resolve().parents[1]


class SearchTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build_site.planned_outputs(ROOT)

    def page(self, path):
        return BeautifulSoup(self.pages[ROOT/path], 'html.parser')

    def test_localized_sharing_metadata_matches_page_kind_and_canonical(self):
        paths = list(PAIRS.values()) + [path_for(locale, key) for locale in LOCALES for key in PAGES]
        for path in paths:
            with self.subTest(path=path):
                soup = self.page(path)
                schema = json.loads(soup.select_one('script[type="application/ld+json"]').string)
                expected = 'article' if schema['@type'] == 'Article' else 'website'
                self.assertEqual(len(soup.select('meta[property="og:type"]')), 1)
                self.assertEqual(soup.select_one('meta[property="og:type"]')['content'], expected)
                self.assertEqual(soup.select_one('meta[property="og:url"]')['content'], url(path))
                self.assertEqual(soup.select_one('link[rel="canonical"]')['href'], url(path))
                self.assertEqual(soup.select_one('meta[name="twitter:card"]')['content'], 'summary_large_image')

    def test_translation_bylines_expose_the_attribution_used_in_schema(self):
        paths = [path for english, path in PAIRS.items() if english.startswith('learn-')]
        paths += [path_for(locale, key) for locale in LOCALES for key in ('reit', 'bdc', 'coverage', 'comparison')]
        for path in paths:
            with self.subTest(path=path):
                soup = self.page(path)
                schema = json.loads(soup.select_one('script[type="application/ld+json"]').string)
                byline = soup.select_one('.article-meta a[href="/editorial-policy.html"]')
                self.assertIsNotNone(byline)
                self.assertEqual(byline.get_text(strip=True), schema['author']['name'])
                self.assertEqual(urljoin(url(path), byline['href']), schema['author']['url'])
                self.assertEqual(schema['dateModified'], soup.select_one('.article-meta time')['datetime'])

    def test_comparison_editions_share_a_traceable_historical_policy_source(self):
        for path in ['reit-vs-bdc.html'] + [path_for(locale, 'comparison') for locale in LOCALES]:
            with self.subTest(path=path):
                soup = self.page(path)
                note = soup.select_one('main .source-note')
                self.assertIsNotNone(note)
                self.assertIn('Prospect Capital', note.get_text())
                self.assertIn('2024', note.get_text())
                self.assertEqual({a['href'] for a in note.select('a')}, {PROSPECT_POLICY, PROSPECT_FILING})
                body = soup.select_one('main').get_text(' ', strip=True)
                position = body.index('PIK')
                self.assertIn('payment-in-kind', body[max(0, position-50):position+60].lower())

    def test_localized_pik_explanation_does_not_require_another_article(self):
        for locale in LOCALES:
            soup = self.page(path_for(locale, 'coverage'))
            body = soup.select_one('main').get_text(' ', strip=True)
            position = body.index('PIK')
            self.assertIn('payment-in-kind', body[max(0, position-50):position+60].lower())
        soup = self.page('es/calculadora-cobertura-affo.html')
        self.assertIn('payment-in-kind, PIK', soup.select_one('main').get_text())

    def test_specific_claims_link_to_tax_rule_and_interest_policy_sources(self):
        for locale in LOCALES:
            reit = self.page(path_for(locale, 'reit'))
            self.assertTrue(reit.select('#sources a[href="https://www.irs.gov/instructions/i1120rei"]'))
            coverage = self.page(path_for(locale, 'coverage'))
            self.assertTrue(coverage.select(f'#sources a[href="{PROSPECT_POLICY}"]'))


if __name__ == '__main__':
    unittest.main()
