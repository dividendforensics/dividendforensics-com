import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from learning_search import records
from build_site import planned_outputs
ROOT=Path(__file__).resolve().parents[1]
class LearningSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages=planned_outputs(ROOT)
        cls.records=records(ROOT,cls.pages)
        cls.soup=BeautifulSoup(cls.pages[ROOT/'learning-search.html'],'html.parser')
    def test_actual_routes_and_unique_records(self):
        urls=[r['url'] for r in self.records]
        self.assertEqual(len(urls),len(set(urls)))
        for record in self.records:
            self.assertIn(ROOT/record['url'][1:],self.pages)
            self.assertTrue(record['description'])
        self.assertEqual(sum(r['url'].startswith('/learn-') and not r['url'].startswith('/learn-bdc') for r in self.records),36)
        self.assertEqual(sum(r['url'].startswith('/learn-bdc-') for r in self.records),16)
        self.assertFalse(any('brief-' in url or 'research-desk' in url for url in urls))
    def test_curated_topics_are_supported_by_actual_pages(self):
        supported={'stock-classification':['market cap'], 'market-labels':['ticker','S&P 500','EPS'],
                   'dividends-buybacks-guide':['buyback','free cash flow']}
        for slug, terms in supported.items():
            text=BeautifulSoup(self.pages[ROOT/(slug+'.html')],'html.parser').get_text(' ').lower()
            for term in terms:self.assertIn(term.lower(),text)
    def test_accessible_static_directory_and_escape_routes(self):
        ids=[el['id'] for el in self.soup.select('[id]')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(self.soup.select('[data-learning-result]')),len(self.records))
        for control in ('learning-query','learning-topic'):
            self.assertIsNotNone(self.soup.select_one(f'label[for="{control}"]'))
        self.assertEqual(self.soup.select_one('#learning-count')['role'],'status')
        self.assertGreaterEqual(len(self.soup.select('#learning-empty a')),4)
        self.assertIsNotNone(self.soup.select_one('noscript'))
    def test_reit_filter_remains_distinct(self):
        soup=BeautifulSoup(self.pages[ROOT/'learn.html'],'html.parser')
        self.assertEqual(len(soup.select('[data-lesson]')),36)
        self.assertIsNotNone(soup.select_one('#lesson-category'))
        self.assertIsNotNone(soup.select_one('#lesson-level'))
        self.assertIsNotNone(soup.select_one('#lesson-empty a[href="/learning-search.html#search-results"]'))
        self.assertIsNotNone(soup.select_one('a[href="/learning-search.html#search-results"]'))
    def test_stable_glossary_aliases_retain_definition_mapping(self):
        from education import GLOSSARY
        from bdc_education import TERMS
        for filename, terms in [('glossary.html',GLOSSARY),('glossary-bdc.html',TERMS)]:
            soup=BeautifulSoup(self.pages[ROOT/filename],'html.parser')
            ids=[e['id'] for e in soup.select('[id]')]
            self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(len(soup.select('[data-term]')),len(terms))
            for i,(term,meaning,slug) in enumerate(terms):
                entry=soup.select_one(f'#term-{i}')
                self.assertEqual(entry.dt.get_text(),term)
                self.assertTrue(entry.dt.get('id'))
                self.assertIn(meaning,entry.dd.get_text())
    def test_stock_next_reading_has_no_self_link(self):
        from stock_basics import GUIDES
        for guide in GUIDES:
            soup=BeautifulSoup(self.pages[ROOT/(guide['slug']+'.html')],'html.parser')
            self.assertIsNotNone(soup.select_one('nav.reading-next'))
            self.assertFalse(soup.select(f'.stock-basics-discovery a[href="/{guide["slug"]}.html"]'))
