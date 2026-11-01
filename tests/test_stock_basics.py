"""Publication and accessibility contracts for the separate introductory guides."""
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from stock_basics import GUIDES, outputs

ROOT = Path(__file__).resolve().parents[1]


class StockBasicsTests(unittest.TestCase):
    def test_generated_guides_have_sources_byline_and_article_schema(self):
        planned = outputs(ROOT)
        for guide in GUIDES:
            with self.subTest(guide=guide['slug']):
                page = BeautifulSoup(planned[ROOT/(guide['slug']+'.html')], 'html.parser')
                self.assertEqual(page.h1.get_text(), guide['title'])
                self.assertEqual(page.select_one('[rel="author"]').get_text(), 'DFB Education')
                article = next(json.loads(s.string) for s in page.select('script[type="application/ld+json"]') if json.loads(s.string).get('@type') == 'Article')
                self.assertEqual(article['author']['@type'], 'Organization')
                self.assertEqual(article['author']['name'], 'DFB Education')
                self.assertTrue(page.select('.stock-basics-article a[href^="https://"]'))
                self.assertNotIn('PRIVATE DRAFT', page.get_text())
                self.assertNotIn('Requires independent', page.get_text())
                self.assertGreater(len(page.select('.stock-basics-article p')), 8)

    def test_both_introductions_discoverable_from_home_and_learning_center(self):
        for path in ('index.html','learn.html'):
            page = BeautifulSoup((ROOT/path).read_text(), 'html.parser')
            for guide in GUIDES:
                self.assertTrue(page.select(f'a[href="/{guide["slug"]}.html"]'), (path,guide['slug']))

    def test_subject_entry_points_offer_separate_stock_basics_reading(self):
        for name in ('learn-reit-basics.html','course-beginner.html','glossary.html',
                     'operating-companies.html','learn-bdc-basics.html','course-bdc-beginner.html'):
            page=BeautifulSoup((ROOT/name).read_text(),'html.parser')
            blocks=page.select('aside.stock-basics-prerequisites')
            self.assertEqual(len(blocks),1,name)
            for guide in GUIDES:
                self.assertTrue(blocks[0].select(f'a[href="/{guide["slug"]}.html"]'),name)
        glossary=BeautifulSoup((ROOT/'glossary.html').read_text(),'html.parser')
        self.assertEqual(len(glossary.select('[data-term]')),25)
        self.assertEqual(glossary.select_one('#glossary-count').get_text(),'25 terms')
        from education import load_articles
        from bdc_education import load_articles as load_bdc_articles
        self.assertEqual(len(load_articles(ROOT)),36)
        self.assertEqual(len(load_bdc_articles(ROOT)),16)

    def test_overlap_figure_keeps_labels_as_real_text(self):
        page = BeautifulSoup(outputs(ROOT)[ROOT/'stock-classification.html'], 'html.parser')
        figure = page.select_one('.stock-labels')
        self.assertIsNotNone(figure)
        self.assertEqual(len(figure.select('dl > div')), 4)
        self.assertIn('Hypothetical', figure.figcaption.get_text())
        self.assertIn('Large-cap', figure.get_text())
        self.assertIn('Dividend-paying', figure.get_text())
        self.assertFalse(figure.select('img'))

    def test_source_images_offer_visible_full_size_link(self):
        from curriculum import figure
        page = BeautifulSoup(figure('property-atlas',ROOT), 'html.parser')
        link = page.select_one('figcaption a.illustration-full-size')
        self.assertEqual(link['href'], '/img/education/property-atlas.webp')
        self.assertIn('full-size', link.get_text())
