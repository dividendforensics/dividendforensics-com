from pathlib import Path
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
class CalculatorSafety(unittest.TestCase):
    def test_all_twenty_calculator_forms_start_disabled(self):
        found=[]
        for path in list(ROOT.glob('calculator-*.html'))+[p for loc in ('es','de','ja','zh-hant') for p in (ROOT/loc).glob('*.html')]:
            soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
            for form in soup.select('form.calculator-form'):
                found.append(path)
                controls=form.select_one('fieldset[data-calculator-controls][disabled]')
                self.assertIsNotNone(controls,path)
                for control in form.select('input,select,textarea,button'):
                    self.assertIn(controls,control.parents,path)
        self.assertEqual(len(found),20)
    def test_locales_and_accounting_terms(self):
        for folder,locale in [('de','de_DE'),('ja','ja_JP'),('zh-hant','zh_TW')]:
            for path in (ROOT/folder).glob('*.html'):
                soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
                self.assertEqual(soup.select_one('meta[property="og:locale"]')['content'],locale)
        de=(ROOT/'de/comparison.html').read_text(encoding='utf-8')
        zh=(ROOT/'zh-hant/comparison.html').read_text(encoding='utf-8')
        self.assertNotIn('nicht mehr verzinste Problemkredite',de)
        self.assertIn('periodengerechter Erfassung von Zinserträgen',de)
        self.assertNotIn('停止計息貸款',zh)
        self.assertIn('停止應計利息收入',zh)
