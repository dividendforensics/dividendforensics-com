"""Instructions and dated practice routes must be visible without JavaScript."""
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from education import TOOLS, FILING_PRACTICE

ROOT = Path(__file__).resolve().parents[1]


class ToolReadingRoutes(unittest.TestCase):
    def page(self, name):
        return BeautifulSoup((ROOT/name).read_text(), 'html.parser')

    def test_six_short_tools_explain_the_source_to_input_boundary(self):
        self.assertEqual(len(FILING_PRACTICE),6)
        for tool in TOOLS:
            if tool['kind'] not in FILING_PRACTICE:
                continue
            page = self.page(tool['slug']+'.html')
            section = page.select_one('#filing-practice')
            self.assertIsNotNone(section,tool['slug'])
            self.assertTrue(page.select('a[href="#filing-practice"]'))
            self.assertTrue(section.select('a[href="/filing-lab-realty-income-2024.html"]'))
            self.assertIn('Assumptions and limitations',page.select_one('#limits').get_text())
            if tool['kind'] in ('return','reinvestment'):
                self.assertIn('transaction',section.get_text())
            if tool['kind'] in ('nav','refinancing'):
                self.assertIn('not a completed',section.get_text())

    def test_bdc_usage_and_limits_have_explicit_headings(self):
        for name in ('calculator-bdc-non-accrual.html','calculator-bdc-pik-ratios.html'):
            page = self.page(name)
            self.assertIn('How to use',page.select_one('#filing-inputs h2').get_text())
            self.assertEqual(page.select_one('#limits h2').get_text(),'Assumptions and limitations')

    def test_workbench_related_learning_block(self):
        page = self.page('cash-flow-workbench.html')
        block = page.select_one('#workbench-related').parent
        for link in ('operating-cash-flow-guide','dividends-buybacks-guide','filing-lab-apple-2024'):
            self.assertTrue(block.select(f'a[href="/{link}.html"]'))
        self.assertIn('not current company data',block.get_text())

    def test_date_guide_and_preferred_bridge_instructions(self):
        self.assertEqual(len(self.page('dividend-dates.html').select('#use-date-guide + ol > li')),4)
        text = self.page('calculator-preferred-common.html').get_text()
        self.assertIn('How to use: find the basis',text)
        self.assertIn('Assumptions and limitations:',text)
