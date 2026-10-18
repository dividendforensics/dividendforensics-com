import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import operating_companies as O

ROOT=Path(__file__).resolve().parents[1]


class OperatingPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages=O.outputs(ROOT)

    def test_four_substantive_distinct_pages(self):
        self.assertEqual({p.stem for p in self.pages},{p[0] for p in O.PAGES})
        for path,raw in self.pages.items():
            soup=BeautifulSoup(raw,'html.parser')
            self.assertEqual(len(soup.select('main h1')),1)
            self.assertEqual(soup.find('link',rel='canonical')['href'],'https://dividendforensics.com/'+path.name)
            self.assertGreater(len(soup.find('main').get_text().split()),450)
            self.assertIn(O.SEC_GUIDE,raw)
            self.assertIn(O.SEC_NONGAAP,raw)
            self.assertIn('operating-companies.css',raw)

    def test_workbench_gates_every_form_control_and_has_static_math(self):
        soup=BeautifulSoup(self.pages[ROOT/'cash-flow-workbench.html'],'html.parser')
        form=soup.select_one('form.calculator-form')
        self.assertIsNotNone(form.select_one('fieldset[data-calculator-controls][disabled]'))
        self.assertIsNotNone(form.select_one('[data-calculator-loading]'))
        self.assertFalse(form.has_attr('action'))
        for field in form.select('input,select'):
            self.assertIsNotNone(soup.find('label',attrs={'for':field['id']}))
            self.assertIsNotNone(field.find_parent('fieldset',disabled=True))
        for button in soup.select('[data-operating-export],[data-operating-baseline],[data-operating-clear]'):
            self.assertTrue(button.has_attr('disabled'))
        text=soup.get_text()
        for phrase in ['135 OCF','80 user-defined FCF','−15 residual','103 ending cash','Cash gap','subtracted','No data is sent or saved']:
            self.assertIn(phrase,text)
        scripts=[s.get('src','') for s in soup.find_all('script')]
        self.assertLess(scripts.index('/vendor/decimal.js/decimal.js'),scripts.index('/operating-calculators.js?v='+O.VERSION))

    def test_source_examples_are_inert_safe_json(self):
        examples=[{'id':'example','label':'</script><script>alert(1)</script>','values':{'scenarioLabel':'<b>test</b>'}}]
        soup=BeautifulSoup(O.workbench(ROOT,examples),'html.parser')
        embedded=soup.find('script',id='operating-examples')
        self.assertEqual(json.loads(embedded.string),examples)
        self.assertNotIn('<script>',embedded.string)

    def test_local_only_engine(self):
        js=(ROOT/'operating-calculators.js').read_text(encoding='utf-8')
        for forbidden in ['fetch(', 'XMLHttpRequest','localStorage','sessionStorage','sendBeacon','form.submit(']:
            self.assertNotIn(forbidden,js)
        self.assertIn('precision:80',js)
        self.assertIn('Base.clone',js)


if __name__=='__main__':
    unittest.main()
