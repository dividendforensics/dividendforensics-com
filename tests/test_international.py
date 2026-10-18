import json
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
import build_site
from international import LOCALES, PAGES, groups, path_for
from localized import PAIRS, url

ROOT=Path(__file__).resolve().parents[1]

class InternationalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.pages=build_site.planned_outputs(ROOT)

    def test_eighteen_pages_have_self_canonicals_and_full_reciprocal_groups(self):
        count=0
        for locale in LOCALES:
            for key,english in PAGES.items():
                count+=1;path=path_for(locale,key)
                soup=BeautifulSoup(self.pages[ROOT/path],'html.parser')
                self.assertEqual(soup.html['lang'],locale)
                self.assertEqual(soup.select_one('link[rel=canonical]')['href'],url(path))
                expected={lang:url(p) for lang,p in groups(PAIRS)[english].items()}
                expected['x-default']=url(english)
                for member in groups(PAIRS)[english].values():
                    target=BeautifulSoup(self.pages[ROOT/member],'html.parser')
                    self.assertEqual({x['hreflang']:x['href'] for x in target.select('link[hreflang]')},expected)
                self.assertEqual(len(soup.select('h1')),1)
                crumbs=json.loads(soup.select('script[type="application/ld+json"]')[1].string)['itemListElement']
                self.assertEqual(crumbs[-1]['item'],url(path))
                self.assertEqual(len({c['item'] for c in crumbs}),len(crumbs))
                self.assertEqual([c['position'] for c in crumbs],list(range(1,len(crumbs)+1)))
                self.assertIn(url(path),self.pages[ROOT/'sitemap.xml'])
                for a in soup.select('a[href^="#"]'): self.assertIsNotNone(soup.find(id=a['href'][1:]))
        self.assertEqual(count,18)

    def test_article_text_examples_answers_and_usd_are_static(self):
        for locale in LOCALES:
            data=json.loads((ROOT/'content'/f'edition-{locale}.json').read_text(encoding='utf-8'))
            for key,a in data['articles'].items():
                soup=BeautifulSoup(self.pages[ROOT/path_for(locale,key)],'html.parser')
                text=soup.select_one('main').get_text(' ',strip=True)
                for passage in [a['example'],a['question'],a['answer']]+[s[1] for s in a['sections']]:
                    self.assertIn(passage,text)
                self.assertIn('USD',text)
                self.assertGreater(len(soup.select_one('article').get_text()),1000)
                self.assertTrue(soup.select('#sources a[href^="https://"]'))
                schema=json.loads(soup.select_one('script[type="application/ld+json"]').string)
                self.assertEqual(schema['inLanguage'],locale)
                self.assertEqual(schema['isBasedOn'],url(PAGES[key]))
                self.assertEqual(schema['dateModified'],soup.time['datetime'])

    def test_financial_scale_and_rounding_examples_are_retained(self):
        for locale in LOCALES:
            data=json.loads((ROOT/'content'/f'edition-{locale}.json').read_text(encoding='utf-8'))
            example=data['articles']['coverage']['example']
            for number in ['120','100','115','105']:self.assertIn(number,example)
            self.assertIn('1,0435' if locale=='de' else '1.0435',example)
            self.assertIn('95,8333' if locale=='de' else '95.8333',example)
            self.assertIn({'de':'Millionen USD','ja':'百万USD','zh-Hant':'百萬 USD'}[locale],example)
            self.assertIn('90,91' if locale=='de' else '90.91',data['articles']['comparison']['example'])

    def test_calculator_has_localized_labels_and_no_js_formula(self):
        for locale in LOCALES:
            soup=BeautifulSoup(self.pages[ROOT/path_for(locale,'income')],'html.parser')
            self.assertEqual(len(soup.select('input[name]')),4)
            self.assertTrue(soup.select('noscript'))
            config=json.loads(soup.select_one('#calculator-translations').string)
            self.assertEqual(len(config['labels']),4)
            self.assertTrue(all(config.values()))
            for field in soup.select('input[name]'):self.assertIsNotNone(soup.find('label',attrs={'for':field['id']}))
