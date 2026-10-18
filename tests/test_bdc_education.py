"""Publication invariants for a separate, sequential BDC learning room."""
import json
import re
import unittest
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
import bdc_education as b

ROOT=Path(__file__).resolve().parents[1]


class BdcEducationTests(unittest.TestCase):
    def test_quiz_positions_do_not_reward_one_repeated_choice(self):
        articles=b.load_articles(ROOT)
        answers=Counter(question['answer'] for article in articles for question in article['quiz'])
        self.assertEqual(sum(answers.values()),16)
        for position in range(3):
            self.assertGreaterEqual(answers[position],4)
            self.assertLessEqual(answers[position],7)

    def test_standalone_expert_units_are_explicit(self):
        articles={a['slug']:a for a in b.load_articles(ROOT)}
        for slug in ('learn-bdc-expert-refinancing','learn-bdc-expert-credit-memo'):
            article=articles[slug]
            introduction=article['sections'][0]['text']
            self.assertIn('USD millions',introduction)
            self.assertIn('shares are in millions',introduction)
            self.assertIn('per-share amounts are in USD',introduction)
            self.assertIn('USD millions',' '.join(article['table']['headers']))

    def test_spanish_dates_and_first_pik_explanation_are_source_fields(self):
        articles=json.loads((ROOT/'content/spanish.json').read_text(encoding='utf-8'))
        for article in articles:
            self.assertRegex(article['published'],r'^\d{4}-\d{2}-\d{2}$')
            self.assertGreaterEqual(article['updated'],article['published'])
        article=next(a for a in articles if a['english_slug']=='learn-bdc-nii-coverage')
        body=' '.join(s['text'] for s in article['sections'])
        self.assertIn('intereses pagados en especie (payment-in-kind, PIK)',body)
        self.assertIn('sin cobrarse en efectivo',body)
        self.assertEqual(article['related_english']['slug'],'learn-bdc-pik-income')
        self.assertIn('inglés',article['related_english']['title'])

    def test_curriculum_depth_sources_and_prerequisites(self):
        articles=b.load_articles(ROOT)
        self.assertEqual(Counter(a['level'] for a in articles),{l['name']:4 for l in b.LEVELS})
        seen=set()
        for a in articles:
            self.assertTrue(set(a['prerequisites'])<=seen,a['slug'])
            seen.add(a['slug'])
            self.assertGreaterEqual(len(a['sections']),4)
            self.assertGreaterEqual(len(' '.join(s['text'] for s in a['sections']).split()),300,a['slug'])
            self.assertGreaterEqual(len(a['sources']),2)
            self.assertTrue(a['exercise']['answer'] and a['quiz'][0]['explanation'])

    def test_static_content_scope_links_and_schemas(self):
        output=b.outputs(ROOT)
        self.assertEqual(len(output),22)
        for path,text in output.items():
            soup=BeautifulSoup(text,'html.parser')
            self.assertEqual(len(soup.select('h1')),1,path.name)
            schema=[json.loads(s.string) for s in soup.select('script[type="application/ld+json"]')]
            crumbs=next(s for s in schema if s['@type']=='BreadcrumbList')['itemListElement']
            urls=[i['item'] for i in crumbs]
            self.assertEqual(len(urls),len(set(urls)))
            self.assertEqual(urls[-1],'https://dividendforensics.com/'+path.name)
            if path.name.startswith('learn-bdc-'):
                self.assertIn('US BDC education.',text)
                self.assertNotIn('This guide focuses on US REITs.',text)
                self.assertIn('data-quiz',text)
                self.assertIn('Synthetic example',text)

    def test_two_rooms_are_discoverable_without_javascript(self):
        import build_site
        output=build_site.planned_outputs(ROOT)
        for name in ('index.html','learn.html','bdc-guide.html','calculator-bdc-nii-pik.html'):
            self.assertIn('href="/learn-bdc.html"',output[ROOT/name],name)
        text=output[ROOT/'sitemap.xml']
        for path in b.outputs(ROOT):
            self.assertIn('https://dividendforensics.com/'+path.name,text)
        self.assertNotIn('{{bdc_lesson_count}}',output[ROOT/'index.html'])
