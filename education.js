/* Progressive enhancement: every lesson and definition exists in the HTML. */
(() => {
  const search = document.getElementById('lesson-search');
  if (search) {
    const category = document.getElementById('lesson-category'), level = document.getElementById('lesson-level'), lessons = [...document.querySelectorAll('[data-lesson]')];
    document.querySelector('[data-library-controls]').hidden = false;
    search.value = new URLSearchParams(window.location.search).get('q') || '';
    function filter() {
      const query = search.value.trim().toLowerCase(); let count = 0;
      lessons.forEach(item => { const visible = item.dataset.search.includes(query) && (category.value === 'all' || item.dataset.category === category.value) && (level.value === 'all' || item.dataset.level === level.value); item.hidden = !visible; count += visible ? 1 : 0; });
      document.getElementById('lesson-count').textContent = count + (count === 1 ? ' guide' : ' guides');
      document.getElementById('lesson-empty').hidden = count !== 0;
    }
    search.addEventListener('input', filter); category.addEventListener('change', filter); level.addEventListener('change', filter);
    document.getElementById('lesson-reset').addEventListener('click', () => { search.value = ''; category.value = 'all'; level.value = 'all'; filter(); search.focus(); });
    filter();
    // A submitted query should arrive at the answers, not the page introduction.
    // Do not move focus for ordinary visits or subsequent typing/filtering.
    if (search.value.trim()) {
      // Fragment navigation runs after deferred scripts and can reset focus.
      // Hand focus to the results only after navigation's pageshow lifecycle,
      // on the next rendering frame; never refocus during later filter input.
      const focusResults = () => window.requestAnimationFrame(() => {
        const library = document.getElementById('library');
        const active = document.activeElement;
        // Preserve an explicit focus choice made while the page was loading.
        if (active && ![document.body, document.documentElement, library, search].includes(active)) return;
        library?.scrollIntoView({block: 'start'});
        search.focus({preventScroll: true});
      });
      if (document.readyState === 'complete') focusResults();
      else window.addEventListener('pageshow', focusResults, {once: true});
    }
  }
  const glossary = document.getElementById('glossary-search');
  if (glossary) {
    document.querySelector('[data-glossary-control]').hidden = false;
    glossary.addEventListener('input', () => {
      let count = 0; const query = glossary.value.trim().toLowerCase();
      document.querySelectorAll('[data-term]').forEach(item => { item.hidden = !item.dataset.search.includes(query); if (!item.hidden) count++; });
      document.getElementById('glossary-count').textContent = count + (count === 1 ? ' term' : ' terms');
      document.getElementById('glossary-empty').hidden = count !== 0;
    });
  }
  document.querySelectorAll('[data-quiz]').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault(); if (!form.reportValidity()) return;
      let score = 0; const questions = [...form.querySelectorAll('fieldset')];
      questions.forEach(question => {
        const choice = question.querySelector('input:checked');
        const correct = choice && choice.value === question.dataset.answer;
        if (correct) score++;
        const feedback = question.querySelector('.quiz-feedback');
        feedback.textContent = (correct ? 'Correct. ' : 'Review this one. ') + feedback.dataset.explanation;
        feedback.hidden = false;
      });
      form.querySelector('.quiz-score').textContent = score + ' of ' + questions.length + ' correct. Read the explanations before moving on.';
    });
    form.addEventListener('change', () => {
      form.querySelector('.quiz-score').textContent = 'Answers changed. Check again to update the result.';
      form.querySelectorAll('.quiz-feedback').forEach(item => { item.hidden = true; });
    });
  });
})();
