"""Four learning paths with prerequisites, outcomes and formative self-checks."""
import html
import json
E=lambda s:html.escape(str(s),quote=True)

LEVELS=[
 dict(key='beginner',name='Beginner',number='01',title='Build the foundation.',
      description='Start with what a REIT owns, how a shareholder gets paid, and the difference between income and investment return.',
      prerequisite='No accounting background required. Bring curiosity and a willingness to separate a company from its share price.',
      outcome='Explain the business model, identify the income measure in a claim, and calculate a simple dividend return without confusing yield with safety.',
      image='property-atlas',
      slugs=['learn-reit-basics','learn-reit-types','learn-distribution-rule','learn-yield-total-return','learn-reinvestment','learn-read-filings'],
      task='Choose a REIT you already know. Write three sentences: what it owns or finances, where its income comes from, and which document you would read first. Then use the total return calculator with a price decline as well as a dividend.',
      tool='calculator-total-return',
      quiz=[
          ('A US REIT must generally distribute 90% of which base?',['Revenue','REIT taxable income, subject to the applicable rules','AFFO'],1,'The tax distribution rule is not a requirement to distribute 90% of revenue, FFO or AFFO.'),
          ('A share starts at 100, pays 6 and ends at 90. Simple pretax total return is:',['6%','−4%','−10%'],1,'(90 − 100 + 6) / 100 = −4%. Cash income only partly offsets the price decline.'),
          ('Which question best distinguishes equity and mortgage REITs?',['Do they own properties or finance real estate?','Do they pay monthly or quarterly?','Is their yield above 5%?'],0,'The underlying business matters more than the distribution schedule or headline yield.')]),
 dict(key='intermediate',name='Intermediate',number='02',title='Connect the business to the numbers.',
      description='Read different property models, then follow the accounting bridge from property operations to common-share distributions.',
      prerequisite='Understand the listed REIT structure, dividend yield and the basic layout of an annual filing.',
      outcome='Explain the key operating driver in each sector, distinguish NOI from FFO and AFFO, and calculate coverage on a consistent basis.',
      image='cash-flow',
      slugs=['learn-net-lease','learn-apartments','learn-industrial-logistics','learn-retail','learn-office','learn-healthcare','learn-data-centers','learn-towers','learn-self-storage','learn-hotels','learn-mortgage-reits','learn-reit-etfs','learn-noi','learn-ffo','learn-affo','learn-payout-ratio','learn-lease-expirations','learn-same-store-noi'],
      task='Choose two property sectors. Compare who pays operating expenses, how quickly rents reset, and which capital costs sit outside a headline earnings measure. Rebuild one hypothetical FFO-to-AFFO bridge using the calculator.',
      tool='calculator-ffo-affo',
      quiz=[
          ('Two issuers report AFFO. Before comparing their payout ratios, you should:',['Assume the definitions match','Compare definitions, adjustments and common-share bases','Use the company with the lower ratio automatically'],1,'AFFO is not standardized. An adjustment policy can change the denominator without changing the cash dividend.'),
          ('A triple-net lease means:',['The landlord never spends money on the property','Specified expenses shift to the tenant under the contract','The share price cannot fall'],1,'Lease exceptions, tenant defaults, capital work and corporate financing still matter.'),
          ('AFFO is 4 per share and the dividend is 3 for the same year. The payout ratio is:',['75%','133%','25%'],0,'Dividend / AFFO = 3 / 4 = 75%. Coverage is the inverse: 1.33×.')]),
 dict(key='advanced',name='Advanced',number='03',title='Stress the assumptions.',
      description='Move beyond a single ratio. Connect valuation, refinancing, per-share dilution and dividend funding across scenarios.',
      prerequisite='Be able to reconcile FFO and AFFO and explain property-level NOI. Be comfortable with percentages and per-share calculations.',
      outcome='Build a valuation range, isolate a refinancing sensitivity and explain why company growth can differ from shareholder growth.',
      image='capital-stack',
      slugs=['learn-nav','learn-cap-rate','learn-debt-maturities','learn-interest-coverage','learn-dilution','learn-dividend-cuts','learn-interest-rates','learn-checklist'],
      task='Combine the NAV and refinancing calculators. Hold NOI constant while increasing the cap rate; then reprice only the debt actually maturing. Write down what each model omits before interpreting the results.',
      tool='calculator-nav',
      quiz=[
          ('With NOI fixed, increasing the cap rate used in NOI / cap rate will:',['Increase property value','Decrease property value','Leave value unchanged'],1,'A larger denominator produces a lower value. Debt can amplify the percentage change in common equity value.'),
          ('200 million of debt reprices from 3% to 5%. The isolated full-year interest increase is:',['2 million','4 million','10 million'],1,'200 million × (5% − 3%) = 4 million, before fees, hedges and timing effects.'),
          ('AFFO grows from 100 to 110 while shares rise from 50 to 60. AFFO per share:',['Rises 10%','Stays at 2.00','Falls from 2.00 to about 1.83'],2,'Total growth is not per-share growth. Check the timing and expected earnings contribution of the new capital.')]),
 dict(key='expert',name='Expert',number='04',title='Make the research reproducible.',
      description='Work through definition differences, joint-venture ownership, financing timing and competing interpretations in an evidence-led research memo.',
      prerequisite='Complete the advanced path or bring equivalent experience with issuer reconciliations, capital structures and valuation sensitivities.',
      outcome='Produce an auditable worksheet and a bounded conclusion that distinguishes reported facts, your calculations, assumptions and unresolved evidence.',
      image='evidence-desk',
      slugs=['learn-expert-affo-normalization','learn-expert-jv-nav','learn-expert-refinancing-model','learn-expert-investment-memo'],
      task='Prepare a two-page research memo and a supporting calculation sheet. Include one operating scenario, one financing scenario, a counterargument and the next disclosure that could change your conclusion. Use the workshop self-checks to test consistency.',
      tool='calculator-refinancing',
      quiz=[
          ('You include 40% of a joint venture’s NOI in NAV. Its debt should generally be:',['Ignored because it is not consolidated','Included on the same 40% economic basis, with guarantees assessed separately','Always included at 100%'],1,'Ownership-consistent income and debt avoid overstating NAV. Guarantees or other obligations require a separate assessment.'),
          ('An issuer excludes a recurring cash cost from AFFO. The strongest comparison is:',['Hide the adjustment','Show the issuer measure and a clearly labeled normalized alternative','Call it fraud without further evidence'],1,'Show the reconciliation and your analytical judgment separately. Different definitions alone do not establish misconduct.'),
          ('What makes a research conclusion falsifiable?',['A precise price target alone','A statement that it must eventually be right','Specific future evidence that would weaken or change it'],2,'A verification plan names the disclosure, metric and result that would challenge the interpretation.')])
]

IMAGES={
 'property-atlas':('Illustrated map of net-lease retail, apartments, logistics warehouses, offices, data centers and healthcare properties.','Different buildings earn income in different ways. Net lease describes a contract structure and can apply to more than one property type.'),
 'cash-flow':('Conceptual illustration of the reconciliation from net income through FFO to issuer-defined AFFO.','Start with the reported measure, then inspect the adjustments. FFO and AFFO are not the cash-flow statement; AFFO definitions differ by issuer.'),
 'capital-stack':('Conceptual illustration of property assets and the debt, preferred and common equity claims against them.','Common equity is the residual claim. Asset values, liabilities and senior claims must be measured on a consistent ownership basis.'),
 'evidence-desk':('Illustrated research desk connecting filings, reconciliation schedules, lease contracts and debt documents.','A conclusion should be traceable to the filing, the arithmetic and the assumptions. An illustration is not evidence about a real company.')
}

def level_for(slug):
    return next(level for level in LEVELS if slug in level['slugs'])

def image_for(article):
    slug=article['slug']
    if article['category']=='Property sectors':return 'property-atlas'
    if slug in ('learn-read-filings','learn-checklist') or slug.startswith('learn-expert-'):return 'evidence-desk'
    if slug in ('learn-ffo','learn-affo','learn-noi','learn-same-store-noi','learn-payout-ratio','learn-distribution-rule','learn-reinvestment','learn-yield-total-return'):return 'cash-flow'
    return level_for(slug)['image']

def figure(key,root,compact=False):
    path=root/'img'/'education'/(key+'.webp')
    if not path.exists():return ''
    alt,caption=IMAGES[key]
    metadata=json.loads((root/'img/education/assets.json').read_text(encoding='utf-8'))[key]
    return f'<figure class="education-visual {"visual-compact" if compact else ""}"><a href="/img/education/{key}.webp" target="_blank" rel="noopener" aria-label="Open full illustration"><img src="/img/education/{key}.webp" width="{metadata["width"]}" height="{metadata["height"]}" loading="lazy" alt="{E(alt)}"></a><figcaption>{E(caption)} <a class="illustration-full-size" href="/img/education/{key}.webp" target="_blank" rel="noopener">Open full-size illustration ↗</a><span>Conceptual educational illustration; not company data. <a href="/editorial-policy.html">Image and source policy</a>.</span></figcaption></figure>'

def level_cards(articles):
    lookup={a['slug']:a for a in articles}
    return '<div class="course-grid">'+''.join(f'<a class="course-card" href="/course-{l["key"]}.html"><span class="kicker">Level {l["number"]} / {len(l["slugs"])} guides</span><h3>{l["name"]}</h3><p>{E(l["title"])} {E(l["description"])}</p><span class="text-link">Open learning path ↗</span></a>' for l in LEVELS)+'</div>'

def course_pages(root,articles,shell,section_head):
    lookup={a['slug']:a for a in articles};out={}
    for idx,l in enumerate(LEVELS):
        lessons=''.join(f'<li><span>{i:02d}</span><div><h3><a href="/{slug}.html">{E(lookup[slug]["title"])}</a></h3><p>{E(lookup[slug]["description"])}</p></div></li>' for i,slug in enumerate(l['slugs'],1))
        questions=''
        for i,(question,options,correct,explanation) in enumerate(l['quiz']):
            choices=''.join(f'<label><input type="radio" name="question-{i}" value="{j}" required> <span>{E(option)}</span></label>' for j,option in enumerate(options))
            questions+=f'<fieldset data-answer="{correct}"><legend>{i+1}. {E(question)}</legend>{choices}<p class="quiz-feedback" hidden data-explanation="{E(explanation)}"></p></fieldset>'
        prev=f'<a class="text-link" href="/course-{LEVELS[idx-1]["key"]}.html">← {LEVELS[idx-1]["name"]}</a>' if idx else '<a class="text-link" href="/learn.html">← All guides</a>'
        nex=f'<a class="btn btn-p" href="/course-{LEVELS[idx+1]["key"]}.html">Next: {LEVELS[idx+1]["name"]} →</a>' if idx<3 else '<a class="btn btn-p" href="/research.html">Explore published research →</a>'
        body='<div class="wrap breadcrumbs"><a href="/learn.html">Learning center</a><span>/</span>'+l['name']+'</div>'
        body+=section_head(f'Level {l["number"]} / {l["name"]}',E(l['title']),l['description'])
        if l['key']=='beginner':
            from stock_basics import prerequisite_links
            body+=prerequisite_links()
        body+='<div class="wrap course-intro"><div><div class="course-note"><h2>Before you start</h2><p>'+E(l['prerequisite'])+'</p></div><div class="course-note"><h2>What you will be able to do</h2><p>'+E(l['outcome'])+'</p></div><p class="small-note">'+str(len(l['slugs']))+' guides · Self-paced · Free access<br>Levels describe material difficulty, not a qualification or professional certification.</p></div>'+figure(l['image'],root,True)+'</div>'
        body+='<section class="wrap education-section"><div class="section-heading"><div><span class="kicker">Read in this order</span><h2>Your learning route.</h2></div><a class="text-link" href="/glossary.html">Keep the glossary nearby ↗</a></div><ol class="course-lessons">'+lessons+'</ol></section>'
        body+='<section class="wrap education-section"><div class="worked-example"><span class="kicker">Apply what you have read</span><h2>The practical exercise.</h2><p>'+E(l['task'])+'</p><a class="text-link" href="/'+l['tool']+'.html">Open the related calculator ↗</a></div></section>'
        body+='<section class="wrap education-section"><div class="section-heading"><div><span class="kicker">Check your understanding</span><h2>Can you explain the difference?</h2></div></div><form class="course-quiz" data-quiz>'+questions+'<button class="btn btn-p" type="submit">Check my answers →</button><p class="quiz-score" role="status" aria-live="polite"></p><noscript><p>Use the guide text to check your answers. Interactive scoring requires JavaScript.</p></noscript></form><p class="small-note">This self-check is for learning, not an assessment of investing suitability. Answers stay in this tab and are not saved.</p><div class="btns course-next">'+prev+nex+'</div></section>'
        out[root/f'course-{l["key"]}.html']=shell(root,f'course-{l["key"]}.html',l['name']+' REIT learning path',l['description'],body,'CollectionPage')
    return out
