"""Guard approved public positioning and the paused membership state."""
import unittest
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build_site as build

class PublicCopyTests(unittest.TestCase):
    def test_home_describes_method_not_dividend_only_scope(self):
        text=(ROOT/'templates/home.html').read_text()
        for term in ('Filing-anchored structural research','capital structure','debt','dilution','financing','refinancing','credit','payout mechanics'):
            self.assertIn(term,text)
        self.assertNotIn('REITs &amp; BDCs, with selected work across other income assets',text)

    def test_membership_removed_from_shared_navigation(self):
        self.assertNotIn('membership.html',build.header('index.html'))
        self.assertNotIn('membership.html',build.footer())

    def test_membership_is_status_only(self):
        text=(ROOT/'membership.html').read_text()
        main=text.split('<main id="main" tabindex="-1">',1)[1].split('</main>',1)[0]
        self.assertIn('Membership is not open for enrollment or payment.',main)
        self.assertIn('No public price or opening date has been announced.',main)
        self.assertNotRegex(main,r'\$\s*\d|(?i:waitlist|mailto:|checkout|join now|enroll now|limited availability)')
        self.assertNotIn('<form',main)

    def test_front_door_has_no_framework_name_pitch(self):
        for name in ('templates/home.html','about.html','research-desk.html'):
            text=(ROOT/name).read_text()
            for term in ('Buffer Half-Life','Three Clocks','BBB− Cliff'):
                self.assertNotIn(term,text,name)

    def test_earlier_framework_references_are_preserved(self):
        text=(ROOT/'methodology.html').read_text()
        for term in ('framework-notes','Earlier income research','Three Clocks','Buffer Half-Life','BBB− Cliff'):
            self.assertIn(term,text)

    def test_social_routes_match_active_channels(self):
        text=(ROOT/'templates/footer.html').read_text()
        self.assertNotIn('substack.com',text)
        self.assertIn('https://stocktwits.com/DividendForensicsBureau',text)
        self.assertIn('https://muckrack.com/jeong-mo-goo',text)

    def test_author_and_research_boundaries_remain_visible(self):
        self.assertIn('Analysis by Jeong-Mo Goo',build.header('index.html'))
        text=build.footer()
        self.assertIn('The author holds no position in any security mentioned.',text)
        self.assertIn('Structural research, not personalized investment advice.',text)

    def test_existing_free_report_destination_unchanged(self):
        self.assertIn('0417e6b9-d489-438e-9b2c-913437003238',build.REPORT_URL)
        self.assertIn('Published REIT working paper',(ROOT/'templates/home.html').read_text())

    def test_no_review_only_report_paths_in_active_pages(self):
        for p in ROOT.glob('*.html'):
            text=p.read_text()
            if 'name="dfb-design"' in text:
                self.assertNotRegex(text,r'(?i)href=[\"\'][^\"\']*(?:AUDIT_FREEZE|SAMPLE_REVIEW|v1\.3_REVIEW|Execution_Pack)')

    def test_search_descriptions_are_broadened(self):
        for name in ('index.html','research.html','about.html','research-desk.html','methodology.html'):
            text=(ROOT/name).read_text()
            self.assertNotIn('Structural Research on Dividend Durability',text)
            self.assertNotIn('content="An independent research desk examining what is left after a dividend is paid.',text)

    def test_sitemap_excludes_paused_membership_and_keeps_methodology(self):
        ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        tree=ET.parse(ROOT/'sitemap.xml')
        self.assertEqual(tree.getroot().tag,'{'+ns['s']+'}urlset')
        urls=[node.text for node in tree.findall('s:url/s:loc',ns)]
        self.assertTrue(urls)
        self.assertEqual(len(urls),len(set(urls)))
        self.assertIn('https://dividendforensics.com/methodology.html',urls)
        self.assertNotIn('https://dividendforensics.com/membership.html',urls)

    def test_sitemap_targets_are_canonical_indexable_site_pages(self):
        ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for node in ET.parse(ROOT/'sitemap.xml').findall('s:url/s:loc',ns):
            with self.subTest(url=node.text):
                url=urlsplit(node.text)
                self.assertEqual(url.scheme,'https')
                self.assertEqual(url.netloc,'dividendforensics.com')
                self.assertFalse(url.query or url.fragment)
                relative=url.path.lstrip('/') or 'index.html'
                self.assertNotIn('..',Path(relative).parts)
                target=ROOT/relative
                self.assertTrue(target.is_file())
                text=target.read_text(encoding='utf-8')
                canonical=re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"',text)
                self.assertIsNotNone(canonical)
                self.assertEqual(canonical.group(1),node.text)
                self.assertNotRegex(text,r'(?i)<meta[^>]*name="robots"[^>]*content="[^"]*noindex')
                self.assertNotRegex(text,r'(?i)<meta[^>]*http-equiv="refresh"')

if __name__=='__main__':
    unittest.main()
