#!/usr/bin/env python3
"""One-time, idempotent migration to the September 2026 editorial design.

Run only on the design branch, before review. Existing policy wording, research
content, report assets, redirects, inquiry endpoint and CNAME are preserved.
Subsequent publishing uses build_site.py, not this migration.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_site as build

ADDITIONS = [
 {'url':'https://www.benzinga.com/Opinion/26/09/61662923/800m-financing-run-puts-blue-owl-technology-dividend-coverage-in-focus','title':"Blue Owl Technology's $800M Financing Run Puts Dividend Coverage In Focus",'blurb':'Three financing transactions serve different functions. The recurring dividend test still sits in net investment income per share.','date':'2026-09-08','group':'BDC','label':'Technology lending','case_key':'OTF','case_slug':'otf-financing'},
 {'url':'https://www.benzinga.com/Opinion/26/09/61574057/how-ahr-873-mln-kensington-deal-could-shift-its-dividend-payout-ratio','title':"How AHR's $873M Kensington Deal Could Shift Its Dividend Payout Ratio",'blurb':'Acquisition closings and forward equity settlements move on different schedules. The post-deal per-share result connects them.','date':'2026-09-02','group':'REIT','label':'Healthcare','case_key':'AHR','case_slug':'ahr-kensington'},
 {'url':'https://www.benzinga.com/Opinion/26/08/61521462/mid-america-apartment-communities-preferred-stock-redemption-seen-as-accretive-to-core-ffo-per-share','title':"MAA's 8.5% Preferred Redemption Shifts The Dividend Math To Common Shares",'blurb':'A scheduled preferred-stock redemption exchanges preferred dividend payments for common-equity funding and a changing share denominator.','date':'2026-08-31','group':'REIT','label':'Residential','case_key':'MAA','case_slug':'maa-preferred'},
 {'url':'https://www.benzinga.com/Opinion/26/08/61457452/saratoga-investment-pushes-debt-maturity-to-2031-but-dividend-coverage-remains-under-pressure','title':"Saratoga Extends A Debt Maturity. Dividend Coverage Remains A Separate Test.",'blurb':'Replacing a lower-coupon maturity does not automatically resolve the gap between net investment income and the regular distribution.','date':'2026-08-27','group':'BDC','label':'Refinancing','case_key':'SAR','case_slug':'sar-refinancing'},
 {'url':'https://www.benzinga.com/Opinion/26/08/61433319/how-ryman-grande-lakes-deal-shifts-the-dividend-math','title':"How Ryman's $1.38B Grande Lakes Deal Shifts The Dividend Math",'blurb':'Equity and debt financing change the cash requirements and share count behind a pre-acquisition payout ratio.','date':'2026-08-26','group':'REIT','label':'Hospitality','case_key':'RHP','case_slug':'rhp-grande-lakes'},
 {'url':'https://www.benzinga.com/Opinion/26/08/61386664/how-the-prologis-segro-deal-could-change-the-dividend-payout-dynamics','title':'How The Prologis-SEGRO Deal Could Change The Dividend Payout Dynamics','blurb':'An expanded equity base makes post-close per-share earnings more informative than the standalone payout snapshot.','date':'2026-08-24','group':'REIT','label':'Logistics','case_key':'PLD / SEGRO','case_slug':'pld-segro'},
 {'url':'https://www.benzinga.com/Opinion/26/08/61335361/public-storage-vs-extra-space-a-dividend-comparison','title':'Public Storage Vs. Extra Space: A Dividend Comparison','blurb':'Two guidance-based payout ratios sit above different same-store operating trends and different financing structures.','date':'2026-08-20','group':'REIT','label':'Self-storage','case_key':'PSA / EXR','case_slug':'psa-exr'},
]

DESK_OVERRIDES = '''
/* September 2026: preserve the forensic desk, refine its typesetting. */
.desk-page {
 --paper:#202b27; --paper-light:#29352e; --paper-shade:#27332d;
 --text:#efede3; --muted:#b7c0b3; --accent:#d0b78d; --accent-hover:#e1cdaa;
 --ink:#202b27; --ink-2:#27332d; --ink-3:#303d34; --archive:#19231f;
 --cream:#efede3; --cream-dim:#c7cfc1; --cream-mute:#b7c0b3;
 --gold:#d0b78d; --gold-deep:#b6a17f; --gold-soft:#ddc7a3;
 --rule:#536052; --rule-2:#667560; --line:#536052; --line-2:#455346;
 --teal:#a3bcab; --teal-dim:#809988;
 background:var(--paper);color:var(--text);
}
.desk-page .site-masthead{background:var(--paper)}
.desk-page .site-links a{color:var(--cream-dim)}
.desk-page .site-links a[aria-current]{color:var(--gold)}
.desk-page .site-footer{background:#18211e}
.desk-page .rd-hero{padding:74px 0 56px}
.desk-page .rd-hero::before{display:none}
.desk-page .rd-h1{font-family:var(--display);font-weight:400;font-size:clamp(48px,6.2vw,80px);line-height:1.02;max-width:19ch;letter-spacing:-.035em;margin-top:26px}
.desk-page .rd-lede{font-family:var(--sans);font-size:16px;line-height:1.85;max-width:70ch;color:var(--cream-dim);margin-top:30px}
.desk-page .rd-for{font-family:var(--sans);font-size:10px;letter-spacing:.09em;max-width:none;line-height:1.9}
.desk-page .rd-eyebrow,.desk-page .rd-lab{font-family:var(--sans);font-size:10px;letter-spacing:.14em}
.desk-page .rd-h2{font-family:var(--display);font-weight:400;font-size:clamp(34px,4.1vw,54px);line-height:1.06;letter-spacing:-.025em}
.desk-page .rd-sec{padding:64px 0}
.desk-page .rd-authorship{display:grid;grid-template-columns:repeat(4,1fr);gap:25px;margin-top:35px;border-block:1px solid var(--rule);padding:20px 0}
.desk-page .rd-authorship dt{font-size:9px;letter-spacing:.11em;text-transform:uppercase;color:var(--gold)}
.desk-page .rd-authorship dd{font-size:11px;line-height:1.75;margin-top:9px;color:var(--cream-dim)}
.desk-page .rd-rail{display:none}
.desk-page .rd-row h4{font-family:var(--display);font-size:30px;letter-spacing:0;line-height:1.15}
.desk-page .rd-row p,.desk-page .rd-sub{font-size:14px;line-height:1.85}
.desk-page .rd-list{margin-top:35px}
.desk-page .rd-mc{padding:28px 26px}
.desk-page .rd-mc b{font-family:var(--display);font-size:28px;font-weight:400}
.desk-page .rd-mc p{font-size:13px;line-height:1.8}
.desk-page .rd-principle{padding:30px 35px}
.desk-page .rd-principle p{font-family:var(--display);font-size:32px;line-height:1.25}
.desk-page .rd-ck>i,.desk-page .rd-ck>em{font-family:var(--sans);font-size:10px;letter-spacing:.06em}
.desk-page .rd-rec{background:transparent;border:1px solid var(--rule);font-family:var(--sans);font-size:11px}
.desk-page .rd-rec .hd{letter-spacing:.07em;font-size:9px}
.desk-page .rd-rec .r>span:first-child{letter-spacing:.04em}
.desk-page .rd-fig img{box-shadow:none;border:10px solid #e5ded0;background:#e5ded0}
.desk-page .rd-cap b{font-family:var(--sans);font-size:9px;letter-spacing:.08em}
.desk-page .rd-cap p{font-size:13px}
.desk-page .rd-cap cite{font:400 10px/1.9 var(--sans);letter-spacing:0;color:var(--cream-mute)}
.desk-page .rd-cap cite s{white-space:normal}
.desk-page .rd-ob>b{font-family:var(--sans);font-size:10px;letter-spacing:.1em}
.desk-page .rd-ob li{font-size:13px;line-height:1.75}
.desk-page .rd-obs-note{font:400 10px/1.8 var(--sans);letter-spacing:.06em;color:var(--muted)}
.desk-page .rd-not{border:1px solid var(--rule);padding:0 30px}
.desk-page .rd-not li{font-size:15px;padding-left:29px}
.desk-page .rd-cov{width:100%;border-collapse:collapse;margin-top:32px;table-layout:fixed}
.desk-page .rd-cov th{font:400 10px/1.7 var(--sans);text-align:left;color:var(--gold);letter-spacing:.08em;padding:14px 0;border-bottom:1px solid var(--rule)}
.desk-page .rd-cov td{padding:18px 18px 18px 0;border-bottom:1px solid var(--rule);font-size:13px;line-height:1.8;color:var(--cream-dim);overflow-wrap:anywhere}
.desk-page .rd-cov th:first-child,.desk-page .rd-cov td:first-child{width:33%;font-family:var(--sans)}
.desk-page .rd-cta{padding:40px;border:1px solid var(--rule);background:var(--ink-2)}
.desk-page .rd-form{margin-top:30px}
.desk-page .rd-form label{font-size:11px;letter-spacing:.03em;color:var(--cream-dim)}
.desk-page .rd-form input,.desk-page .rd-form textarea,.desk-page .rd-form select{border:1px solid var(--rule);background:var(--ink);color:var(--cream);border-radius:0;padding:13px 14px;font-size:14px}
.desk-page .rd-submit{border:1px solid var(--gold);background:var(--gold);color:#202b27;padding:13px 25px;font-size:12px;letter-spacing:.02em;min-height:48px}
.desk-page .rd-alt{font-size:12px;color:var(--muted)}
@media(max-width:780px){.desk-page .rd-hero{padding:42px 0}.desk-page .rd-h1{font-size:53px}.desk-page .rd-lede{font-size:14px}.desk-page .rd-authorship{grid-template-columns:1fr 1fr;gap:22px}.desk-page .rd-sec{padding:46px 0}.desk-page .rd-ev,.desk-page .rd-obs{grid-template-columns:1fr;gap:35px}.desk-page .rd-row{grid-template-columns:26px 1fr;gap:16px}.desk-page .rd-ck{grid-template-columns:105px 1fr;gap:14px}.desk-page .rd-ck>em{grid-column:2}.desk-page .rd-cta{padding:25px 20px}.desk-page .rd-form .rd-2{grid-template-columns:1fr}.desk-page .rd-principle{padding:24px}.desk-page .rd-principle p{font-size:28px}.desk-page .rd-method{grid-template-columns:1fr}.desk-page .rd-cov td{font-size:11px;padding-right:13px}}
.desk-page .btn-p { color:#202b27; }
.desk-page .btn-p:hover { color:#202b27; }
'''

def page_html(title, description, content, name, classes='content-page', robots=None, extra_css='', head_extra=''):
    canonical = 'https://dividendforensics.com/' + ('' if name == 'index.html' else name)
    og = 'og-research.png' if name.startswith('case-') or name in ('research.html','research-desk.html') else 'og-learn.png' if 'guide' in name or name in ('learn.html','reit-what-is-a-reit.html','reit-ffo-vs-eps.html') else 'og-tools.png' if name in ('tools.html','methodology.html') else 'og.png'
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{build.esc(title)}</title>
<meta name="description" content="{build.esc(description)}">
<meta name="author" content="Jeong-Mo Goo"><meta name="dfb-design" content="editorial-20260917">
{f'<meta name="robots" content="{build.esc(robots)}">' if robots else ''}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Dividend Forensics Bureau">
<meta property="og:title" content="{build.esc(title)}"><meta property="og:description" content="{build.esc(description)}">
<meta property="og:url" content="{canonical}"><meta property="og:image" content="https://dividendforensics.com/img/{og}?v=20260917">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#f3f0e8">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/dfb.css"><link rel="stylesheet" href="/newsroom.css">{extra_css}
{head_extra}
<script src="/site.js" defer></script>
</head><body class="{classes}">
{build.HEADER_START}
{build.header(name)}
{build.HEADER_END}
<main id="main" tabindex="-1">
{content}
</main>
{build.FOOTER_START}
{build.footer()}
{build.FOOTER_END}
</body></html>
'''

def root_paths(soup):
    for el in soup.select('[href], [src]'):
        for attr in ('href','src'):
            val=el.get(attr)
            if not val or val.startswith(('/', '#', '?')) or urlsplit(val).scheme:
                continue
            el[attr] = '/' + val.lstrip('./')
    # Drop outdated per-element style overrides. Keep honeypot hidden.
    for el in soup.select('[style]'):
        if el.name == 'input' and el.get('name') == '_honey':
            el['hidden']='';el['tabindex']='-1';el['autocomplete']='off'
        del el['style']
    for img in soup.select('img'):
        if not img.get('loading'): img['loading']='lazy'
    for el in soup.select('[onclick]'):
        del el['onclick']


def apply():
    # Existing baseline is retained in git history, never overwritten in _legacy.
    cfg=json.loads((ROOT/'articles.json').read_text())
    existing={a['url'] for a in cfg['articles']}
    additions=[dict(a,status='published',publication_verified='2026-09-17') for a in ADDITIONS if a['url'] not in existing]
    cfg['articles']=additions+cfg['articles']
    cfg['published_count']=cfg.get('published_count',86)+len(additions)
    cfg['_published_count_note']='Legacy running total plus verified additions. Not displayed as an independently audited count; the website displays the number of selected public records.'
    cfg['_readme']=[
      'Canonical publishing file: /articles.json. Only published public URLs belong in the live archive.',
      'Array order is editorial order. home:false excludes a record only from the home page.',
      'case_slug is optional. An existing case-{slug}.html is used when present; otherwise the public article URL is used.',
      'Latest publication is the maximum public article date, not the array order or build date.',
      'The website displays the selected archive count, not the legacy published_count.',
      'After editing run: python build_site.py; python tools/check_site.py. CI performs the same steps.',
      'Required fields: url, title, blurb, date (YYYY-MM or YYYY-MM-DD), group, label, case_key.',
      'Optional: home (boolean), home_title, case_slug, status (published/draft/internal_review).'
    ]
    (ROOT/'articles.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    active=[]
    for path in ROOT.glob('*.html'):
        original=path.read_text(encoding='utf-8')
        soup=BeautifulSoup(original,'html.parser')
        if not soup.body or soup.select_one('meta[name="dfb-design"]') or soup.select_one('meta[http-equiv="refresh"]'):
            continue
        active.append(path.name)
        title=soup.title.get_text() if soup.title else path.stem
        desc=soup.select_one('meta[name="description"]')
        description=desc.get('content','') if desc else 'Dividend Forensics Bureau publication.'
        extra_css=''; head_extra=''
        for ld in soup.select('script[type="application/ld+json"]'):
            head_extra+=str(ld)+'\n'
        if path.name=='index.html':
            content=(ROOT/'templates/home.html').read_text().replace('{{report_url}}',build.esc(build.REPORT_URL))
            classes='home-page'
        elif path.name=='research.html':
            title='Research Archive | Dividend Forensics Bureau'
            description='Selected filing-anchored research on dividends, capital structure, REITs and BDCs by Jeong-Mo Goo.'
            content=(ROOT/'templates/research.html').read_text().replace('{{report_url}}',build.esc(build.REPORT_URL))
            classes='research-page'
        elif path.name=='404.html':
            title='Page Not Found | Dividend Forensics Bureau'
            description='This address could not be found. Return to the research archive, field guides or home page.'
            classes='error-page'
            content='''<section class="error-main"><div class="error-numeral" aria-hidden="true">404.</div><span class="sr-only">Error 404.</span><h1>This address is<br>not on the desk.</h1><p>The page may have moved, or the address may be incomplete. The research archive is a good place to start again.</p><div class="btns"><a class="btn btn-p" href="/research.html">Browse research &rarr;</a><a class="btn btn-s" href="/">Return home</a></div><p>Looking for an introduction? <a href="/learn.html">Open the field guides.</a></p></section>'''
        else:
            classes='content-page page-'+path.stem.lower()
            if path.name=='research-desk.html':
                styles='\n'.join(s.get_text() for s in soup.select('style'))
                styles=styles.replace(':root{','.desk-page{').replace('body{background:var(--ink)}','.desk-page{background:var(--ink)}')
                (ROOT/'research-desk.css').write_text(styles+'\n'+DESK_OVERRIDES)
                extra_css='<link rel="stylesheet" href="/research-desk.css">'
                classes='desk-page'
                rd_for=soup.select_one('.rd-for')
                rd_for.insert_before(BeautifulSoup('<div class="btns"><a class="btn btn-p" href="#inquiries">Research inquiries <span aria-hidden="true">&rarr;</span></a><a class="text-link" href="#evidence">Inspect the working papers <span aria-hidden="true">&darr;</span></a></div>','html.parser'))
                # Preserve existing section IDs and add a semantic evidence anchor.
                evidence=soup.find(id='s4')
                anchor=soup.new_tag('span',id='evidence')
                evidence.insert(0,anchor)
            if path.name in ('privacy.html','disclaimer.html'):
                main=soup.select_one('main.main-body')
                # Retain every policy paragraph. Remove only decorative SVG furniture.
                body_fragment=BeautifulSoup(str(main),'html.parser')
                for el in body_fragment.select('svg,.pew-pattern,.greek-key,.dome-band,.lectern-band'): el.decompose()
                h1=soup.find('h1')
                content=f'<div class="wrap policy-content"><span class="kicker">Reader information</span><h1>{h1.decode_contents()}</h1>'+body_fragment.main.decode_contents()+'</div>'
                classes='policy-page'
            elif path.name=='legal.html':
                main=soup.body.find('div',class_='wrap',recursive=False)
                for foot in main.select('footer'):foot.decompose()
                content='<div class="wrap policy-content">'+main.decode_contents()+'</div>'
                classes='policy-page'
            elif path.name=='Refund.html':
                main=soup.body.find('div',class_='wrap',recursive=False)
                status=soup.body.find('div',recursive=False)
                for foot in main.select('footer'): foot.decompose()
                content='<div class="wrap policy-content"><div class="note">'+status.decode_contents()+'</div>'+main.decode_contents()+'</div>'
                classes='policy-page'
            else:
                for el in soup.select('nav.nav,footer.ft,script,style'): el.decompose()
                content=soup.body.decode_contents()
            frag=BeautifulSoup(content,'html.parser')
            root_paths(frag)
            # Avoid nested main landmarks on legacy policy pages.
            for nested in frag.select('main'): nested.name='div'
            content=str(frag)
        html=page_html(title,description,content,path.name,classes,robots='noindex,follow' if path.name=='404.html' else None,extra_css=extra_css,head_extra=head_extra)
        path.write_text(html,encoding='utf-8')
    # Unused root workflow copy is archived; only .github/workflows/main.yml runs.
    shadow=ROOT/'buildsite.yml'
    if shadow.exists():
        (ROOT/'_legacy/buildsite-before-editorial.yml').write_bytes(shadow.read_bytes())
        shadow.unlink()
    rc=build.main([])
    if rc: raise RuntimeError('Post-migration build failed.')
    # A sitemap contains only real pages, not retired redirects or the error page.
    urls=[]
    for p in sorted(ROOT.glob('*.html')):
        t=p.read_text()
        if 'name="dfb-design"' in t and p.name!='404.html':
            urls.append('https://dividendforensics.com/'+('' if p.name=='index.html' else p.name))
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls)+'</urlset>\n')
    print('Editorial design applied:',len(active),'pages. Added public records:',len(additions))

if __name__=='__main__':
    apply()
