/* Pure scenario arithmetic shared by the browser UI and node tests. No network or storage. */
(function (root) {
  'use strict';
  function calculate(kind, v) {
    if (Object.values(v).some(x => !Number.isFinite(x))) throw new Error('Enter a finite number in every field.');
    const rate = (v.yield || 0) / 100 * (1 - (v.tax || 0) / 100);
    let metrics = [], columns = [], rows = [], note = '';
    const m = (label, value, format = 'number') => ({ label, value, format });
    switch (kind) {
      case 'income': {
        const gross = v.capital * v.yield / 100, net = v.capital * rate;
        metrics = [m('Annual gross distributions', gross), m('Annual after-withholding income', net), m('Monthly equivalent', net / 12), m('Capital for monthly target', v.target === 0 ? 0 : rate > 0 ? v.target * 12 / rate : null)];
        columns = ['Yield scenario', 'Gross annual', 'After withholding'];
        rows = [0.75, 1, 1.25].map(f => [(v.yield * f).toFixed(2) + '%', gross * f, net * f]);
        note = 'Income scenarios assume unchanged capital. A null target result means the target cannot be funded at zero after-withholding yield. Figures do not include price change.';
        break;
      }
      case 'reinvestment': {
        let balance = v.capital, earned = 0;
        columns = ['Year', 'Total contributed', 'Reinvested income', 'Ending balance'];
        for (let month = 1; month <= v.years * 12; month++) {
          const income = balance * rate / 12;
          earned += income;
          balance += income + v.contribution;
          if (month % 12 === 0) rows.push([String(month / 12), v.capital + v.contribution * month, earned, balance]);
        }
        metrics = [m('Modeled ending balance', balance), m('Total contributed', v.capital + v.contribution * v.years * 12), m('Reinvested income', earned)];
        note = 'Constant yield, monthly reinvestment, contributions at month-end. No price changes or fees are modeled. This is not a forecast.';
        break;
      }
      case 'payout': {
        const stressed = v.affo * (1 - v.decline / 100);
        metrics = [m('Current payout', v.dividend / v.affo * 100, 'percent'), m('Current coverage', v.dividend > 0 ? v.affo / v.dividend : null, 'multiple'), m('Stressed payout', stressed > 0 ? v.dividend / stressed * 100 : null, 'percent'), m('Stressed per-share cushion', stressed - v.dividend)];
        columns = ['Scenario', 'AFFO per share', 'Dividend per share', 'Remaining cushion'];
        rows = [['Base', v.affo, v.dividend, v.affo - v.dividend], ['Selected decline (' + v.decline + '%)', stressed, v.dividend, stressed - v.dividend]];
        note = 'Ratios with a zero denominator are undefined. A negative cushion means the assumed dividend exceeds the selected AFFO measure; it is not a prediction of a cut.';
        break;
      }
      case 'bridge': {
        const ffo = v.net + v.depreciation - v.gains + v.ffoOther, affo = ffo - v.capex - v.rent + v.affoOther;
        metrics = [m('Simplified FFO', ffo), m('Modeled AFFO', affo), m('Net FFO-to-AFFO adjustment', affo - ffo)];
        columns = ['Bridge line', 'Amount'];
        rows = [['Common net income', v.net], ['Real-estate D&A add-back', v.depreciation], ['Qualifying sale gains deduction', -v.gains], ['Other FFO adjustments', v.ffoOther], ['Simplified FFO', ffo], ['Recurring capex deduction', -v.capex], ['Straight-line rent deduction', -v.rent], ['Other AFFO adjustments', v.affoOther], ['Modeled AFFO', affo]];
        note = 'All amounts retain your chosen currency and scale. This teaching bridge does not define any issuer’s AFFO or replace a full Nareit reconciliation.';
        break;
      }
      case 'nav': {
        const property = v.noi / (v.cap / 100), equity = property + v.cash - v.debt;
        metrics = [m('Property value (millions)', property), m('Common equity NAV (millions)', equity), m('NAV per share', equity / v.shares)];
        columns = ['Cap-rate scenario', 'Property value (m)', 'Equity NAV (m)', 'NAV per share'];
        rows = [...new Set([Math.max(0.01, v.cap - 1), v.cap, Math.min(100, v.cap + 1)])].map(cap => {
          const pv = v.noi / (cap / 100), ev = pv + v.cash - v.debt;
          return [cap.toFixed(2) + '%', pv, ev, ev / v.shares];
        });
        note = 'Negative equity values remain visible. Cap-rate scenarios hold NOI and every other assumption constant; they are not appraisals.';
        break;
      }
      case 'refinancing': {
        const oldCost = v.principal * v.old / 100, newCost = v.principal * v.new / 100;
        metrics = [m('Old annual interest (millions)', oldCost), m('New annual interest (millions)', newCost), m('Annual expense change (millions)', newCost - oldCost), m('Expense change per common share', (newCost - oldCost) / v.shares, 'precise')];
        note = 'Positive change means higher expense; negative means savings. Full-year, constant-principal sensitivity before fees, hedges and other effects.';
        break;
      }
      case 'return': {
        const initial = v.start + v.buyFees;
        const price = (v.end - v.start) / initial * 100, income = v.dividends / initial * 100, fees = (v.buyFees + v.sellFees) / initial * 100;
        metrics = [m('Holding-period total return', price + income - fees, 'percent'), m('Price return component', price, 'percent'), m('Cash distribution component', income, 'percent'), m('Fee drag', fees, 'percent')];
        note = 'Holding-period result, not annualized. All components divide by initial cost including purchase fees. No reinvestment or interim purchases. Tax and currency effects are not calculated.';
        break;
      }
      default: throw new Error('Unknown calculator.');
    }
    if (metrics.some(x => x.value !== null && !Number.isFinite(x.value))) throw new Error('These inputs produce a result too large to display. Reduce the assumptions.');
    return { metrics, columns, rows, note };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { calculate };
  if (typeof document === 'undefined') return;
  const format = (x, type = 'number') => x === null ? 'Not defined' : x.toLocaleString('en-US', { minimumFractionDigits: type === 'precise' ? 4 : 2, maximumFractionDigits: type === 'precise' ? 4 : 2 }) + (type === 'percent' ? '%' : type === 'multiple' ? '×' : '');
  function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
  document.querySelectorAll('[data-calculator]').forEach(form => {
    const output = form.closest('.calculator-layout').querySelector('[data-result]'), error = form.querySelector('.calculator-error');
    let current = null;
    function render() {
      error.hidden = true;
      if (!form.checkValidity()) { output.replaceChildren(el('p', 'Correct the highlighted inputs, then calculate again.')); form.reportValidity(); return; }
      try {
        const v = Object.fromEntries([...form.querySelectorAll('input')].map(input => [input.name, input.valueAsNumber]));
        current = calculate(form.dataset.calculator, v);
        output.replaceChildren();
        const dl = el('dl', undefined, 'result-metrics');
        current.metrics.forEach(m => { const group = el('div'); group.append(el('dt', m.label), el('dd', format(m.value, m.format))); dl.append(group); });
        output.append(dl, el('p', current.note, 'result-note'));
        if (current.rows.length) {
          const wrap = el('div', undefined, 'table-scroll'), table = el('table'), head = el('thead'), tr = el('tr');
          wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Scrollable scenario details');
          table.append(el('caption', 'Scenario details')); current.columns.forEach(label => { const th = el('th', label); th.scope = 'col'; tr.append(th); }); head.append(tr); table.append(head);
          const tbody = el('tbody'); current.rows.forEach(row => { const tr = el('tr'); row.forEach(value => tr.append(el('td', typeof value === 'number' ? format(value) : value))); tbody.append(tr); }); table.append(tbody); wrap.append(table); output.append(wrap);
        }
        const download = el('button', 'Download this scenario (CSV)', 'btn btn-s'); download.type = 'button';
        download.addEventListener('click', () => {
          const quote = x => '"' + String(x === null ? 'Not defined' : x).replaceAll('"', '""') + '"';
          const data = [['Educational scenario — not a forecast'], ['Input', 'Value'], ...Object.entries(v), [], ['Result', 'Value'], ...current.metrics.map(m => [m.label, m.value]), [], current.columns, ...current.rows, [], [current.note]];
          const blob = new Blob(['\uFEFF' + data.map(row => row.map(quote).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
          const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'dfb-' + form.dataset.calculator + '-scenario.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        output.append(download);
      } catch (err) { output.replaceChildren(); error.textContent = err.message; error.hidden = false; }
    }
    form.addEventListener('submit', e => { e.preventDefault(); render(); });
    form.addEventListener('reset', () => setTimeout(render, 0));
    form.addEventListener('input', () => { output.replaceChildren(el('p', 'Inputs changed. Select Calculate to update your scenario.')); });
    render();
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
