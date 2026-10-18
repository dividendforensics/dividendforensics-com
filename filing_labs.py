"""Dated, reproducible filing exercises. Building these pages makes no network requests."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from education import E, section_head, shell

REIT_ADJUSTMENTS = (
    'redemption_adjustment', 'share_compensation', 'debt_amortization',
    'swap_amortization', 'credit_allowance', 'leasing_costs', 'recurring_capex',
    'straight_line', 'lease_amortization', 'deferred_tax', 'unconsolidated',
    'other_adjustments',
)
BDC_INCOME = ('interest_income', 'structuring_fees', 'dividend_income', 'other_income')
BDC_EXPENSES = ('interest_fees', 'management_fee', 'income_fee', 'capital_gains_fee',
                'administrative_fee', 'other_expenses')
PIK_INTEREST = ('pik_interest_nonaffiliate', 'pik_interest_affiliate', 'pik_interest_controlled')
PIK_DIVIDENDS = ('pik_dividend_nonaffiliate', 'pik_dividend_controlled')


def load(root):
    """Reject missing provenance, changed periods and lossy numerical input before rendering."""
    data = json.loads((Path(root) / 'content' / 'filing-labs.json').read_text(encoding='utf-8'))
    slugs = set()
    for lab in data['labs']:
        if not re.fullmatch(r'filing-lab-[a-z0-9-]+', lab['slug']) or lab['slug'] in slugs:
            raise ValueError('Invalid or duplicate filing-lab slug')
        slugs.add(lab['slug'])
        if lab['sector'] not in ('reit', 'bdc'):
            raise ValueError('Unknown filing-lab sector')
        if date.fromisoformat(lab['updated']) < date.fromisoformat(lab['published']):
            raise ValueError('Lab update precedes publication')
        if date.fromisoformat(lab['periodStart']) > date.fromisoformat(lab['periodEnd']):
            raise ValueError('Invalid lab period')
        for key, fact in lab['facts'].items():
            raw = fact['value']
            if not isinstance(raw, str) or not re.fullmatch(r'-?\d+(?:\.\d+)?', raw):
                raise ValueError(f'{key}: facts require finite decimal strings')
            source = data['sources'][fact['sourceID']]
            if fact['sourceID'] not in lab['sourceIDs'] or fact['sourceURL'] != source['url']:
                raise ValueError(f'{key}: source provenance mismatch')
            if fact['availableFrom'] != source['published']:
                raise ValueError(f'{key}: availability date mismatch')
            if urlsplit(fact['sourceURL']).scheme != 'https':
                raise ValueError(f'{key}: source requires HTTPS')
            if not all(fact.get(field) for field in ('unit', 'basis', 'locator', 'provenance')):
                raise ValueError(f'{key}: incomplete source record')
            if fact['unit'].startswith('USD') and fact['currency'] != 'USD':
                raise ValueError(f'{key}: currency mismatch')
            if fact['periodStart'] not in (None, lab['periodStart']):
                raise ValueError(f'{key}: reporting period mismatch')
            if fact['periodEnd'] != lab['periodEnd'] or fact['asOf'] != lab['asOf']:
                raise ValueError(f'{key}: reporting date mismatch')
            if date.fromisoformat(source['published']) < date.fromisoformat(fact['asOf']):
                raise ValueError(f'{key}: source predates historical fact')
            if date.fromisoformat(fact['checkedOn']) < date.fromisoformat(source['published']):
                raise ValueError(f'{key}: source check predates publication')
    return data


def amounts(lab, keys, unit):
    result = []
    for key in keys:
        fact = lab['facts'][key]
        if fact['unit'] != unit:
            raise ValueError(f'{key}: expected {unit}, received {fact["unit"]}')
        result.append(Decimal(fact['value']))
    return result


def number(lab, key, unit):
    return amounts(lab, (key,), unit)[0]


def ratio(numerator, denominator):
    if denominator <= 0:
        raise ValueError('Historical ratio requires a positive denominator')
    return numerator / denominator


def calculate_reit(lab):
    with localcontext() as context:
        context.prec = 40
        unit = 'USD thousand'
        n = lambda key: number(lab, key, unit)
        normalized = n('ffo_common') + n('normalizing_costs')
        adjustment = sum(amounts(lab, REIT_ADJUSTMENTS, unit))
        affo = normalized + adjustment
        diluted = affo + n('affo_nci')
        if (normalized, affo, diluted) != (n('normalized_ffo'), n('affo_common'), n('affo_diluted')):
            raise ValueError('REIT reconciliation does not tie to the source totals')
        per_share = number(lab, 'affo_diluted_ps', 'USD per share')
        dividend = number(lab, 'dividend_paid_ps', 'USD per share')
        return dict(normalized=normalized, adjustment=adjustment, affo=affo,
                    diluted=diluted, surplus=affo-n('distributions_paid'),
                    aggregate_payout=ratio(n('distributions_paid'), affo)*100,
                    share_payout=ratio(dividend, per_share)*100,
                    share_coverage=ratio(per_share, dividend),
                    annualized_payout=ratio(number(lab, 'annualized_dividend_ps', 'USD per share'), per_share)*100,
                    implied_affo_ps=ratio(diluted, number(lab, 'diluted_shares', 'thousand shares')))


def calculate_bdc(lab):
    with localcontext() as context:
        context.prec = 40
        unit = 'USD million'
        n = lambda key: number(lab, key, unit)
        income = sum(amounts(lab, BDC_INCOME, unit))
        expenses = sum(amounts(lab, BDC_EXPENSES, unit))
        nii = income - expenses - n('tax')
        if (income, expenses, nii) != (n('tii'), n('total_expenses'), n('nii')):
            raise ValueError('BDC NII reconciliation does not tie to the source totals')
        interest = sum(amounts(lab, PIK_INTEREST, unit))
        dividends = sum(amounts(lab, PIK_DIVIDENDS, unit))
        pik = interest + dividends
        core = sum(amounts(lab, ('gaap_eps', 'core_gain_adjustment', 'core_fee_adjustment', 'core_tax_adjustment'), 'USD per share'))
        if core != number(lab, 'core_eps', 'USD per share'):
            raise ValueError('Core EPS reconciliation does not tie to the source total')
        distribution = n('distributions_declared')
        dividend_ps = number(lab, 'dividends_ps', 'USD per share')
        scenarios = []
        for fraction in ('0', '0.25', '0.5', '1'):
            f = Decimal(fraction)
            sensitivity = nii-pik*f
            scenarios.append(dict(fraction=f, income=sensitivity, coverage=ratio(sensitivity, distribution)))
        return dict(income=income, expenses=expenses, nii=nii, pik_interest=interest,
                    pik_dividends=dividends, pik=pik, pik_tii=ratio(pik, income)*100,
                    pik_nii=ratio(pik, nii)*100, core=core,
                    reported_coverage=ratio(nii, distribution),
                    share_coverage=ratio(number(lab, 'nii_ps', 'USD per share'), dividend_ps),
                    core_coverage=ratio(core, dividend_ps), scenarios=scenarios)


def fmt(value, places=0):
    value = Decimal(value)
    return f'{value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP):,.{places}f}'


def value(lab, key):
    raw = lab['facts'][key]['value']
    places = len(raw.partition('.')[2])
    return fmt(raw, places)


def link(source, label):
    return f'<a href="{E(source["url"])}" target="_blank" rel="noopener">{E(label)} ↗</a>'


def input_table(lab, keys, caption, sources):
    rows = []
    for key in keys:
        f = lab['facts'][key]
        source = sources[f['sourceID']]
        # The short label stays legible; the complete locator is visible when expanded.
        rows.append(f'<tr><th scope="row">{E(f["label"])}<details><summary>Source location</summary>'
                    f'<p class="small-note">{E(f["locator"])}. {E(f["basis"])}. '
                    f'{link(source, "Open disclosure")}</p></details></th>'
                    f'<td>{E(value(lab,key))}</td><td>{E(f["unit"])}</td></tr>')
    return (f'<div class="table-scroll" tabindex="0" role="region" aria-label="{E(caption)}">'
            f'<table><caption>{E(caption)}</caption><thead><tr><th scope="col">Source input</th>'
            f'<th scope="col">Reported value</th><th scope="col">Unit</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')


def answer(question, text):
    return f'<details class="workshop-answer"><summary>{E(question)}</summary><p>{text}</p></details>'


def reit_content(lab, data):
    s = data['sources']
    r = calculate_reit(lab)
    table = lambda keys, title: input_table(lab, keys, title, s)
    bridge = table(REIT_ADJUSTMENTS, 'FY2024 signed adjustments after Normalized FFO; USD thousands')
    return f'''
<section id="task"><h2>Your assignment: audit a payout sentence.</h2>
<p>A research note says, “The annual dividend was 3.168 and AFFO was 4.19, so the 2024 payout was about 75.6%.” Before accepting that sentence, identify what each number measures. Then rebuild the issuer’s AFFO and decide which numerator belongs in a historical paid-dividend calculation.</p>
<p>FFO means <strong>funds from operations</strong>; AFFO means <strong>adjusted funds from operations</strong>. They supplement the financial statements prepared under US generally accepted accounting principles (GAAP). The adjustments and the claim attributable to common shareholders matter as much as the metric’s name.</p>
<ol><li>Start with FFO and the separate normalization adjustment. Add every signed AFFO adjustment below.</li><li>Calculate paid dividends divided by diluted AFFO per share. Repeat using aggregate common amounts.</li><li>Explain the difference between the two valid ratios and the error in the opening sentence.</li><li>Find a capital-expenditure disclosure that the headline ratio alone cannot explain.</li></ol>
<p>Use the full-year 2024 columns throughout. Read the source locations before opening the answers; all calculations and explanations remain available without JavaScript.</p></section>

<section id="inputs"><h2>Choose the period and the common-share claim.</h2>
<p>The earnings release presents a quarter beside a full year. Its detailed tables use <strong>USD thousands</strong>, while the summary uses millions. Per-share amounts are in USD, and the share denominator is in thousands of shares. These scales cancel only when paired correctly. {link(s['o-release'], 'Release, pp.8–10')}</p>
{table(('net_income_common','ffo_common','normalizing_costs','normalized_ffo'), 'Annual starting amounts; do not combine the Q4 column with the year column')}
<p>GAAP net income is the accounting starting point. FFO, Normalized FFO and AFFO are distinct non-GAAP measures. This lab begins its arithmetic bridge at disclosed FFO; the full GAAP-to-FFO reconciliation is on page 9. Normalization does not make an expense economically irrelevant.</p>
{table(('affo_diluted_ps','dividend_paid_ps','annualized_dividend_ps','distributions_paid'), 'Dividend inputs: annual paid amount versus year-end annualized rate')}
<p>The summary rounds the annual paid dividend to $3.126. The detailed income table gives <strong>${value(lab,'dividend_paid_ps')}</strong>, also confirmed by the monthly distribution schedule in {link(s['o-10k'], '10-K Note 17A, p.81')}. Preserve that precision until the final display.</p></section>

<section id="calculation"><h2>Rebuild the bridge before calculating a ratio.</h2>
<p>FFO {value(lab,'ffo_common')} + normalization {value(lab,'normalizing_costs')} = <strong>{fmt(r['normalized'])}</strong> of Normalized FFO, all in USD thousands. Next add the signed items; parentheses in the source mean negative adjustments.</p>
{bridge}
{answer('Reveal the complete AFFO reconciliation', f'The signed adjustments sum to <strong>+{fmt(r["adjustment"])} USD thousand</strong>. Normalized FFO {fmt(r["normalized"])} + {fmt(r["adjustment"])} = <strong>{fmt(r["affo"])} USD thousand</strong> of AFFO available to common stockholders. This exactly matches the disclosed total. The net increase hides both substantial additions and deductions; it is not a single cash-flow adjustment.')}
<p>Do not deduct leasing costs, recurring capex or straight-line rent a second time from the disclosed AFFO. They have already passed through this reconciliation.</p>
{answer('Reveal the two payout calculations', f'Using the reported per-share figures: ${value(lab,"dividend_paid_ps")} ÷ ${value(lab,"affo_diluted_ps")} × 100 = <strong>{fmt(r["share_payout"],4)}%</strong>; coverage is <strong>{fmt(r["share_coverage"],4)}×</strong>. Using aggregate common amounts: {value(lab,"distributions_paid")} ÷ {fmt(r["affo"])} × 100 = <strong>{fmt(r["aggregate_payout"],4)}%</strong>. Aggregate AFFO less distributions is <strong>{fmt(r["surplus"])} USD thousand</strong>. This last amount is an arithmetic excess under the issuer definition, not a bank balance or uncommitted cash.')}
</section>

<section id="interpretation"><h2>Why two valid ratios do not match exactly.</h2>
{table(('affo_common','affo_nci','affo_diluted','diluted_shares'), 'Bridge to diluted AFFO per share; distinguish numerator attribution from the share count')}
<p>The diluted numerator adds the amount attributable to dilutive noncontrolling interests: {value(lab,'affo_common')} + {value(lab,'affo_nci')} = {value(lab,'affo_diluted')}. Divide by {value(lab,'diluted_shares')} thousand weighted-average diluted shares to obtain approximately <strong>${fmt(r['implied_affo_ps'],6)}</strong>, which the issuer displays as $4.19. The aggregate common calculation uses the common-only numerator instead.</p>
<p>A year’s dividends per share sum the payments on one continuously held share. An aggregate payment total reflects shares entitled to each payment. That entitlement population need not equal the weighted-average diluted earnings denominator. Attribution, timing and displayed per-share rounding can therefore separate these ratios. Label the basis instead of forcing agreement.</p>
{answer('Correct the opening research note', f'The $3.168 figure is a year-end annualized rate. Dividing it by $4.19 produces {fmt(r["annualized_payout"],4)}%, but mixes a year-end run rate with a full year of earnings. For historical paid-dividend payout, use $3.1255 and report {fmt(r["share_payout"],4)}%. Note 17A identifies a $0.2640 amount payable at year-end and paid in January 2025; multiplying that monthly amount by 12 explains $3.168. It is not the sum of payments made in 2024.')}
</section>

<section id="limits"><h2>What the reconstructed result leaves unanswered.</h2>
<p>An add-back can remove an accounting expense from a performance metric without removing the underlying economic risk. The credit-loss allowance adjustment does not establish collection; adding back share compensation does not erase dilution. Lease and financing amortization adjustments also need their own accounting context. Read the release’s AFFO footnotes and definition before comparing another REIT.</p>
<p>The recurring-capex deduction is {value(lab,'recurring_capex')} USD thousand. Separately, the 10-K reports <strong>${value(lab,'existing_property_costs')} million</strong> capitalized on existing properties, including <strong>${value(lab,'nonrecurring_improvements')} million</strong> classified as non-recurring building improvements. {link(s['o-10k'], '10-K Note 4B, Investments in Existing Properties')}</p>
<p>The useful follow-up is to examine those classifications and their funding. Deducting all property investment indiscriminately would mix maintenance with investment activity; assuming only the AFFO deduction can ever require cash would also skip a real funding question. This lab does not decide a replacement capex allowance.</p>
<p>AFFO is not operating cash flow, liquidity or a forecast of distributions. The ratio does not test debt maturities, borrowing covenants, future tenant payments, taxes or the durability of excluded costs. No pass/fail threshold or company rating follows from it.</p></section>

<section id="quiz"><h2>Check your reasoning.</h2>
{answer('1. Can 2,691,719 ÷ 4.19 be called the payout ratio?', 'No. The numerator is USD thousands and the denominator is USD per diluted share. Pair aggregate common distributions with aggregate common AFFO, or pair per-share values with per-share values. A percentage requires compatible dimensions.')}
{answer('2. Is the entire 57,486 increase from Normalized FFO an additional cash receipt?', 'No. It is the net of the signed issuer adjustments. Several are noncash accounting items, and other entries are deductions. A reconciliation of a performance metric is not a cash-receipts schedule.')}
{answer('3. Why does the detailed table use 3.1255 rather than the headline 3.126?', 'The headline rounds the annual payment. Keeping the detailed figure avoids introducing another rounding difference, although the disclosed AFFO per-share figure itself is still rounded. Four decimal places in our ratio describe the arithmetic of those published inputs, not four-decimal economic certainty.')}
</section>

<section id="next"><h2>Reproduce and extend the work.</h2>
<p>In the <a href="/calculator-payout-ratio.html">AFFO payout calculator</a>, enter annual AFFO per common share <strong>4.19</strong>, annual dividend per share <strong>3.1255</strong> and decline <strong>0</strong> to reproduce the historical per-share calculation. Any nonzero decline you enter is a new hypothetical assumption, not a company forecast. The calculator’s initial example is synthetic; replace its inputs.</p>
<p>Continue with <a href="/learn-affo.html">issuer-defined AFFO</a>, <a href="/learn-expert-affo-normalization.html">normalization decisions</a> and <a href="/learn-read-filings.html">reading a filing</a>. Record the calculation basis and unresolved capex question in the <a href="/dividend-research-worksheet.html">research worksheet</a>.</p></section>'''


def bdc_content(lab, data):
    s = data['sources']
    r = calculate_bdc(lab)
    table = lambda keys, title: input_table(lab, keys, title, s)
    scenarios = ''.join(f'<tr><th scope="row">{fmt(row["fraction"]*100)}%</th><td>{fmt(row["income"],2)}</td><td>{fmt(row["coverage"],4)}×</td></tr>' for row in r['scenarios'])
    return f'''
<section id="task"><h2>Your assignment: identify which income covers which distribution.</h2>
<p>You receive three per-share numbers from the same earnings release: net income under US generally accepted accounting principles (GAAP), reported <strong>net investment income (NII)</strong> and the issuer’s <strong>Core EPS</strong> (core earnings per share). They are not interchangeable. Reproduce the reported income first, then trace the issuer adjustment and the noncash income embedded in the starting amount.</p>
<p><strong>Payment-in-kind (PIK)</strong> income is recognized before the corresponding cash is received. Depending on the contract, interest can be added to loan principal, while dividends can increase the investment claim or be paid in additional securities. A recorded income amount therefore needs a separate collection question.</p>
<ol><li>Rebuild annual NII from investment income, expenses and tax.</li><li>Calculate reported NII coverage using both aggregate amounts and the separately reported per-share amounts.</li><li>Sum PIK interest and PIK dividends across all disclosed ownership categories.</li><li>Compute a constant-expense PIK deduction sensitivity, then explain why it is not cash earnings.</li></ol>
<p>All source inputs relate to <strong>January 1–December 31, 2024</strong>. Ares Capital’s release places Q4 beside full-year data; use FY2024. Aggregate amounts are <strong>USD millions</strong>. Per-share figures are <strong>USD per basic common share</strong>. {link(s['arcc-release'], 'Release, pp.1 and 8–9')}</p></section>

<section id="inputs"><h2>Reconstruct the reported NII line.</h2>
{table(BDC_INCOME, 'FY2024 investment-income components; USD millions')}
{table(BDC_EXPENSES+('tax',), 'FY2024 expenses and tax; USD millions')}
{answer('Reveal the NII reconstruction', f'Investment income: 2,162 + 172 + 594 + 62 = <strong>{fmt(r["income"])}</strong>. Expenses: 715 + 374 + 364 + 18 + 12 + 31 = <strong>{fmt(r["expenses"])}</strong>. Subtract expenses and tax: {fmt(r["income"])} − {fmt(r["expenses"])} − 73 = <strong>{fmt(r["nii"])} USD million</strong> of reported NII. Neither gross investment income nor NII before tax is the final reported NII line.')}
{table(('nii_ps','core_eps','gaap_eps','dividends_ps','distributions_declared','cash_dividends_paid'), 'Coverage inputs: retain per-share versus aggregate and declared versus cash-paid distinctions')}
<p>The aggregate denominator comes from the 10-K cash-flow statement’s supplemental disclosure, also shown in stockholders’ equity. The financing cash-flow line is a different amount. {link(s['arcc-10k'], '10-K, pp.F-144–F-145')}</p></section>

<section id="calculation"><h2>Keep the coverage measure visible.</h2>
{answer('Reveal reported NII coverage', f'Aggregate reported NII coverage is {value(lab,"nii")} ÷ {value(lab,"distributions_declared")} = <strong>{fmt(r["reported_coverage"],4)}×</strong>, using common dividends declared and payable. The separate published per-share calculation is $2.25 ÷ $1.92 = <strong>{fmt(r["share_coverage"],4)}×</strong>. Their denominators reflect different share populations and timing; the per-share earnings input is also rounded. Do not manufacture an aggregate distribution by multiplying $1.92 by year-end or weighted-average shares when the actual aggregate is disclosed.')}
<p>A coverage calculation answers a narrow accounting question. It neither shows when cash arrived nor identifies the tax character of a distribution. Substituting the smaller cash-paid figure would answer a different question from coverage of the total declared distribution.</p>
<h3>Follow Core EPS through its own reconciliation.</h3>
{table(('gaap_eps','core_gain_adjustment','core_fee_adjustment','core_tax_adjustment','core_eps'), 'Schedule 1: signed bridge from GAAP net income per basic share to Core EPS')}
{answer('Reveal the Core EPS bridge and comparison', f'$2.44 − $0.19 + $0.03 + $0.05 = <strong>${fmt(r["core"],2)}</strong>. Core EPS divided by declared dividends per share is $2.33 ÷ $1.92 = <strong>{fmt(r["core_coverage"],4)}×</strong>, compared with {fmt(r["share_coverage"],4)}× using reported NII per share. Core EPS is the issuer’s non-GAAP measure: its gain/loss, related fee and tax adjustments change the question. Label that definition explicitly; do not describe $2.33 as reported GAAP NII.')}
<p>This bridge excludes specified gains, losses and associated items. It does not show that all remaining income was collected in cash or that structuring fees repeat at the same level. {link(s['arcc-release'], 'Core EPS definition and Schedule 1')}</p></section>

<section id="interpretation"><h2>PIK is more than the interest row.</h2>
<p>The full 10-K separates income from non-controlled/non-affiliate, non-controlled affiliate and controlled affiliate investments. Sum the explicitly labeled PIK interest <em>and</em> dividend rows before choosing a denominator. {link(s['arcc-10k'], 'Consolidated Statement of Operations, p.F-6')}</p>
{table(PIK_INTEREST+PIK_DIVIDENDS, 'FY2024 recognized PIK income; USD millions; these are income flows, not investment balances')}
{answer('Reveal the complete PIK total and ratios', f'PIK interest = 174 + 14 + 18 = <strong>{fmt(r["pik_interest"])}</strong>; PIK dividends = 253 + 4 = <strong>{fmt(r["pik_dividends"])}</strong>. Total PIK = <strong>{fmt(r["pik"])} USD million</strong>. PIK ÷ total investment income = 463 ÷ 2,990 = <strong>{fmt(r["pik_tii"],4)}%</strong>. PIK ÷ positive reported NII = 463 ÷ 1,403 = <strong>{fmt(r["pik_nii"],4)}%</strong>. The first describes the composition of gross recognized income. The second scales that gross component against income after expenses and tax; it is not the percentage of net cash profit left uncollected.')}
<p>Counting only PIK interest would omit the PIK dividends. Conversely, a portfolio’s principal or fair value tagged as PIK is a balance at a date; it cannot replace PIK income recognized during the year. These categories answer different questions.</p>
<h3>A deliberately limited deduction sensitivity.</h3>
<p>Set sensitivity income = 1,403 − 463 × deduction fraction. Divide by the <strong>same 1,219</strong> of aggregate common dividends declared and payable. Hold every expense, fee, tax and other item constant.</p>
<div class="table-scroll" tabindex="0" role="region" aria-label="Hypothetical PIK deduction sensitivity"><table><caption>Historical inputs; hypothetical deductions, not issuer guidance</caption><thead><tr><th scope="col">PIK deduction</th><th scope="col">Income, USD million</th><th scope="col">Declared-distribution coverage</th></tr></thead><tbody>{scenarios}</tbody></table></div>
<p>The zero-deduction row is reported NII coverage. The other rows are constructed arithmetic sensitivities. A ratio crossing 1× here does not demonstrate a funding shortfall or predict a distribution change; the construction has deliberately omitted cash collections and the responses of other accounts.</p></section>

<section id="limits"><h2>Why NII minus PIK is not cash earnings.</h2>
<p>PIK adds income before receipt of the corresponding cash. The filing also explains that income-based fees can be calculated on accrued income not yet collected. {link(s['arcc-10k'], 'Income Based Fee policy and related risk discussion, p.44')}</p>
<p>Our sensitivity removes a gross income component while retaining the original fee and tax expense. That is useful for isolating one input, but it is not a recalculation under the advisory agreement. Actual fee hurdles, catch-up provisions, tax treatment and timing require a separate model. No automatic fee rebate is assumed.</p>
<p>Other noncash accruals can remain after PIK is removed. Cash received this year can also relate to income recognized in an earlier year. A cash analysis therefore needs cash-flow and collection evidence, borrowing activity, investment purchases and repayments, and the distribution settlement record. Neither Core EPS nor this sensitivity supplies those missing pieces.</p>
<p>The 100% deduction is not a claim that PIK will be lost, and the historical ratios do not establish future credit performance. This exercise makes no estimate of defaults, fair values, future income or distributions.</p></section>

<section id="quiz"><h2>Check your reasoning.</h2>
{answer('1. A note reports only 206 million of PIK. What is missing?', 'It added the three PIK interest rows but omitted 257 million of PIK dividend income. The complete recognized PIK total in this exercise is 463 million. Preserve the ownership categories while checking that each income row is counted once.')}
{answer('2. Can the 940 million sensitivity be divided by the 1.92 per-share dividend?', 'No. That mixes an aggregate USD-million amount with USD per share. The matching declared-distribution denominator is 1,219 million. The resulting 0.7711× remains a fixed-expense sensitivity, not cash distribution coverage.')}
{answer('3. Does 33.0007% mean one third of NII was definitely never collected?', 'No. It divides a gross PIK income component by a net accounting measure. It does not trace collections, the timing of earlier accruals, losses or expenses. PIK is noncash at recognition; that fact alone does not establish whether or when it will be collected.')}
{answer('4. Why is it incorrect to silently use Core EPS for reported NII coverage?', 'Core EPS removes particular realized/unrealized effects and related fees and taxes under the issuer definition. A comparison must name that measure. The arithmetic difference does not prove one definition is universally better, and neither is automatically a cash measure.')}
</section>

<section id="next"><h2>Reproduce the calculation in a worksheet.</h2>
<p>Open the <a href="/calculator-bdc-nii-pik.html">NII, PIK and distribution worksheet</a>. Replace the synthetic example with period <strong>2024-01-01 to 2024-12-31</strong>, analysis as-of <strong>2026-10-18</strong>, currency <strong>USD</strong>, scale <strong>millions</strong>, reported NII <code data-lab-input="nii">1403</code>, PIK <code data-lab-input="pik">463</code>, total investment income <code data-lab-input="tii">2990</code>, regular common distributions <code data-lab-input="regular">1219</code>, supplemental <strong>0</strong> and special <strong>0</strong>, on a declared basis. Enter numbers without thousands separators; the input-ready values above intentionally omit commas. The full-year source distribution here comprises the regular quarterly dividends; preserve the source record rather than assuming absent disclosures mean zero in a new case.</p>
<p>The <a href="/calculator-bdc-pik-ratios.html">PIK ratios worksheet</a> uses the same income inputs without a distribution denominator. For interpretation, read <a href="/learn-bdc-nii-coverage.html">NII coverage</a>, <a href="/learn-bdc-pik-income.html">PIK recognition</a> and <a href="/learn-bdc-incentive-fees.html">incentive fees</a>. Save the open questions in the <a href="/dividend-research-worksheet.html">research worksheet</a>.</p></section>'''


def source_section(lab, data):
    items = []
    for sid in lab['sourceIDs']:
        source = data['sources'][sid]
        items.append(f'<li>{link(source,source["title"])} — dated <time datetime="{source["published"]}">{source["published"]}</time>. '
                     f'{E(source["locator"])}. Accession {E(source["accession"])}.</li>')
    amendment = ('<p>The March 24, 2025 amendment adds IHAM financial statements and updates exhibits; its explanatory note states that otherwise the original 10-K is unchanged. It does not turn the historical period into a current assessment.</p>'
                 if lab['sector'] == 'bdc' else '')
    return '<section id="sources"><h2>Primary sources and calculation record.</h2><ul class="source-list">' + ''.join(items) + f'''</ul>{amendment}
<p>Source inputs were checked on <time datetime="2026-10-18">October 18, 2026</time>. These pages deliberately preserve the FY2024 exercise. Later filings are outside its numerical scope. The reporting date describes what was measured; the 2025 publication dates above describe when the cited information became available. Each expandable input location identifies the original table, period, unit and definition; the <a href="/content/filing-labs.json">structured source ledger</a> preserves decimal values, provenance and these separate dates.</p>
<p>Calculations use decimal arithmetic without intermediate display rounding; displayed ratios round half up to four decimal places. Reproducing a disclosure does not verify its underlying estimates or make the resulting measure comparable to another issuer’s definition.</p>
<p class="small-note">Educational material, not an investment recommendation. <a href="/editorial-policy.html">Editorial approach</a> · <a href="/research-desk.html#inquiries">Report a correction</a>. Include the field, source location and reproducible calculation.</p></section>'''


def lab_page(root, lab, data):
    from build_site import display_date
    body = f'''<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/filing-labs.html">Filing labs</a><span>/</span><span aria-current="page">{E(lab['issuer'])} 2024</span></div>'''
    body += section_head('Historical filing lab / ' + lab['sector'].upper(), E(lab['title']), lab['description'])
    body += f'''<div class="wrap article-meta"><a href="/editorial-policy.html">DFB Education</a><span>·</span>Published <time datetime="{lab['published']}">{display_date(lab['published'])}</time><span>·</span>Updated <time datetime="{lab['updated']}">{display_date(lab['updated'])}</time></div>
<section class="wrap education-section"><div class="worked-example"><span class="kicker">Period lock: FY2024</span><h2>Real disclosures. A historical exercise.</h2><p>Reporting period: January 1–December 31, 2024. Snapshot date: December 31, 2024. This is a source-reading exercise, not a current company assessment or forecast. The source publication dates appear below; later results are outside the calculation.</p></div></section>'''
    toc = [('task','Your assignment'),('inputs','Source inputs'),('calculation','Reproduce the calculation'),
           ('interpretation','Interpret the differences'),('limits','Limits'),('quiz','Check your reasoning'),
           ('next','Use the calculators'),('sources','Primary sources')]
    body += '<div class="wrap reading-layout"><aside class="article-toc"><span class="kicker">In this lab</span><ol>' + ''.join(f'<li><a href="#{key}">{label}</a></li>' for key,label in toc) + '</ol></aside><article class="lesson-body">'
    body += reit_content(lab,data) if lab['sector'] == 'reit' else bdc_content(lab,data)
    body += source_section(lab,data) + '</article></div>'
    other = next(item for item in data['labs'] if item['slug'] != lab['slug'])
    body += f'<section class="wrap education-section"><h2>Try the other filing lab.</h2><p><a href="/{other["slug"]}.html">{E(other["title"])}</a> · <a href="/filing-labs.html">All filing labs</a></p></section>'
    return shell(root,lab['slug']+'.html',lab['title'],lab['description'],body,'Article',article=lab)


def cards(root, sector=None):
    if sector not in (None, 'reit', 'bdc'):
        raise ValueError('Unknown filing-lab card sector')
    labs = [lab for lab in load(root)['labs'] if sector is None or lab['sector'] == sector]
    rows = ''.join(f'<article class="lesson-card"><span class="kicker">{lab["sector"].upper()} / historical FY2024</span><h3><a href="/{lab["slug"]}.html">{E(lab["title"])}</a></h3><p>{E(lab["description"])}</p><a class="text-link" href="/{lab["slug"]}.html">Work through the source →</a></article>' for lab in labs)
    return '<section class="wrap education-section"><div class="section-heading"><div><span class="kicker">Practice with primary evidence</span><h2>Read a real filing. Rebuild the numbers.</h2></div><a class="text-link" href="/filing-labs.html">All filing labs →</a></div><div class="lesson-grid">' + rows + '</div></section>'


def index_page(root):
    title = 'Filing labs: work through real REIT and BDC disclosures'
    description = 'Two historical FY2024 exercises with exact source inputs, reproducible calculations, interpretation and answer keys for REIT AFFO and BDC NII and PIK.'
    body = '<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><span aria-current="page">Filing labs</span></div>'
    body += section_head('The filing practice room',title,description)
    body += '''<section class="wrap policy-reading lesson-body"><h2>Turn a metric into an auditable calculation.</h2><p>Knowing a formula is only the first step. These exercises ask you to locate a number, preserve its definition and period, rebuild a reconciliation, and explain what the result cannot establish. Each uses a specific issuer’s FY2024 disclosures and a worked answer you can open after trying the task.</p><p>Start with Realty Income to learn the difference between annual paid dividends, a year-end annualized rate and the diluted AFFO denominator. Continue with Ares Capital to distinguish reported NII from Core EPS and to collect PIK income across several source rows. The companies are teaching examples, not a comparison, ranking or investment selection.</p><h2>Bring these three habits to either lab.</h2><ol><li><strong>Label the column.</strong> Record the full period, currency, scale and common-share basis before doing arithmetic.</li><li><strong>Preserve the reconciliation.</strong> An adjusted metric can add back an economically meaningful cost. Retain both the reported result and the definition.</li><li><strong>Write the unanswered question.</strong> A coverage ratio cannot by itself resolve cash timing, future spending or credit risk.</li></ol><p>All source tables, calculations and answer keys are readable without JavaScript. The linked calculators are optional ways to reproduce the arithmetic. <a href="/editorial-policy.html">How DFB prepares educational material</a>.</p></section>'''
    body += cards(root)
    body += '<section class="wrap education-section"><h2>Keep your own source record.</h2><p>Use the <a href="/dividend-research-worksheet.html">dividend research worksheet</a> to record what you found, or revisit the <a href="/learn.html">REIT curriculum</a> and <a href="/learn-bdc.html">BDC curriculum</a> before starting. For a new period, replace every relevant input and recheck the source definition; copying the historical conclusion is not an update.</p></section>'
    return shell(root,'filing-labs.html',title,description,body,'CollectionPage')


def outputs(root):
    root = Path(root)
    data = load(root)
    result = {root/(lab['slug']+'.html'):lab_page(root,lab,data) for lab in data['labs']}
    result[root/'filing-labs.html'] = index_page(root)
    return result
