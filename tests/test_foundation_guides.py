import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from foundation_guides import outputs,GUIDE
ROOT=Path(__file__).resolve().parents[1]
class FoundationGuideTests(unittest.TestCase):
    def test_reviewed_source_renders_without_private_notes(self):
        page=BeautifulSoup(outputs(ROOT)[ROOT/'three-financial-statements.html'],'html.parser')
        template=BeautifulSoup((ROOT/'templates/foundations/three-financial-statements.html').read_text(),'html.parser')
        self.assertEqual(page.select_one('article').get_text(),template.get_text())
        self.assertNotIn('PRIVATE SOURCE',str(page))
        self.assertEqual(page.h1.get_text(),GUIDE['title'])
        text=page.select_one('article').get_text(' ')
        for required in ('hypothetical example, not Apple','USD millions','no restricted cash',
                         '50 + 30 − 20 − 8 + 1 = 53','Financing cash flow is not free cash flow'):
            self.assertIn(required,text)
        article=next(json.loads(s.string) for s in page.select('script[type="application/ld+json"]') if json.loads(s.string).get('@type')=='Article')
        self.assertEqual(article['author']['name'],'DFB Education')
        self.assertEqual(article['datePublished'],'2026-11-01')
        self.assertTrue(page.select('a[href="/filing-lab-apple-2024.html"]'))
    def test_primer_is_discoverable_without_relabeling_specialized_lessons(self):
        for name in ('index.html','learn.html','operating-companies.html','learning-search.html'):
            soup=BeautifulSoup((ROOT/name).read_text(),'html.parser')
            self.assertTrue(soup.select('a[href="/three-financial-statements.html"]'),name)
