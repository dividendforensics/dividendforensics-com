"""Independent source transcription and regression checks for the FY2025 exercise."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import equinix_filing_lab as lab


class EquinixFilingLabTests(unittest.TestCase):
    def test_all_seventeen_source_rows_and_totals(self):
        data = lab.load(ROOT)
        # Independently transcribed from the 2025 column, SEC 10-K p.61.
        expected = [20,5,-52,23,498,3,568,-1,200,16,-284,-1,33,18,68,-24,3]
        self.assertEqual([Fraction(r['value']) for r in data['adjustments']], expected)
        self.assertEqual([Fraction(r['value']) for r in data['ffoRows']], [1348,2,1350,1282,0,36,2668])
        self.assertEqual(sum(expected), 1093)
        self.assertEqual(sum(n for n in expected if n > 0), 1455)
        self.assertEqual(sum(n for n in expected if n < 0), -362)
        self.assertEqual(2668+sum(expected), Fraction(data['affo']))
        self.assertEqual(2668-284,2384)
        self.assertEqual(3761-2384,1377)
        self.assertEqual(498+568+200,1266)
        self.assertEqual(20+5-52,-27)

    def test_bad_source_sign_period_units_and_missing_rows_fail(self):
        original = lab.load(ROOT)
        mutations = [lambda d: d['adjustments'][10].update(value='284'),
                     lambda d: d['adjustments'].pop(),
                     lambda d: d['adjustments'][0].update(value=20),
                     lambda d: d['adjustments'][0].update(value='NaN'),
                     lambda d: d['adjustments'][0].update(unit='USD thousand'),
                     lambda d: d['adjustments'][0].update(periodEnd='2026-12-31'),
                     lambda d: d['adjustments'][0].update(sourceURL='https://example.com'),
                     lambda d: d.update(checkedOn='2025-12-31'),
                     lambda d: d.update(affo='3762')]
        for mutate in mutations:
            data=deepcopy(original);mutate(data)
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'content').mkdir()
                (root/'content/equinix-2025-affo.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): lab.load(root)

    def test_static_page_has_sources_dates_answers_and_accessible_tables(self):
        html=lab.outputs(ROOT)[ROOT/(lab.SLUG+'.html')]
        soup=BeautifulSoup(html,'html.parser')
        self.assertEqual(len(soup.select('h1')),1)
        self.assertEqual(soup.html['lang'],'en')
        ids=[node['id'] for node in soup.select('[id]')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(soup.select('article table')),2)
        self.assertEqual(len(soup.select('article table')[1].select('tbody tr')),19)
        for table in soup.select('article table'):
            self.assertTrue(table.caption)
            self.assertTrue(table.select('th[scope="row"]'))
            self.assertTrue(table.select('th[scope="col"]'))
            self.assertEqual(table.parent.get('tabindex'),'0')
        self.assertEqual(len(soup.select('details.workshop-answer')),5)
        self.assertTrue(soup.select('a[href="/content/equinix-2025-affo.json"]'))
        for a in soup.select('a[href]'):
            if a['href'].startswith('#'):self.assertIn(a['href'][1:],ids)
            if a.get('target')=='_blank':self.assertIn('noopener',a.get('rel',[]))
        schemas=[json.loads(s.string) for s in soup.select('script[type="application/ld+json"]')]
        article=next(s for s in schemas if s['@type']=='Article')
        self.assertEqual(article['datePublished'],'2026-11-10')
        self.assertEqual(article['dateModified'],'2026-11-10')
        self.assertEqual(article['author']['name'],'DFB Education')
        self.assertEqual(soup.select_one('link[rel="canonical"]')['href'], 'https://dividendforensics.com/'+lab.SLUG+'.html')
        self.assertNotIn('{{',html)
        self.assertIn('Subsequent quarters',soup.get_text())
        self.assertIn('Structural research, not investment advice.',soup.get_text())

    def test_home_discovery_and_news_preservation(self):
        home=BeautifulSoup((ROOT/'index.html').read_text(),'html.parser')
        hero=home.select_one('.cash-sheet')
        self.assertIn('USD millions',hero.get_text())
        self.assertTrue(hero.select('a[href="/filing-lab-equinix-2025.html"]'))
        self.assertIn('2,668',hero.get_text())
        self.assertIn('+1,455',hero.get_text())
        self.assertIn('−362',hero.get_text())
        self.assertIn('3,761',hero.get_text())
        for name in ('filing-labs.html','learning-search.html','learn-affo.html','learn-ffo.html','learn.html'):
            soup=BeautifulSoup((ROOT/name).read_text(),'html.parser')
            self.assertTrue(soup.select('a[href="/filing-lab-equinix-2025.html"]'),name)
        sitemap=(ROOT/'sitemap.xml').read_text()
        self.assertIn('/filing-lab-equinix-2025.html</loc><lastmod>2026-11-10</lastmod>',sitemap)


if __name__ == '__main__': unittest.main()
