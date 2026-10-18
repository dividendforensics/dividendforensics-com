"""Source-backed BDC curriculum, kept distinct from the REIT accounting path."""
import json
import re
from datetime import date
from urllib.parse import urlsplit
from education import E, shell, section_head, cards, all_tools

LEVELS = [
    dict(key='beginner', name='Beginner', title='Understand the lending business.',
         prerequisite='No accounting background required. Start with the difference between a fund share and a loan to a borrower.',
         outcome='Explain what a BDC owns, distinguish trading liquidity from borrower liquidity, and find the relevant filing.'),
    dict(key='intermediate', name='Intermediate', title='Separate earnings, cash and credit.',
         prerequisite='Complete the beginner route or understand BDC structure, market price and basic financial statements.',
         outcome='Rebuild NII coverage, identify noncash PIK, and compare non-accrual exposure on matching denominators.'),
    dict(key='advanced', name='Advanced', title='Stress the capital and fee structure.',
         prerequisite='Be able to explain NII, PIK, fair value and non-accruals without treating one measure as a safety score.',
         outcome='Read advisory incentives, isolate financing and rate sensitivities, and distinguish tax distribution rules from cash funding.'),
    dict(key='expert', name='Expert', title='Make the filing analysis reproducible.',
         prerequisite='Complete the advanced route or bring experience with fund statements, investment schedules and financing notes.',
         outcome='Produce a traceable reconciliation, credit scenario and research memo with explicit unresolved evidence.'),
]

TERMS = [
    ('NII','Net investment income: investment income less the expenses recognized in that measure. It is neither the cash-flow statement nor total investment return.','nii-coverage'),
    ('PIK','Payment-in-kind income can accrue into a loan balance instead of being paid in cash. Recognition and collectibility require issuer-specific review.','pik-income'),
    ('Non-accrual','An accounting status in which ordinary income accrual is suspended under the issuer’s policy. It is not the same as a realized loss or the entire watch list.','non-accrual'),
    ('Fair value','An estimated value under the applicable valuation framework. An illiquid loan’s reported fair value is not a guaranteed sale price.','nav-discounts'),
    ('NAV per share','Reported net assets attributable to the relevant share class divided by the applicable shares at the reporting date. Preserve its date when comparing a market quote.','nav-discounts'),
    ('First lien','A contractual senior security interest in specified collateral. Priority does not establish collateral adequacy or guarantee full recovery.','loan-pipeline'),
    ('Unitranche','A financing structure combining lending exposures in one facility; intercreditor arrangements can affect the economic priority of different lenders.','loan-pipeline'),
    ('Regular distribution','The issuer’s identified recurring distribution. Match the declared or paid basis and period before comparing it with NII.','nii-coverage'),
    ('Supplemental distribution','An additional issuer-designated distribution. A regular-only coverage ratio omits it; include applicable supplements and specials when testing total distributions.','nii-coverage'),
    ('Incentive fee','Contractual compensation based on a specified income or gain measure. Hurdles, catch-up, waivers, lookbacks and caps can change the amount.','incentive-fees'),
    ('Catch-up','A contractual fee band that can allocate more income to the adviser after a hurdle is passed. A hurdle does not necessarily mean fees apply only to excess income.','incentive-fees'),
    ('Asset coverage','A statutory senior-security coverage test with defined adjustments and possible relief. A simple debt-to-equity worksheet is not a compliance calculation.','leverage-coverage'),
    ('RIC','Regulated investment company is a tax status with separate requirements. A BDC regulatory election does not itself prove compliance with RIC rules.','dividends-tax'),
    ('Spillover','A term used in distribution and tax discussions for income associated with later distributions. It is not necessarily a segregated cash reserve. Read the specific tax period and election.','dividends-tax'),
]


def load_articles(root):
    articles = json.loads((root/'content/bdc.json').read_text(encoding='utf-8'))
    lookup = {a['slug']:a for a in articles}
    tools = {t['slug'] for t in all_tools()}
    if len(lookup) != len(articles):
        raise ValueError('Duplicate BDC guide slug')
    for a in articles:
        if not re.fullmatch(r'learn-bdc-[a-z0-9-]+', a['slug']):
            raise ValueError('Invalid BDC slug')
        if a['level'] not in {l['name'] for l in LEVELS}:
            raise ValueError('Invalid BDC level')
        if date.fromisoformat(a['updated']) < date.fromisoformat(a['published']):
            raise ValueError('BDC modification precedes publication')
        for related in a['related'] + a['prerequisites']:
            if related not in lookup or related == a['slug']:
                raise ValueError('Invalid BDC guide dependency')
        if a.get('calculator') and a['calculator'] not in tools:
            raise ValueError('Unknown BDC calculator')
        if any(urlsplit(s['url']).scheme != 'https' for s in a['sources']):
            raise ValueError('BDC sources require HTTPS')
        for q in a['quiz']:
            if not 0 <= q['answer'] < len(q['options']):
                raise ValueError('Invalid BDC quiz answer')
    def visit(slug, trail):
        if slug in trail:
            raise ValueError('Circular BDC prerequisite')
        for prerequisite in lookup[slug]['prerequisites']:
            visit(prerequisite, trail | {slug})
    for slug in lookup:
        visit(slug, set())
    return articles


def quiz(questions):
    fields = ''
    for i, q in enumerate(questions):
        options = ''.join(f'<label><input type="radio" name="question-{i}" value="{j}" required><span>{E(option)}</span></label>' for j, option in enumerate(q['options']))
        fields += f'<fieldset data-answer="{q["answer"]}"><legend>{i+1}. {E(q["question"])}</legend>{options}<p class="quiz-feedback" hidden data-explanation="{E(q["explanation"])}"></p></fieldset>'
    return '<form class="course-quiz" data-quiz>'+fields+'<button class="btn btn-p" type="submit">Check my answers →</button><p class="quiz-score" role="status" aria-live="polite"></p><noscript><p>Interactive scoring requires JavaScript. Worked answers and explanations remain available in the guide text.</p></noscript></form>'


def diagram():
    return '''<figure class="bdc-flow worked-example"><figcaption><strong>Follow the lending chain.</strong> Conceptual educational diagram; not company data.</figcaption><ol><li><b>Shareholders + lenders</b><span>Provide the BDC's capital</span></li><li><b>BDC loan portfolio</b><span>Borrowers owe principal and interest</span></li><li><b>Reported income</b><span>Cash interest and noncash PIK differ</span></li><li><b>Expenses → NII</b><span>Funding costs and fees reduce income</span></li></ol><p>Distributions, loan repayments and realized losses are separate cash or capital events. NII is not the cash-flow statement.</p></figure>'''


def path_cards(articles):
    return '<div class="course-grid">'+''.join(f'<a class="course-card" href="/course-bdc-{l["key"]}.html"><span class="kicker">BDC / Level {i:02d} / {sum(a["level"]==l["name"] for a in articles)} guides</span><h3>{l["name"]}</h3><p>{E(l["title"])}</p><span class="text-link">Open learning path ↗</span></a>' for i,l in enumerate(LEVELS,1))+'</div>'


def research_links(root):
    from build_site import load, display_date
    records=[a for a in load(root)[1] if a['group']=='BDC']
    rows=''.join(f'<article class="lesson-card"><span class="kicker">Published research / {E(display_date(a["date"]))}</span><h3><a href="{E(a["url"])}" target="_blank" rel="noopener">{E(a["title"])}</a></h3><p>{E(a["blurb"])}</p><a class="text-link" href="{E(a["url"])}" target="_blank" rel="noopener">Read the Benzinga original ↗</a></article>' for a in records)
    return '<section class="wrap education-section"><div class="section-heading"><h2>Read the dated research.</h2><a class="text-link" href="/research.html">Selected archive →</a></div><p>These historical research records show how filing questions are framed. Their company figures are not the synthetic lesson inputs or current portfolio data. Publication does not imply a publisher endorsement or investment qualification.</p><div class="lesson-grid">'+rows+'</div></section>'


def article_page(root, a, lookup):
    from build_site import display_date
    level = next(l for l in LEVELS if l['name']==a['level'])
    toc = ''.join(f'<li><a href="#section-{i}">{E(s["heading"])}</a></li>' for i,s in enumerate(a['sections'],1))
    sections = ''.join(f'<section id="section-{i}"><h2>{E(s["heading"])}</h2><p>{E(s["text"])}</p></section>' for i,s in enumerate(a['sections'],1))
    prereqs = ', '.join(f'<a href="/{s}.html">{E(lookup[s]["title"])}</a>' for s in a['prerequisites']) or 'No prior BDC lessons required.'
    objectives = ''.join(f'<li>{E(x)}</li>' for x in a['learning_objectives'])
    checks = ''.join(f'<li>{E(x)}</li>' for x in a['checklist'])
    sources = ''.join(f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener">{E(s["title"])} ↗</a></li>' for s in a['sources'])
    tool = next((t for t in all_tools() if t['slug']==a.get('calculator')),None)
    tool_link = f'<a class="text-link" href="/{tool["slug"]}.html">Apply this in the {E(tool["title"])} ↗</a>' if tool else ''
    table = ''
    if a.get('table'):
        t=a['table']
        table='<div class="table-scroll" tabindex="0" role="region" aria-label="Worked example table"><table><caption>Synthetic worked example</caption><thead><tr>'+''.join(f'<th scope="col">{E(x)}</th>' for x in t['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{E(x)}</td>' for x in row)+'</tr>' for row in t['rows'])+'</tbody></table></div>'
    body=f'<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/learn-bdc.html">BDC learning</a><span>/</span><span aria-current="page">{E(a["title"])}</span></div>'
    body+=section_head('BDC / '+a['level'],E(a['title']),a['description'])
    body+=f'<div class="wrap article-meta">DFB Education · <a href="/course-bdc-{level["key"]}.html">{a["level"]} route</a> · Updated <time datetime="{a["updated"]}">{display_date(a["updated"])}</time></div>'
    body+=f'<div class="wrap reading-layout"><aside class="article-toc"><span class="kicker">In this guide</span><ol>{toc}<li><a href="#worked-example">Worked example</a></li><li><a href="#source-notes">Sources</a></li></ol>{tool_link}</aside><article class="lesson-body"><section><h2>Before you start</h2><p>{prereqs}</p><ul>{objectives}</ul></section>{sections}<section id="worked-example" class="worked-example"><span class="kicker">Synthetic example / not company data</span><h2>{E(a["example"]["heading"])}</h2><p>{E(a["example"]["text"])}</p>{table}</section><section><h2>Test your reasoning</h2><p>{E(a["exercise"]["question"])}</p><details class="workshop-answer"><summary>Reveal the worked answer</summary><p>{E(a["exercise"]["answer"])}</p></details></section><section class="pitfall"><h2>A common mistake</h2><p>{E(a["pitfall"])}</p></section><section><h2>What to check in the disclosures</h2><ul>{checks}</ul>{tool_link}</section><section><h2>Check your understanding</h2>{quiz(a["quiz"])}</section><section id="source-notes"><h2>Sources &amp; scope</h2><p>US BDC education. Examples are hypothetical unless expressly attributed. Filing dates, contractual definitions and tax rules matter. An issuer source describes that issuer; it is not evidence that every BDC uses the same policy.</p><ul class="source-list">{sources}</ul><p class="small-note">Educational material, not a recommendation or personalized investment advice. <a href="/editorial-policy.html">Source and correction policy</a>.</p></section></article></div>'
    ordered=list(lookup)
    position=ordered.index(a['slug'])
    if position+1<len(ordered):
        next_slug=ordered[position+1]
        body+=f'<nav class="wrap education-section" aria-label="Learning sequence"><a class="btn btn-p" href="/{next_slug}.html">Next lesson: {E(lookup[next_slug]["title"])} →</a></nav>'
    body+='<section class="wrap education-section"><div class="section-heading"><h2>Continue the BDC route.</h2><a class="text-link" href="/learn-bdc.html">All BDC guides →</a></div><div class="lesson-grid">'+cards([lookup[s] for s in a['related']])+'</div></section>'
    body+=research_links(root)
    return shell(root,a['slug']+'.html',a['title'],a['description'],body,'Article',article=a)


def outputs(root):
    articles=load_articles(root)
    lookup={a['slug']:a for a in articles}
    output={root/(a['slug']+'.html'):article_page(root,a,lookup) for a in articles}
    body=section_head('BDC learning room / four levels','Understand the loans.<br><em>Then test the income.</em>',f'{len(articles)} free guides, from BDC structure and NII to credit scenarios and filing workshops. Read in order or search for the question in front of you.')
    body+='<section class="wrap education-section"><div class="btns"><a class="btn btn-s" href="/learn.html">REIT learning room</a><a class="text-link" href="/glossary-bdc.html">BDC glossary ↗</a><a class="text-link" href="/bdc-guide.html">BDC field guide ↗</a><a class="text-link" href="/tools.html">BDC worksheets ↗</a></div>'+diagram()+'</section>'
    body+='<section class="wrap education-section" id="learning-paths"><div class="section-heading"><h2>Choose your depth.</h2></div>'+path_cards(articles)+'<p class="small-note">Difficulty levels describe the material; they are not a qualification or professional certification. No account required. Progress is not stored.</p></section>'
    cats=sorted({a['category'] for a in articles})
    body+='<section class="wrap education-section" id="library"><div class="section-heading"><h2>Find your next BDC question.</h2></div><div class="library-filters" data-library-controls hidden><label>Search BDC guides<input id="lesson-search" type="search" placeholder="NII, PIK, fees, non-accrual…"></label><label>Subject<select id="lesson-category"><option value="all">All subjects</option>'+''.join(f'<option>{E(c)}</option>' for c in cats)+'</select></label><label>Level<select id="lesson-level"><option value="all">All levels</option>'+''.join(f'<option>{l["name"]}</option>' for l in LEVELS)+'</select></label><button id="lesson-reset" type="button" class="btn btn-s">Clear filters</button><p id="lesson-count" aria-live="polite">'+str(len(articles))+' guides</p></div><p id="lesson-empty" hidden>No guides match. Clear the filters or use a shorter term.</p><noscript><p>All guides below remain readable without JavaScript.</p></noscript><div class="lesson-grid">'+cards(articles)+'</div></section>'
    body+=research_links(root)
    output[root/'learn-bdc.html']=shell(root,'learn-bdc.html','BDC learning center: NII, PIK, credit risk & filing workshops','Study BDCs through four free learning levels, with source-backed guides, worked examples, quizzes and related calculators.',body,'CollectionPage')
    for i,l in enumerate(LEVELS):
        lessons=[a for a in articles if a['level']==l['name']]
        rows=''.join(f'<li><span>{j:02d}</span><div><h3><a href="/{a["slug"]}.html">{E(a["title"])}</a></h3><p>{E(a["description"])}</p></div></li>' for j,a in enumerate(lessons,1))
        body='<div class="wrap breadcrumbs"><a href="/learn-bdc.html">BDC learning room</a><span>/</span>'+l['name']+'</div>'+section_head('BDC / Level '+str(i+1),l['title'],l['outcome'])
        body+='<section class="wrap education-section"><div class="course-note"><h2>Before you start</h2><p>'+E(l['prerequisite'])+'</p></div><p class="small-note">Four guides · Free · Self-paced. Difficulty is not a professional certification.</p><ol class="course-lessons">'+rows+'</ol><h2>Apply the route.</h2><p>Complete each guide’s worked exercise. Retain the period, units, source and assumptions with every result. The final exercise asks you to explain what remains unknown.</p><h2>Route self-check</h2>'+quiz([a['quiz'][0] for a in lessons])+'<div class="btns course-next"><a class="text-link" href="/learn-bdc.html">All BDC guides</a>'+(f'<a class="btn btn-p" href="/course-bdc-{LEVELS[i+1]["key"]}.html">Next: {LEVELS[i+1]["name"]} →</a>' if i<3 else '<a class="btn btn-p" href="/research.html">Read published research →</a>')+'</div></section>'
        name='course-bdc-'+l['key']+'.html'
        output[root/name]=shell(root,name,l['name']+' BDC learning path',l['outcome'],body,'CollectionPage')
    terms=''.join(f'<div class="glossary-term" data-term data-search="{E((term+" "+meaning).lower())}"><dt>{E(term)}</dt><dd>{E(meaning)} <a href="/learn-bdc-{slug}.html">Read the full guide ↗</a></dd></div>' for term,meaning,slug in TERMS)
    body=section_head('BDC reference shelf','Keep the definition.<br><em>Check the denominator.</em>',f'{len(TERMS)} BDC terms connected to full guides, worked examples and primary sources.')
    body+='<section class="wrap policy-reading"><label class="glossary-search" data-glossary-control hidden>Find a BDC term<input id="glossary-search" type="search" placeholder="NII, PIK, catch-up…"></label><p id="glossary-count" aria-live="polite">'+str(len(TERMS))+' terms</p><p id="glossary-empty" hidden>No matching terms.</p><dl class="glossary-list">'+terms+'</dl><p><a href="/learn-bdc.html">BDC learning room →</a> · <a href="/glossary.html">REIT glossary →</a></p><p class="small-note">Concise educational definitions. Use each linked guide for scope, primary sources and issuer-specific differences.</p></section>'
    output[root/'glossary-bdc.html']=shell(root,'glossary-bdc.html','BDC glossary: NII, PIK, NAV, credit and fees','Fourteen BDC terms explained with links to source-backed guides and examples.',body,'CollectionPage')
    return output
