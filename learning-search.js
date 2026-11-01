/* Static links remain available without JavaScript. No requests or query storage. */
(function (root) {
  'use strict';
  function normalize(value) { return value.toLowerCase().replace(/&/g, ' and ').replace(/[^\p{L}\p{N}]+/gu, ' ').trim(); }
  function matches(text, query) {
    const words = normalize(text).split(/\s+/);
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    if (query.trim() && !tokens.length) return false;
    // Keep multiword topics together: 'market cap' must not match unrelated
    // mentions of a market quote and capital transactions elsewhere in a title.
    return !tokens.length || words.some((_, start) => tokens.every((token, offset) => words[start + offset]?.startsWith(token)));
  }
  if (typeof module === 'object') module.exports = {normalize, matches};
  if (!root.document) return;
  const query = document.getElementById('learning-query');
  if (!query) return;
  const topic = document.getElementById('learning-topic');
  const rows = [...document.querySelectorAll('[data-learning-result]')];
  document.querySelector('[data-learning-controls]').hidden = false;
  function filter() {
    let count = 0;
    rows.forEach(row => {
      row.hidden = !(matches(row.dataset.search, query.value) && (topic.value === 'all' || row.dataset.topic === topic.value));
      if (!row.hidden) count++;
    });
    document.getElementById('learning-count').textContent = count + (count === 1 ? ' page' : ' pages');
    document.getElementById('learning-empty').hidden = count !== 0;
  }
  function restore() {
    const params = new URLSearchParams(location.search);
    query.value = params.get('q') || '';
    topic.value = [...topic.options].some(o => o.value === params.get('room')) ? params.get('room') : 'all';
    filter();
  }
  function change() {
    filter();
    const url = new URL(location.href);
    query.value.trim() ? url.searchParams.set('q', query.value.trim()) : url.searchParams.delete('q');
    topic.value !== 'all' ? url.searchParams.set('room', topic.value) : url.searchParams.delete('room');
    history.replaceState(history.state, '', url);
  }
  query.addEventListener('input', change); topic.addEventListener('change', change);
  document.getElementById('learning-reset').addEventListener('click', () => {
    query.value = ''; topic.value = 'all'; change(); query.focus();
  });
  window.addEventListener('popstate', restore);
  window.addEventListener('pageshow', restore);
  restore();
  if (query.value.trim()) {
    const focus = () => requestAnimationFrame(() => {
      if (![document.body, document.documentElement, query].includes(document.activeElement)) return;
      document.getElementById('search-results').scrollIntoView({block:'start', behavior:'instant'});
      query.focus({preventScroll:true});
    });
    document.readyState === 'complete' ? focus() : window.addEventListener('pageshow', focus, {once:true});
  }
})(typeof window === 'undefined' ? globalThis : window);
