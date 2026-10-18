"""Small, source-linked US investing editions; no country-specific tax adaptation."""
import json
from datetime import date
from education import E, DOMAIN

LOCALES = {'zh-Hant': 'zh-hant', 'ja': 'ja', 'de': 'de'}
NAMES = {'en': 'English', 'es': 'Español', 'zh-Hant': '繁體中文', 'ja': '日本語', 'de': 'Deutsch'}
PAGES = {'index': 'index.html', 'reit': 'learn-reit-basics.html',
         'bdc': 'learn-bdc-basics.html', 'coverage': 'learn-bdc-nii-coverage.html',
         'comparison': 'reit-vs-bdc.html', 'income': 'calculator-dividend-income.html'}
SOURCES = {
    'reit': [('Investor.gov — REIT', 'https://www.investor.gov/introduction-investing/investing-basics/glossary/real-estate-investment-trust-reit'), ('Nareit — FFO', 'https://www.reit.com/glossary/funds-operation-ffo')],
    'bdc': [('Investor.gov — BDC', 'https://www.investor.gov/introduction-investing/investing-basics/investment-products/closed-end-funds/publicly-traded-business-development-companies-bdcs')],
    'coverage': [('Ares Capital — financial statements and reconciliation', 'https://www.sec.gov/Archives/edgar/data/1287750/000162828026027685/arccq1-2026exhibit991.htm')],
    'comparison': [('Investor.gov — REIT', 'https://www.investor.gov/introduction-investing/investing-basics/glossary/real-estate-investment-trust-reit'), ('Investor.gov — BDC', 'https://www.investor.gov/introduction-investing/investing-basics/investment-products/closed-end-funds/publicly-traded-business-development-companies-bdcs'), ('Nareit — AFFO', 'https://www.reit.com/glossary/adjusted-funds-operations-affo')],
}

def path_for(locale, key):
    return LOCALES[locale] + '/' + ('index.html' if key == 'index' else key + '.html')

def groups(spanish_pairs):
    result = {en: {'en': en, 'es': es} for en, es in spanish_pairs.items()}
    for key, english in PAGES.items():
        group = result.setdefault(english, {'en': english})
        group.update({locale: path_for(locale, key) for locale in LOCALES})
    return result

def outputs(root):
    from localized import url
    result = {}
    for locale in LOCALES:
        data = json.loads((root/'content'/('edition-'+locale+'.json')).read_text(encoding='utf-8'))
        ui = data['ui']
        for key, english in PAGES.items():
            path = path_for(locale, key)
            item = data['articles'].get(key, data['income'] if key == 'income' else data['home'])
            title, description = item['title'], item['description']
            body = f'<header class="wrap education-heading"><p class="kicker">{E(ui["edition"])}</p><h1>{E(title)}</h1><p class="education-lede">{E(description)}</p></header><p class="wrap edition-scope">{E(ui["scope"])}</p>'
            if key == 'index':
                body += '<section class="wrap education-section"><div class="lesson-grid">'
                for other in ('reit', 'bdc', 'comparison', 'coverage', 'income'):
                    card = data['income'] if other == 'income' else data['articles'][other]
                    body += f'<article class="lesson-card"><h2><a href="{url(path_for(locale,other))}">{E(card["title"])}</a></h2><p>{E(card["description"])}</p></article>'
                body += '</div></section>'
            elif key == 'income':
                body += income_body(locale, item, ui)
                body += f'<section class="wrap policy-reading"><h2>{E(ui["sources"])}</h2><p><a href="{url(english)}" lang="en">{E(ui["original"])}</a> · <a href="{url(path_for(locale,"coverage"))}">{E(data["articles"]["coverage"]["title"])}</a></p></section>'
            else:
                if date.fromisoformat(item['updated']) < date.fromisoformat(item['published']):
                    raise ValueError('Translation update precedes publication: '+path)
                body += f'<div class="wrap article-meta">DFB Education · <time datetime="{item["updated"]}">{E(item["updated"])}</time> · <a href="{url(english)}" lang="en">{E(ui["original"])}</a></div>'
                body += f'<nav class="wrap lesson-jump-menu" aria-label="{E(ui["contents"])}"><ol>'
                body += ''.join(f'<li><a href="#section-{i}">{E(s[0])}</a></li>' for i,s in enumerate(item['sections'],1))
                body += f'<li><a href="#example">{E(ui["example"])}</a></li><li><a href="#sources">{E(ui["sources"])}</a></li></ol></nav>'
                body += '<article class="wrap policy-reading lesson-body international-article">'
                body += ''.join(f'<section id="section-{i}"><h2>{E(s[0])}</h2><p>{E(s[1])}</p></section>' for i,s in enumerate(item['sections'],1))
                if key == 'comparison':
                    body += f'<p class="source-note">{E(item["policy_note"])} <a href="https://www.sec.gov/Archives/edgar/data/1287032/000128703224000152/R14.htm" lang="en">Prospect Capital · Form 10-Q · 2024-03-31 · Revenue Recognition</a></p>'
                body += f'<section id="example" class="worked-example"><h2>{E(ui["example"])}</h2><p>{E(item["example"])}</p></section>'
                body += f'<section><h2>{E(ui["exercise"])}</h2><p>{E(item["question"])}</p><details><summary>{E(ui["answer"])}</summary><p>{E(item["answer"])}</p></details></section>'
                body += f'<section><h2>{E(ui["checks"])}</h2><ul>'+''.join(f'<li>{E(x)}</li>' for x in item['checks'])+'</ul></section>'
                body += f'<section id="sources"><h2>{E(ui["sources"])}</h2><p>{E(ui["source_note"])}</p><ul>'+''.join(f'<li><a href="{E(link)}">{E(name)}</a></li>' for name,link in SOURCES[key])+'</ul></section></article>'
                body += f'<p class="wrap"><a href="{url(path_for(locale,"income"))}">{E(data["income"]["title"])}</a> · <a href="{url(path_for(locale,"index"))}">{E(ui["home"])}</a></p>'
            schema = {'@context':'https://schema.org','@type':'Article' if key in data['articles'] else 'WebPage','name':title,'description':description,'url':url(path),'inLanguage':locale,'isAccessibleForFree':True,'isBasedOn':url(english),'publisher':{'@type':'Organization','name':'Dividend Forensics Bureau','url':DOMAIN}}
            if key in data['articles']:
                schema.update(headline=title,datePublished=item['published'],dateModified=item['updated'],author={'@type':'Organization','name':'DFB Education','url':DOMAIN+'/editorial-policy.html'},mainEntityOfPage=url(path))
            crumbs = [{'@type':'ListItem','position':1,'name':ui['home'],'item':url(path_for(locale,'index'))}]
            if key != 'index': crumbs.append({'@type':'ListItem','position':2,'name':title,'item':url(path)})
            structured = [schema, {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs}]
            scripts = ''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script>' for s in structured)
            if key == 'income':
                scripts += '<script src="/vendor/decimal.js/decimal.js" defer></script><script src="/calculators.js?v=original-1.1.1-feedback" defer></script><script src="/international-calculators.js?v=3" defer></script>'
            result[root/path] = f'''<!DOCTYPE html><html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · DFB</title><meta name="description" content="{E(description)}"><meta name="dfb-design" content="international-20261018"><meta name="robots" content="index,follow"><link rel="canonical" href="{url(path)}"><meta property="og:locale" content="{dict(ja="ja_JP",de="de_DE",**{"zh-Hant":"zh_TW"})[locale]}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{url(path)}"><meta property="og:image" content="{DOMAIN}/img/og.png"><link rel="icon" href="/img/favicon-96.png"><link rel="stylesheet" href="/dfb.css"><link rel="stylesheet" href="/newsroom.css"><link rel="stylesheet" href="/education.css"><link rel="stylesheet" href="/bureau.css"><link rel="stylesheet" href="/lesson-formats.css"><link rel="stylesheet" href="/international.css">{scripts}</head><body class="education-page international-page"><a class="skip-link" href="#main">{E(ui['skip'])}</a><header class="site-masthead"><div class="wrap"><nav class="masthead-main" aria-label="{E(ui['home'])}"><a class="site-brand" href="{url(path_for(locale,'index'))}"><span class="brand-initials">DFB</span><span class="brand-name">Dividend Forensics Bureau</span></a><a href="{url(path_for(locale,'index'))}">{E(ui['home'])}</a></nav></div></header><main id="main" tabindex="-1">{body}</main><footer class="site-footer"><div class="wrap"><p>{E(ui['disclaimer'])}</p><p><a href="/editorial-policy.html">{E(ui['policy'])}</a> · <a href="/privacy.html">{E(ui['privacy'])}</a> · <a href="/about.html">{E(ui['about'])}</a></p></div></footer></body></html>'''
    for path in result:
        result[path] = result[path].replace('<header class="site-masthead">','<!-- SITE:HEADER --><header class="site-masthead">').replace('</header><main','</header><!-- /SITE:HEADER --><main').replace('<footer class="site-footer">','<!-- SITE:FOOTER --><footer class="site-footer">').replace('</footer></body>','</footer><!-- /SITE:FOOTER --></body>')
    return result

def income_body(locale, item, ui):
    controls = ''.join(f'<label for="i-{name}">{E(label)}<input id="i-{name}" name="{name}" type="text" inputmode="decimal" value="{default}" required></label>' for (name,default),label in zip([('capital','10000'),('yield','5'),('tax','0'),('target','500')],item['fields']))
    config = json.dumps(item['messages'],ensure_ascii=False).replace('<','\\u003c')
    body = f'<section class="wrap calculator-layout"><form class="calculator-form" data-international-calculator="{locale}"><fieldset data-calculator-controls disabled><p class="calculator-loading" data-calculator-loading>{E(item["messages"]["loading"])}</p><h2>{E(ui["assumptions"])}</h2><p>{E(item["input_note"])}</p><div class="calculator-fields">{controls}</div><div class="btns"><button class="btn btn-p" type="submit">{E(ui["calculate"])}</button><button class="btn btn-s" type="reset">{E(ui["reset"])}</button></div><p role="alert" hidden></p><noscript><p>{E(item["nojs"])}</p></noscript></fieldset></form><div class="calculator-output" aria-live="polite" role="region" aria-label="{E(ui["result"])}" data-international-result><p>{E(item["messages"]["waiting"])}</p></div><script type="application/json" id="calculator-translations">{config}</script></section>'
    body += '<article class="wrap policy-reading lesson-body international-article">'+''.join(f'<section><h2>{E(h)}</h2><p>{E(t)}</p></section>' for h,t in item['sections'])+'</article>'
    return body
