import json
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import education
from curriculum import LEVELS

class EducationTests(unittest.TestCase):
    def test_curriculum_covers_each_guide_once(self):
        slugs=[slug for level in LEVELS for slug in level['slugs']]
        self.assertEqual(len(slugs),len(set(slugs)))
        self.assertEqual(set(slugs),{a['slug'] for a in education.load_articles(ROOT)})
        self.assertEqual([len(level['slugs']) for level in LEVELS],[6,18,8,4])
        for level in LEVELS:
            self.assertTrue(level['prerequisite'] and level['outcome'])
            for question,choices,answer,explanation in level['quiz']:
                self.assertTrue(0<=answer<len(choices))
                self.assertTrue(explanation)

    def test_library_has_substantive_distinct_articles(self):
        articles=education.load_articles(ROOT)
        self.assertEqual(len(articles),36)
        self.assertEqual(len({a['title'] for a in articles}),len(articles))
        for a in articles:
            with self.subTest(slug=a['slug']):
                words=' '.join(s['text'] for s in a['sections']).split()
                self.assertGreater(len(words),250)
                self.assertGreaterEqual(len(a['sources']),1)
                self.assertIn('hypothetical',a['example']['heading'].lower())
                self.assertGreaterEqual(len(a['checklist']),3)

    def test_generated_pages_are_crawlable_and_have_valid_schema(self):
        for path,text in education.education_outputs(ROOT).items():
            if path.suffix!='.html':continue
            with self.subTest(page=path.name):
                self.assertEqual(len(re.findall(r'<h1(?:\s[^>]*)?>',text)),1)
                for value in re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S):
                    data=json.loads(value)
                    self.assertEqual(data['@context'],'https://schema.org')
                self.assertNotIn('adsbygoogle.js',text)
                self.assertNotIn('ca-pub-',text)
                self.assertIn('rel="canonical"',text)
                self.assertIn('name="description"',text)

    def test_calculator_formulas_and_no_javascript_fallback(self):
        lookup={a['slug']:a for a in education.load_articles(ROOT)}
        for tool in education.TOOLS:
            text=education.calculator_page(ROOT,tool,lookup)
            self.assertIn('<noscript>',text)
            self.assertIn('id="formula"',text)
            self.assertIn('id="limits"',text)
            self.assertIn('id="example"',text)

if __name__=='__main__':unittest.main()
