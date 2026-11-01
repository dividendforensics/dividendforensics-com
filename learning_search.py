"""Build a title/topic directory from actual English learning outputs, not navigation."""
from html.parser import HTMLParser
from education import E, shell, section_head

# Editorial synonyms point only at pages that explain these topics.
TOPICS = {
    'stock-classification': 'market cap market capitalization large cap small cap sectors',
    'market-labels': 'ticker NYSE Nasdaq S&P500 S&P 500 EPS earnings per share ETF exchange index',
    'dividends-buybacks-guide': 'buyback share repurchase free cash flow FCF',
    'operating-cash-flow-guide': 'free cash flow FCF operating cash flow working capital',
}

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(); self.title = ''; self.description = ''; self.in_title = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'meta' and a.get('name') == 'description': self.description = a.get('content', '')
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, text):
        if self.in_title: self.title += text

def records(root, pages):
    from stock_basics import GUIDES
    from operating_companies import PAGES
    from research_resources import RESOURCES
    stock = {g['slug'] for g in GUIDES}
    operating = {p[0] for p in PAGES}
    practical = {r['slug'] for r in RESOURCES}
    result = []
    for path, html in pages.items():
        if path.parent != root: continue
        slug = path.stem
        if slug == 'three-financial-statements': topic = 'Financial-statement basics'
        elif slug in stock: topic = 'Stock basics'
        elif slug.startswith('learn-bdc-') or slug in ('glossary-bdc', 'learn-bdc'): topic = 'BDC'
        elif slug.startswith('learn-') or slug == 'glossary': topic = 'REIT'
        elif slug in operating: topic = 'Operating companies'
        elif slug.startswith('calculator-'): topic = 'Calculators'
        elif slug.startswith('filing-lab-'): topic = 'Historical filing labs'
        elif slug in practical: topic = 'Practical guides'
        else: continue
        meta = Metadata(); meta.feed(html)
        title = meta.title.removesuffix(' · DFB')
        result.append(dict(url='/'+path.name, title=title, description=meta.description, topic=topic,
                           search=' '.join((title, meta.description, TOPICS.get(slug, '')))))
    return sorted(result, key=lambda r: (r['topic'], r['title']))

def output(root, pages):
    items = records(root, pages)
    options = ''.join(f'<option>{E(t)}</option>' for t in sorted({r['topic'] for r in items}))
    cards = ''.join(f'<article class="lesson-card" data-learning-result data-topic="{E(r["topic"])}" data-search="{E(r["search"])}"><span class="kicker">{E(r["topic"])}</span><h3><a href="{r["url"]}">{E(r["title"])}</a></h3><p>{E(r["description"])}</p></article>' for r in items)
    body = section_head('All learning rooms', 'Find a topic.<br><em>Choose the right context.</em>', 'Search English learning-page titles, descriptions and selected topic synonyms. Includes the 36 REIT and 16 BDC lessons, stock and financial-statement basics, operating-company guides, calculators, historical filing labs and practical guides. Not a ticker lookup, live-data service or search of the publication archive.')
    body += '<p class="wrap">Prefer a structured route? <a href="/learn.html#library">Filter the 36 REIT guides by subject and level</a>, <a href="/learn-bdc.html">follow the BDC curriculum</a>, or <a href="/operating-companies.html">follow operating-company cash flow</a>.</p>'
    body += f'''<section class="wrap education-section" id="search-results" aria-labelledby="search-heading"><h2 id="search-heading">Search the learning directory</h2>
<div class="library-filters" data-learning-controls hidden><label for="learning-query">Topic or phrase<input id="learning-query" type="search" placeholder="Ticker, market cap, PIK, free cash flow…" aria-controls="learning-results"></label><label for="learning-topic">Learning room<select id="learning-topic"><option value="all">All learning rooms</option>{options}</select></label><button type="button" id="learning-reset" class="btn btn-s">Clear search and room</button><p id="learning-count" role="status" aria-live="polite">{len(items)} pages</p></div>
<noscript><p>All directory pages are listed below; use the links or your browser’s Find command.</p></noscript>
<div id="learning-empty" hidden><h3>No matching learning pages</h3><p>Try a shorter phrase or select All learning rooms. Words are matched in order. This directory does not search live prices or individual tickers.</p><p><a href="/stock-classification.html">Start with stock classifications</a> · <a href="/market-labels.html">Decode tickers and market labels</a> · <a href="/glossary.html">REIT glossary</a> · <a href="/glossary-bdc.html">BDC glossary</a></p></div>
<div id="learning-results" class="lesson-grid">{cards}</div></section>'''
    return {root/'learning-search.html': shell(root,'learning-search.html','Search the learning directory','Find English REIT, BDC and stock basics guides, operating-company cash-flow explanations, calculators and historical filing practice.',body,'CollectionPage',extra='<script src="/learning-search.js?v=1" defer></script>')}
