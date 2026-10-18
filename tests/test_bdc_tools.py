import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import bdc_tools

ROOT=Path(__file__).resolve().parents[1]

class BdcToolsTests(unittest.TestCase):
    def test_five_unique_substantive_static_pages(self):
        pages=bdc_tools.outputs(ROOT)
        self.assertEqual(len(pages),5)
        for path,document in pages.items():
            soup=BeautifulSoup(document,'html.parser')
            self.assertEqual(len(soup.select('h1')),1,path)
            self.assertGreater(len(soup.select_one('main').get_text(' ',strip=True).split()),700,path)
            self.assertEqual(soup.select_one('link[rel=canonical]')['href'],'https://dividendforensics.com/'+path.name)
            self.assertIn('Synthetic example',soup.get_text())
            self.assertIn('Where to find the inputs.',soup.get_text())
            self.assertIn('Jeong-Mo Goo',soup.select_one('main').get_text())
            self.assertTrue(soup.select('[data-bdc-tool]'))
            self.assertFalse(soup.select('[data-calculator]'))
            self.assertTrue(soup.select('noscript'))

    def test_labels_scripts_source_fields_and_links(self):
        for path,document in bdc_tools.outputs(ROOT).items():
            soup=BeautifulSoup(document,'html.parser')
            ids=[node['id'] for node in soup.select('[id]')]
            self.assertEqual(len(ids),len(set(ids)),path)
            for node in soup.select('input,select,textarea'):
                self.assertTrue(soup.select('label[for="'+node['id']+'"]'),node)
            scripts=[s.get('src','').split('?')[0] for s in soup.select('script[src]')]
            self.assertLess(scripts.index('/vendor/decimal.js/decimal.js'),scripts.index('/bdc-calculators.js'))
            for node in soup.select('a[href^="/"]'):
                name=node['href'].split('#')[0].lstrip('/')
                if name:self.assertTrue((ROOT/name).exists(),(path,node['href']))

    def test_nii_static_example_and_safeguards(self):
        doc=bdc_tools.outputs(ROOT)[ROOT/'calculator-bdc-nii-pik.html']
        for text in ['115.5/111/102','1.0043×/0.9652×/0.8870×','not cash earnings','Blank = not found','Formula version bdc-1.0.1','No automatic currency']:
            self.assertIn(text,doc)

    def test_chronology_and_nav_snapshot_explanation_are_static(self):
        pages=bdc_tools.outputs(ROOT)
        for document in pages.values():
            self.assertIn('analysis as-of date must be on or after the reporting period end',document)
            self.assertIn('Analysis as-of date (not the quote date)',document)
            self.assertIn('period fields identify the reporting context, not an averaging interval',document)
        nav=pages[ROOT/'calculator-bdc-nav-discount.html']
        self.assertIn('NAV is a stock measure at its disclosed balance-sheet snapshot date',nav)
        self.assertIn('The market quote can have a different observation date',nav)
        self.assertIn('does not relabel either as a period-end quote',nav)

if __name__=='__main__':unittest.main()
