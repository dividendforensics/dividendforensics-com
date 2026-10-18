"""Offline SEO contracts: static discoverability, identity and honest revision dates."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('seo_audit', ROOT / 'tools/seo_audit.py')
seo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seo)


def page(name, *, title=None, description=None, heading=None, links=(), robots='', schema=None):
    url = seo.DOMAIN + ('/' if name == 'index.html' else '/' + name)
    scripts = '' if schema is None else '<script type="application/ld+json">' + json.dumps(schema) + '</script>'
    return (f'<html lang="en"><head><meta name="dfb-design" content="test">'
            f'<title>{title or name}</title><meta name="description" content="{description or name+" description"}">'
            f'<link rel="canonical" href="{url}">{robots}{scripts}</head>'
            f'<body><main><h1>{heading or name}</h1>'
            + ''.join(f'<a href="{href}">Read</a>' for href in links) + '</main></body></html>')


def sitemap(names, *, modified=None):
    return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + ''.join('<url><loc>' + seo.DOMAIN + ('/' if name == 'index.html' else '/' + name)
                      + '</loc>' + ('<lastmod>' + modified[name] + '</lastmod>' if modified and name in modified else '')
                      + '</url>' for name in names) + '</urlset>')


class SeoTests(unittest.TestCase):
    def pair(self):
        return {'index.html': page('index.html', links=['/topic.html']),
                'topic.html': page('topic.html', links=['/'])}

    def test_valid_unique_static_pages_are_reachable(self):
        pages = self.pair()
        result = seo.audit(pages, sitemap(pages))
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['indexable_pages'], 2)
        self.assertEqual(result['pages'][1]['inbound_pages'], 1)
        self.assertIn('not Google', result['audit_kind'])

    def test_missing_metadata_h1_and_wrong_canonical_are_critical(self):
        edits = [('<title>topic.html</title>', ''),
                 ('<meta name="description" content="topic.html description">', ''),
                 ('<h1>topic.html</h1>', ''),
                 ('href="https://dividendforensics.com/topic.html"', 'href="https://other.example/topic.html"')]
        for old, new in edits:
            with self.subTest(old=old):
                pages = self.pair(); pages['topic.html'] = pages['topic.html'].replace(old, new)
                self.assertEqual(seo.audit(pages, sitemap(pages))['status'], 'fail')

    def test_duplicate_titles_descriptions_and_h1_are_reported(self):
        for field, expected in [('title', 'title'), ('description', 'description'), ('heading', 'h1')]:
            with self.subTest(field=field):
                pages = {name: page(name, **{field: 'Duplicate'}, links=['/' if name != 'index.html' else '/topic.html'])
                         for name in ['index.html', 'topic.html']}
                self.assertTrue(any('duplicate ' + expected in error for error in seo.audit(pages, sitemap(pages))['errors']))

    def test_long_title_is_advisory_not_failed_score(self):
        pages = self.pair()
        pages['topic.html'] = page('topic.html', title='A descriptive long educational heading ' * 4, links=['/'])
        result = seo.audit(pages, sitemap(pages))
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['warnings'])

    def test_noindex_and_redirect_are_excluded_and_must_not_enter_sitemap(self):
        pages = self.pair()
        pages['status.html'] = page('status.html', robots='<meta name="robots" content="noindex,follow">')
        pages['old.html'] = page('old.html', robots='<meta http-equiv="refresh" content="0;url=/">')
        result = seo.audit(pages, sitemap(['index.html', 'topic.html']))
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['excluded_active_pages'], ['old.html', 'status.html'])
        self.assertEqual(seo.audit(pages, sitemap(pages))['status'], 'fail')

    def test_sitemap_missing_duplicate_or_noncanonical_targets_fail(self):
        pages = self.pair()
        for names in [['index.html'], ['index.html', 'topic.html', 'topic.html'], ['index.html', 'topic.html', 'missing.html']]:
            with self.subTest(names=names): self.assertEqual(seo.audit(pages, sitemap(names))['status'], 'fail')

    def test_self_links_or_script_navigation_do_not_hide_orphans(self):
        pages = self.pair()
        pages['index.html'] = page('index.html') + '<script>window.location="/topic.html"</script>'
        pages['topic.html'] = page('topic.html', links=['/topic.html'])
        errors = seo.audit(pages, sitemap(pages))['errors']
        self.assertTrue(any('no crawlable inbound' in value for value in errors))
        self.assertTrue(any('not reachable' in value for value in errors))

    def test_unreachable_cycle_is_not_treated_as_discovered_from_home(self):
        pages = {'index.html': page('index.html'), 'a.html': page('a.html', links=['/b.html']),
                 'b.html': page('b.html', links=['/a.html'])}
        self.assertTrue(any('not reachable' in value for value in seo.audit(pages, sitemap(pages))['errors']))

    def test_relative_query_fragment_links_and_home_alias_resolve(self):
        pages = {'index.html': page('index.html', links=['topic.html?q=education#definition']),
                 'topic.html': page('topic.html', links=['/index.html'])}
        self.assertEqual(seo.audit(pages, sitemap(pages))['status'], 'pass')

    def test_nofollow_is_not_counted_as_crawlable_inbound_contract(self):
        pages = self.pair()
        pages['index.html'] = pages['index.html'].replace('<a href=', '<a rel="nofollow" href=')
        self.assertEqual(seo.audit(pages, sitemap(pages))['status'], 'fail')

    def test_nested_spanish_home_keeps_path_and_reciprocal_language_links(self):
        en, es = seo.DOMAIN + '/', seo.DOMAIN + '/es/'
        alternates = (f'<link rel="alternate" hreflang="en" href="{en}">'
                      f'<link rel="alternate" hreflang="es" href="{es}">'
                      f'<link rel="alternate" hreflang="x-default" href="{en}">')
        pages = {'index.html': page('index.html', links=['/es/']).replace('</head>', alternates + '</head>'),
                 'es/index.html': page('es/index.html', links=['/']).replace('lang="en"', 'lang="es"').replace(
                     seo.DOMAIN + '/es/index.html', es).replace('</head>', alternates + '</head>')}
        xml = sitemap(['index.html']) .replace('</urlset>', f'<url><loc>{es}</loc></url></urlset>')
        result = seo.audit(pages, xml)
        self.assertEqual(result['errors'], [])
        self.assertEqual({r['file'] for r in result['pages']}, {'index.html', 'es/index.html'})
        broken = deepcopy(pages)
        broken['es/index.html'] = broken['es/index.html'].replace('hreflang="en"', 'hreflang="fr"')
        self.assertEqual(seo.audit(broken, xml)['status'], 'fail')

    def article(self):
        return {'@type': 'Article', 'headline': 'Test BDC', 'datePublished': '2026-10-01',
                'dateModified': '2026-10-12', 'mainEntityOfPage': seo.DOMAIN + '/learn-bdc-test.html'}

    def bdc_fixture(self):
        article = {'slug': 'learn-bdc-test', 'title': 'Test BDC', 'published': '2026-10-01', 'updated': '2026-10-12'}
        pages = {'index.html': page('index.html', links=['/learn-bdc-test.html']),
                 'learn-bdc-test.html': page('learn-bdc-test.html', schema=self.article(), links=['/']) + '<p>US BDC education.</p>'}
        return article, pages

    def test_bdc_dates_scope_and_matching_real_update_lastmod_pass(self):
        article, pages = self.bdc_fixture()
        result = seo.audit(pages, sitemap(pages, modified={'learn-bdc-test.html': '2026-10-12'}), [article])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['bdc_articles_checked'], 1)

    def test_build_date_cannot_replace_article_revision_lastmod(self):
        article, pages = self.bdc_fixture()
        result = seo.audit(pages, sitemap(pages, modified={'learn-bdc-test.html': '2026-10-18'}), [article])
        self.assertTrue(any('lastmod does not match' in value for value in result['errors']))

    def test_missing_lastmod_and_modification_before_publication_fail(self):
        article, pages = self.bdc_fixture()
        self.assertEqual(seo.audit(pages, sitemap(pages), [article])['status'], 'fail')
        bad = self.article(); bad['dateModified'] = '2026-09-30'
        pages['learn-bdc-test.html'] = page('learn-bdc-test.html', schema=bad) + '<p>US BDC education.</p>'
        self.assertTrue(any('publication/modification' in value for value in seo.audit(pages, sitemap(pages))['errors']))

    def test_invalid_jsonld_and_wrong_bdc_identity_or_scope_fail(self):
        article, pages = self.bdc_fixture()
        for old, new in [('US BDC education.', 'This guide focuses on US REITs.'),
                         ('"headline": "Test BDC"', '"headline": "Wrong"'),
                         ('"datePublished": "2026-10-01"', '"datePublished": "2026-10-02"'),
                         ('"@type": "Article"', 'invalid JSON')]:
            with self.subTest(old=old):
                edited = deepcopy(pages); edited['learn-bdc-test.html'] = edited['learn-bdc-test.html'].replace(old, new)
                self.assertEqual(seo.audit(edited, sitemap(pages, modified={'learn-bdc-test.html': '2026-10-12'}), [article])['status'], 'fail')

    def test_current_planned_site_has_no_static_critical_issues(self):
        result = seo.site_audit(ROOT)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['indexable_pages'], result['sitemap_urls'])
        expected = len(json.loads((ROOT / 'content/bdc.json').read_text(encoding='utf-8')))
        self.assertEqual(result['bdc_articles_checked'], expected)


if __name__ == '__main__':
    unittest.main()
