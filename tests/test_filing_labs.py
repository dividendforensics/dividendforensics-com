"""Historical-source arithmetic checks using Fraction, independently of renderer Decimal math."""
from copy import deepcopy
from fractions import Fraction
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import filing_labs as labs


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.h1 = 0
        self.summaries = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        self.h1 += tag == 'h1'
        self.summaries += tag == 'summary'


class FilingLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = labs.load(ROOT)
        cls.reit, cls.bdc = cls.data['labs']

    def q(self, lab, key):
        return Fraction(lab['facts'][key]['value'])

    def assertRatio(self, computed, exact):
        # Decimal implementation has 40 significant digits; Fraction does not round.
        self.assertLess(abs(Fraction(computed) - exact), Fraction(1, 10**35))

    def test_reit_complete_signed_reconciliation_and_attribution(self):
        f = lambda key: self.q(self.reit, key)
        # Independently transcribed signed FY2024 source adjustments, not the production key list.
        signed_source_rows = [5116,32741,15361,13935,106801,-8558,-402,-171887,55870,3552,-2078,7035]
        self.assertEqual(sum(signed_source_rows), 57486)
        self.assertEqual(f('ffo_common') + f('normalizing_costs'), 3563951)
        self.assertEqual(f('normalized_ffo') + sum(signed_source_rows), f('affo_common'))
        self.assertEqual(f('affo_common'), 3621437)
        self.assertEqual(f('affo_common') + f('affo_nci'), f('affo_diluted'))
        self.assertEqual(f('affo_diluted'), 3628036)
        self.assertEqual(f('affo_common') - f('distributions_paid'), 929718)
        result = labs.calculate_reit(self.reit)
        self.assertEqual(result['adjustment'], 57486)
        self.assertEqual(result['surplus'], 929718)
        self.assertRatio(result['implied_affo_ps'], Fraction(3628036,865842))

    def test_paid_annualized_and_aggregate_denominators_stay_distinct(self):
        f = lambda key: self.q(self.reit, key)
        self.assertEqual(f('dividend_paid_ps'), Fraction('3.1255'))
        self.assertEqual(f('annualized_dividend_ps'), f('year_end_monthly') * 12)
        result = labs.calculate_reit(self.reit)
        self.assertRatio(result['share_payout'], Fraction('3.1255') / Fraction('4.19') * 100)
        self.assertRatio(result['aggregate_payout'], Fraction(2691719,3621437) * 100)
        self.assertRatio(result['annualized_payout'], Fraction('3.168') / Fraction('4.19') * 100)
        self.assertEqual(labs.fmt(result['share_payout'],4), '74.5943')
        self.assertEqual(labs.fmt(result['aggregate_payout'],4), '74.3274')
        self.assertEqual(labs.fmt(result['annualized_payout'],4), '75.6086')
        self.assertLess(result['aggregate_payout'], result['share_payout'])
        self.assertLess(result['share_payout'], result['annualized_payout'])

    def test_bdc_reported_nii_rebuilt_after_all_expenses_and_tax(self):
        f = lambda key: self.q(self.bdc, key)
        gross = f('interest_income') + f('structuring_fees') + f('dividend_income') + f('other_income')
        costs = (f('interest_fees') + f('management_fee') + f('income_fee') +
                 f('capital_gains_fee') + f('administrative_fee') + f('other_expenses'))
        self.assertEqual(gross,2990)
        self.assertEqual(costs,1514)
        self.assertEqual(gross-costs-f('tax'),1403)
        self.assertEqual(f('nii'),1403)
        result = labs.calculate_bdc(self.bdc)
        self.assertEqual(result['nii'],1403)
        self.assertRatio(result['reported_coverage'],Fraction(1403,1219))
        self.assertRatio(result['share_coverage'],Fraction('2.25')/Fraction('1.92'))
        self.assertEqual(labs.fmt(result['reported_coverage'],4),'1.1509')
        self.assertNotEqual(f('distributions_declared'),f('cash_dividends_paid'))

    def test_core_eps_adjustments_do_not_silently_become_reported_nii(self):
        f = lambda key: self.q(self.bdc, key)
        core = f('gaap_eps') + f('core_gain_adjustment') + f('core_fee_adjustment') + f('core_tax_adjustment')
        self.assertEqual(core,Fraction('2.33'))
        self.assertNotEqual(core,f('nii_ps'))
        result = labs.calculate_bdc(self.bdc)
        self.assertRatio(result['core_coverage'],Fraction(233,192))
        self.assertEqual(labs.fmt(result['core_coverage'],4),'1.2135')

    def test_all_four_dividend_declarations_reconcile_not_just_q4_times_four(self):
        amounts=[self.q(self.bdc,f'q{q}_declared') for q in range(1,5)]
        per_share=[self.q(self.bdc,f'q{q}_dividend_ps') for q in range(1,5)]
        self.assertEqual(amounts,[291,300,308,320])
        self.assertEqual(sum(amounts),self.q(self.bdc,'distributions_declared'))
        self.assertEqual(sum(per_share),Fraction('1.92'))
        bad=deepcopy(self.bdc);bad['facts']['q1_declared']['value']='292'
        with self.assertRaisesRegex(ValueError,'Quarterly dividend schedule'):
            labs.calculate_bdc(bad)

    def test_bdc_pik_includes_dividends_and_uses_consistent_aggregate_sensitivity(self):
        f = lambda key: self.q(self.bdc, key)
        interest = f('pik_interest_nonaffiliate')+f('pik_interest_affiliate')+f('pik_interest_controlled')
        dividends = f('pik_dividend_nonaffiliate')+f('pik_dividend_controlled')
        self.assertEqual(interest,206)
        self.assertEqual(dividends,257)
        self.assertEqual(interest+dividends,463)
        result = labs.calculate_bdc(self.bdc)
        self.assertRatio(result['pik_tii'],Fraction(463,2990)*100)
        self.assertRatio(result['pik_nii'],Fraction(463,1403)*100)
        self.assertEqual(labs.fmt(result['pik_tii'],4),'15.4849')
        self.assertEqual(labs.fmt(result['pik_nii'],4),'33.0007')
        for scenario, fraction in zip(result['scenarios'],(Fraction(0),Fraction(1,4),Fraction(1,2),Fraction(1))):
            exact = Fraction(1403)-Fraction(463)*fraction
            self.assertEqual(Fraction(scenario['income']),exact)
            self.assertRatio(scenario['coverage'],exact/Fraction(1219))
        self.assertEqual(result['scenarios'][-1]['income'],940)
        self.assertEqual(labs.fmt(result['scenarios'][-1]['coverage'],4),'0.7711')

    def test_changed_sign_or_mixed_scale_fails_before_publication(self):
        reit = deepcopy(self.reit)
        reit['facts']['recurring_capex']['value'] = '402'
        with self.assertRaisesRegex(ValueError,'does not tie'):
            labs.calculate_reit(reit)
        bdc = deepcopy(self.bdc)
        bdc['facts']['pik_dividend_controlled']['unit'] = 'USD thousand'
        with self.assertRaisesRegex(ValueError,'expected USD million'):
            labs.calculate_bdc(bdc)
        bdc = deepcopy(self.bdc)
        bdc['facts']['distributions_declared']['value'] = '0'
        with self.assertRaisesRegex(ValueError,'positive denominator'):
            labs.calculate_bdc(bdc)

    def test_ledger_dates_and_provenance_separate_measurement_from_availability(self):
        self.assertIn('not the date',self.data['dateDefinitions']['asOf'])
        for lab in self.data['labs']:
            for key, fact in lab['facts'].items():
                with self.subTest(lab=lab['slug'],fact=key):
                    self.assertIsInstance(fact['value'],str)
                    self.assertEqual(fact['asOf'],'2024-12-31')
                    self.assertGreater(fact['availableFrom'],fact['asOf'])
                    self.assertEqual(fact['availableFrom'],self.data['sources'][fact['sourceID']]['published'])
                    self.assertTrue(fact['locator'] and fact['basis'] and fact['provenance'])
                    self.assertEqual(fact['checkedOn'],'2026-10-18')
        self.assertEqual(self.data['sources']['arcc-amendment']['published'],'2025-03-24')

    def test_ledger_rejects_numeric_float_stale_period_or_wrong_source(self):
        mutations = [('value',3.1255),('value','NaN'),('periodEnd','2025-12-31'),
                     ('sourceURL','https://example.com/wrong'),('availableFrom','2024-12-31')]
        for field,new in mutations:
            data = deepcopy(self.data)
            data['labs'][0]['facts']['dividend_paid_ps'][field] = new
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'content').mkdir()
                (root/'content'/'filing-labs.json').write_text(json.dumps(data),encoding='utf-8')
                with self.subTest(field=field,new=new),self.assertRaises(ValueError):
                    labs.load(root)

    def test_static_exercises_have_worked_answers_sources_and_resolved_internal_links(self):
        output = labs.outputs(ROOT)
        self.assertEqual({p.name for p in output},{'filing-labs.html',self.reit['slug']+'.html',self.bdc['slug']+'.html'})
        for path,text in output.items():
            doc = Document(); doc.feed(text)
            self.assertEqual(doc.h1,1)
            self.assertEqual(len(doc.ids),len(set(doc.ids)))
            for url in doc.links:
                if url.startswith('#'):
                    self.assertIn(url[1:],doc.ids)
                elif url.startswith('/') and not url.startswith('//'):
                    target = ROOT/url.split('#')[0].lstrip('/')
                    self.assertTrue(target in output or target.exists(),url)
            for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S):
                json.loads(raw)
            if path.name != 'filing-labs.html':
                for section in ('task','inputs','calculation','interpretation','limits','quiz','next','sources'):
                    self.assertIn(section,doc.ids)
                self.assertGreaterEqual(doc.summaries,10)
                self.assertIn('not a current company assessment or forecast',text)
                self.assertIn('/content/filing-labs.json',text)
                self.assertNotIn('<form',text)
        bdc_html = output[ROOT/(self.bdc['slug']+'.html')]
        self.assertIn('constant-expense',bdc_html)
        self.assertIn('not cash earnings',bdc_html)
        self.assertIn('analysis as-of <strong>2026-10-18',bdc_html)

    def test_card_discovery_filters_the_sector(self):
        both = labs.cards(ROOT)
        reit = labs.cards(ROOT,'reit')
        bdc = labs.cards(ROOT,'bdc')
        self.assertIn(self.reit['slug'],both)
        self.assertIn(self.bdc['slug'],both)
        self.assertIn(self.reit['slug'],reit)
        self.assertNotIn(self.bdc['slug'],reit)
        self.assertIn(self.bdc['slug'],bdc)
        self.assertNotIn(self.reit['slug'],bdc)


if __name__ == '__main__':
    unittest.main()
