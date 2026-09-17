#!/usr/bin/env python3
"""Offline integrity checks for the generated DFB site. No external requests."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from collections import Counter
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True)
        self.links=[];self.ids=[];self.tags=Counter();self.forms=[];self.fields=[];self.scripts=[]
        self.feed(text)
    def handle_starttag(self,tag,attributes):
        a=dict(attributes);self.tags[tag]+=1
        if 'id' in a:self.ids.append(a['id'])
        for attr in ('href','src'):
            if a.get(attr):self.links.append((tag,attr,a[attr]))
        if tag=='form':self.forms.append(a)
        if tag in ('input','textarea','select'):self.fields.append(a)
        if tag=='script':self.scripts.append(a)

def check(root=ROOT):
    errors=[];pages={p.name:Page(p.read_text(encoding='utf-8')) for p in root.glob('*.html')}
    active=[]
    for name,parsed in pages.items():
        text=(root/name).read_text()
        if 'name="dfb-design"' not in text:continue
        active.append(name)
        if parsed.tags['main']!=1 or parsed.tags['h1']!=1:errors.append(f'{name}: expected one main and one h1')
        for ident,n in Counter(parsed.ids).items():
            if n>1:errors.append(f'{name}: duplicate id {ident}')
        if 'SITE:HEADER' not in text or 'SITE:FOOTER' not in text:errors.append(f'{name}: missing shell markers')
        if '{{' in text:errors.append(f'{name}: unrendered template token')
        for tag,attr,url in parsed.links:
            u=urlsplit(url)
            if u.scheme in ('mailto','tel','data'):continue
            if u.scheme or u.netloc:
                if u.scheme not in ('http','https'):errors.append(f'{name}: invalid URL scheme {url}')
                continue
            if u.path and not u.path.startswith('/'):
                errors.append(f'{name}: relative asset/navigation path {url}')
            target=(root/unquote(u.path.lstrip('/'))) if u.path else root/name
            if target.is_dir():target=target/'index.html'
            if not target.exists():errors.append(f'{name}: missing target {url}');continue
            if u.fragment and target.suffix=='.html':
                dest=pages.get(target.name)
                if dest and unquote(u.fragment) not in dest.ids:errors.append(f'{name}: missing anchor {url}')
        if 'contributor.benzinga.com' in text:errors.append(f'{name}: private contributor URL must not be public')
    error=(root/'404.html').read_text()
    if 'noindex,follow' not in error:errors.append('404: missing noindex')
    desk=pages['research-desk.html']
    expected='https://formsubmit.co/ba46f1f257eba5688fcf0b5122a8b335'
    if len(desk.forms)!=1 or desk.forms[0].get('action')!=expected or desk.forms[0].get('method','').upper()!='POST':errors.append('Research Desk: inquiry endpoint changed')
    for field in ('Name','Organization','Email','Inquiry type','Message'):
        if not any(f.get('name')==field and 'required' in f for f in desk.fields):errors.append(f'Research Desk: required field {field} missing')
    if (root/'CNAME').read_text().strip()!='dividendforensics.com':errors.append('CNAME changed')
    if (root/'google5e69369cc3191f61.html').read_text().strip()!='google-site-verification: google5e69369cc3191f61.html':errors.append('Google verification changed')
    if errors:
        for err in errors:print('FAIL',err)
        return 1
    print(f'PASS: {len(active)} active pages; local links, assets, anchors, form, canonical domain and verification file.')
    return 0
if __name__=='__main__':sys.exit(check())
