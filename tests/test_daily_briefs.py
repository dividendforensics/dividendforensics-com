import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from daily_briefs import calculations, digest, load, outputs, validate, CHECKS
ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,1,tzinfo=timezone.utc)


def fixture():
    # Entirely synthetic; no source verification or company news implied.
    return json.loads('{"status": "approved", "category": "Operating Companies", "slug": "synthetic-example-not-news", "author": "synthetic-author", "title": "Synthetic example, not financial news", "summary": "Test fixture only. Not a factual company report.", "event_date": "2026-10-29", "reporting_period": {"start": "2026-07-01", "end": "2026-09-30"}, "source_checked_at": "2026-10-31T20:00:00Z", "published_at": "2026-10-31T22:00:00Z", "event_source_id": "sec", "event_key": "sec:000000000026000001", "sources": {"sec": {"kind": "sec", "url": "https://www.sec.gov/Archives/edgar/data/0/000000000026000001/synthetic-test.htm", "title": "SYNTHETIC nonexistent test source", "locator": "Test table", "published_at": "2026-10-29T12:00:00Z", "checked_at": "2026-10-31T20:00:00Z", "content_sha256": "0000000000000000000000000000000000000000000000000000000000000000"}}, "facts": {"first": {"value": "100", "unit": "USD thousands", "basis": "Synthetic basis", "source_id": "sec", "locator": "Test cell", "period": {"start": "2026-07-01", "end": "2026-09-30"}}, "second": {"value": "-25", "unit": "USD thousands", "basis": "Synthetic basis", "source_id": "sec", "locator": "Test cell", "period": {"start": "2026-07-01", "end": "2026-09-30"}}, "third": {"value": "5", "unit": "USD thousands", "basis": "Synthetic basis", "source_id": "sec", "locator": "Test cell", "period": {"start": "2026-07-01", "end": "2026-09-30"}}, "numerator": {"value": "12", "unit": "USD thousands", "basis": "Synthetic basis", "source_id": "sec", "locator": "Test cell", "period": {"start": "2026-07-01", "end": "2026-09-30"}}, "denominator": {"value": "40", "unit": "USD thousands", "basis": "Synthetic basis", "source_id": "sec", "locator": "Test cell", "period": {"start": "2026-07-01", "end": "2026-09-30"}}}, "calculations": [{"id": "total", "operation": "sum", "inputs": ["first", "second", "third"], "expected": "80", "decimal_places": 0, "unit": "USD thousands", "precision_note": "Approximate ratio example; synthetic numbers only."}, {"id": "ratio", "operation": "ratio_percent", "inputs": ["numerator", "denominator"], "expected": "30", "decimal_places": 0, "unit": "percent", "precision_note": "Approximate ratio example; synthetic numbers only."}], "sections": [{"type": "fact", "heading": "Synthetic fact", "text": "Synthetic test prose only; not verified financial information.", "source_ids": ["sec"]}, {"type": "inference", "heading": "Synthetic inference", "text": "Synthetic test prose only; not verified financial information.", "source_ids": ["sec"]}, {"type": "open_question", "heading": "Synthetic open_question", "text": "Synthetic test prose only; not verified financial information.", "source_ids": ["sec"]}], "limitations": "Synthetic test; no real company or financial claim."}')


def review(b):
    return {'reviewer':'independent-test-reviewer','decision':'pass','reviewed_at':'2026-10-31T21:00:00Z','brief_sha256':digest(b),'checks':{k:{'result':'pass','evidence':'Synthetic test evidence only; not an actual editorial review.'} for k in CHECKS}}


class DailyBriefTests(unittest.TestCase):
    def test_empty_catalog_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'content/daily-briefs').mkdir(parents=True)
            (root/'content/daily-briefs/catalog.json').write_text('{"schema_version":1,"briefs":[],"reviews":[]}')
            self.assertEqual(load(root),[])
            self.assertEqual(outputs(root),({},[]))
    def test_decimal_arithmetic(self):
        self.assertEqual(calculations(fixture()),{'total':'80','ratio':'30'})
    def test_kst_date(self):
        b=fixture();self.assertEqual(validate(b,review(b),NOW),'2026-11-01')
    def test_mutated_content_invalidates_review(self):
        b=fixture();r=review(b);b['title']='Changed'
        with self.assertRaisesRegex(ValueError,'exact brief'):validate(b,r,NOW)
    def test_arithmetic_failure(self):
        b=fixture();b['calculations'][0]['expected']='686026'
        with self.assertRaisesRegex(ValueError,'arithmetic'):validate(b,review(b),NOW)
    def test_nonapproved_and_self_review_blocked(self):
        for field,value in [('status','draft'),('author','independent-test-reviewer')]:
            b=fixture();b[field]=value
            with self.assertRaises(ValueError):validate(b,review(b),NOW)
    def test_missing_evidence_each_gate(self):
        for check in CHECKS:
            b=fixture();r=review(b);r['checks'][check]['evidence']=''
            with self.assertRaises(ValueError):validate(b,r,NOW)
    def test_dates_sources_units_decimal_fail_closed(self):
        mutations=[lambda b:b.update(published_at='2027-01-01T00:00:00Z'),lambda b:b.update(source_checked_at='2026-11-02T00:00:00Z'),lambda b:b['facts']['first'].update(value=795263),lambda b:b['facts']['first'].update(unit='USD millions'),lambda b:b['sources']['sec'].update(url='http://example.com'),lambda b:b['facts']['first'].update(source_id='missing')]
        for mutate in mutations:
            b=fixture();mutate(b)
            with self.assertRaises(ValueError):validate(b,review(b),NOW)
    def test_duplicate_kst_date(self):
        b=fixture();c=copy.deepcopy(b);c['slug']='second-brief';c['published_at']='2026-11-01T00:00:00Z'
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'content/daily-briefs').mkdir(parents=True)
            (r/'content/daily-briefs/catalog.json').write_text(json.dumps({'schema_version':1,'briefs':[b,c],'reviews':[review(b),review(c)]}))
            with self.assertRaisesRegex(ValueError,'KST'):load(r,NOW)
    def test_missing_review_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'content/daily-briefs').mkdir(parents=True)
            (r/'content/daily-briefs/catalog.json').write_text(json.dumps({'schema_version':1,'briefs':[fixture()],'reviews':[]}))
            with self.assertRaisesRegex(ValueError,'review'):load(r,NOW)
    def test_render_escapes_and_is_idempotent(self):
        from unittest.mock import patch
        b=fixture();b['title']='<script>alert(1)</script>'
        with patch('daily_briefs.load', return_value=[b]), patch.object(Path, 'glob', return_value=[]):
            a, _=outputs(ROOT);c, _=outputs(ROOT)
        self.assertEqual(a,c)
        self.assertEqual(len(a),2)
        detail=a[ROOT/('brief-'+b['slug']+'.html')]
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',detail)
        self.assertNotIn('<script>alert(1)</script>',detail)
        self.assertNotIn('<table',detail)
        self.assertNotIn('<h2',detail.split('<main',1)[1].split('</main>',1)[0])
        self.assertNotIn('Recalculation ledger',detail)
        self.assertNotIn('USD thousands',detail)
        for section in b['sections']:self.assertIn(section['text'],detail)
        for key in b['facts']:self.assertNotIn('>'+key+'<',detail)

    def test_full_builder_approved_fixture_rebuild_stable(self):
        import shutil
        from unittest.mock import patch
        import build_site
        b=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)/'site'
            shutil.copytree(ROOT,r,ignore=shutil.ignore_patterns('.git','__pycache__','brief-*.html','daily-briefs.html'))
            with patch('daily_briefs.load',return_value=[b]):
                first=build_site.planned_outputs(r)
                for p,text in first.items():p.write_text(text)
                second=build_site.planned_outputs(r)
            self.assertEqual(first,second)
            xml=second[r/'sitemap.xml']
            self.assertEqual(xml.count('<loc>https://dividendforensics.com/daily-briefs.html</loc>'),1)
            self.assertEqual(xml.count('<loc>https://dividendforensics.com/brief-'+b['slug']+'.html</loc>'),1)
            self.assertIn('Daily Brief',second[r/'research.html'])
            self.assertIn('Daily Brief',second[r/'index.html'])

    def test_newsletter_paragraph_count_without_weakening_ledger(self):
        b=fixture();b['sections']*=2
        with self.assertRaisesRegex(ValueError,'three or four'):validate(b,review(b),NOW)
        b=fixture();b['calculations'][0]['expected']='999'
        with self.assertRaisesRegex(ValueError,'arithmetic'):validate(b,review(b),NOW)

    def test_exact_review_may_follow_editorial_decision_not_deployment(self):
        b=fixture();r=review(b);r['reviewed_at']='2026-10-31T23:00:00Z'
        validate(b,r,NOW)
        r['reviewed_at']='2026-11-02T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'chronology'):validate(b,r,NOW)

    def test_truthful_source_date_only(self):
        b=fixture();src=b['sources']['sec'];src.pop('published_at');src.update(published_date='2026-10-29',publication_precision='date')
        validate(b,review(b),NOW)
        src['published_at']='2026-10-29T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'invent'):validate(b,review(b),NOW)
        src.pop('published_at');src['published_date']='2026-11-10'
        with self.assertRaisesRegex(ValueError,'publication date'):validate(b,review(b),NOW)

    def test_sec_domain_path_and_source_required(self):
        for url in ['https://evil.example/fake', 'https://sec.gov.evil.example/Archives/edgar/data/0/000000000026000001/test.htm', 'https://www.sec.gov/news/test.htm', 'https://www.sec.gov/Archives/edgar/data/0/not-accession/test.htm']:
            b=fixture();b['sources']['sec']['url']=url
            with self.assertRaisesRegex(ValueError,'SEC'):validate(b,review(b),NOW)
        b=fixture();b['sources']['sec']['kind']='issuer'
        with self.assertRaisesRegex(ValueError,'SEC'):validate(b,review(b),NOW)
        b=fixture();b['sources']['sec']['content_sha256']=''
        with self.assertRaisesRegex(ValueError,'SHA256'):validate(b,review(b),NOW)

    def test_same_event_new_date_and_slug_rejected(self):
        b=fixture();c=copy.deepcopy(b);c['slug']='repackaged-event';c['published_at']='2026-11-02T00:00:00Z'
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'content/daily-briefs').mkdir(parents=True)
            (r/'content/daily-briefs/catalog.json').write_text(json.dumps({'schema_version':1,'briefs':[b,c],'reviews':[review(b),review(c)]}))
            with self.assertRaisesRegex(ValueError,'event already'):load(r,datetime(2026,11,3,tzinfo=timezone.utc))
        c['event_key']='sec:arbitrary-new-label'
        with self.assertRaisesRegex(ValueError,'accession'):validate(c,review(c),datetime(2026,11,3,tzinfo=timezone.utc))

    def test_comparison_period_and_derived_cash_calculations(self):
        b=fixture();prior={'start':'2025-07-01','end':'2025-09-30'};b['comparison_periods']=[prior]
        for key,value,period in [('current_ocf','100.5',b['reporting_period']),('current_ppe','30.2',b['reporting_period']),('prior_ocf','80.1',prior),('prior_ppe','20.3',prior)]:
            b['facts'][key]={'value':value,'unit':'USD thousands','basis':'Synthetic reported positive spending','source_id':'sec','locator':'Test cell','period':period}
        def calc(id,op,inputs,expected,unit='USD thousands',places=1):
            return {'id':id,'operation':op,'inputs':inputs,'expected':expected,'unit':unit,'decimal_places':places,'precision_note':'Synthetic arithmetic fixture, not real financial data.','comparison_basis':'Compare corresponding three-month periods; both inputs use the same cash definition.'}
        b['calculations']=[calc('current_fcf','subtract',['current_ocf','current_ppe'],'70.3'),calc('prior_fcf','subtract',['prior_ocf','prior_ppe'],'59.8'),calc('delta','subtract',['current_fcf','prior_fcf'],'10.5'),calc('growth','percent_change',['current_fcf','prior_fcf'],'17.6','percent'),calc('multiple','ratio',['current_fcf','prior_fcf'],'1.2','times')]
        validate(b,review(b),NOW)
        self.assertEqual(calculations(b),{'current_fcf':'70.3','prior_fcf':'59.8','delta':'10.5','growth':'17.6','multiple':'1.2'})
        b['calculations'][0]['inputs']=['growth','current_ppe']
        with self.assertRaisesRegex(ValueError,'unknown calculation'):calculations(b)

    def test_removed_public_records_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'content/daily-briefs').mkdir(parents=True)
            (r/'content/daily-briefs/catalog.json').write_text('{"schema_version":1,"briefs":[],"reviews":[]}')
            (r/'brief-existing.html').write_text('published')
            with self.assertRaisesRegex(ValueError,'removed'):outputs(r)

if __name__=='__main__':unittest.main()
