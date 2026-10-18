"""One fixed, sourced operating-company exercise; rendering never fetches live data."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from education import E, section_head, shell

ADJUSTMENTS = ('depreciation', 'stock_compensation', 'other_adjustments')
OPERATING_CHANGES = ('receivables', 'vendor_receivables', 'inventories',
                     'other_assets', 'payables', 'other_liabilities')
INVESTING = ('securities_purchases', 'securities_maturities', 'securities_sales',
             'capex_cash', 'investing_other')
FINANCING = ('equity_tax_cash', 'dividends_cash', 'repurchases_cash',
             'term_debt_issued', 'term_debt_repaid', 'commercial_paper', 'financing_other')
SHARES = ('shares_beginning', 'shares_repurchased', 'shares_issued', 'shares_ending')
BEGINNING = ('cash_beginning', 'shares_beginning')
POINTS = BEGINNING + ('cash_ending', 'shares_ending', 'restricted_cash')


def load(root):
    data = json.loads((Path(root) / 'content' / 'operating-company-lab.json').read_text(encoding='utf-8'))
    validate(data)
    return data


def validate(data):
    lab = data['lab']
    if lab['slug'] != 'filing-lab-apple-2024' or lab['sector'] != 'operating-company':
        raise ValueError('Unexpected historical lab')
    if (lab['periodStart'], lab['periodEnd'], lab['asOf']) != ('2023-10-01', '2024-09-28', '2024-09-28'):
        raise ValueError('Apple FY2024 period mismatch')
    if date.fromisoformat(lab['updated']) < date.fromisoformat(lab['published']):
        raise ValueError('Update precedes publication')
    for key, fact in lab['facts'].items():
        if not isinstance(fact['value'], str) or not re.fullmatch(r'-?\d+(?:\.\d+)?', fact['value']):
            raise ValueError(f'{key}: require finite decimal strings')
        source = data['sources'][fact['sourceID']]
        if fact['sourceID'] not in lab['sourceIDs'] or fact['sourceURL'] != source['url']:
            raise ValueError(f'{key}: provenance mismatch')
        if urlsplit(fact['sourceURL']).scheme != 'https':
            raise ValueError(f'{key}: source requires HTTPS')
        if fact['availableFrom'] != source['published']:
            raise ValueError(f'{key}: availability mismatch')
        for field in ('unit', 'basis', 'locator', 'provenance'):
            if not fact.get(field):
                raise ValueError(f'{key}: missing {field}')
        expected_end = '2023-09-30' if key in BEGINNING else lab['periodEnd']
        expected_start = None if key in POINTS else lab['periodStart']
        if (fact['periodStart'], fact['periodEnd'], fact['asOf']) != (expected_start, expected_end, expected_end):
            raise ValueError(f'{key}: measurement period mismatch')
        expected_unit = ('thousand shares' if key in SHARES else 'USD billion' if key == 'restricted_cash'
                         else 'USD per share or RSU' if key == 'dividends_declared_per_share' else 'USD million')
        if fact['unit'] != expected_unit or fact['currency'] != ('USD' if expected_unit.startswith('USD') else None):
            raise ValueError(f'{key}: currency or scale mismatch')
        if not (date.fromisoformat(fact['asOf']) <= date.fromisoformat(fact['availableFrom'])
                <= date.fromisoformat(fact['checkedOn'])):
            raise ValueError(f'{key}: invalid source chronology')
        if fact['checkedOn'] != data['checkedOn']:
            raise ValueError(f'{key}: check date mismatch')
    calculate(lab)


def amount(lab, key, unit='USD million'):
    fact = lab['facts'][key]
    if fact['unit'] != unit:
        raise ValueError(f'{key}: incompatible unit')
    return Decimal(fact['value'])


def calculate(lab):
    with localcontext() as ctx:
        ctx.prec = 40
        n = lambda key: amount(lab, key)
        total = lambda keys: sum((n(key) for key in keys), Decimal(0))
        adjustments = total(ADJUSTMENTS)
        operating_changes = total(OPERATING_CHANGES)
        ocf = n('net_income') + adjustments + operating_changes
        investing, financing = total(INVESTING), total(FINANCING)
        change = ocf + investing + financing
        ending = n('cash_beginning') + change
        source_totals = (n('operating_cash'), n('investing_cash'), n('financing_cash'), n('cash_change'), n('cash_ending'))
        if (ocf, investing, financing, change, ending) != source_totals:
            raise ValueError('Reconciliation does not match reported cash-flow totals')
        share = lambda key: amount(lab, key, 'thousand shares')
        if share('shares_beginning') + share('shares_repurchased') + share('shares_issued') != share('shares_ending'):
            raise ValueError('Share reconciliation does not match source')
        if any(n(key) > 0 for key in ('capex_cash', 'dividends_cash', 'repurchases_cash')):
            raise ValueError('Cash uses must preserve source negative signs')
        fcf = ocf + n('capex_cash')
        if fcf <= 0:
            raise ValueError('Historical FCF denominator must be positive')
        capital_returns = -n('dividends_cash') - n('repurchases_cash')
        residual = fcf - capital_returns
        return dict(adjustments=adjustments, operating_changes=operating_changes, ocf=ocf,
                    investing=investing, financing=financing, change=change, ending=ending,
                    fcf=fcf, capital_returns=capital_returns, residual=residual,
                    dividend_payout=-n('dividends_cash') / fcf * 100,
                    return_payout=capital_returns / fcf * 100,
                    other_investing=investing-n('capex_cash'),
                    other_financing=financing-n('dividends_cash')-n('repurchases_cash'),
                    dividend_difference=-n('dividends_cash')+n('dividends_declared'),
                    equity_repurchase_difference=-n('repurchases_equity')+n('repurchases_cash'),
                    share_change=share('shares_ending')-share('shares_beginning'))


def fmt(number, places=0):
    return f'{Decimal(number).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP):,.{places}f}'


def source_link(source, label):
    return f'<a href="{E(source["url"])}" target="_blank" rel="noopener">{E(label)} ↗</a>'


def fact_table(lab, keys, caption, data):
    rows = []
    for key in keys:
        f = lab['facts'][key]
        period = f'{f["periodStart"]} to {f["periodEnd"]}' if f['periodStart'] else f'At {f["asOf"]}'
        places = len(f['value'].partition('.')[2])
        rows.append(f'<tr><th scope="row">{E(f["label"])}<details><summary>Source and measurement</summary>'
                    f'<p>{E(f["locator"])}. {E(f["basis"])}.</p><p>{E(period)}. '
                    f'Cited filing available {E(f["availableFrom"])}; checked {E(f["checkedOn"])}. '
                    f'{source_link(data["sources"][f["sourceID"]], "Open original filing")}</p></details></th>'
                    f'<td>{fmt(f["value"],places)}</td><td>{E(f["unit"])}</td></tr>')
    return (f'<div class="table-scroll" tabindex="0" role="region" aria-label="{E(caption)}">'
            f'<table><caption>{E(caption)}</caption><thead><tr><th scope="col">Source input</th>'
            '<th scope="col">Signed value</th><th scope="col">Unit</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>')


def answer(question, text):
    return f'<details class="workshop-answer"><summary>{E(question)}</summary><p>{text}</p></details>'


def copy_table(lab, r):
    rows = [('netIncome', 'Net income', lab['facts']['net_income']['value']),
            ('noncash', 'Signed noncash and other reconciliation adjustments', str(r['adjustments'])),
            ('workingCapital', 'Signed operating-asset and liability changes', str(r['operating_changes'])),
            ('reportedOCF', 'Reported operating cash flow for reconciliation check', lab['facts']['operating_cash']['value']),
            ('capex', 'PP&E cash capex — positive cash-use amount', str(-amount(lab,'capex_cash'))),
            ('dividends', 'Cash dividends and equivalents — positive cash-use amount', str(-amount(lab,'dividends_cash'))),
            ('buybacks', 'Cash repurchases — positive cash-use amount', str(-amount(lab,'repurchases_cash'))),
            ('beginningCash', 'Beginning cash including restricted amounts', lab['facts']['cash_beginning']['value']),
            ('netInvesting', 'Net investing cash flow — signed', str(r['investing'])),
            ('netFinancing', 'Net financing cash flow — signed', str(r['financing'])),
            ('fx', 'Separate FX / cash-reconciliation adjustment — see convention below', '0'),
            ('endingCash', 'Reported ending cash including restricted amounts', lab['facts']['cash_ending']['value'])]
    return ('<div class="table-scroll" tabindex="0" role="region" aria-label="Workbench input values"><table>'
            '<caption>Copy-ready workbench values; all USD millions, without thousands separators</caption>'
            '<thead><tr><th scope="col">Input</th><th scope="col">Value to enter</th></tr></thead><tbody>'
            + ''.join(f'<tr><th scope="row">{E(label)}</th><td><code data-lab-input="{key}">{E(value)}</code></td></tr>' for key,label,value in rows)
            + '</tbody></table></div>')


def lab_page(root, data):
    lab = data['lab']
    r = calculate(lab)
    table = lambda keys, caption: fact_table(lab,keys,caption,data)
    filing = source_link(data['sources']['apple-10k'],'Apple FY2024 10-K')
    body = '<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/filing-labs.html">Filing labs</a><span>/</span><span aria-current="page">Apple FY2024</span></div>'
    body += section_head('Operating-company filing lab / historical FY2024',lab['title'],lab['description'])
    body += f'''<div class="wrap article-meta"><a href="/editorial-policy.html">DFB Education</a><span>·</span> Source checked <time datetime="{data['checkedOn']}">{data['checkedOn']}</time><span>·</span>Fixed historical exercise</div>
<section class="wrap education-section"><div class="worked-example"><h2>Keep three dates separate.</h2><p>The business period is <strong>October 1, 2023–September 28, 2024</strong>. The cited 10-K was filed <strong>November 1, 2024</strong>. DFB checked this historical source on <strong>October 18, 2026</strong>. The check date does not make FY2024 results current. This exercise makes no current dividend, valuation or investment assessment.</p></div></section>'''
    toc = [('task','Assignment'),('operating','Earnings to cash'),('allocation','Cash allocation'),('cash-balance','Cash balance'),('shares','Shares and compensation'),('limits','Limits'),('quiz','Answer checks'),('next','Workbench inputs'),('sources','Sources')]
    body += '<div class="wrap reading-layout"><aside class="article-toc"><span class="kicker">In this lab</span><ol>' + ''.join(f'<li><a href="#{key}">{label}</a></li>' for key,label in toc) + '</ol></aside><article class="lesson-body">'
    body += f'''
<section id="task"><h2>Your assignment: test a cash-distribution claim.</h2>
<p>A draft note says, “Apple produced more cash than earnings, so its cash after capital expenditure was available for dividends and buybacks.” Locate the missing steps before accepting that conclusion. An operating company has cash tied to customers, suppliers, inventory, investment and financing. A profitable year and a positive cash-flow measure answer only part of the funding question.</p>
<ol><li>Rebuild operating cash flow from net income and every signed adjustment.</li><li>Define cash capex and calculate a simple free-cash-flow measure.</li><li>Deduct actual cash dividends and repurchases, preserving their cash-paid basis.</li><li>Reconcile the full change in cash and distinguish repurchase dollars from changes in shares.</li></ol>
<p>Use the FY2024 column of {filing}, particularly pages 32–33 and Note 10. All cash-flow inputs below are <strong>USD millions</strong>. Negative values are cash uses or negative reconciliation adjustments. The answers open with native disclosure controls and remain readable without JavaScript.</p></section>

<section id="operating"><h2>Net income is the starting point, not the cash total.</h2>
{table(('net_income',)+ADJUSTMENTS, 'FY2024 net income and reconciliation adjustments; USD millions')}
<p>The first group reverses or adjusts items included in earnings before the statement addresses operating assets and liabilities. Keep the issuer’s “Other” amount visible: the cash-flow table does not break it into a list of purely noncash charges. Calling the whole group depreciation would discard both share compensation and the negative other adjustment.</p>
{table(OPERATING_CHANGES+('operating_cash',), 'FY2024 changes in operating assets and liabilities, and reported operating cash flow')}
<p>Use the signs in the cash-flow statement. A receivable increase can absorb cash even when revenue is recognized; a payable increase can temporarily support cash. The issuer also includes current and non-current items, so this group is broader than a mechanical change in current assets minus current liabilities.</p>
{answer('Reveal the complete operating-cash reconciliation', f'First adjustments: 11,445 + 11,688 − 2,266 = <strong>{fmt(r["adjustments"])}</strong>. Changes in operating assets and liabilities: −3,788 − 1,356 − 1,046 − 11,731 + 6,020 + 15,552 = <strong>{fmt(r["operating_changes"])}</strong>. Net income 93,736 + 20,867 + 3,651 = <strong>{fmt(r["ocf"])} USD million</strong>, exactly matching reported operating cash flow. The increase over earnings is a reconciliation, not a separate sales receipt.')}
<p>Working-capital timing can reverse. The positive net change does not establish a recurring source of cash. Likewise, the 11,688 share-compensation add-back explains cash-flow presentation; employees still receive an economically valuable claim.</p></section>

<section id="allocation"><h2>Define FCF before describing what it can fund.</h2>
{table(('capex_cash','dividends_cash','repurchases_cash'), 'FY2024 cash uses: PP&E purchases and capital returns')}
<p>For this exercise only, <strong>free cash flow (FCF) = operating cash flow − cash paid to acquire property, plant and equipment (PP&amp;E)</strong>. The source records the capex payment as −9,447. Subtract its positive magnitude once, or add its signed value once. Net investing cash flow is not a substitute for this specific cash-capex input.</p>
{answer('Reveal FCF and the cash allocation residual', f'118,254 − 9,447 = <strong>{fmt(r["fcf"])} USD million</strong> under the stated FCF definition. Cash dividends and equivalents plus repurchases are 15,234 + 94,949 = <strong>{fmt(r["capital_returns"])}</strong>. FCF less those uses is <strong>{fmt(r["residual"])}</strong>. A negative result here says those two cash uses exceeded this defined annual FCF amount; it is not the ending cash balance or a finding of insolvency.')}
{answer('Reveal the two explicitly labeled payout ratios', f'Cash dividends and equivalents ÷ defined FCF = 15,234 ÷ 108,807 × 100 = <strong>{fmt(r["dividend_payout"],4)}%</strong>. Cash dividends plus repurchases ÷ defined FCF = 110,183 ÷ 108,807 × 100 = <strong>{fmt(r["return_payout"],4)}%</strong>. These annual arithmetic comparisons have different numerators. Neither establishes future dividend capacity or an appropriate buyback price.')}
{table(('dividends_declared','dividends_declared_per_share','repurchases_equity'), 'Different measurement bases in shareholders’ equity; do not substitute these for cash payments')}
<p>The equity statement records declared dividends and equivalents of 15,218, versus 15,234 paid in cash: a <strong>{fmt(r['dividend_difference'])}</strong> difference. It records a common-stock repurchase equity reduction of 95,846, versus 94,949 in cash: a <strong>{fmt(r['equity_repurchase_difference'])}</strong> difference. Recognition and settlement bases matter. These two tables alone do not explain every component of those differences; do not invent a timing or tax bridge from their subtraction.</p>
<p>The declared $0.98 per share or restricted stock unit is another measurement. Multiplying it by year-end shares will not reconstruct actual aggregate cash payments: entitlement, share counts and timing vary. Use the disclosed aggregate cash row for a cash allocation exercise.</p></section>

<section id="cash-balance"><h2>Close the cash statement with investing and financing.</h2>
{table(INVESTING+('investing_cash',), 'Complete FY2024 investing section; USD millions')}
{answer('Reveal investing cash flow', '−48,656 + 51,211 + 11,135 − 9,447 − 1,308 = <strong>2,935 USD million</strong>. Security maturities and sales generate cash here, but they are not operating cash flow. Adding 2,935 to FCF would double-count the PP&E payment already deducted in FCF.')}
{table(FINANCING+('financing_cash',), 'Complete FY2024 financing section; USD millions')}
{answer('Reveal financing cash flow', '−5,441 − 15,234 − 94,949 + 0 − 9,958 + 3,960 − 361 = <strong>−121,983 USD million</strong>. The source dash for term-debt issuance is represented as zero. Debt repayments, commercial-paper proceeds and equity-award settlement taxes all belong in the cash statement even though a dividend-and-buyback subtotal excludes them.')}
{table(('cash_beginning','cash_change','cash_ending'), 'Cash balances include cash equivalents and restricted cash; beginning is September 30, 2023')}
{answer('Reveal the full cash reconciliation', f'30,737 + 118,254 + 2,935 − 121,983 = <strong>{fmt(r["ending"])} USD million</strong>. The change is <strong>{fmt(r["change"])}</strong>. This agrees with both reported cash rows. No separate exchange-rate-effects row appears in this source statement; the three activity totals already explain the reported change.')}
{answer('Connect the allocation residual to the cash change without double-counting', f'Start with the FCF allocation residual of −1,376. Investing cash excluding the PP&amp;E payment is 2,935 − (−9,447) = <strong>{fmt(r["other_investing"])}</strong>. Financing cash excluding dividends and repurchases is −121,983 + 15,234 + 94,949 = <strong>{fmt(r["other_financing"])}</strong>. Thus −1,376 + 12,382 − 11,800 = <strong>−794</strong>. This explains why the simplified residual and total cash change differ.')}
<p>This annual reconciliation does not trace a particular borrowing to a particular repurchase. Cash is pooled, and the order of transactions within the year is absent from these annual totals. Describe the total financing mix without claiming a direct use-of-proceeds relationship that the source has not established.</p></section>

<section id="shares"><h2>Repurchase cash is not the share-count result.</h2>
{table(SHARES, 'Note 10 common-share reconciliation; thousands of shares, not USD millions')}
{answer('Reveal the common-share change', f'15,550,061 − 499,372 + 66,097 = <strong>15,116,786 thousand shares</strong>. Outstanding shares declined by <strong>{fmt(-r["share_change"])}</strong> thousand, less than the 499,372 thousand repurchased because net issuance adds shares. Do not report the cash repurchase amount as a count of shares or as a percentage reduction in the share count.')}
<p>The 11,688 share-compensation expense was added back in the operating-cash bridge. That does not make compensation economically free: the employee receives value, and shares issued can offset part of the repurchase effect. The cash statement separately includes 5,441 of equity-award settlement taxes. Adding a noncash expense back and then examining dilution and settlement cash are different analytical steps; neither licenses blindly deducting the same cash payment twice.</p>
<p>The Note 10 table measures beginning and ending shares outstanding. It is not the weighted-average diluted share denominator used for earnings per share. Dividing profit by ending shares does not reproduce reported diluted EPS.</p></section>

<section id="limits"><h2>Positive FCF is not cash available for distribution.</h2>
<p>This lab’s FCF is a defined non-GAAP calculation, not a separately reported GAAP subtotal, a company forecast or a universal issuer definition. Its PP&amp;E deduction does not identify maintenance versus growth spending. It also excludes other investing and financing transactions, future commitments and changes in the cash required to run the business. Compare definitions before comparing companies.</p>
{table(('restricted_cash',), 'Note 4 restriction on part of the reported cash balance; issuer-rounded USD billions')}
<p>Note 4 identifies $2.6 billion of cash and equivalents held in escrow and restricted from general use at year-end. The ending cash total therefore cannot be labeled entirely distributable. The rounded restriction disclosure is context, not a precise calculation of unrestricted cash to the nearest million. Future operating needs, other restrictions and obligations still require their own review.</p>
<p>The exercise deliberately keeps a single historical fiscal year. It cannot tell whether a cash-conversion pattern persists, whether replacement capex is sufficient, whether the share repurchases created value, or what a later dividend will be. Reconstructing a published result checks the arithmetic and classification; it does not independently verify the issuer’s underlying estimates.</p></section>

<section id="quiz"><h2>Check the conclusion before using the number.</h2>
{answer('1. Why not use net income plus depreciation as operating cash flow?', 'That shortcut omits share compensation, the other reconciliation adjustment and all six operating-asset and liability changes. The omitted items have different signs. Use the complete bridge instead of treating one add-back as the entire reconciliation.')}
{answer('2. Does the −1,376 allocation residual prove a dividend shortfall?', 'No. It combines dividends and discretionary repurchases under the stated FCF definition. Dividends alone are a different numerator, and the residual also omits other investing and financing cash flows. It cannot establish a future payment decision or liquidity failure.')}
{answer('3. Can I subtract dividends, buybacks and net financing from FCF?', 'That double-counts dividends and buybacks because net financing already includes both. Reconcile with full operating, investing and financing totals, or explicitly remove already-counted items before adding the remaining categories.')}
{answer('4. Does a zero FX worksheet input mean the company has no currency exposure?', 'No. This source presents no separate exchange-rate-effects line in its cash statement. Zero is a worksheet convention to reproduce this particular statement, whose reported categories already tie. It is not evidence of zero foreign-currency business exposure.')}
{answer('5. Rewrite the opening claim in a supportable way.', 'Apple’s FY2024 statement reports 118,254 of operating cash flow. Deducting 9,447 of PP&E cash purchases gives 108,807 under this lab’s FCF definition. Cash dividends and repurchases total 110,183; the resulting −1,376 residual is one subtotal within a complete cash statement whose cash change is −794. Availability for future distributions remains a separate question. All amounts are USD millions.')}
</section>

<section id="next"><h2>Reproduce the exact historical inputs.</h2>
<p>Open the <a href="/cash-flow-workbench.html?example=apple-2024">operating-company cash-flow workbench with the Apple FY2024 example</a>. Use period <strong>2023-10-01 to 2024-09-28</strong>, currency <strong>USD</strong> and scale <strong>millions</strong>. The same values below omit grouping commas so they can be copied directly. In the cash-use fields, enter positive magnitudes; signed reconciliation fields retain their source signs.</p>
{copy_table(lab,r)}
<p>The 20,867 adjustment is the sum of 11,445 + 11,688 − 2,266, including the issuer’s unitemized Other adjustment. The 3,651 input includes current and non-current operating assets and liabilities. In the separate cash-balance reconciliation, enter <strong>0</strong> for the additional FX/cash adjustment only because no separate line is needed to reproduce this filing. That zero is a worksheet convention, not a transcribed fact and not a claim of no currency effects.</p>
<p>Expected checks: operating cash flow <strong>118254</strong>; defined FCF <strong>108807</strong>; cash allocation residual <strong>-1376</strong>; cash change <strong>-794</strong>; calculated ending cash <strong>29943</strong>; unexplained difference <strong>0</strong>. Keep net investing and financing totals in the cash-balance section only. Save the source and remaining questions in the <a href="/dividend-research-worksheet.html">research worksheet</a>.</p></section>
'''
    sources = ''.join(f'<li>{source_link(source,source["title"])} — filed {E(source["published"])}. {E(source["locator"])}. Accession {E(source["accession"])}.</li>' for source in data['sources'].values())
    body += f'''<section id="sources"><h2>Primary sources and a reproducible record.</h2><ul class="source-list">{sources}</ul>
<p>This lab records <strong>{len(lab['facts'])} sourced facts</strong>, one underlying 10-K and its SEC filing-details page: <strong>{len(data['sources'])} primary-source URLs</strong>, not two independent financial reports. Every input’s expandable record shows its location, basis and dates. The <a href="/content/operating-company-lab.json">structured source ledger</a> preserves exact decimal strings, currency, unit, period, measurement date, source availability and check date.</p>
<p>“As of” means the measurement date; “available from” means the cited document’s filing date, not a claim about the earliest public appearance of a number; “checked on” means the inspection date for this exercise. Beginning balances are measured on September 30, 2023. Flow values cover the following fiscal year. No market-data connection or automatic financial update is used.</p>
<p>Calculations use decimal arithmetic without intermediate display rounding. Ratios round half up to four decimal places. The exact published inputs, not that display precision, define the exercise. <a href="/editorial-policy.html">Editorial approach</a> · <a href="/filing-labs.html">All filing labs</a>.</p></section></article></div>'''
    return shell(root,lab['slug']+'.html',lab['title'],lab['description'],body,'Article',article=lab)


def outputs(root):
    root = Path(root)
    data = load(root)
    return {root / (data['lab']['slug'] + '.html'): lab_page(root,data)}


def workbench_example(root):
    """Provide the verified teaching dataset to the optional interactive workbench."""
    lab = load(root)['lab']
    r = calculate(lab)
    f = lab['facts']
    return dict(id='apple-2024', label='Apple FY2024 historical filing',
                sourceLabel='Apple FY2024 10-K, p.33; fiscal period 2023-10-01 to 2024-09-28; '
                'filed 2024-11-01, checked 2026-10-18. Noncash/other includes the issuer Other adjustment. '
                'FX input 0 is a worksheet convention: no separate FX row is presented, and reported activity totals already tie. '
                'Historical exercise, not current data.',
                values=dict(scenarioLabel='Apple FY2024 historical exercise', fiscalYear='2024',
                            cashDefinition='Cash, cash equivalents, and restricted cash and cash equivalents',
                            netIncome=f['net_income']['value'], noncash=str(r['adjustments']),
                            workingCapital=str(r['operating_changes']), reportedOCF=f['operating_cash']['value'],
                            capex=str(-amount(lab,'capex_cash')), dividends=str(-amount(lab,'dividends_cash')),
                            buybacks=str(-amount(lab,'repurchases_cash')), beginningCash=f['cash_beginning']['value'],
                            netInvesting=str(r['investing']), netFinancing=str(r['financing']), fx='0',
                            endingCash=f['cash_ending']['value']))
