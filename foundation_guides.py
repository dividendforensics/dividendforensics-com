"""Reviewed prerequisite articles, distinct from specialized lesson counts."""
from education import E, shell
GUIDE = dict(slug='three-financial-statements', title='How the three financial statements connect',
             description='Connect profit, operating cash flow and the cash balance with a clearly hypothetical annual example; distinguish financing from free cash flow.',
             published='2026-11-01', updated='2026-11-01')

def outputs(root):
    name=GUIDE['slug']+'.html'
    content=(root/'templates/foundations'/name).read_text(encoding='utf-8')
    body='<div class="wrap breadcrumbs"><a href="/">Home</a><span>/</span><a href="/learning-search.html">Learning directory</a><span>/</span><span aria-current="page">Financial-statement basics</span></div>'
    body+=f'<header class="wrap education-heading stock-basics-heading"><span class="kicker">Financial-statement basics · Beginner guide</span><h1>{E(GUIDE["title"])}</h1><div class="article-meta"><a href="/editorial-policy.html" rel="author">DFB Education</a> · Published <time datetime="2026-11-01">1 November 2026</time></div></header>'
    body+='<article class="wrap lesson-body stock-basics-article">'+content+'</article>'
    return {root/name:shell(root,name,GUIDE['title'],GUIDE['description'],body,'Article',article=GUIDE)}
