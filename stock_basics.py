"""Beginner stock vocabulary, separate from the numbered REIT/BDC courses."""
from education import E, shell

GUIDES = (
    dict(slug='stock-classification', title='How stocks are classified',
         description='Understand how size, style, sector, structure and dividend policy describe different features of an investment.',
         published='2026-11-01', updated='2026-11-01'),
    dict(slug='market-labels', title='Tickers, exchanges, indexes, and ETFs',
         description='A beginner guide to stock-market labels: tickers, NYSE, Nasdaq, the S&P 500, ETFs and basic trading vocabulary.',
         published='2026-11-01', updated='2026-11-01'),
)


def discovery(exclude_slug=""):
    cards = ''.join(f'<article class="lesson-card"><span class="kicker">Stock basics · Beginner guide</span><h3><a href="/{g["slug"]}.html">{E(g["title"])}</a></h3><p>{E(g["description"])}</p><a class="text-link" href="/{g["slug"]}.html">Read the introduction →</a></article>' for g in GUIDES if g['slug'] != exclude_slug)
    return '<section class="wrap education-section stock-basics-discovery" aria-labelledby="stock-basics-title"><div class="section-heading"><div><span class="kicker">Before choosing a learning room</span><h2 id="stock-basics-title">Start with the labels.</h2></div></div><div class="stock-basics-grid">'+cards+'</div><p>Ready to read company accounts? See <a href="/three-financial-statements.html">how the three financial statements connect</a>.</p></section>'


def prerequisite_links():
    """Compact optional vocabulary route; not part of specialized lesson counts."""
    return '<aside class="wrap stock-basics-prerequisites" aria-label="Stock basics reading"><h2>Stock basics</h2><p>New to the vocabulary? Start with <a href="/stock-classification.html">how stocks are classified</a> and <a href="/market-labels.html">tickers, exchanges, indexes, and ETFs</a>. These introductions are separate from the REIT and BDC lesson sequences.</p></aside>'


def outputs(root):
    result = {}
    for guide in GUIDES:
        name = guide['slug']+'.html'
        content = (root/'templates'/'stock-basics'/name).read_text(encoding='utf-8')
        body = '<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/learn.html">Learning center</a><span>/</span><span aria-current="page">Stock basics</span></div>'
        body += f'<header class="wrap education-heading stock-basics-heading"><span class="kicker">Stock basics · Beginner guide</span><h1>{E(guide["title"])}</h1><div class="article-meta"><a href="/editorial-policy.html" rel="author">DFB Education</a> · Published <time datetime="{guide["published"]}">1 November 2026</time></div></header>'
        next_reading = '<nav class="reading-next" aria-label="Continue learning"><h2>Keep reading</h2>'
        if guide['slug'] == 'stock-classification':
            next_reading += '<p>Next, distinguish <a href="/market-labels.html">tickers, exchanges, indexes, and ETFs</a>. Keep the <a href="/glossary.html#equity-reit">equity REIT definition</a> nearby when you begin the property-income route.</p>'
        else:
            next_reading += '<p>Choose the business you want to study: <a href="/learn.html">REITs</a>, <a href="/learn-bdc.html">BDCs</a>, or <a href="/operating-companies.html">operating companies</a>. For a lending fund, begin with the <a href="/glossary-bdc.html#nii">NII definition</a> rather than assuming earnings equal cash.</p>'
        next_reading += '</nav>'
        body += '<article class="wrap lesson-body stock-basics-article">'+content+next_reading+'</article>'+discovery(exclude_slug=guide['slug'])
        result[root/name] = shell(root,name,guide['title'],guide['description'],body,'Article',article=guide)
    return result
