"""Spanish publication invariants: paired translations, USD scope and shared math."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import build_site
import localized
from international import groups

ROOT=Path(__file__).resolve().parents[1]


class LocalizedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages=build_site.planned_outputs(ROOT)

    def test_seven_pairs_have_reciprocal_hreflang_and_self_canonicals(self):
        self.assertEqual(len(localized.PAIRS),7)
        for english,spanish in localized.PAIRS.items():
            expected={lang:localized.url(path) for lang,path in groups(localized.PAIRS)[english].items()}
            expected['x-default']=localized.url(english)
            for path in (english,spanish):
                soup=BeautifulSoup(self.pages[ROOT/path],'html.parser')
                links=soup.select('link[rel=alternate][hreflang]')
                self.assertEqual(len(links),len(expected),path)
                self.assertEqual({x['hreflang']:x['href'] for x in links},expected,path)
                canonicals=soup.select('link[rel=canonical]')
                self.assertEqual(len(canonicals),1,path)
                self.assertEqual(canonicals[0]['href'],localized.url(path),path)
                self.assertEqual(soup.html['lang'],'es' if path==spanish else 'en',path)
                self.assertEqual(len(soup.select('h1')),1,path)

    def test_spanish_schema_matches_language_url_and_article_source(self):
        for english,spanish in localized.PAIRS.items():
            soup=BeautifulSoup(self.pages[ROOT/spanish],'html.parser')
            schemas=[json.loads(node.string) for node in soup.select('script[type="application/ld+json"]')]
            page=next(s for s in schemas if s['@type']!='BreadcrumbList')
            self.assertEqual(page['inLanguage'],'es')
            self.assertEqual(page['url'],localized.url(spanish))
            if english.startswith('learn-'):
                self.assertEqual(page['@type'],'Article')
                self.assertEqual(page['isBasedOn'],localized.url(english))
            crumbs=next(s for s in schemas if s['@type']=='BreadcrumbList')['itemListElement']
            self.assertEqual(crumbs[-1]['item'],localized.url(spanish))
            self.assertEqual(len({s['item'] for s in crumbs}),len(crumbs))

    def test_four_static_translations_have_sources_examples_and_us_scope(self):
        guides=json.loads((ROOT/'content/spanish.json').read_text(encoding='utf-8'))
        self.assertEqual(len(guides),4)
        for article in guides:
            self.assertGreaterEqual(len(article['sections']),4)
            self.assertGreaterEqual(len(article['sources']),2)
            self.assertTrue(all(urlsplit(s['url']).scheme=='https' for s in article['sources']))
            soup=BeautifulSoup(self.pages[ROOT/'es'/(article['slug']+'.html')],'html.parser')
            body=soup.select_one('main').get_text(' ',strip=True)
            self.assertIn('Estados Unidos',body)
            self.assertIn('no adapta las normas a España',body)
            self.assertIn('no hay conversión de moneda',body)
            self.assertIn(article['example']['text'],body)
            self.assertIn(article['exercise']['answer'],body)
            self.assertTrue(soup.select('.pitfall'))

    def test_calculators_declare_decimal_input_usd_and_load_shared_engine_in_order(self):
        for path in ['es/calculadora-dividendos.html','es/calculadora-cobertura-affo.html']:
            soup=BeautifulSoup(self.pages[ROOT/path],'html.parser')
            body=soup.select_one('main').get_text(' ',strip=True)
            self.assertIn('Importes en USD, sin conversión de moneda',body)
            self.assertIn('Escriba decimales con punto; los resultados usan coma decimal',body)
            self.assertIn('Fórmula y base',body)
            self.assertTrue(soup.select('noscript'))
            self.assertFalse(soup.select('[data-calculator]'))
            scripts=[s['src'].split('?')[0] for s in soup.select('script[src]')]
            self.assertLess(scripts.index('/vendor/decimal.js/decimal.js'),scripts.index('/calculators.js'))
            self.assertLess(scripts.index('/calculators.js'),scripts.index('/spanish-calculators.js'))
            for input_ in soup.select('input'):
                self.assertTrue(soup.select('label[for="'+input_['id']+'"]'))

    def test_spanish_dates_are_per_article_and_visible_date_matches_schema(self):
        articles=json.loads((ROOT/'content/spanish.json').read_text(encoding='utf-8'))
        articles[0]['published']='2026-10-16'
        articles[0]['updated']='2026-10-17'
        with patch.object(localized.json,'loads',return_value=articles):
            output=localized.outputs(ROOT)
        for a in articles:
            soup=BeautifulSoup(output[ROOT/'es'/(a['slug']+'.html')],'html.parser')
            schema=json.loads(soup.select_one('script[type="application/ld+json"]').string)
            self.assertEqual(schema['datePublished'],a['published'])
            self.assertEqual(schema['dateModified'],a['updated'])
            self.assertEqual(soup.select_one('time')['datetime'],a['updated'])
        self.assertEqual(articles[1]['updated'],'2026-10-18')

    def test_income_formula_defines_percentage_conversion_and_home_link_is_canonical(self):
        soup=BeautifulSoup(self.pages[ROOT/'es/calculadora-dividendos.html'],'html.parser')
        text=soup.select_one('main').get_text(' ',strip=True)
        self.assertIn('Rentabilidad neta decimal = (rentabilidad anual / 100)',text)
        self.assertIn('Capital objetivo = objetivo mensual × 12 / rentabilidad neta decimal',text)
        self.assertIn('Restablecer valores iniciales',text)
        home=BeautifulSoup(self.pages[ROOT/'index.html'],'html.parser')
        self.assertEqual(home.select_one('[data-language-switch] a')['href'],localized.url('es/index.html'))


if __name__=='__main__':unittest.main()
