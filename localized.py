"""Initial Spanish edition. Every translation keeps its English source and US scope."""
import json
from datetime import date
from pathlib import Path
from education import E, DOMAIN

PAIRS={
    'index.html':'es/index.html',
    'learn-reit-basics.html':'es/que-es-un-reit.html',
    'learn-bdc-basics.html':'es/que-es-una-bdc.html',
    'learn-yield-total-return.html':'es/rentabilidad-dividendos.html',
    'learn-bdc-nii-coverage.html':'es/nii-cobertura-dividendos.html',
    'calculator-dividend-income.html':'es/calculadora-dividendos.html',
    'calculator-payout-ratio.html':'es/calculadora-cobertura-affo.html',
}


def url(path):
    return DOMAIN+('/' if path=='index.html' else '/'+path[:-10] if path.endswith('/index.html') else '/'+path)


def alternates(english,spanish):
    return ''.join(f'<link rel="alternate" hreflang="{lang}" href="{url(path)}">\n' for lang,path in [('en',english),('es',spanish),('x-default',english)])


def inject_alternates(path,text,root):
    import re
    from international import groups, NAMES
    relative=path.relative_to(root).as_posix()
    group=next((g for g in groups(PAIRS).values() if relative in g.values()),None)
    if not group:return text
    text=re.sub(r'<link\b[^>]*hreflang="[^"]+"[^>]*>\s*','',text)
    links=''.join(f'<link rel="alternate" hreflang="{lang}" href="{url(target)}">\n' for lang,target in {**group,'x-default':group['en']}.items())
    text=text.replace('</head>',links+'</head>')
    text=re.sub(r'<nav\b[^>]*data-language-switch[^>]*>.*?</nav>','',text,flags=re.S)
    # Spanish remains the first alternative on English pages for established links.
    choices=' · '.join(f'<a href="{url(target)}" lang="{lang}" hreflang="{lang}">{NAMES[lang]}</a>' for lang,target in group.items() if target!=relative)
    text=text.replace('<main id="main" tabindex="-1">','<main id="main" tabindex="-1"><nav class="wrap language-switch" aria-label="Language" data-language-switch>'+choices+'</nav>',1)
    return text


def shell(path,title,description,body,english,article=None,extra=''):
    canonical=url(path)
    schema={'@context':'https://schema.org','@type':'Article' if article else 'WebPage','name':title,'description':description,'url':canonical,'inLanguage':'es','isAccessibleForFree':True,'publisher':{'@type':'Organization','name':'Dividend Forensics Bureau','url':DOMAIN}}
    if article:
        schema.update(headline=title,datePublished=article['published'],dateModified=article['updated'],author={'@type':'Organization','name':'DFB Education','url':DOMAIN+'/editorial-policy.html'},mainEntityOfPage=canonical,isBasedOn=url(english))
    crumbs=[{'@type':'ListItem','position':1,'name':'Inicio en español','item':url('es/index.html')}]
    if path!='es/index.html':crumbs.append({'@type':'ListItem','position':2,'name':title,'item':canonical})
    breadcrumb={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs}
    header=f'''<a class="skip-link" href="#main">Ir al contenido</a><header class="site-masthead"><div class="wrap"><nav class="masthead-main" aria-label="Navegación principal"><a class="site-brand" href="/es/"><span class="brand-initials">DFB</span><span class="brand-name">Dividend Forensics Bureau</span></a><div class="btns"><a href="/es/">Aprender</a><a href="/es/calculadora-dividendos.html">Calculadoras</a><a href="{E(url(english))}" hreflang="en" lang="en">English</a></div></nav></div></header>'''
    footer='''<footer class="site-footer"><div class="wrap"><p>Dividend Forensics Bureau · Educación sobre REIT y BDC de Estados Unidos.</p><p>Material educativo, sin recomendaciones personalizadas. Los ejemplos son hipotéticos salvo atribución expresa. No hay conversión de USD a otra moneda.</p><p><a href="/editorial-policy.html">Fuentes y correcciones (inglés)</a> · <a href="/privacy.html">Privacidad (inglés)</a> · <a href="/disclaimer.html">Aviso financiero (inglés)</a> · <a href="/research.html">Investigaciones publicadas (inglés)</a></p></div></footer>'''
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · DFB</title><meta name="description" content="{E(description)}"><meta name="dfb-design" content="spanish-20261018"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}">
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:locale" content="es_ES"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{DOMAIN}/img/og.png"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/dfb.css"><link rel="stylesheet" href="/newsroom.css"><link rel="stylesheet" href="/education.css"><link rel="stylesheet" href="/bureau.css">
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')}</script><script type="application/ld+json">{json.dumps(breadcrumb,ensure_ascii=False)}</script>{extra}</head><body class="education-page spanish-page">
<!-- SITE:HEADER -->{header}<!-- /SITE:HEADER -->
<main id="main" tabindex="-1">{body}</main>
<!-- SITE:FOOTER -->{footer}<!-- /SITE:FOOTER -->
</body></html>'''


def heading(title,description):
    return f'<header class="education-heading wrap"><span class="kicker">Edición en español / Estados Unidos</span><h1>{E(title)}</h1><p class="education-lede">{E(description)}</p></header>'


def calculator(kind):
    if kind=='income':
        title='Calculadora de ingresos por dividendos en USD'
        fields=[('capital','Capital invertido (USD)',10000,0,1e12),('yield','Rentabilidad anual supuesta (%)',5,0,100),('tax','Retención supuesta (%)',0,0,100),('target','Objetivo mensual (USD)',500,0,1e9)]
        formula='Ingreso bruto anual = capital × rentabilidad anual / 100. Ingreso después de la retención supuesta = bruto × (1 − retención/100). Rentabilidad neta decimal = (rentabilidad anual / 100) × (1 − retención / 100). Capital objetivo = objetivo mensual × 12 / rentabilidad neta decimal.'
        example='Con 10 000 USD y un 5 % anual, el ingreso bruto es 500 USD. Para reproducir este ejemplo, cambie la retención inicial del 0 % al 15 %. Si se supone una retención del 15 %, quedan 425 USD al año y un promedio mensual de 35,42 USD. Un objetivo mensual de 500 USD requiere aproximadamente 141 176,47 USD bajo esas hipótesis constantes.'
        limits='El promedio mensual no es un calendario de pagos. La retención es una hipótesis del usuario, no la determinación de su impuesto final en ningún país. No incluye variaciones de precio o divisa, comisiones ni recortes de dividendos. Con rentabilidad neta cero, un objetivo positivo no puede financiarse.'
        guide='rentabilidad-dividendos'
    else:
        title='Calculadora de cobertura y estrés de AFFO de un REIT'
        fields=[('affo','AFFO anual por acción ordinaria (USD)',4,-1e9,1e9),('dividend','Dividendo anual por acción ordinaria (USD)',3,0,1e9),('decline','Descenso supuesto del AFFO (%)',15,0,100)]
        formula='Payout = dividendo/AFFO. Cobertura = AFFO/dividendo. AFFO bajo estrés = AFFO − |AFFO| × descenso/100. Margen bajo estrés = AFFO bajo estrés − dividendo. Las cifras deben corresponder al mismo período anual y a la misma clase de acción.'
        example='Con AFFO anual de 4 USD por acción y un dividendo anual de 3 USD, el payout es del 75 % y la cobertura es 1,33 veces. Una caída del 15 % deja AFFO de 3,40 USD, payout del 88,24 % y margen de 0,40 USD por acción. Si el AFFO inicial es −4 y el descenso es del 25 %, pasa a −5; el margen frente a 3 de dividendo es −8.'
        limits='AFFO no tiene una definición uniforme. Lea la conciliación del emisor y los costes recurrentes excluidos. Con AFFO cero o negativo no se presenta un payout o una cobertura convencional; se conserva el margen negativo. El descenso de AFFO negativo amplía la pérdida. No es un modelo de BDC: para BDC se estudia NII, PIK y crédito. No produce una calificación de seguridad ni una previsión.'
        guide='que-es-un-reit'
    controls=''.join(f'<label for="es-{key}">{E(label)}<input id="es-{key}" name="{key}" type="number" value="{value}" min="{minimum}" max="{maximum}" step="any" required inputmode="decimal"></label>' for key,label,value,minimum,maximum in fields)
    body=heading(title,'Modifique las hipótesis y examine el cálculo. No son datos actuales de una empresa ni una recomendación.')
    body+=f'<section class="wrap calculator-layout"><form class="calculator-form" data-es-calculator="{kind}"><h2>Sus hipótesis</h2><p>Importes en USD, sin conversión de moneda. Escriba decimales con punto; los resultados usan coma decimal. El valor 5 significa 5 %, no 0,05 %. Los datos permanecen en esta pestaña.</p><div class="calculator-fields">{controls}</div><div class="btns"><button class="btn btn-p" type="submit">Calcular →</button><button class="btn btn-s" type="reset">Restablecer valores iniciales</button></div><p class="calculator-error" role="alert" hidden></p><noscript><p>El cálculo interactivo requiere JavaScript. La fórmula y el ejemplo siguen disponibles abajo.</p></noscript></form><div class="calculator-output" role="region" aria-label="Resultado del escenario" aria-live="polite" data-es-result><p>Seleccione Calcular para ver su escenario.</p></div></section>'
    body+=f'<section class="wrap policy-reading lesson-body"><section><h2>Fórmula y base</h2><p>{E(formula)}</p></section><section><h2>Ejemplo hipotético</h2><p>{E(example)}</p></section><section><h2>Cómo interpretar el resultado</h2><p>{E(limits)}</p><p>Un escenario mantiene constantes las demás variables. Un dividendo alto no prueba que el emisor pueda sostenerlo. Conserve la fecha, el período y la definición del dato antes de comparar resultados.</p></section><section><h2>Busque los datos en su fuente</h2><p>La rentabilidad indicada depende del dividendo y del precio elegidos. En un REIT, localice la conciliación de AFFO y la distribución atribuible a las acciones ordinarias en el informe correspondiente. No mezcle un trimestre con un año ni ingresos totales con cifras por acción. El <a href="https://www.reit.com/glossary" target="_blank" rel="noopener">glosario de Nareit</a> ofrece definiciones del sector; el contrato y los estados del emisor determinan el caso concreto.</p></section><p><a href="/es/{guide}.html">Estudiar el concepto →</a> · <a href="/es/nii-cobertura-dividendos.html">Cobertura de NII de una BDC →</a></p></section>'
    return title,body


def outputs(root):
    guides=json.loads((root/'content/spanish.json').read_text(encoding='utf-8'))
    output={}
    for a in guides:
        if date.fromisoformat(a['updated']) < date.fromisoformat(a['published']):
            raise ValueError('Spanish update precedes publication')
        path='es/'+a['slug']+'.html'
        if PAIRS[a['english_slug']+'.html']!=path:raise ValueError('Spanish translation pair mismatch')
        sections=''.join(f'<section><h2>{E(s["heading"])}</h2><p>{E(s["text"])}</p></section>' for s in a['sections'])
        checks=''.join(f'<li>{E(x)}</li>' for x in a['checklist'])
        sources=''.join(f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener">{E(s["title"])} ↗</a></li>' for s in a['sources'])
        related=a.get('related_english')
        related_english=f'<p><a href="/{E(related["slug"])}.html" lang="en">{E(related["title"])} →</a></p>' if related else ''
        body=heading(a['title'],a['description'])+f'<div class="wrap article-meta">DFB Education · Última revisión: <time datetime="{a["updated"]}">{E(a["updated"])}</time> · <a href="/{a["english_slug"]}.html" lang="en">Original en inglés</a></div><article class="wrap policy-reading lesson-body"><p>Ámbito: REIT y BDC de Estados Unidos. La traducción no adapta las normas a España ni a un país latinoamericano. USD significa dólares estadounidenses; no hay conversión de moneda.</p>{sections}{related_english}<section class="worked-example"><h2>{E(a["example"]["heading"])}</h2><p>{E(a["example"]["text"])}</p></section><section><h2>Compruebe su razonamiento</h2><p>{E(a["exercise"]["question"])}</p><details><summary>Ver respuesta y explicación</summary><p>{E(a["exercise"]["answer"])}</p></details></section><section class="pitfall"><h2>Un error frecuente</h2><p>{E(a["pitfall"])}</p></section><section><h2>Qué comprobar</h2><ul>{checks}</ul></section><section><h2>Fuentes y alcance</h2><ul>{sources}</ul><p>Las fuentes pueden estar en inglés. Las cifras son hipotéticas salvo atribución expresa. Consulte el documento y su fecha; esta página no determina obligaciones fiscales individuales.</p></section><div class="btns"><a class="btn btn-s" href="/es/calculadora-dividendos.html">Calcular ingresos en USD</a><a class="text-link" href="/es/">Todas las guías en español →</a></div></article>'
        from lesson_formats import compose
        body=compose(body,a,spanish=True)
        output[root/path]=shell(path,a['title'],a['description'],body,a['english_slug']+'.html',article=a,extra='<link rel="stylesheet" href="/lesson-formats.css">')
    for kind,en,path in [('income','calculator-dividend-income.html','es/calculadora-dividendos.html'),('payout','calculator-payout-ratio.html','es/calculadora-cobertura-affo.html')]:
        title,body=calculator(kind)
        extra='<script src="/vendor/decimal.js/decimal.js" defer></script><script src="/calculators.js?v=original-1.1.1" defer></script><script src="/spanish-calculators.js?v=es-1.0.1" defer></script>'
        description=('Estime ingresos por dividendos en USD, retención supuesta y capital para un objetivo mensual; con fórmula y ejemplo.' if kind=='income' else 'Compare el dividendo anual con AFFO por acción de un REIT y pruebe un descenso; conserve pérdidas y límites del cálculo.')
        output[root/path]=shell(path,title,description,body,en,extra=extra)
    cards=''.join(f'<article class="lesson-card"><span class="kicker">Guía en español / Estados Unidos</span><h2><a href="/es/{a["slug"]}.html">{E(a["title"])}</a></h2><p>{E(a["description"])}</p></article>' for a in guides)
    body=heading('Aprenda a leer las cifras detrás del dividendo','REIT y BDC de Estados Unidos: estructura, ingresos, riesgos y cálculos reproducibles.')
    body+='<section class="wrap education-section"><p>Edición inicial en español: cuatro guías y dos calculadoras. La biblioteca completa en inglés contiene las rutas de REIT y BDC. Los ejemplos no son recomendaciones, rentabilidades garantizadas ni reglas fiscales de su país.</p><div class="lesson-grid">'+cards+'</div><div class="btns"><a class="btn btn-p" href="/es/calculadora-dividendos.html">Ingresos por dividendos</a><a class="btn btn-s" href="/es/calculadora-cobertura-affo.html">Cobertura de AFFO</a></div><p><a href="/learn.html" lang="en">Ruta completa de REIT (inglés)</a> · <a href="/learn-bdc.html" lang="en">Ruta completa de BDC (inglés)</a> · <a href="/research.html" lang="en">Investigaciones publicadas (inglés)</a></p></section>'
    output[root/'es/index.html']=shell('es/index.html','REIT y BDC de Estados Unidos: guías y calculadoras','Aprenda qué son los REIT y las BDC de Estados Unidos, cómo analizar dividendos y qué límites tienen los cálculos en USD.',body,'index.html')
    return output
