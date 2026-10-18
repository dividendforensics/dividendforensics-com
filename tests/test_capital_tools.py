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
            self.assertIn('/capital-calculators.js',[s.get('src') for s in soup.find_all('script')])
    def test_no_remote_input_transmission(self):
        js=(ROOT/'capital-calculators.js').read_text(encoding='utf-8')
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage'):
            self.assertNotIn(forbidden,js)
if __name__=='__main__':unittest.main()
