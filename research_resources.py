"""Source-backed practical guides outside the numbered REIT/BDC curricula."""
from datetime import date
from education import E, shell, section_head

RESOURCES = [
    dict(slug='reit-vs-bdc', title='REIT vs BDC: dividends, cash flow and risks',
         description='Compare US equity REITs and BDCs: AFFO vs NII, property and credit risks, NAV, and a worked example of two identical dividend yields.',
         published='2026-10-18', updated='2026-10-18'),
    dict(slug='dividend-dates', title='Ex-dividend date vs record date vs payment date',
         description='Understand US dividend dates under T+1, ordinary cash-dividend entitlement, special-distribution exceptions and why dividend capture is not free income.',
         published='2026-10-18', updated='2026-10-18'),
    dict(slug='dividend-research-worksheet', title='Dividend research worksheet for REITs and BDCs',
         description='Build a source-linked dividend research note: locate filing inputs, reconcile AFFO or NII, record risks, then download or print your worksheet.',
         published='2026-10-18', updated='2026-10-18'),
]


def resource_cards(exclude=None):
    cards=''.join(f'<article class="lesson-card"><span class="kicker">Practical guide</span><h3><a href="/{r["slug"]}.html">{E(r["title"])}</a></h3><p>{E(r["description"])}</p><a class="text-link" href="/{r["slug"]}.html">Open the guide ↗</a></article>' for r in RESOURCES if r['slug']!=exclude)
    return '<section class="wrap education-section resource-links"><div class="section-heading"><div><span class="kicker">From learning to a research note</span><h2>Answer the next practical question.</h2></div></div><div class="lesson-grid">'+cards+'</div></section>'


def outputs(root):
    from build_site import display_date
    result={}
    for r in RESOURCES:
        if date.fromisoformat(r['updated']) < date.fromisoformat(r['published']):
            raise ValueError('Resource revision precedes publication')
        content=(root/'templates'/'resources'/(r['slug']+'.html')).read_text(encoding='utf-8')
        body='<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><span aria-current="page">'+E(r['title'])+'</span></div>'
        body+=section_head('Practical dividend research',E(r['title']),r['description'])
        body+=f'<div class="wrap article-meta">DFB Education <span>·</span> Updated <time datetime="{r["updated"]}">{display_date(r["updated"])}</time> <span>·</span> <a href="/editorial-policy.html">Sources and editorial approach</a></div>'
        body+='<article class="wrap policy-reading lesson-body resource-article">'+content+'</article>'+resource_cards(r['slug'])
        extra='<link rel="stylesheet" href="/research-resources.css">'
        if r['slug']=='dividend-research-worksheet':
            extra+='<script src="/research-worksheet.js" defer></script>'
        result[root/(r['slug']+'.html')]=shell(root,r['slug']+'.html',r['title'],r['description'],body,'Article',extra=extra,article=r)
    return result
