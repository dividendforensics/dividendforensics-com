/* Pure scenario arithmetic shared by the browser UI and node tests. No network or storage.
 * Input contract: percentage fields use percentage points (5 means 5%, not 0.05).
 * Income/reinvestment use one currency; bridge keeps any consistent currency/scale.
 * NAV/refinancing amounts AND shares are in millions; their quotient is currency/share.
 * Payout and total return use currency/share. Annual inputs must cover matching periods.
 * Reinvestment credits income before each month-end contribution and applies assumed
 * withholding; income applies withholding too. Other tools are pretax sensitivities
 * except that total return may accept user-entered net dividends. Only total return
 * models explicit purchase/sale fees. Reinvestment years are whole years, 1 through 50.
 */
(function (root) {
  'use strict';
  const Decimal = typeof module === 'object' && module.exports ? require('./vendor/decimal.js/decimal.js') : root.Decimal;
  if (!Decimal) {
    if (typeof document !== 'undefined') document.querySelectorAll('[data-calculator]').forEach(form => {
      const output=form.closest('.calculator-layout').querySelector('[data-result]');
      output.textContent='This cached page needs the current calculation library. Reload this page before calculating.';
      form.addEventListener('submit',event=>event.preventDefault());
      form.querySelector('[type=submit]').disabled=true;
    });
    return;
  }
  // Finite 80-significant-digit arithmetic, not unlimited/exact rational arithmetic.
  // Decimal strings remain authoritative through display and CSV serialization.
  const D = Decimal.clone({precision:80,rounding:Decimal.ROUND_HALF_UP});
  const VERSION='original-1.1.2';
  const FIELDS={income:['capital','yield','tax','target'],reinvestment:['capital','contribution','yield','tax','years'],payout:['affo','dividend','decline'],bridge:['net','depreciation','gains','ffoOther','capex','rent','affoOther'],nav:['noi','cap','debt','cash','shares'],refinancing:['principal','old','new','shares'],return:['start','end','dividends','buyFees','sellFees']};
  function decimal(value) {
    if (!['string','number'].includes(typeof value) || String(value).trim()==='' || String(value).length>512) throw Error('Enter a finite number in every field.');
    const raw=String(value).trim(), syntax=raw.match(/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e([+-]?\d+))?$/i);
    if(!syntax || syntax[1] && Math.abs(Number(syntax[1]))>10000) throw Error('Enter a finite decimal number; exponent magnitude cannot exceed 10000.');
    let d;
    try { d=new D(raw); } catch (_) { throw Error('Enter a finite number in every field.'); }
    if(!d.isFinite()) throw Error('Enter a finite number in every field.');
    return d;
  }
  function exported(value) {
    if(!D.isDecimal(value)) return value;
    if(value.isZero()) return 0;
    const n=value.toNumber();
    if(!Number.isFinite(n)) throw Error('These inputs produce a result too large to display. Reduce the assumptions.');
    // Preserve real values below the Number range; never flatten them to zero.
    return n===0 ? value.toString() : n;
  }
  function calculate(kind, input) {
    if(!FIELDS[kind]) throw Error('Unknown calculator.');
    const v=Object.fromEntries(FIELDS[kind].map(key=>[key,decimal(input[key])]));
    if (['nav', 'refinancing'].includes(kind) && !v.shares.gt(0)) throw new Error('Common shares must be greater than zero.');
    if (kind === 'nav' && !v.cap.gt(0)) throw new Error('Capitalization rate must be greater than zero.');
    if (kind === 'return' && !v.start.gt(0)) throw new Error('Purchase price must be greater than zero.');
    if (kind === 'return' && (v.buyFees.lt(0) || v.sellFees.lt(0))) throw new Error('Fees cannot be negative.');
    if (kind === 'payout' && (v.dividend.lt(0) || v.decline.lt(0) || v.decline.gt(100))) throw new Error('Use a nonnegative dividend and an AFFO decline from 0 to 100%.');
    if (kind === 'reinvestment' && (!v.years.isInteger() || v.years.lt(1) || v.years.gt(50))) throw new Error('Enter a whole number of years from 1 to 50.');
    const rate = (v.yield || new D(0)).div(100).times(new D(1).minus((v.tax || new D(0)).div(100)));
    let metrics = [], columns = [], rows = [], note = '';
    const m = (label, value, format = 'number') => ({ label, value, format });
    switch (kind) {
      case 'income': {
        const gross = v.capital.times(v.yield).div(100), net = v.capital.times(rate);
        metrics = [m('Annual gross distributions', gross), m('Annual after-withholding income', net), m('Monthly equivalent', net.div(12)), m('Capital for monthly target', v.target.isZero() ? new D(0) : rate.gt(0) ? v.target.times(12).div(rate) : null)];
        columns = ['Yield scenario', 'Gross annual', 'After withholding'];
        rows = ['0.75','1','1.25'].map(f => [v.yield.times(f).toFixed(2) + '%', gross.times(f), net.times(f)]);
        note = 'Income scenarios assume unchanged capital. A target result shown as Not defined means a positive target cannot be funded at zero after-withholding yield. Figures do not include price change.';
        break;
      }
      case 'reinvestment': {
        let balance = v.capital, earned = new D(0);
        columns = ['Year', 'Total contributed', 'Reinvested income', 'Ending balance'];
        for (let month = 1; month <= v.years.toNumber() * 12; month++) {
          const income = balance.times(rate).div(12);
          earned = earned.plus(income);
          balance = balance.plus(income).plus(v.contribution);
          if (month % 12 === 0) rows.push([String(month / 12), v.capital.plus(v.contribution.times(month)), earned, balance]);
        }
        metrics = [m('Modeled ending balance', balance), m('Total contributed', v.capital.plus(v.contribution.times(v.years).times(12))), m('Reinvested income', earned)];
        note = 'Constant yield, monthly reinvestment, contributions at month-end. No price changes or fees are modeled. This is not a forecast.';
        break;
      }
      case 'payout': {
        const stressed = v.affo.minus(v.affo.abs().times(v.decline).div(100));
        metrics = [m('Current payout', v.affo.gt(0) ? v.dividend.div(v.affo).times(100) : null, 'percent'), m('Current coverage', v.affo.gt(0) && v.dividend.gt(0) ? v.affo.div(v.dividend) : null, 'multiple'), m('Stressed payout', stressed.gt(0) ? v.dividend.div(stressed).times(100) : null, 'percent'), m('Stressed per-share cushion', stressed.minus(v.dividend))];
        columns = ['Scenario', 'AFFO per share', 'Dividend per share', 'Remaining cushion'];
        rows = [['Base', v.affo, v.dividend, v.affo.minus(v.dividend)], ['Selected decline (' + v.decline.toString() + '%)', stressed, v.dividend, stressed.minus(v.dividend)]];
        note = 'Payout and coverage are not meaningful with zero or negative AFFO and are shown as Not defined. Coverage is undefined at zero dividends. The downside scenario subtracts the selected percentage of the absolute AFFO amount, so a negative AFFO becomes more negative; zero stays zero. Cash cushions remain visible and do not predict a cut.';
        break;
      }
      case 'bridge': {
        const ffo = v.net.plus(v.depreciation).minus(v.gains).plus(v.ffoOther), affo = ffo.minus(v.capex).minus(v.rent).plus(v.affoOther);
        metrics = [m('Simplified FFO', ffo, 'bridge'), m('Modeled AFFO', affo, 'bridge'), m('Net FFO-to-AFFO adjustment', affo.minus(ffo), 'bridge')];
        columns = ['Bridge line', 'Amount'];
        rows = [['Common net income', v.net], ['Real-estate D&A add-back', v.depreciation], ['Qualifying sale gains deduction', v.gains.negated()], ['Other FFO adjustments', v.ffoOther], ['Simplified FFO', ffo], ['Recurring capex deduction', v.capex.negated()], ['Straight-line rent deduction', v.rent.negated()], ['Other AFFO adjustments', v.affoOther], ['Modeled AFFO', affo]];
        note = 'All amounts retain your chosen currency and scale. Bridge lines and metrics display up to the model’s 80 significant digits, without cent rounding. An approximation sign marks any longer input shortened for display; CSV retains the stored decimal strings. Bold FFO and AFFO rows are subtotals, not additional adjustments. This teaching bridge does not define any issuer’s AFFO or replace a full Nareit reconciliation.';
        break;
      }
      case 'nav': {
        const property = v.noi.div(v.cap.div(100)), equity = property.plus(v.cash).minus(v.debt);
        metrics = [m('Property value (millions)', property), m('Common equity NAV (millions)', equity), m('NAV per share', equity.div(v.shares))];
        columns = ['Cap-rate scenario', 'Property value (m)', 'Equity NAV (m)', 'NAV per share'];
        const scenarios=[D.max('0.01',v.cap.minus(1)),v.cap,D.min(100,v.cap.plus(1))];
        rows = [...new Map(scenarios.map(cap=>[cap.toString(),cap])).values()].map(cap => {
          const pv = v.noi.div(cap.div(100)), ev = pv.plus(v.cash).minus(v.debt);
          return [cap.toFixed(2) + '%', pv, ev, ev.div(v.shares)];
        });
        note = 'Negative equity values remain visible. Cap-rate scenarios hold NOI and every other assumption constant; they are not appraisals.';
        break;
      }
      case 'refinancing': {
        const oldCost = v.principal.times(v.old).div(100), newCost = v.principal.times(v.new).div(100), change = newCost.minus(oldCost);
        metrics = [m('Old annual interest (millions)', oldCost), m('New annual interest (millions)', newCost), m('Annual expense change (millions)', change), m('Expense change per common share', change.div(v.shares), 'precise')];
        note = 'Positive change means higher expense; negative means savings. Full-year, constant-principal sensitivity before fees, hedges and other effects.';
        break;
      }
      case 'return': {
        const initial = v.start.plus(v.buyFees);
        const price = v.end.minus(v.start).div(initial).times(100), income = v.dividends.div(initial).times(100), fees = v.buyFees.plus(v.sellFees).div(initial).times(100);
        // Calculate the return from its decimal cash numerator, not rounded components.
        const total=v.end.minus(v.start).plus(v.dividends).minus(v.buyFees).minus(v.sellFees).div(initial).times(100);
        metrics = [m('Holding-period total return', total, 'percent'), m('Price return component', price, 'percent'), m('Cash distribution component', income, 'percent'), m('Fee drag', fees, 'percent')];
        note = 'Holding-period result, not annualized. All components divide by initial cost including purchase fees. No reinvestment or interim purchases. Tax and currency effects are not calculated.';
        break;
      }
    }
    const exact=value=>D.isDecimal(value) ? value.toString() : value;
    return {
      // value/rows retain the old approximate Number API. Display/export consumers
      // must use exactValue/exactRows instead of converting these approximations back.
      metrics:metrics.map(m=>({...m,value:exported(m.value),exactValue:exact(m.value)})),
      columns,rows:rows.map(row=>row.map(exported)),exactRows:rows.map(row=>row.map(exact)),
      numericCells:rows.map(row=>row.map(value=>D.isDecimal(value))),
      note:note+' '+(kind==='bridge' ? 'Scientific notation limits very long decimal displays.' : 'Display rounds half up to two decimal places (four for per-share refinancing changes). Values smaller than the display step retain four significant digits instead of rounding to zero. Plain decimals are used through 24 fractional places; longer tiny values use scientific notation. CSV retains the stored decimal strings.'),formulaVersion:VERSION,
      arithmetic:{precision:80,rounding:'ROUND_HALF_UP',authoritativeFields:['metrics[].exactValue','exactRows']}
    };
  }
  function format(x, type = 'number') {
    if (x === null) return 'Not defined';
    const d=decimal(x), digits = type === 'precise' ? 4 : 2;
    if(type==='bridge') {
      const display=d.toSignificantDigits(80);
      const text=display.decimalPlaces()>24 ? display.toExponential() : display.toFixed(Math.max(2,display.decimalPlaces()));
      const [whole,fraction]=text.split('.');
      return (display.eq(d)?'':'≈ ')+(text.includes('e')?text:whole.replace(/\B(?=(\d{3})+(?!\d))/g,',')+'.'+fraction);
    }
    const small=!d.isZero() && d.abs().lt(new D(10).pow(-digits));
    let shown;
    if(small) {const display=d.toSignificantDigits(4);shown=display.decimalPlaces()>24 ? display.toExponential() : display.toFixed();}
    // Group only the integer part; the decimal fraction must stay untouched.
    if(!small){const [whole,fraction]=d.toFixed(digits).split('.');shown=whole.replace(/\B(?=(\d{3})+(?!\d))/g,',')+'.'+fraction;}
    return shown + (type === 'percent' ? '%' : type === 'multiple' ? '×' : '');
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { calculate, format };
  else root.DFBOriginal = { calculate, format };
  if (typeof document === 'undefined') return;
  function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
  document.querySelectorAll('[data-calculator]').forEach(form => {
    const output = form.closest('.calculator-layout').querySelector('[data-result]'), error = form.querySelector('.calculator-error');
    let current = null;
    function render() {
      error.hidden = true;
      if (!form.checkValidity()) { output.replaceChildren(el('p', 'Correct the highlighted inputs, then calculate again.')); form.reportValidity(); return; }
      try {
        const v = Object.fromEntries([...form.querySelectorAll('input')].map(input => [input.name, input.value]));
        current = calculate(form.dataset.calculator, v);
        output.replaceChildren();
        const dl = el('dl', undefined, 'result-metrics');
        current.metrics.forEach(m => { const group = el('div'); group.append(el('dt', m.label), el('dd', format(m.exactValue, m.format))); dl.append(group); });
        output.append(dl, el('p', current.note, 'result-note'));
        if (current.rows.length) {
          const wrap = el('div', undefined, 'table-scroll'), table = el('table'), head = el('thead'), tr = el('tr');
          wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Scrollable scenario details');
          const bridge=form.dataset.calculator==='bridge';
          if(bridge)wrap.style.maxHeight='none';
          table.append(el('caption', bridge ? 'FFO-to-AFFO reconciliation · bold rows are subtotals' : 'Scenario details')); current.columns.forEach(label => { const th = el('th', label); th.scope = 'col'; tr.append(th); }); head.append(tr); table.append(head);
          const tbody = el('tbody'); current.exactRows.forEach((row,i) => {
            const tr = el('tr'),subtotal=bridge && (i===4 || i===8);
            if(subtotal)tr.setAttribute('data-bridge-subtotal','');
            row.forEach((value,j) => {
              const text=current.numericCells[i][j] ? format(value,bridge?'bridge':'number') : value;
              const cell=el(j===0?'th':'td');if(j===0)cell.scope='row';
              if(subtotal)cell.append(el('strong',text));else cell.textContent=text;
              tr.append(cell);
            });tbody.append(tr);
          }); table.append(tbody); wrap.append(table); output.append(wrap);
        }
        const download = el('button', 'Download this scenario (CSV)', 'btn btn-s'); download.type = 'button';
        download.addEventListener('click', () => {
          const quote = x => '"' + String(x === null ? 'Not defined' : x).replaceAll('"', '""') + '"';
          const data = [['Educational scenario — not a forecast'], ['Input', 'Value'], ...Object.entries(v), [], ['Result', 'Value'], ...current.metrics.map(m => [m.label, m.exactValue]), [], current.columns, ...current.exactRows, [], [current.note]];
          const blob = new Blob(['\uFEFF' + data.map(row => row.map(quote).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
          const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'dfb-' + form.dataset.calculator + '-scenario.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        output.append(download);
      } catch (err) { output.replaceChildren(); error.textContent = err.message; error.hidden = false; }
    }
    form.addEventListener('submit', e => { e.preventDefault(); render(); });
    form.addEventListener('reset', () => setTimeout(render, 0));
    form.addEventListener('input', () => { output.replaceChildren(el('p', 'Inputs changed. Select Calculate to update your scenario.')); });
    form.querySelector("[data-calculator-controls]").disabled=false;
    render();
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
