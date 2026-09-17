/* Progressive enhancement only: all research and navigation remain in the HTML. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.getElementById('site-links');
  if (toggle && menu) {
    const setMenu = (open, returnFocus = false) => {
      menu.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.querySelector('span').textContent = open ? '\u2212' : '+';
      if (returnFocus) toggle.focus();
    };
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menu.classList.contains('open')) setMenu(false, true);
    });
    document.addEventListener('click', (e) => {
      if (!menu.contains(e.target) && !toggle.contains(e.target)) setMenu(false);
    });
    menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
    window.matchMedia('(min-width: 781px)').addEventListener('change', () => setMenu(false));
  }
  const input = document.getElementById('research-search');
  const entries = [...document.querySelectorAll('.archive-entry')];
  if (input && entries.length) {
    document.querySelectorAll('[data-enhanced]').forEach(el => { el.hidden = false; });
    const buttons = [...document.querySelectorAll('[data-filter]')];
    let group = 'all';
    const filter = () => {
      const terms = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      let visible = 0;
      entries.forEach(entry => {
        const text = entry.dataset.search;
        const matches = (group === 'all' || entry.dataset.group === group) && terms.every(t => text.includes(t));
        entry.hidden = !matches;
        if (matches) visible += 1;
      });
      document.getElementById('research-count').textContent = `${visible} of ${entries.length} research records`;
      document.getElementById('archive-empty').hidden = visible !== 0;
    };
    input.addEventListener('input', filter);
    buttons.forEach(button => button.addEventListener('click', () => {
      group = button.dataset.filter;
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      filter();
    }));
  }
  // The original Research Desk inquiry form uses a normal HTTPS POST.
  // No form contents are read, logged or submitted by this script.
})();
