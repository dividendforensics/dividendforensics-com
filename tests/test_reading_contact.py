"""Regression contracts for discoverability without invented publishing claims."""
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]

class ReadingContactTests(unittest.TestCase):
    def soup(self, name):
        return BeautifulSoup((ROOT / name).read_text(), 'html.parser')

    def test_home_search_targets_existing_library(self):
        form = self.soup('index.html').select_one('form.home-library-search')
        self.assertEqual(form['action'], '/learn.html#library')
        self.assertEqual(form['method'], 'get')
        self.assertIsNotNone(self.soup('learn.html').select_one('#library'))

    def test_contact_navigation_and_truthful_delivery_notice(self):
        for name in ('index.html', 'research.html', 'learn.html'):
            link = self.soup(name).select_one('footer a[href="/research-desk.html#inquiries"]')
            self.assertIsNotNone(link, name)
            self.assertEqual(link.get_text(), 'Contact / Corrections')
        desk = self.soup('research-desk.html')
        self.assertIsNotNone(desk.select_one('#inquiries'))
        self.assertIsNotNone(desk.select_one('a[href^="mailto:dividendforensics@gmail.com"]'))
        self.assertNotIn('One test submission', desk.get_text())
        self.assertIn('Send a question, correction or proposal using the form below.', desk.get_text())
        self.assertIn('If submission cannot be confirmed, your entries remain on this page.', desk.get_text())
        self.assertNotIn('has not yet completed an end-to-end inbox delivery check', desk.get_text())

    def test_contact_receipt_privacy_and_reader_route(self):
        privacy = self.soup('privacy.html').get_text()
        self.assertNotIn('One test submission', privacy)
        self.assertIn('FormSubmit privacy policy', privacy)
        self.assertIn('For questions about an inquiry or its personal information', privacy)
        self.assertNotIn('that test has not yet been completed', privacy)
        desk = self.soup('research-desk.html')
        self.assertIn('Questions, corrections and project proposals.', desk.select_one('#inquiries h2').get_text())
        self.assertIsNotNone(desk.select_one('#inquiries a[href="#proposal-form"]'))
        expected = {'/img/report001-recon.png': ('1242', '1437'), '/img/report001-ladder.png': ('1242', '1527')}
        for src, dimensions in expected.items():
            image = desk.select_one(f'img[src="{src}"]')
            self.assertEqual((image.get('width'), image.get('height')), dimensions)

    def test_onsite_labs_separate_from_external_records(self):
        soup = self.soup('research.html')
        labs = soup.select('[data-onsite-research] a')
        self.assertEqual(len(labs), 3)
        for link in labs:
            self.assertTrue((ROOT / link['href'].lstrip('/')).is_file())
        archive = soup.select_one('#research-archive')
        self.assertEqual(len(archive.select('article.archive-entry')), 20)
        self.assertTrue(archive.select('a[href^="https://www.benzinga.com/"]'))
        self.assertIsNotNone(soup.select_one('#external-research-title'))

if __name__ == '__main__':
    unittest.main()
