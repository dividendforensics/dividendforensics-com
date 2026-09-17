import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build_site as b

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.a={'url':'https://www.benzinga.com/example','title':'Example & research','blurb':'Known, not assumed.','date':'2026-08-01','group':'REIT','label':'Net lease','case_key':'TEST','case_slug':'test'}
    def tearDown(self):self.tmp.cleanup()
    def write(self,arts):
        (self.root/'articles.json').write_text(json.dumps({'articles':arts,'published_count':99}))
    def test_valid_record(self):
        self.write([self.a]);self.assertEqual(len(b.load(self.root)[1]),1)
    def test_external_fallback(self):
        self.assertEqual(b.destination(self.a,self.root),(self.a['url'],True))
    def test_existing_local_page(self):
        (self.root/'case-test.html').write_text('test')
        self.assertEqual(b.destination(self.a,self.root),('/case-test.html',False))
    def test_optional_case_slug(self):
        a=dict(self.a);del a['case_slug'];self.write([a]);b.load(self.root)
        self.assertTrue(b.destination(a,self.root)[1])
    def test_duplicate_url(self):
        self.write([self.a,self.a]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_private_preview_rejected(self):
        self.write([dict(self.a,url='https://contributor.benzinga.com/?p=123')]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_non_https_rejected(self):
        self.write([dict(self.a,url='javascript:alert(1)')]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_slug_traversal_rejected(self):
        self.write([dict(self.a,case_slug='../legal')]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_invalid_date_rejected(self):
        self.write([dict(self.a,date='2026-02-31')]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_month_only_date(self):self.assertEqual(b.display_date('2026-06'),'Jun 2026')
    def test_drafts_excluded(self):
        draft=dict(self.a,url='https://www.benzinga.com/draft',case_slug='draft',status='internal_review')
        self.write([self.a,draft]);self.assertEqual(len(b.load(self.root)[1]),1)
    def test_all_hidden_from_home_rejected(self):
        self.write([dict(self.a,home=False)]);self.assertRaises(b.BuildError,b.load,self.root)
    def test_escape_html(self):
        self.assertEqual(b.esc('"<script>&'), '&quot;&lt;script&gt;&amp;')
    def test_rendered_labels_follow_target(self):
        out=b.build_index([self.a],self.root)
        self.assertIn('Read on Benzinga',out);self.assertIn('Example &amp; research',out)
        (self.root/'case-test.html').write_text('test')
        self.assertIn('Open research record',b.build_index([self.a],self.root))
    def test_editorial_order_preserved(self):
        old=dict(self.a,date='2026-06-01');new=dict(self.a,url='https://www.benzinga.com/new',case_slug='new',date='2026-09-08')
        self.write([old,new]);_,arts=b.load(self.root)
        self.assertEqual(arts[0]['date'],'2026-06-01')
        self.assertEqual(max(arts,key=lambda a:b.date_key(a['date']))['date'],'2026-09-08')
    def test_splice_retains_outside(self):
        s='before'+b.START+'old'+b.END+'after'
        self.assertEqual(b.splice(s,'new'),'before'+b.START+'\nnew\n'+b.END+'after')
    def test_duplicate_markers_rejected(self):
        self.assertRaises(b.BuildError,b.splice,b.START+b.START+b.END,'new')
    def test_actual_site_is_idempotent(self):
        for p,text in b.planned_outputs(ROOT).items():self.assertEqual(p.read_text(),text,p.name)
    def test_actual_site_has_public_entries_only(self):
        _,arts=b.load(ROOT)
        self.assertGreater(len(arts),0)
        self.assertTrue(all('contributor.benzinga.com' not in a['url'] for a in arts))
    def test_selected_count_is_not_total_published(self):
        text=(ROOT/'index.html').read_text()
        _,arts=b.load(ROOT)
        self.assertIn(f'{len(arts)}</span> research records',text)
        self.assertNotIn('data-dfb="count"',text)

if __name__=='__main__':unittest.main()
