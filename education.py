"""Static, crawlable DFB education pages. Content is local and version controlled."""
from pathlib import Path
import html
import json
import re
from datetime import date
from urllib.parse import urlsplit

DOMAIN = 'https://dividendforensics.com'
E = lambda value: html.escape(str(value), quote=True)

# id, label, example value, minimum, maximum, step
TOOLS = [
    dict(slug='calculator-dividend-income', kind='income', title='Dividend income calculator',
         description='Estimate annual distributions, after-withholding income and the capital needed for a monthly income target.',
         inputs=[('capital','Investment amount',10000,0,1e12,'any'),('yield','Annual dividend yield (%)',5,0,100,'any'),('tax','Assumed withholding (%)',0,0,100,'any'),('target','Monthly income target',500,0,1e9,'any')],
         formula='Annual gross income = investment × annual yield. After-withholding income = gross income × (1 − withholding rate). Required capital = monthly target × 12 ÷ after-withholding yield.',
         example='At 10,000 invested and a 5% yield, gross annual income is 500. At an assumed 15% withholding rate it is 425 after withholding, or a monthly equivalent of 35.42. A 500 monthly target would require about 141,176.47 under those unchanged assumptions.',
         limits='The monthly figure is an average, not a payment calendar. Withholding is a user assumption, not your final tax rate. Excludes price changes, fees, currency movements and dividend cuts. Zero net yield cannot fund a positive income target.',
         related=['learn-yield-total-return','learn-payout-ratio','learn-dividend-cuts']),
    dict(slug='calculator-reinvestment',kind='reinvestment',title='Dividend reinvestment calculator',
         description='Explore a constant-yield monthly reinvestment scenario and separate contributions from modeled income.',
         inputs=[('capital','Starting balance',10000,0,1e12,'any'),('contribution','End-of-month contribution',200,0,1e9,'any'),('yield','Constant annual yield (%)',5,0,30,'any'),('tax','Assumed withholding (%)',0,0,100,'any'),('years','Years',10,1,50,1)],
         formula='Each month: income = opening balance × annual yield ÷ 12 × (1 − withholding rate). Closing balance = opening balance + income + end-of-month contribution. Repeat for years × 12.',
         example='With a 10,000 starting balance, 6% constant annual yield, no withholding and no contributions, one modeled year ends at 10,616.78. Monthly compounding makes the result different from simply adding 600 once at year-end.',
         limits='This is a constant-yield balance model, not a share-price or dividend-growth forecast. It assumes monthly reinvestment, fractional purchases, unchanged principal value apart from income and contributions, and no fees. Actual payment schedules, prices and taxes differ.',
         related=['learn-reinvestment','learn-yield-total-return','learn-dividend-cuts']),
    dict(slug='calculator-payout-ratio',kind='payout',title='AFFO payout & stress calculator',
         description='Compare common dividends with AFFO on a matching basis, then model a decline in the chosen measure.',
         inputs=[('affo','Annual AFFO per common share',4,-1e9,1e9,'any'),('dividend','Annual dividend per common share',3,0,1e9,'any'),('decline','AFFO decline scenario (%)',15,0,100,'any')],
         formula='Payout = dividend ÷ AFFO. Coverage = AFFO ÷ dividend. Stressed AFFO = AFFO × (1 − decline). Cushion = AFFO − dividend. Use consistent annual periods and common-share bases.',
         example='With AFFO of 4.00 and a dividend of 3.00, payout is 75% and coverage is 1.33×. A 15% AFFO decline reduces AFFO to 3.40 and raises payout to 88.24%. The remaining cushion is 0.40 per share.',
         limits='AFFO has no single standardized definition. Use the issuer reconciliation and account for excluded recurring cash costs. Coverage is not a safety rating. Payout and coverage are not meaningful when AFFO is zero or negative and are shown as Not defined. Coverage is also undefined when the dividend is zero. Negative cash cushions remain visible. For negative AFFO, the decline input scales the signed amount; it is not a worsening-loss model.',
         related=['learn-affo','learn-payout-ratio','learn-dividend-cuts']),
    dict(slug='calculator-ffo-affo',kind='bridge',title='FFO to AFFO learning calculator',
         description='Build a simplified non-GAAP reconciliation and see how recurring capex and straight-line rent change a modeled result.',
         inputs=[('net','Net income attributable to common',50,-1e12,1e12,'any'),('depreciation','Real-estate depreciation & amortization',40,0,1e12,'any'),('gains','Net qualifying property-sale gains (losses negative)',10,-1e12,1e12,'any'),('ffoOther','Other applicable FFO adjustments (+/−)',0,-1e12,1e12,'any'),('capex','Recurring capital expenditure deduction',8,0,1e12,'any'),('rent','Noncash straight-line rent deduction',2,-1e12,1e12,'any'),('affoOther','Other issuer-defined AFFO adjustments (+/−)',0,-1e12,1e12,'any')],
         formula='Simplified FFO = common net income + real-estate D&A − qualifying sale gains + other FFO adjustments. Modeled AFFO = simplified FFO − recurring capex − noncash straight-line rent + other issuer adjustments.',
         example='50 of common net income + 40 of real-estate D&A − 10 of qualifying sale gains = 80 of simplified FFO. Deducting 8 of recurring capex and 2 of noncash rent gives 70 of modeled AFFO, before any other adjustments.',
         limits='Use one currency and scale throughout. This is a teaching bridge, not a complete implementation of the Nareit definition. Qualifying impairments, joint ventures and attribution adjustments may be needed. AFFO is issuer-defined; never apply these illustrative deductions without checking the company reconciliation.',
         related=['learn-ffo','learn-affo','learn-read-filings']),
    dict(slug='calculator-nav',kind='nav',title='Cap-rate & NAV sensitivity calculator',
         description='Translate a property NOI assumption into a simplified equity value and compare cap-rate scenarios.',
         inputs=[('noi','Annual stabilized NOI (millions)',100,0,1e9,'any'),('cap','Capitalization rate (%)',6,0.01,100,'any'),('debt','Debt & other senior claims (millions)',600,0,1e12,'any'),('cash','Cash & other net assets (millions)',50,0,1e12,'any'),('shares','Common shares (millions)',100,0.000001,1e9,'any')],
         formula='Property value = stabilized annual NOI ÷ cap rate. Simplified common equity NAV = property value + cash and other net assets − debt and other senior claims. NAV per share = equity NAV ÷ common shares.',
         example='100 million NOI at a 6% cap rate implies 1,666.67 million of property value. Add 50 million of cash and subtract 600 million of senior claims: equity NAV is 1,116.67 million, or 11.17 per share with 100 million shares.',
         limits='This is not an appraisal or price target. Corporate costs, taxes, transaction costs, development, joint ventures, preferred claims and other assets or liabilities must be reflected appropriately. A negative result is displayed as a scenario result, not floored to zero. One cap rate may be unsuitable for a mixed portfolio.',
         related=['learn-nav','learn-cap-rate','learn-noi']),
    dict(slug='calculator-refinancing',kind='refinancing',title='Refinancing cost calculator',
         description='Estimate the annual interest and per-share effect of repricing one debt maturity.',
         inputs=[('principal','Debt being refinanced (millions)',200,0,1e12,'any'),('old','Old annual interest rate (%)',3,0,100,'any'),('new','New annual interest rate (%)',5,0,100,'any'),('shares','Common shares (millions)',100,0.000001,1e9,'any')],
         formula='Annual interest change = refinanced principal × (new rate − old rate). Per-share expense change = annual interest change ÷ common shares. Positive means more interest expense; negative means savings.',
         example='Refinancing 200 million from 3% to 5% adds 4 million in annual interest. Across 100 million common shares, the isolated annual interest increase is 0.04 per share.',
         limits='Assumes unchanged principal for a full year. Excludes issuance fees, amortization, hedges, taxes, capitalized interest, partial-year timing and changes in share count. The result is an expense sensitivity, not an FFO or AFFO forecast.',
         related=['learn-debt-maturities','learn-interest-rates','learn-interest-coverage']),
    dict(slug='calculator-total-return',kind='return',title='Dividend total return calculator',
         description='Combine price change with cash distributions to see a simple holding-period return.',
         inputs=[('start','Purchase price per share',100,0.000001,1e9,'any'),('end','Ending price per share',90,0,1e9,'any'),('dividends','Cash dividends received per share',6,0,1e9,'any'),('buyFees','Purchase fees per share',0,0,1e9,'any'),('sellFees','Sale / other fees per share',0,0,1e9,'any')],
         formula='Initial cost = purchase price + purchase fees. Holding-period return = (ending price − purchase price + cash distributions − purchase fees − sale/other fees) ÷ initial cost. Every return component uses the same initial-cost denominator.',
         example='A share bought at 100, ending at 90, with 6 in cash distributions and no fees has a −4% holding-period return. The 6% cash distribution component did not offset the 10% price decline.',
         limits='Not annualized. Assumes one purchase and no reinvestment or additional cash flows. Enter all figures in one currency. Excludes tax unless you enter net distributions; it is not a money-weighted or time-weighted portfolio return.',
         related=['learn-yield-total-return','learn-reinvestment','learn-dividend-cuts'])
]

def load_articles(root):
    articles=[]
    for name in ('foundations','sectors','metrics','expert'):
        articles.extend(json.loads((root/'content'/f'{name}.json').read_text(encoding='utf-8')))
    from curriculum import level_for
    for article in articles: article['level']=level_for(article['slug'])['name']
    slugs=[a['slug'] for a in articles]
    if len(slugs)!=len(set(slugs)): raise ValueError('Duplicate education slug')
    for a in articles:
        if not re.fullmatch(r'learn-[a-z0-9-]+',a['slug']): raise ValueError('Invalid article slug')
        published=date.fromisoformat(a['published'])
        updated=date.fromisoformat(a['updated'])
        if updated<published: raise ValueError(f'Update precedes publication: {a["slug"]}')
        if a.get('calculator') not in {None,*(t['slug'] for t in TOOLS)}:
            raise ValueError(f'Unknown calculator: {a["slug"]}')
        for link in a['related']:
            if link not in slugs: raise ValueError(f'Unknown related article: {link}')
        for s in a['sources']:
            if urlsplit(s['url']).scheme!='https': raise ValueError('Sources require HTTPS')
    return articles

def breadcrumb_items(name,title):
    trail=[('Home',DOMAIN+'/')]
    if name.startswith('calculator-'):
        trail.append(('Calculators',DOMAIN+'/tools.html'))
    elif name.startswith(('learn-','course-')):
        trail.append(('Learn',DOMAIN+'/learn.html'))
    if name!='index.html':trail.append((title,DOMAIN+'/'+name))
    return [{'@type':'ListItem','position':i,'name':label,'item':url} for i,(label,url) in enumerate(trail,1)]

def shell(root,name,title,description,body,kind='WebPage',extra='',index=True,article=None):
    from build_site import header,footer
    url=DOMAIN+('/' if name=='index.html' else '/'+name)
    schema={'@context':'https://schema.org','@type':kind,'name':title,'description':description,'url':url,'inLanguage':'en','isAccessibleForFree':True,'publisher':{'@type':'Organization','name':'Dividend Forensics Bureau','url':DOMAIN}}
    if kind=='Article':
        schema.update(headline=title,datePublished=article['published'],dateModified=article['updated'],author={'@type':'Organization','name':'DFB Education','url':DOMAIN+'/editorial-policy.html'},mainEntityOfPage=url)
    breadcrumb={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':breadcrumb_items(name,title)}
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · DFB</title><meta name="description" content="{E(description)}"><meta name="dfb-design" content="education-20261018">
<link rel="canonical" href="{url}"><meta name="robots" content="{'index,follow' if index else 'noindex,follow'}">
<meta property="og:type" content="{'article' if kind=='Article' else 'website'}"><meta property="og:site_name" content="Dividend Forensics Bureau"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{DOMAIN}/img/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#f3f0e8"><link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/dfb.css"><link rel="stylesheet" href="/newsroom.css"><link rel="stylesheet" href="/education.css">
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')}</script>
<script type="application/ld+json">{json.dumps(breadcrumb,ensure_ascii=False).replace('<','\\u003c')}</script>
<script src="/site.js" defer></script><script src="/education.js" defer></script>{extra}</head><body class="education-page">
<!-- SITE:HEADER -->
{header(name,root)}
<!-- /SITE:HEADER -->
<main id="main" tabindex="-1">{body}</main>
<!-- SITE:FOOTER -->
{footer(root,name)}
<!-- /SITE:FOOTER -->
</body></html>'''

def cards(articles):
    return ''.join(f'<article class="lesson-card" data-lesson data-category="{E(a["category"])}" data-level="{E(a["level"])}" data-search="{E((a["title"]+" "+a["description"]).lower())}"><span class="kicker">{E(a["category"])} / {E(a["level"])}</span><h3><a href="/{a["slug"]}.html">{E(a["title"])}</a></h3><p>{E(a["description"])}</p><a class="text-link" href="/{a["slug"]}.html">Read the guide <span aria-hidden="true">↗</span></a></article>' for a in articles)

def section_head(kicker,title,description=''):
    return f'<header class="education-heading wrap"><span class="kicker">{E(kicker)}</span><h1>{title}</h1><p class="education-lede">{E(description)}</p></header>'

def article_page(root,a,lookup):
    from curriculum import level_for,figure,image_for
    level=level_for(a['slug'])
    toc=''.join(f'<li><a href="#section-{i}">{E(s["heading"])}</a></li>' for i,s in enumerate(a['sections'],1))
    content=''.join(f'<section id="section-{i}"><h2>{E(s["heading"])}</h2><p>{E(s["text"])}</p></section>' for i,s in enumerate(a['sections'],1))
    checklist=''.join(f'<li>{E(c)}</li>' for c in a['checklist'])
    sources=''.join(f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener">{E(s["title"])} ↗</a></li>' for s in a['sources'])
    related=cards([lookup[s] for s in a['related']])
    matching=next((t for t in TOOLS if t['slug']==a.get('calculator')),None)
    calculator_link=(f'<a class="text-link" href="/{matching["slug"]}.html">Try a related calculator ↗</a>' if matching else '')
    updated=date.fromisoformat(a['updated'])
    display_updated=f'{updated.day} {("January","February","March","April","May","June","July","August","September","October","November","December")[updated.month-1]} {updated.year}'
    words=len(' '.join(s['text'] for s in a['sections']).split())+len(a['example']['text'].split())
    exercise=''
    if a.get('exercise'):
        exercise=f'<section><h2>Test your reasoning</h2><p>{E(a["exercise"]["question"])}</p><details class="workshop-answer"><summary>Reveal the worked answer</summary><p>{E(a["exercise"]["answer"])}</p></details></section>'
    body=f'''<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/learn.html">Learn</a><span>/</span><span aria-current="page">{E(a['title'])}</span></div>
{section_head(a['category'],E(a['title']),a['description'])}
<div class="wrap article-meta">DFB Education <span>·</span> <a href="/course-{level['key']}.html">{E(a['level'])} learning path</a> <span>·</span> {max(3,round(words/180))} min read <span>·</span> Updated <time datetime="{a['updated']}">{display_updated}</time> <span>·</span> <a href="/editorial-policy.html">Editorial approach</a></div>
<div class="wrap article-visual">{figure(image_for(a),root)}</div>
<div class="wrap reading-layout"><aside class="article-toc"><span class="kicker">In this guide</span><ol>{toc}<li><a href="#worked-example">Worked example</a></li><li><a href="#source-notes">Sources &amp; next steps</a></li></ol>{calculator_link}</aside>
<article class="lesson-body">{content}<section class="worked-example" id="worked-example"><span class="kicker">Work through the numbers</span><h2>{E(a['example']['heading'])}</h2><p>{E(a['example']['text'])}</p></section>{exercise}<section class="pitfall"><h2>A common mistake</h2><p>{E(a['pitfall'])}</p></section><section><h2>What to check in the disclosures</h2><ul>{checklist}</ul></section><section id="source-notes"><h2>Sources &amp; scope</h2><p>This guide focuses on US REITs. Examples are hypothetical unless explicitly attributed. Definitions and issuer disclosures can change; use the current source and the issuer's own reconciliation.</p><ul class="source-list">{sources}</ul><p class="small-note">Educational material, not a recommendation or personalized investment advice. <a href="/editorial-policy.html">How these guides are prepared</a> · <a href="mailto:dividendforensics@gmail.com?subject=Education%20correction%3A%20{a['slug']}">Report a correction</a></p></section></article></div>
<section class="wrap education-section"><div class="section-heading"><div><span class="kicker">Continue learning</span><h2>Connect the next piece.</h2></div><a class="text-link" href="/learn.html">All guides →</a></div><div class="lesson-grid">{related}</div></section>'''
    return shell(root,a['slug']+'.html',a['title'],a['description'],body,'Article',article=a)

def hub(root,articles):
    from curriculum import level_cards,LEVELS
    cats=list(dict.fromkeys(a['category'] for a in articles))
    options=''.join(f'<option value="{E(c)}">{E(c)}</option>' for c in cats)
    paths=[('01','Start with the business','learn-reit-basics','What a REIT owns, how it earns income, and what shareholders actually hold.'),('02','Learn the accounting','learn-ffo','Follow FFO, AFFO and the adjustments between earnings and recurring cash.'),('03','Read the lease','learn-net-lease','Understand tenants, property expenses and the risks inside long contracts.'),('04','Test the dividend','learn-payout-ratio','Put the payout alongside recurring capex, debt and a downside scenario.')]
    pathhtml=''.join(f'<a class="learning-path" href="/{slug}.html"><span>{n}</span><div><h3>{title}</h3><p>{desc}</p></div><b aria-hidden="true">↗</b></a>' for n,title,slug,desc in paths)
    body=section_head('The DFB learning center','Understand the property.<br><em>Then follow the cash.</em>',f'{len(articles)} free guides to REIT businesses, financial measures and dividend analysis. Start from the basics or go straight to the question in your filing.')
    level_options=''.join(f'<option value="{l["name"]}">{l["name"]}</option>' for l in LEVELS)
    body+='<section class="wrap education-section" id="learning-paths"><div class="section-heading"><div><span class="kicker">Four levels / one connected library</span><h2>Choose your depth.</h2></div></div>'+level_cards(articles)+'</section>'
    body+=f'<section class="wrap learning-paths" aria-label="Suggested starting questions">{pathhtml}</section><section class="wrap education-section" id="library"><div class="section-heading"><div><span class="kicker">The complete reading room</span><h2>Find your next question.</h2></div><a class="text-link" href="/glossary.html">Open the glossary ↗</a></div><div class="library-filters" data-library-controls hidden><label>Search guides<input id="lesson-search" type="search" placeholder="Try AFFO, net lease, refinancing…"></label><label>Subject<select id="lesson-category"><option value="all">All subjects</option>{options}</select></label><label>Level<select id="lesson-level"><option value="all">All levels</option>{level_options}</select></label><button id="lesson-reset" type="button" class="btn btn-s">Clear filters</button><p id="lesson-count" aria-live="polite">{len(articles)} guides</p></div><noscript><p>All guides are listed below. Search is an optional enhancement.</p></noscript><p id="lesson-empty" hidden>No guides match. Try a shorter term or clear the filters.</p><div class="lesson-grid">{cards(articles)}</div></section>'
    body+='<section class="wrap education-section" id="property-sectors"><div class="section-heading"><div><span class="kicker">Different assets, different questions</span><h2>Explore the property sectors.</h2></div></div><div class="sector-strip">'+''.join(f'<a href="/{a["slug"]}.html">{E(a["title"].split(":")[0])} ↗</a>' for a in articles if a['category']=='Property sectors')+'</div></section>'
    body+='<section class="wrap education-section"><div class="section-heading"><div><span class="kicker">Beyond the REIT library</span><h2>Keep the wider context.</h2></div></div><div class="sector-strip"><a href="/research.html">Published research ↗</a><a href="/bdc-guide.html">BDC field guide ↗</a><a href="/industrials-guide.html">Industrials field guide ↗</a><a href="/telecom-guide.html">Telecom field guide ↗</a><a href="/methodology.html">DFB methodology ↗</a><a href="/tools.html">Working papers &amp; calculators ↗</a></div></section>'
    return shell(root,'learn.html','REIT learning center: free guides, sectors & financial analysis','Learn what REITs are, explore property sectors and understand FFO, AFFO, net leases, dividends, valuation and refinancing risk.',body,'CollectionPage')

def calculator_page(root,t,lookup):
    fields=''.join(f'<label for="input-{key}">{E(label)}<input id="input-{key}" name="{key}" type="number" value="{value}" min="{minimum}" max="{maximum}" step="{step}" required inputmode="decimal"></label>' for key,label,value,minimum,maximum,step in t['inputs'])
    body=f'<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/tools.html">Calculators</a><span>/</span><span aria-current="page">{E(t["title"])}</span></div>'+section_head('Free tools / transparent assumptions',E(t['title']),t['description'])
    body+=f'''<section class="wrap calculator-layout"><form class="calculator-form" data-calculator="{t['kind']}"><h2>Your assumptions</h2><p class="small-note">Educational scenario, not a forecast. Use one currency throughout. Figures below are illustrative inputs, not market data. Percentage inputs use 5 for 5%, not 0.05.</p><div class="calculator-fields">{fields}</div><div class="btns"><button class="btn btn-p" type="submit">Calculate <span aria-hidden="true">→</span></button><button class="btn btn-s" type="reset">Reset example</button></div><p class="calculator-error" role="alert" hidden></p><p class="small-note">Calculations stay in this browser tab. No inputs are saved or sent to DFB.</p><noscript><p>Enable JavaScript to calculate interactively, or use the formula and worked example below.</p></noscript></form><div class="calculator-output" role="region" aria-label="Calculation results" aria-live="polite"><span class="kicker">Your scenario</span><h2>The result, with context.</h2><div data-result><p>Select Calculate to run the example or enter your own assumptions.</p></div></div></section>
<div class="wrap reading-layout calculator-notes"><aside class="article-toc"><span class="kicker">How to use this tool</span><ol><li><a href="#formula">Formula</a></li><li><a href="#example">Worked example</a></li><li><a href="#limits">What it leaves out</a></li></ol></aside><article class="lesson-body"><section id="formula"><h2>The calculation</h2><p>{E(t['formula'])}</p></section><section id="example" class="worked-example"><span class="kicker">Hypothetical illustration</span><h2>Check the arithmetic.</h2><p>{E(t['example'])}</p></section><section id="limits"><h2>Read the limits before the result.</h2><p>{E(t['limits'])}</p><p>The output is an educational scenario. It is not a forecast, a tax determination or a personalized investment recommendation.</p><p><a href="/editorial-policy.html">Method and corrections</a> · <a href="/sources.html">Primary-source reading room</a></p></section></article></div><section class="wrap education-section"><h2>Understand the inputs.</h2><div class="lesson-grid">{cards([lookup[s] for s in t['related']])}</div></section>'''
    return shell(root,t['slug']+'.html',t['title'],t['description'],body,extra='<script src="/calculators.js" defer></script>')

def tools_page(root):
    from build_site import REPORT_URL
    tiles=''.join(f'<a class="tool-card" href="/{t["slug"]}.html"><span class="kicker">0{i} / Interactive calculator</span><h2>{E(t["title"])}</h2><p>{E(t["description"])}</p><span class="text-link">Open calculator ↗</span></a>' for i,t in enumerate(TOOLS,1))
    body=section_head('The numbers desk','Test an assumption.<br><em>Understand the result.</em>','Free calculators for income, reinvestment, coverage, valuation and debt. Each shows its formula, a worked example and the limits of the model.')
    body+=f'<section class="wrap tool-grid">{tiles}</section><section class="wrap education-section"><div class="worked-example"><span class="kicker">Published REIT working paper / Report 001</span><h2>See the method in a real research record.</h2><p>Read the MAA / W. P. Carey working paper and its REIT Dividend Checklist. The existing free report is delivered through the original checkout; email is required for delivery.</p><div class="btns"><a class="btn btn-p" href="{E(REPORT_URL)}" target="_blank" rel="noopener">Get Report No. 001 — Free ↗</a><a class="text-link" href="/learn-checklist.html">Read the research checklist →</a></div></div></section>'
    return shell(root,'tools.html','Free REIT & dividend calculators','Seven free tools for dividend income, reinvestment, AFFO coverage, FFO, NAV, refinancing and total return. Formulas and limitations included.',body,'CollectionPage')

def editorial(root):
    body=section_head('About this learning library','Evidence first.<br><em>Assumptions in view.</em>','How DFB separates education, published research, advertising and future membership.')
    body+='''<div class="wrap policy-reading lesson-body"><section><h2>Purpose and scope</h2><p>DFB Education explains US REIT businesses and financial measures for readers who want to understand filings. It complements the existing research by Jeong-Mo Goo and links to that research without treating an educational example as an issuer finding. See the <a href="/about.html">author biography</a> and <a href="/methodology.html">research methodology</a>.</p></section><section><h2>How the guides are prepared</h2><p>This education expansion was prepared with AI-assisted research, drafting and implementation, using linked primary sources. Educational articles are labeled DFB Education; that label is not a claim of independent expert review or a professional credential. Existing research records retain their original attribution. Readers can inspect the sources and report issues for correction.</p><p>Sources include regulators, Nareit definitions and issuer filings. Worked examples are original hypothetical illustrations. Company-specific non-GAAP measures must be read with the issuer's reconciliation. A guide's update date records a content revision; it does not mean every underlying company disclosure is current to that date.</p></section><section><h2>Facts, calculations and interpretation</h2><p>A quoted filing figure, a calculated ratio and a judgment about risk are different kinds of statements. Guides explain their assumptions and discuss limitations or competing interpretations. Calculators disclose their formulas, do not fetch market prices, and do not assign investment ratings. No hypothetical figure is presented as current company data.</p></section><section><h2>Educational illustrations and learning levels</h2><p>The property atlas, reconciliation, capital-claims and evidence-desk illustrations were generated with GPT image generation. They are conceptual teaching aids, not photographs, audited financial diagrams or evidence about a real company. The adjacent HTML text and worked examples state the applicable definitions and limitations. Open an illustration to inspect it at full size.</p><p>Beginner, Intermediate, Advanced and Expert describe the depth and prerequisite knowledge of each learning path. Expert workshops include reconciliation and scenario exercises; completing a path or quiz does not confer a credential or establish investing suitability. Quiz answers are processed in the browser and are not saved.</p></section><section><h2>Corrections</h2><p>Send the page URL, the relevant passage and supporting source to <a href="mailto:dividendforensics@gmail.com">dividendforensics@gmail.com</a>. Material corrections should explain what changed and update the affected guide's revision date. This page does not claim that a correction has been independently verified before it has been checked.</p></section><section><h2>Advertising and editorial boundaries</h2><p>DFB intends to support free education with advertising. This release has no AdSense publisher code and does not serve Google ads. If advertising is enabled later, placements will be labeled and kept separate from navigation, calculator controls and editorial conclusions. Advertising will not constitute a recommendation of a security or service. The privacy notice must be updated to reflect any advertising or consent tools actually deployed.</p></section><section><h2>Free access and future membership</h2><p>The education library and calculators are freely accessible without an account. Membership remains in preparation and is not open for enrollment or payment. Future paid offerings, if introduced, will be described separately. There is no public opening date or pricing commitment on this site.</p></section><section><h2>Further information</h2><p><a href="/privacy.html">Privacy</a> · <a href="/disclaimer.html">Financial disclaimer</a> · <a href="/legal.html">Terms</a> · <a href="/research-desk.html">Contact the Research Desk</a></p></section></div>'''
    return shell(root,'editorial-policy.html','Education standards, sources & corrections','How DFB prepares its education library, labels hypothetical examples, handles sources and separates advertising from research.',body)

def sources_page(root,articles):
    sources={s['url']:s['title'] for a in articles for s in a['sources']}
    links=''.join(f'<li><a href="{E(url)}" target="_blank" rel="noopener">{E(title)} ↗</a><small>{E(urlsplit(url).hostname)}</small></li>' for url,title in sorted(sources.items()))
    body=section_head('Primary-source reading room','Go back to<br><em>the evidence.</em>','Regulator education, industry definitions and issuer disclosures used across the learning library.')
    body+='''<div class="wrap policy-reading lesson-body"><section><h2>Choose the source for the question</h2><p>Use Investor.gov for investor education and SEC filings for company disclosures. Nareit is an industry association and a key source for FFO definitions and sector terminology; its industry perspective is not independent investment advice. Issuer releases define company-specific measures but represent the issuer's own reporting. Read them alongside the filed financial statements.</p></section><section><h2>Keep the date and definition attached</h2><p>A historical filing is evidence for its reporting period. It is not a live quote or a current portfolio database. When a definition differs between companies, retain each issuer's wording and reconciliation rather than assuming the labels are comparable.</p></section><section><h2>Source directory</h2><ul class="source-directory">'''+links+'</ul></section><p><a href="/learn-read-filings.html">Read a filing step by step →</a> · <a href="/editorial-policy.html">Editorial approach and corrections</a></p></div>'
    return shell(root,'sources.html','REIT primary sources & filing research directory','A primary-source reading room for REIT definitions, SEC investor education and issuer financial disclosures.',body,'CollectionPage')

GLOSSARY=[
('AFFO','An issuer-defined adjustment to FFO intended to describe recurring performance. Definitions and cash-cost exclusions differ.','learn-affo'),
('Cap rate','Annual property NOI divided by property value or price; a valuation input with sensitivity to both assumptions.','learn-cap-rate'),
('Common equity','The residual ownership claim after liabilities and senior claims. Common distributions are not guaranteed.','learn-reit-basics'),
('Coverage','An income or cash measure divided by the distribution or expense being tested. The measure and period must match.','learn-payout-ratio'),
('Dilution','A reduction in a per-share claim or result as share count grows, depending on what the new capital earns.','learn-dilution'),
('Dividend yield','Annual dividends per share divided by price. Identify whether dividends are trailing, indicated or forecast.','learn-yield-total-return'),
('DRIP','A dividend reinvestment plan that uses distributions to purchase additional shares under stated terms.','learn-reinvestment'),
('Equity REIT','A REIT that generally owns or operates income-producing real estate.','learn-reit-basics'),
('FFO','Funds from operations: a supplemental non-GAAP operating-performance measure with specified real-estate adjustments.','learn-ffo'),
('Interest coverage','A specified earnings measure divided by interest expense; definitions and cash versus accrued bases matter.','learn-interest-coverage'),
('Lease rollover','The expiration, renewal or replacement of leases, bringing opportunities to reset rents and risks of downtime.','learn-lease-expirations'),
('Mortgage REIT','A REIT that generally finances real estate through loans or mortgage-backed securities.','learn-mortgage-reits'),
('NAV','Estimated net asset value after liabilities and other claims; sensitive to asset valuation assumptions.','learn-nav'),
('Net lease','A lease assigning certain property expenses to the tenant as well as rent. The contract determines the allocation.','learn-net-lease'),
('NOI','Net operating income at the property level, before financing and corporate items; issuer definitions need checking.','learn-noi'),
('Payout ratio','Distributions divided by a specified income or cash measure on a consistent basis.','learn-payout-ratio'),
('Recurring capex','Ongoing capital expenditure needed to maintain earning capacity, distinct from some growth investments.','learn-affo'),
('Refinancing','Replacing or renewing financing, potentially changing interest cost, terms, collateral or maturity.','learn-debt-maturities'),
('REIT ETF','An exchange-traded fund holding REIT-related securities according to its stated strategy or index.','learn-reit-etfs'),
('Same-store NOI','NOI growth for a defined comparable property pool, which can differ between issuers and periods.','learn-same-store-noi'),
('Straight-line rent','Accounting recognition that can spread contractual rent over a lease term and differ from cash received.','learn-affo'),
('Tenant concentration','Dependence on a small number of tenants, measured using a disclosed base such as annualized rent.','learn-net-lease'),
('Total return','The combination of income and value change over a period, with reinvestment treatment stated.','learn-yield-total-return'),
('Triple-net lease','A net lease generally allocating property taxes, insurance and maintenance obligations to tenants, subject to contract details.','learn-net-lease'),
('Weighted lease term','An average remaining lease term weighted by a disclosed base; it can conceal near-term concentrations.','learn-lease-expirations')]

def glossary(root):
    terms=''.join(f'<div class="glossary-term" data-term data-search="{E((term+" "+meaning).lower())}" id="term-{i}"><dt>{E(term)}</dt><dd>{E(meaning)} <a href="/{slug}.html">Read the full guide ↗</a></dd></div>' for i,(term,meaning,slug) in enumerate(GLOSSARY))
    body=section_head('The language of REITs','A definition is<br><em>just the beginning.</em>','Quick explanations of 25 common terms, each connected to a full guide with examples and limitations.')
    body+='<section class="wrap policy-reading"><label class="glossary-search" data-glossary-control hidden>Find a term<input id="glossary-search" type="search" placeholder="FFO, cap rate, triple-net…"></label><p id="glossary-count" aria-live="polite">25 terms</p><p id="glossary-empty" hidden>No matching terms. Try an abbreviation or a shorter word.</p><dl class="glossary-list">'+terms+'</dl><p class="small-note">These are concise educational explanations. See each linked guide for primary sources, scope and issuer-specific differences.</p></section>'
    return shell(root,'glossary.html','REIT glossary: FFO, AFFO, NAV, net lease & more','Understand 25 REIT terms with clear definitions and links to detailed, source-backed guides.',body,'CollectionPage')

def education_outputs(root):
    articles=load_articles(root)
    lookup={a['slug']:a for a in articles}
    output={root/(a['slug']+'.html'):article_page(root,a,lookup) for a in articles}
    output.update({root/(t['slug']+'.html'):calculator_page(root,t,lookup) for t in TOOLS})
    output.update({root/'learn.html':hub(root,articles),root/'tools.html':tools_page(root),root/'editorial-policy.html':editorial(root),root/'sources.html':sources_page(root,articles),root/'glossary.html':glossary(root)})
    from curriculum import course_pages
    output.update(course_pages(root,articles,shell,section_head))
    pages={p:p.read_text(encoding='utf-8') for p in root.glob('*.html')}
    pages.update(output)
    urls=[]
    for path,text in pages.items():
        if path.name in ('membership.html','404.html','breakbefore.html'):continue
        if re.search(r'(?i)http-equiv="refresh"|content="[^"]*noindex',text):continue
        match=re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"',text)
        if match and match[1].startswith(DOMAIN+'/'):urls.append(match[1])
    output[root/'sitemap.xml']='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{E(url)}</loc></url>\n' for url in sorted(set(urls)))+'</urlset>\n'
    return output
