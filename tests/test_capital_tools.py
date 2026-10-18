import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import capital_tools

ROOT=Path(__file__).resolve().parents[1]
class CapitalPages(unittest.TestCase):
    def test_three_original_pages(self):
        pages=capital_tools.outputs(ROOT)
        self.assertEqual(len(pages),3)
        for path,raw in pages.items():
            soup=BeautifulSoup(raw,'html.parser')
            self.assertEqual(len(soup.find_all('h1')),1)
            self.assertIn('Synthetic example',soup.get_text())
            self.assertIn('Formula and synthetic worked example',soup.get_text())
            self.assertIn('Questions readers ask',soup.get_text())
            self.assertGreater(len(soup.find('article').get_text().split()),500)
            self.assertEqual(soup.find('link',rel='canonical')['href'],'https://dividendforensics.com/'+path.name)
            for field in soup.select('form input,form select,form textarea'):
                self.assertIsNotNone(soup.find('label',attrs={'for':field['id']}))
            self.assertIn('/capital-calculators.js',[s.get('src','').split('?')[0] for s in soup.find_all('script')])
    def test_preferred_has_earnings_definition_without_debt_basis(self):
        raw=capital_tools.outputs(ROOT)[ROOT/'calculator-preferred-common.html']
        soup=BeautifulSoup(raw,'html.parser')
        self.assertIsNone(soup.select_one('[name=basis]'))
        self.assertIsNotNone(soup.select_one('[name=earningsDefinition]'))
        self.assertIsNotNone(soup.select_one('[name=earningsBasis]'))
        self.assertIn('Selected earnings measure and definition',soup.get_text())

    def test_fiscal_and_dated_labels_have_separate_meanings(self):
        raw=capital_tools.outputs(ROOT)[ROOT/'calculator-debt-ladder.html']
        soup=BeautifulSoup(raw,'html.parser')
        self.assertIn('Dated maturity cutoff',soup.find('label',attrs={'for':'capital-horizonEnd'}).get_text())
        self.assertIn('not a maturity cutoff',soup.find('label',attrs={'for':'capital-resourceDate'}).get_text())
        self.assertIsNotNone(soup.select_one('[data-fiscal-hint]'))
        self.assertTrue(soup.select_one('[name=resourceDate]').has_attr('disabled'))
        self.assertTrue(soup.find('label',attrs={'for':'capital-resourceDate'}).has_attr('hidden'))
        self.assertIn('Complete liquidity and residuals are not calculated',soup.get_text())
        self.assertIn('totals every supplied year bucket',soup.get_text())

    def test_no_remote_input_transmission(self):
        js=(ROOT/'capital-calculators.js').read_text(encoding='utf-8')
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage'):
            self.assertNotIn(forbidden,js)
if __name__=='__main__':unittest.main()
