"""A period-locked, source-reconciled Equinix exercise. No network or client code."""
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import re

from education import E, shell, section_head

SLUG = 'filing-lab-equinix-2025'
SOURCE = 'https://www.sec.gov/Archives/edgar/data/1101239/000110123926000032/eqix-20251231.htm'
FFO_KEYS = ('net_income', 'nci', 'common_income', 'real_estate_depreciation',
            'real_estate_disposition', 'ffo_jv', 'ffo')
AFFO_KEYS = ('installation', 'rent', 'contract_cost', 'financing_amortization',
             'share_compensation', 'share_charity', 'non_real_estate_depreciation',
             'asset_disposition', 'amortization', 'accretion', 'recurring_capex',
             'debt_extinguishment', 'restructuring', 'transaction_costs', 'impairment',
             'tax', 'affo_jv')


def calculate(data):
    f = {row['key']: Decimal(row['value']) for row in data['ffoRows']}
    adjustments = [Decimal(row['value']) for row in data['adjustments']]
    if f['net_income'] + f['nci'] != f['common_income']:
        raise ValueError('Equinix common-stockholder income does not reconcile')
    if sum(f[k] for k in ('common_income', 'real_estate_depreciation',
                         'real_estate_disposition', 'ffo_jv')) != f['ffo']:
        raise ValueError('Equinix FFO does not reconcile')
    net = sum(adjustments)
    if f['ffo'] + net != Decimal(data['affo']):
        raise ValueError('Equinix AFFO does not reconcile')
    return dict(ffo=f['ffo'], positive=sum(n for n in adjustments if n > 0),
                negative=sum(n for n in adjustments if n < 0), net=net,
                affo=Decimal(data['affo']))


def load(root):
    data = json.loads((Path(root)/'content/equinix-2025-affo.json').read_text(encoding='utf-8'))
    if (data['slug'], data['periodStart'], data['periodEnd'], data['unit']) != (
            SLUG, '2025-01-01', '2025-12-31', 'USD million'):
        raise ValueError('Equinix exercise requires its original period and units')
    if data['source']['url'] != SOURCE or data['source']['filed'] != '2026-02-11':
        raise ValueError('Equinix source provenance changed')
    if not (date.fromisoformat(data['source']['filed']) <= date.fromisoformat(data['checkedOn'])
            <= date.fromisoformat(data['updated'])):
        raise ValueError('Equinix source dates are inconsistent')
    if date.fromisoformat(data['published']) > date.fromisoformat(data['updated']):
        raise ValueError('Equinix update precedes publication')
    for group, keys in (('ffoRows', FFO_KEYS), ('adjustments', AFFO_KEYS)):
        if tuple(row['key'] for row in data[group]) != keys:
            raise ValueError('Equinix source rows missing, duplicated or reordered')
        for row in data[group]:
            if not isinstance(row['value'], str) or not re.fullmatch(r'-?\d+(?:\.\d+)?', row['value']):
                raise ValueError('Equinix values require finite decimal strings')
            if any(row[field] != data[field] for field in ('unit', 'periodStart', 'periodEnd')):
                raise ValueError('Equinix row period or unit mismatch')
            if row['sourceURL'] != SOURCE or not row['locator'] or not row['provenance']:
                raise ValueError('Equinix row provenance mismatch')
    if not isinstance(data['affo'], str) or not re.fullmatch(r'\d+(?:\.\d+)?', data['affo']):
        raise ValueError('Equinix AFFO requires a finite decimal string')
    endpoint = data['affoFact']
    if (endpoint['value'] != data['affo'] or endpoint['sourceURL'] != SOURCE
            or not endpoint['locator'] or not endpoint['provenance']
            or any(endpoint[field] != data[field] for field in ('unit', 'periodStart', 'periodEnd'))):
        raise ValueError('Equinix AFFO endpoint provenance mismatch')
    result = calculate(data)
    # Narrative is deliberately period-locked. Source changes need editorial review too.
    if result != dict(ffo=2668, positive=1455, negative=-362, net=1093, affo=3761):
        raise ValueError('Equinix narrative and source calculation no longer agree')
    return data


def table(rows, caption, signed=False):
    body = ''.join(f'<tr><th scope="row">{E(row["label"])}</th>'
                   f'<td>{format(Decimal(row["value"]), "+,.0f" if signed and not row.get("endpoint") else ",.0f")}</td></tr>'
                   for row in rows)
    return (f'<div class="table-scroll" tabindex="0" role="region" aria-label="{E(caption)}">'
            f'<table><caption>{E(caption)}</caption><thead><tr><th scope="col">Reported row</th>'
            '<th scope="col">USD millions</th></tr></thead><tbody>'+body+'</tbody></table></div>')


def card(root):
    data = load(root)
    return (f'<article class="lesson-card"><span class="kicker">REIT / historical FY2025</span>'
            f'<h3><a href="/{SLUG}.html">{E(data["title"])}</a></h3><p>{E(data["description"])}</p>'
            f'<a class="text-link" href="/{SLUG}.html">Rebuild all 17 adjustments →</a></article>')


def outputs(root):
    root = Path(root)
    data = load(root)
    content = (root/'templates/filing-labs/equinix-2025.html').read_text(encoding='utf-8')
    rows = [{**data['ffoRows'][-1], 'endpoint': True},
            *data['adjustments'], {**data['affoFact'], 'endpoint': True}]
    replacements = dict(source_url=E(data['source']['url']), metadata_url=E(data['source']['metadataURL']),
                        nareit_url=E(data['definitionSource']['url']),
                        ffo_table=table(data['ffoRows'], 'Equinix FY2025: GAAP net income to FFO; USD millions'),
                        affo_table=table(rows, 'Equinix FY2025: FFO, 17 signed adjustments and AFFO; USD millions', True))
    for key, value in replacements.items():
        content = content.replace('{{'+key+'}}', value)
    if '{{' in content:
        raise ValueError('Unresolved Equinix lesson template variable')
    from build_site import display_date
    body = '<nav class="wrap breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/filing-labs.html">Filing labs</a><span>/</span><span aria-current="page">Equinix 2025</span></nav>'
    body += section_head('Historical filing lab / REIT', data['title'], data['description'])
    body += f'<div class="wrap article-meta"><a href="/editorial-policy.html" rel="author">DFB Education</a> · Published <time datetime="{data["published"]}">{display_date(data["published"])}</time> · Sources checked <time datetime="{data["checkedOn"]}">{display_date(data["checkedOn"])}</time></div>'
    body += '<section class="wrap education-section"><div class="worked-example"><span class="kicker">Period lock: FY2025</span><h2>A historical reconciliation, not a current rating.</h2><p>Reporting period: January 1–December 31, 2025. All table amounts: USD millions. FFO and AFFO: attributable to common stockholders. The cited 10-K was filed February 11, 2026.</p></div></section>'
    toc = [('assignment','Your assignment'),('starting-point','Net income to FFO'),
           ('reconciliation','The 17 adjustments'),('interpretation','Questions behind the rows'),
           ('limits','Limits'),('practice','Check your reasoning'),('sources','Sources and source ledger')]
    body += '<div class="wrap reading-layout"><nav class="article-toc" aria-label="On this page"><span class="kicker">In this lab</span><ol>'
    body += ''.join(f'<li><a href="#{key}">{label}</a></li>' for key, label in toc)
    body += '</ol></nav><article class="lesson-body">'+content+'</article></div>'
    return {root/(SLUG+'.html'):shell(root,SLUG+'.html',data['title'],data['description'],body,'Article',article=data)}
