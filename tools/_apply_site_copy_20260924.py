"""One-time, audit-branch-only copy migration. Not a production entry point."""
from pathlib import Path
import re, html
R = Path(__file__).resolve().parents[1]
def rep(n, old, new, count=1):
    p=R/n; s=p.read_text(); assert s.count(old)==count,(n,old[:80],s.count(old)); p.write_text(s.replace(old,new))
def main(n,new):
    p=R/n;s=p.read_text();a=s.index('<main id="main" tabindex="-1">');b=s.index('</main>',a);p.write_text(s[:a]+'<main id="main" tabindex="-1">\n'+new.strip()+'\n</main>'+s[b+7:])
def meta(n,title=None,desc=None):
    p=R/n;s=p.read_text()
    if title:
        s=re.sub(r'<title>.*?</title>',lambda _: '<title>'+html.escape(title)+'</title>',s,count=1)
        s=re.sub(r'(<meta property="og:title" content=")[^"]*(")',lambda m:m[1]+html.escape(title,quote=True)+m[2],s,count=1)
    if desc:
        for attr in ('name="description"','property="og:description"'):
            s=re.sub(r'(<meta '+attr+r' content=")[^"]*(")',lambda m:m[1]+html.escape(desc,quote=True)+m[2],s,count=1)
    p.write_text(s)
rep('templates/header.html','>By Jeong-Mo Goo</a>','>Analysis by Jeong-Mo Goo</a>')
rep('build_site.py',"('membership.html','Membership'),",'')
rep('templates/footer.html','Independent structural research on dividends, capital structure and the cash behind the payout.','Independent, filing-anchored research on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics.')
rep('templates/footer.html','About the editor','About the author')
rep('templates/footer.html','<li><a href="/membership.html" class="footer-dim">Membership &middot; In preparation</a></li>','')
rep('templates/footer.html','<li><a href="https://jungmoku.substack.com/" target="_blank" rel="noopener">Substack &nearr;</a></li>','<li><a href="https://stocktwits.com/DividendForensicsBureau" target="_blank" rel="noopener">Stocktwits &nearr;</a></li><li><a href="https://muckrack.com/jeong-mo-goo" target="_blank" rel="noopener">Muck Rack &nearr;</a></li>')
rep('templates/home.html','A dividend is<br>the last line of<br>the <em>investigation.</em>','Follow the filing.<br>Trace the<br><em>capital.</em>')
rep('templates/home.html','We reconstruct the cash structure above it. The assets, the debt, the capital decisions &mdash; and what remains for the payout.','Independent research on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics.')
rep('templates/home.html','REITs &amp; BDCs, with selected work across other income assets.<br>No positions. No ratings. No recommendations.','Analysis by Jeong-Mo Goo. Benzinga contributor.<br>No stock ratings. No price targets. No personalized investment advice.')
rep('templates/home.html','Recent investigations','Recent research')
rep('templates/home.html','Filing-level work on payout coverage, debt maturities and financing access. A separate desk for readers who use the research professionally.','Read the method, inspect published working papers and contact the author about sources, corrections or research use.')
rep('templates/home.html','Field guides to the structures that produce income. Start with what the company owns, owes and earns.','Field guides to business models, cash flow and financing. REITs and BDCs remain core areas of the published research.')
rep('templates/home.html','Working paper &nbsp; / &nbsp; No. 001','Published REIT working paper &nbsp; / &nbsp; No. 001')
rep('templates/research.html','Company and sector work built from filings. Each record names the source, distinguishes the denominator and leaves the limits of the analysis visible.','Filing-anchored work on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics. Each record identifies its source, period, definitions and analytical limits.')
rep('templates/research.html','By Jeong-Mo Goo &middot; No position','Analysis by Jeong-Mo Goo &middot; No positions in securities mentioned')
meta('index.html','Dividend Forensics Bureau · Filing-Anchored Structural Research','Independent research by Jeong-Mo Goo on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics. No ratings or price targets.')
meta('research.html',desc='Selected filing-anchored research by Jeong-Mo Goo on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics.')
meta('membership.html','Membership Status · Dividend Forensics Bureau','DFB membership is in preparation and is not open for enrollment or payment. No public price or opening date has been announced.')
main('membership.html','''
<header class="wrap page-heading">
<span class="kicker">Membership status</span>
<h1>In preparation.</h1>
<p class="lede">The Structural Income Desk is being prepared as one founding membership for continuing research on selected REITs, BDCs and income structures.</p>
<p class="membership-no-payment"><strong>Membership is not open for enrollment or payment.</strong> No public price or opening date has been announced.</p>
<p>The intended focus is the record after a public article: material financing changes, source-linked calculations, corrections and unresolved questions. Coverage and delivery details will be published only when the records, access and billing workflow are ready and approved.</p>
<p>The public research archive and existing free working paper remain available. They do not require a paid membership.</p>
<div class="btns"><a class="btn btn-p" href="/research.html">Read the public research <span aria-hidden="true">&rarr;</span></a><a class="btn btn-s" href="/methodology.html">Read the methodology <span aria-hidden="true">&rarr;</span></a></div>
</header>
<section class="sec"><div class="wrap">
<div class="kicker">Research boundary</div><h2>One research standard.</h2>
<p>Company-reported figures, DFB calculations and unresolved questions are kept separate. Announced, priced, issued, closed, outstanding and repaid describe different facts.</p>
<p>No individual stock recommendations, buy/sell ratings, price targets, portfolio-specific advice or short-term trading strategies. Paid comments, member chat and personalized investment Q&amp;A are not part of the planned initial offering.</p>
</div></section>
''')
meta('about.html','About Jeong-Mo Goo · Dividend Forensics Bureau','Jeong-Mo Goo publishes independent, filing-anchored financial research through Dividend Forensics Bureau and contributes to Benzinga.')
main('about.html','''
<header class="wrap"><div class="kicker">About</div><h1>Independent research.<br>Documented reasoning.</h1><p class="lede">Dividend Forensics Bureau is an independent financial research publication by Jeong-Mo Goo. The work focuses on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics.</p></header>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">Analysis by</div><h2>Jeong-Mo Goo</h2></div>
<p class="lede">Benzinga contributor &middot; Independent financial research</p>
<p>Jeong-Mo Goo publishes through Dividend Forensics Bureau and contributes to <a href="https://www.benzinga.com/author/jeong-mo-goo" target="_blank" rel="noopener">Benzinga</a>. Public bylines and publication history can also be found on <a href="https://muckrack.com/jeong-mo-goo" target="_blank" rel="noopener">Muck Rack</a>.</p>
<p>Published work includes REITs, BDCs and selected operating companies. The same method applies to financing transactions and share-count changes at growth companies. Research is selected for the question supported by the filings, not for whether the issuer pays a dividend.</p>
<p>A published article does not imply continuous coverage of that issuer. Dates, scope and subsequent updates belong to each research record.</p>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">The method</div><h2>Keep the source and the conclusion connected.</h2></div>
<p>The work starts with filings, transaction documents and issuer disclosures. Issuer-reported facts, DFB calculations and analytical interpretations are identified separately. Units, periods, denominators and the relevant issuer or borrowing entity are checked before figures are compared.</p>
<p>An announcement is not treated as a completed transaction. A calculation is not presented as an issuer disclosure. When the available documents leave a material question open, the limitation stays in the record.</p>
<div class="method"><div class="mt">The research sequence</div><p>Start with the filing.<br/>Identify the transaction state.<br/>Trace the capital structure.<br/>Recalculate the numbers.<br/>Record what remains unresolved.</p></div>
<p><a class="text-link" href="/methodology.html">Read the methodology &rarr;</a></p>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">Research focus</div><h2>Questions the filings can answer.</h2></div>
<div class="grid g3">
<div class="card"><h3>Capital structure</h3><p>Debt, equity, guarantees and potential dilution, with the entity, measurement basis and date stated.</p></div>
<div class="card"><h3>Financing</h3><p>Issuance, refinancing, facility changes, swaps and proceeds deployment, with plans separated from completed steps.</p></div>
<div class="card"><h3>Payout mechanics</h3><p>Cash generation and distributions read against the issuer's own measures, alongside funding commitments and debt claims.</p></div>
</div></div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">Corrections &amp; revisions</div><h2>The record includes its changes.</h2></div>
<p>Research records identify the revisions recorded on this site. A material correction states what changed, when it changed and, where relevant, whether it changes the analytical conclusion. A historical record remains dated rather than being presented as a current assessment.</p>
<p>Factual corrections, source questions and permissions inquiries can be sent through the <a href="/research-desk.html#inquiries">Research Desk</a>.</p>
</div></section>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">Scope limits</div><h2>What DFB does not provide.</h2></div>
<p>Individual stock recommendations, buy/sell ratings, price targets, portfolio-specific advice and short-term trading strategies are outside the declared scope. The research does not address a reader's individual investment circumstances.</p>
<div class="btns"><a class="btn btn-s" href="/legal.html">Terms</a><a class="btn btn-s" href="/privacy.html">Privacy</a><a class="btn btn-s" href="/disclaimer.html">Research disclaimer</a></div>
</div></section>
''')
meta('methodology.html','Methodology · Filing-Anchored Structural Research','DFB research method: primary disclosures, entity and transaction-state checks, reproducible calculations, comparable definitions and explicit unresolved questions.')
p=R/'methodology.html';s=p.read_text();start=s.index('<header class="wrap">',s.index('<main'));end=s.index('</header>',start)+len('</header>')
intro='''<header class="wrap"><div class="kicker">Methodology</div><h1>From the filing<br>to the finding.</h1><p class="lede">DFB separates what an issuer reports, what the arithmetic establishes and what the available evidence leaves unresolved.</p><div class="guide-banner"><b>Evidence standard</b> Primary filings and transaction documents come first. Issuer definitions, dates and scope stay attached to the figures.</div></header>
<section class="sec"><div class="wrap">
<div class="sec-head"><div class="kicker">Research sequence</div><h2>A repeatable method, not a rating.</h2></div>
<div class="grid g3">
<div class="card"><h3>Identify the record</h3><p>Name the issuer, borrowing entity, document, reporting period and event date. Separate a current disclosure from a historical reference.</p></div>
<div class="card"><h3>Check the transaction state</h3><p>Distinguish announced, priced, issued, closed, outstanding and repaid. Track new borrowing and repayment of old debt as separate events.</p></div>
<div class="card"><h3>Recalculate the figures</h3><p>Preserve units and denominators. Keep capacity, principal, net proceeds, coupon, yield and swap exposure in their respective fields.</p></div>
<div class="card"><h3>Read the definitions</h3><p>Issuer-defined measures are compared only on an explicit basis. Show material differences rather than treating shared labels as identical arithmetic.</p></div>
<div class="card"><h3>Keep limits visible</h3><p>Unverified is not the same as undisclosed. Record the evidence reviewed and the next document that could resolve the question.</p></div>
<div class="card"><h3>Date the conclusion</h3><p>Separate observed facts from interpretation. Record corrections and later evidence without rewriting the original as if it were current.</p></div>
</div></div></section>
<section class="sec" id="framework-notes"><div class="wrap"><div class="kicker">Earlier income research</div><h2>Framework reference notes.</h2><p>The following named frameworks appear in earlier DFB income research. They remain here to explain those publications, not as a substitute for source verification or as a rating system.</p></div></section>'''
p.write_text(s[:start]+intro+s[end:])
meta('research-desk.html','Research Desk · Dividend Forensics Bureau','Independent, filing-anchored research by Jeong-Mo Goo on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics. Sources, methodology and research-use inquiries.')
rep('research-desk.html','Dividend Forensics Bureau  ·  Structural Income Desk™','Dividend Forensics Bureau &nbsp;&middot;&nbsp; Independent research')
rep('research-desk.html','Structural income research for professional investors','Filing-anchored structural research')
rep('research-desk.html','Filing-level work on dividend coverage, capital structure, maturity schedules and financing access. Every reported figure or calculation traces to issuer disclosures and stated arithmetic. Every reconstructed schedule is tied back to the issuer’s stated total before publication.','Research on capital structure, debt, dilution, financing, refinancing, credit and payout mechanics. Reported facts, DFB calculations and unresolved questions are kept distinct, with the source, period and limitations visible.')
rep('research-desk.html','Editor, Dividend Forensics Bureau','Benzinga contributor &middot; DFB author')
rep('research-desk.html','Five things, read in the order the cash moves','Five questions in the disclosed record')
rep('research-desk.html','A dividend is the last event in a sequence. The work reconstructs that sequence from primary filings rather than inferring it from a payout ratio.','The method follows the issuer, the transaction and the funding terms. It applies to growth companies as well as REITs, BDCs and other income structures.')
rep('research-desk.html','<h4>Payout structure</h4>\n<p>Coverage measured against each issuer’s own adjusted measure, on the period the issuer reported and on the period it guided. Where the two disagree, both are shown and the denominators are named.</p>','<h4>Capital structure and dilution</h4>\n<p>Debt, equity, conversion terms and share-count changes read on their stated basis. Repurchase authorization, forward settlement capacity and shares actually issued remain separate.</p>')
rep('research-desk.html','<h4>Issuer-defined reconciliation</h4>\n<p>Where two companies use the same word for different arithmetic — cap rate, annualized base rent, adjusted EBITDA — the definitions are set side by side and the comparison is withheld.</p>','<h4>Cash flow and payout mechanics</h4>\n<p>Issuer-defined earnings measures, cash generation and distributions are read with their periods and adjustments stated. Differences in definitions remain visible in any comparison.</p>')
rep('research-desk.html','Three frameworks and one rule','Reported facts, calculations and open questions')
rep('research-desk.html','<div class="rd-mc"><b>Three Clocks™</b>\n<p>Coverage today, maturity tomorrow, market access when tomorrow arrives. The three do not run at the same speed, and a single quarter shows their position rather than settling which one matters most.</p></div>','<div class="rd-mc"><b>Reported facts</b>\n<p>Amounts and terms stay attached to the entity, reporting date and original disclosure. A maturity date and completed repayment are recorded separately.</p></div>')
rep('research-desk.html','<div class="rd-mc"><b>Buffer Half-Life™</b>\n<p>Coverage measures the surface. Half-life asks how many periods a stated rate of compression would take to halve or exhaust the cushion an issuer currently reports.</p></div>','<div class="rd-mc"><b>DFB calculations</b>\n<p>Calculations show their inputs, units and scope. A stated coupon comparison is not presented as an all-in financing cost or a forecast of earnings.</p></div>')
rep('research-desk.html','<div class="rd-mc"><b>BBB− Cliff™</b>\n<p>The distance between the lowest investment-grade rung and the first speculative one is not one notch of risk. Crossing below investment grade can change the eligible buyer base under mandates that restrict speculative-grade holdings.</p></div>','<div class="rd-mc"><b>Unresolved questions</b>\n<p>A missing confirmation remains an evidence gap, not an allegation. The record identifies what was reviewed and which later evidence could change the status.</p></div>')
rep('research-desk.html','Most research asks to be believed. These two pages are reproduced from the Technical Appendix so the method can be inspected before anything is read.','These pages reproduce the published MAA / W. P. Carey Technical Appendix. They show the calculations and reconciliation format in an existing REIT working paper.')
rep('research-desk.html','The common thread is not an asset class. It is the sequence from distribution to cash generation to capital requirement to maturity to financing access — which is legible in any issuer that pays one.','REITs and BDCs remain core areas of published work. The same filing-based method is used for selected operating companies and can be applied to growth-company financing. The examples below are not a promise of continuous coverage.')
rep('research-desk.html','Organizational research use, data or platform licensing, coverage requests, methodology questions, data verification, media and speaking. Replies come from the author.','Questions about published research, sources, methodology, factual corrections, permissions, media and speaking are welcome. Organizational-use and data-delivery requests are inquiries only, not active product offers. DFB does not provide personalized investment advice or transaction instructions.')
meta('learn.html','Field Guides · Business Models, Cash Flow and Financing','DFB field guides to business models, cash flow and financing, including REITs, BDCs, industrial companies and telecommunications.')
rep('learn.html','Map the business before the yield.','Understand the business.<br/>Then read the numbers.')
p=R/'learn.html';s=p.read_text();m=re.search(r'<p class="lede">.*?</p>',s,re.S);assert m
p.write_text(s[:m.start()]+'<p class="lede">Field guides to how businesses earn cash, fund assets and meet financial claims. The current library covers REITs, BDCs, industrial companies and telecommunications.</p>'+s[m.end():])
rep('learn.html','Start with the property.<br/>Trace the rent.<br/>Check the debt.<br/>Then judge the payout.','Start with the filing.<br/>Understand the business.<br/>Check the cash and capital structure.<br/>Read each measure on its stated basis.')
meta('tools.html','Working Papers & Tools · Dividend Forensics Bureau','Published DFB working papers, source reconciliations, field guides and research checklists. Existing free materials remain available without a paid membership.')
rep('tools.html','<h3>DFB analytical frameworks</h3><p>Three Clocks™, Buffer Half-Life™ and BBB− Cliff™ with the evidence rules that limit their use.</p>','<h3>Source and calculation discipline</h3><p>Transaction states, issuer definitions, reproducible arithmetic and unresolved questions, with reference notes for earlier research.</p>')
rep('tools.html',' Ongoing membership research is still <a href="/membership.html">in preparation</a>.','')
for p in sorted(R.glob('case-*.html')):
    p.write_text(p.read_text().replace('filing-anchored structural income research by Jeong-Mo Goo.','filing-anchored structural research by Jeong-Mo Goo.'))
for p in R.glob('*.html'):
    s=p.read_text()
    if 'name="dfb-design"' in s:
        p.write_text(re.sub(r'(https://dividendforensics\.com/img/og(?:-research|-learn|-tools)?\.png)\?v=20260917',r'\1?v=20260924',s))
rep('tools/render_social.py',"'og.png':('The publication','A dividend is the last<br>line of the <em>investigation.</em>','Filing-anchored research on dividends, REITs &amp; BDCs.'),","'og.png':('Filing-anchored structural research','Follow the filing.<br><em>Trace the capital.</em>','Capital structure. Debt. Dilution. Financing. Credit. Payout mechanics.'),")
rep('tools/render_social.py',"'og-learn.png':('The reading room','Before the ratio,<br><em>understand the business.</em>','Field guides to real estate, private credit and cash flow.'),","'og-learn.png':('The reading room','Understand the business.<br><em>Then read the numbers.</em>','Field guides to business models, cash flow and financing.'),")
rep('README.md','Independent, filing-anchored research on dividend durability, capital structure\nand financing access.','Independent, filing-anchored research on capital structure, debt, dilution,\nfinancing, refinancing, credit and payout mechanics.')
rep('README.md','The visual evidence is\nfrom the original reports, not generated artwork. A premium presentation does\nnot imply a paid subscription is available. Membership remains **not open**.','The visual evidence is\nfrom the original reports, not generated artwork. A premium presentation does\nnot imply a paid subscription is available. Membership remains **not open**.\n\n## Public copy state — 2026-09-24\n\nDFB remains Dividend Forensics Bureau, with analysis by Jeong-Mo Goo. Public\npositioning is method-led rather than limited to dividend-paying companies.\nExisting REIT/BDC research, field guides and the published MAA/WPC working\npaper are preserved; historical article findings are not rewritten for branding.\nThe three named income frameworks remain reference material on Methodology,\nnot the front-door description of the publication.\n\nMembership is removed from shared navigation and launch-notice promotion.\n`membership.html` remains a status-only URL: in preparation, not open for\nenrollment or payment, no public price or launch date. Do not upload review-only\nWeekly or MRP sample files, enable checkout, or publish internal pricing through\na copy change. The existing free Report No. 001 checkout is a separate, already\npublished MAA/WPC working paper; preserve its variant ID.\n\nActive social destinations are Benzinga, Stocktwits, Muck Rack, X and Bluesky.\nSubstack is no longer promoted. The Research Desk form is preserved as an\ninquiry route, not represented as a live paid custom-research or data product.\n')
print('Applied the approved copy migration; run the normal site builder next.')
