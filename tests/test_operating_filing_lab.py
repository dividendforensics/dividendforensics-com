"""Independently reconstruct the primary-source amounts using rational arithmetic."""
from copy import deepcopy
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import operating_filing_lab as lab_module


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs = [], []
        self.h1 = self.tables = self.captions = self.summary = 0
        self.headers = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a':
            self.hrefs.append(a.get('href',''))
        if tag == 'th':
            self.headers.append(a.get('scope'))
        self.h1 += tag == 'h1'
        self.tables += tag == 'table'
        self.captions += tag == 'caption'
        self.summary += tag == 'summary'


class OperatingFilingLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = lab_module.load(ROOT)
        cls.lab = cls.data['lab']
        cls.result = lab_module.calculate(cls.lab)

    def test_full_operating_reconciliation_not_just_depreciation(self):
        # Independent transcription of p.33 FY2024, deliberately not production key lists.
        adjustments = Fraction(11445) + 11688 - 2266
        operating_changes = Fraction(-3788) - 1356 - 1046 - 11731 + 6020 + 15552
        self.assertEqual(adjustments,20867)
        self.assertEqual(operating_changes,3651)
        self.assertEqual(93736+adjustments+operating_changes,118254)
        self.assertEqual(self.result['adjustments'],adjustments)
        self.assertEqual(self.result['operating_changes'],operating_changes)
        self.assertEqual(self.result['ocf'],118254)

    def test_cash_allocation_is_not_the_cash_change(self):
        fcf = Fraction(118254)-9447
        uses = Fraction(15234)+94949
        self.assertEqual(fcf,108807)
        self.assertEqual(uses,110183)
        self.assertEqual(fcf-uses,-1376)
        self.assertEqual(self.result['fcf'],fcf)
        self.assertEqual(self.result['residual'],fcf-uses)
        self.assertNotEqual(self.result['residual'],self.result['change'])
        for key, exact in [('dividend_payout',Fraction(15234,108807)*100),
                           ('return_payout',Fraction(110183,108807)*100)]:
            self.assertLess(abs(Fraction(self.result[key])-exact),Fraction(1,10**35))

    def test_complete_investing_financing_and_cash_balance(self):
        investing = Fraction(-48656)+51211+11135-9447-1308
        financing = Fraction(-5441)-15234-94949+0-9958+3960-361
        self.assertEqual(investing,2935)
        self.assertEqual(financing,-121983)
        self.assertEqual(118254+investing+financing,-794)
        self.assertEqual(30737+118254+investing+financing,29943)
        self.assertEqual(self.result['investing'],investing)
        self.assertEqual(self.result['financing'],financing)
        self.assertEqual(self.result['ending'],29943)
        self.assertEqual(self.result['other_investing'],12382)
        self.assertEqual(self.result['other_financing'],-11800)
        self.assertEqual(self.result['residual']+self.result['other_investing']+self.result['other_financing'],-794)

    def test_cash_declared_equity_and_shares_are_separate(self):
        q = lambda key: Fraction(self.lab['facts'][key]['value'])
        self.assertEqual(q('dividends_cash'),-15234)
        self.assertEqual(q('dividends_declared'),-15218)
        self.assertEqual(q('repurchases_cash'),-94949)
        self.assertEqual(q('repurchases_equity'),-95846)
        self.assertEqual(q('dividends_declared_per_share'),Fraction('0.98'))
        self.assertEqual(15550061-499372+66097,15116786)
        self.assertEqual(self.result['share_change'],-433275)
        self.assertEqual(q('shares_issued')+q('shares_repurchased'),-433275)
        self.assertEqual(self.lab['facts']['shares_ending']['unit'],'thousand shares')
        self.assertEqual(self.result['dividend_difference'],16)
        self.assertEqual(self.result['equity_repurchase_difference'],897)

    def test_dates_and_source_count_do_not_claim_live_data(self):
        self.assertEqual(len(self.lab['facts']),36)
        self.assertEqual(len(self.data['sources']),2)
        self.assertEqual({f['sourceID'] for f in self.lab['facts'].values()},{'apple-10k'})
        self.assertEqual(self.lab['periodStart'],'2023-10-01')
        self.assertEqual(self.lab['periodEnd'],'2024-09-28')
        for key in ('cash_beginning','shares_beginning'):
            self.assertIsNone(self.lab['facts'][key]['periodStart'])
            self.assertEqual(self.lab['facts'][key]['asOf'],'2023-09-30')
        for f in self.lab['facts'].values():
            self.assertIsInstance(f['value'],str)
            self.assertEqual(f['availableFrom'],'2024-11-01')
            self.assertEqual(f['checkedOn'],'2026-10-18')
        self.assertNotIn('fx',self.lab['facts'])

    def test_wrong_units_periods_signs_and_source_dates_fail(self):
        cases = [('net_income','value',93736), ('net_income','value','NaN'),
                 ('operating_cash','unit','USD thousand'), ('net_income','currency','EUR'),
                 ('cash_beginning','asOf','2024-09-28'), ('capex_cash','value','9447'),
                 ('net_income','availableFrom','2024-09-28'), ('net_income','locator',''),
                 ('financing_other','value','-360'), ('shares_issued','value','66098'),
                 ('net_income','periodStart','2024-01-01')]
        for key,field,value in cases:
            with self.subTest(key=key,field=field,value=value):
                data = deepcopy(self.data)
                data['lab']['facts'][key][field] = value
                with self.assertRaises(ValueError):
                    lab_module.validate(data)

    def test_workbench_handoff_reproduces_source_and_marks_fx_convention(self):
        example = lab_module.workbench_example(ROOT)
        self.assertEqual(example['id'],'apple-2024')
        values = example['values']
        self.assertEqual(values['fiscalYear'],'2024')
        self.assertIn('restricted cash',values['cashDefinition'])
        self.assertIn('worksheet convention',example['sourceLabel'])
        n = lambda key: Fraction(values[key])
        cfo = n('netIncome')+n('noncash')+n('workingCapital')
        self.assertEqual(cfo,n('reportedOCF'))
        self.assertEqual(cfo-n('capex')-n('dividends')-n('buybacks'),-1376)
        self.assertEqual(n('beginningCash')+cfo+n('netInvesting')+n('netFinancing')+n('fx'),n('endingCash'))
        self.assertTrue(all(isinstance(value,str) for value in values.values()))

    def test_generated_page_contains_accessible_sources_and_native_answers(self):
        outputs = lab_module.outputs(ROOT)
        self.assertEqual(list(outputs),[ROOT/'filing-lab-apple-2024.html'])
        html = next(iter(outputs.values()))
        doc = Structure()
        doc.feed(html)
        self.assertEqual(doc.h1,1)
        self.assertEqual(len(doc.ids),len(set(doc.ids)))
        self.assertEqual(doc.tables,doc.captions)
        self.assertGreater(doc.tables,8)
        self.assertTrue(all(scope in ('col','row') for scope in doc.headers))
        self.assertGreater(doc.summary,40)
        self.assertIn('/cash-flow-workbench.html?example=apple-2024',doc.hrefs)
        for href in doc.hrefs:
            if href.startswith('#'):
                self.assertIn(href[1:],doc.ids)
        for f in self.lab['facts'].values():
            self.assertIn(lab_module.E(f['locator']),html)
        self.assertIn('not a separately reported GAAP subtotal',html)
        self.assertIn('worksheet convention, not a transcribed fact',html)
        self.assertNotIn('fetch(',html)


if __name__ == '__main__':
    unittest.main()
