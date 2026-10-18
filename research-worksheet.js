/* Local research notes: no network, cookies or persistent storage. */
(function () {
  'use strict';
  const form = document.getElementById('research-worksheet');
  if (!form) return;
  const fields = [...form.querySelectorAll('[data-label]')];
  const status = document.getElementById('worksheet-status');
  const printArea = document.getElementById('worksheet-print');
  function note() {
    return ['DFB dividend research note', 'Educational worksheet — not a recommendation or verification.',
      'Source: https://dividendforensics.com/dividend-research-worksheet.html',
      'Entries are user supplied. Blank fields remain not recorded.', '',
      ...fields.flatMap(field => [field.dataset.label, field.value.trim() || '[Not recorded]', ''])].join('\n');
  }
  function preparePrint() {
    printArea.textContent = note();
  }
  form.querySelector('[data-download-note]').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob(['\ufeff' + note()], {type:'text/plain;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url; link.download = 'dfb-dividend-research-note.txt';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = 'Download prepared. Keep the file before closing this tab; entries are not saved automatically.';
  });
  form.querySelector('[data-print-note]').addEventListener('click', () => { preparePrint(); window.print(); });
  window.addEventListener('beforeprint', preparePrint);
  form.addEventListener('input', preparePrint);
  form.addEventListener('change', preparePrint);
  preparePrint();
  document.documentElement.classList.add('worksheet-ready');
  form.querySelector('.worksheet-actions').hidden = false;
})();
