"""A layout change must not drop reviewed explanations, inputs or evidence."""
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
import education
import bdc_education
import localized
from lesson_formats import format_for

ROOT = Path(__file__).resolve().parents[1]


class ReadingFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = education.load_articles(ROOT) + bdc_education.load_articles(ROOT)
        cls.outputs = education.education_outputs(ROOT)

    def test_all_six_structures_are_used_and_anchors_resolve(self):
        self.assertEqual({format_for(a) for a in self.articles},
                         {'concept', 'sector', 'calculation', 'risk', 'workflow', 'workshop'})
        for a in self.articles:
            soup = BeautifulSoup(self.outputs[ROOT/(a['slug']+'.html')], 'html.parser')
            self.assertEqual(soup.select_one('[data-reading-format]')['data-reading-format'], format_for(a))
            ids = [node['id'] for node in soup.select('[id]')]
            self.assertEqual(len(ids), len(set(ids)), a['slug'])
            for link in soup.select('.lesson-jump-menu a[href^="#"]'):
                self.assertIn(link['href'][1:], ids)

    def test_reviewed_prose_examples_and_sources_survive(self):
        for a in self.articles:
            soup = BeautifulSoup(self.outputs[ROOT/(a['slug']+'.html')], 'html.parser')
            text = soup.get_text(' ', strip=True)
            original = [s['text'] for s in a['sections']] + [a['example']['text'], a['pitfall']] + a['checklist']
            if a.get('exercise'):
                original += list(a['exercise'].values())
            for passage in original:
                self.assertIn(passage, text, a['slug'])
            hrefs = {x['href'] for x in soup.select('a[href]')}
            for source in a['sources']:
                self.assertIn(source['url'], hrefs)
            if a.get('table'):
                for row in a['table']['rows']:
                    for cell in row:
                        self.assertIn(str(cell), text)

    def test_numbers_follow_definition_and_workshop_results_follow_analysis(self):
        cases = [('learn-ffo', 'section-1', 'worked-example')]
        cases += [(a['slug'], 'section-' + str(len(a['sections'])), 'worked-example')
                  for a in self.articles if format_for(a) == 'workshop']
        self.assertEqual(len(cases), 9)
        for slug, earlier, later in cases:
            soup = BeautifulSoup(self.outputs[ROOT/(slug+'.html')], 'html.parser')
            order = [node['id'] for node in soup.select('article.lesson-body [id]')]
            self.assertLess(order.index(earlier), order.index(later))
            for table in soup.select('.table-scroll'):
                self.assertIsNotNone(soup.find(id=table['aria-describedby']))

    def test_spanish_original_values_and_us_scope_remain(self):
        articles = json.loads((ROOT/'content/spanish.json').read_text(encoding='utf-8'))
        for a in articles:
            soup = BeautifulSoup(self.outputs[ROOT/'es'/(a['slug']+'.html')], 'html.parser')
            text = soup.get_text(' ', strip=True)
            self.assertIn(a['example']['text'], text)
            self.assertIn('USD', text)
            self.assertEqual(soup.html['lang'], 'es')
            self.assertIsNotNone(soup.select_one('[data-reading-format]'))
            links = soup.select('.lesson-jump-menu a')
            self.assertGreaterEqual(len(links), len(a['sections']))
            for link in links:
                self.assertIsNotNone(soup.find(id=link['href'][1:]))
