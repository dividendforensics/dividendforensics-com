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
            self.assertEqual(soup.select_one('#filing-inputs h2').get_text(), 'How to use: find and match the inputs')
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
        for text in ['115.5/111/102','1.0043×/0.9652×/0.8870×','not cash earnings','Blank = not found','Formula version bdc-1.0.2','No automatic currency']:
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

    def test_pik_and_nii_are_expanded_before_the_input_form(self):
        pages=bdc_tools.outputs(ROOT)
        for name in ('calculator-bdc-nii-pik.html','calculator-bdc-pik-ratios.html'):
            soup=BeautifulSoup(pages[ROOT/name],'html.parser')
            intro=soup.select_one('[data-pik-introduction]')
            self.assertIsNotNone(intro,name)
            self.assertIn('PIK means payment-in-kind',intro.get_text())
            self.assertIn('net investment income (NII)',intro.get_text())
            self.assertIn('Total investment income (TII)',intro.get_text())
            self.assertIs(intro.find_next('form'),soup.select_one('[data-bdc-tool]'))
            self.assertFalse(intro.find_parent('form'))

    def test_nav_has_only_applicable_context_controls(self):
        from bdc_tools import TOOLS, page
        for tool in TOOLS:
            soup=BeautifulSoup(page(ROOT,tool),'html.parser')
            controls=soup.select('[name="incomeBasis"], [name="distributionBasis"]')
            self.assertEqual(len(controls),0 if tool['kind']=='nav' else 2)
            self.assertIn('Arithmetic precision does not increase the accuracy of the source inputs.',soup.get_text())

    def test_visible_availability_and_error_description_contract(self):
        for tool in bdc_tools.TOOLS:
            soup=BeautifulSoup(bdc_tools.page(ROOT,tool),'html.parser')
            controls=soup.select('[data-bdc-input]')
            self.assertEqual(len(soup.select('[data-bdc-status]')),len(controls))
            for control in controls:
                status=soup.find(id=control['name']+'-status')
                self.assertIsNone(status.find_parent('details'))
                self.assertIn(status['id'],control['aria-describedby'].split())
                self.assertIsNotNone(soup.select_one('[name="'+control['name']+'Availability"]'))
            error=soup.select_one('#bdc-input-error')
            self.assertEqual(error['role'],'alert')
            self.assertEqual(len(soup.select('.bdc-nav-notes')),2 if tool['kind']=='nav' else 0)
            self.assertIn('bdc-1.0.2-availability-1',str(soup))
        self.assertIn('.bdc-nav-notes>p{max-width:70ch}',(ROOT/'bureau.css').read_text())
        self.assertIn('.bdc-nav-notes>h2{margin-bottom:.5em}',(ROOT/'bureau.css').read_text())

if __name__=='__main__':unittest.main()
