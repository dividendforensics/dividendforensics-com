const test = require('node:test');
const assert = require('node:assert/strict');
const {matches} = require('../learning-search.js');
test('title/topic matching normalizes punctuation, not unknown text into a wildcard', () => {
  assert(matches('S&P500 S&P 500 indexes', 's&p500'));
  assert(matches('market capitalization market cap', 'Market cap'));
  assert(matches('payment-in-kind PIK income', 'PIK'));
  assert(!matches('REIT property income', 'PIK'));
  assert(!matches('English learning text', '없는검색어'));
  assert(!matches('English learning text', '<script>alert(1)</script>'));
  assert(matches('Stock basics', ''));
  assert(!matches('Follow the steps', 'EPS'));
  assert(!matches('Any page', '...'));
  assert(matches('Buybacks and tickers', 'buyback'));
  assert(!matches('Market discounts and capital transactions', 'market cap'));
});
test('required queries reach relevant generated pages without navigation-only hits', () => {
  const html=require('node:fs').readFileSync(require('node:path').join(__dirname,'../learning-search.html'),'utf8');
  const decode=s=>s.replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#x27;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
  const records=[...html.matchAll(/data-learning-result data-topic="[^"]*" data-search="([^"]*)"[\s\S]*?<a href="([^"]*)"/g)].map(m=>({text:decode(m[1]),url:m[2]}));
  const expected={'ticker':'market-labels','market cap':'stock-classification','S&P500':'market-labels','buyback':'dividends-buybacks-guide','free cash flow':'dividends-buybacks-guide','EPS':'market-labels','PIK':'learn-bdc-pik-income'};
  assert(records.length>52);
  for(const [query,slug] of Object.entries(expected))assert(records.some(r=>matches(r.text,query)&&r.url===`/${slug}.html`),query);
  assert.deepEqual(records.filter(r=>matches(r.text,'market cap')).map(r=>r.url),['/stock-classification.html']);
  assert.equal(records.filter(r=>matches(r.text,'없는검색어')).length,0);
});
