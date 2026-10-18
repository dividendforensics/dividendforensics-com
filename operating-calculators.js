/* DFB operating cash-flow workbench. No remote requests or browser persistence. */
(function (root) {
'use strict';
const Base = typeof module === 'object' && module.exports ? require('./vendor/decimal.js/decimal.js') : root.Decimal;
if (!Base) return;
const D = Base.clone({precision:80, rounding:Base.ROUND_HALF_UP});
const VERSION = 'operating-1.0.0';
const LABELS = Object.freeze({scenarioLabel:'Scenario / source label',fiscalYear:'Fiscal year',cashDefinition:'Cash balance definition',netIncome:'Net income',noncash:'Signed noncash and other reconciliation adjustments',workingCapital:'Signed working-capital / other operating changes',reportedOCF:'Reported operating cash flow',capex:'Cash PP&E purchases',dividends:'Cash dividends paid',buybacks:'Cash share repurchases',beginningCash:'Beginning cash',netInvesting:'Signed net investing cash flow',netFinancing:'Signed net financing cash flow',fx:'Signed currency / other cash reconciliation effect',endingCash:'Reported ending cash'});
const METRICS = Object.freeze({operatingCashFlow:'Reconstructed operating cash flow',reportedOCF:'Reported operating cash flow',operatingGap:'OCF gap: reconstructed less reported',freeCashFlow:'User-defined FCF: reconstructed OCF less cash PP&E purchases',shareholderCash:'Cash dividends plus cash share repurchases',residual:'Residual after entered shareholder cash payments',cashChange:'Net change in cash from reported categories',computedEndingCash:'Calculated ending cash',endingCash:'Reported ending cash',cashGap:'Cash gap: calculated less reported ending cash'});
const DEFAULT = Object.freeze({scenarioLabel:'Synthetic manufacturer · annual exercise',fiscalYear:'2024',cashDefinition:'Cash and cash equivalents; no restricted cash in this synthetic example',netIncome:'120',noncash:'40',workingCapital:'-25',reportedOCF:'135',capex:'55',dividends:'30',buybacks:'65',beginningCash:'100',netInvesting:'-45',netFinancing:'-85',fx:'-2',endingCash:'103'});
function invalid(message, field) {const error=new Error(message);error.field=field;throw error;}
function numeric(v, key, nonnegative=false, optional=false) {
  const raw = v === undefined || v === null ? '' : String(v).trim();
  if (!raw && optional) return null;
  if (!/^[-+]?(?:\d{1,30}(?:\.\d{0,16})?|\.\d{1,16})$/.test(raw)) invalid(LABELS[key]+': enter a plain decimal (up to 30 integer and 16 fractional digits), without commas or exponent notation. Blank is unknown.',key);
  const d = new D(raw);
  if (!d.isFinite() || (nonnegative && d.lt(0))) invalid(LABELS[key]+': enter zero or a positive cash amount'+(['beginningCash','endingCash'].includes(key)?'.':'; the workbench subtracts this payment.'),key);
  return d;
}
const exact = d => d === null ? null : d.isZero() ? '0' : d.toFixed();
function textValue(v,key) {
  const s = String(v === undefined || v === null ? '' : v).trim();
  if (!s || s.length > 240 || /[\u0000-\u001f\u007f]/.test(s)) invalid(LABELS[key]+': enter 1–240 characters on one line.',key);
  return s;
}
function provenance(values) {
  const p=values.provenance || {};
  const sourceNotes=String(p.sourceNotes || 'Unreviewed user-supplied inputs; no source notes supplied.').trim();
  const status=String(p.status || 'User scenario; source values have not been independently verified.').trim();
  if (sourceNotes.length>2400 || status.length>240 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(sourceNotes+status)) throw new Error('Source notes are too long or contain unsupported control characters.');
  return {sourceNotes,status};
}
function calculate(values) {
  if (!values || typeof values !== 'object') throw new Error('Enter a complete annual scenario.');
  const v = {}, numbers = {};
  v.scenarioLabel = textValue(values.scenarioLabel,'scenarioLabel');
  v.cashDefinition = textValue(values.cashDefinition,'cashDefinition');
  v.fiscalYear = String(values.fiscalYear || '').trim();
  if (!/^\d{4}$/.test(v.fiscalYear) || Number(v.fiscalYear) < 1900 || Number(v.fiscalYear) > 2200) invalid('Fiscal year: enter a four-digit year from 1900 to 2200.','fiscalYear');
  const cashKeys = ['beginningCash','netInvesting','netFinancing','fx','endingCash'];
  const hasCash = cashKeys.some(k => values[k] !== undefined && values[k] !== null && String(values[k]).trim() !== '');
  for (const key of ['netIncome','noncash','workingCapital','reportedOCF','capex','dividends','buybacks',...cashKeys]) {
    const optional = key === 'reportedOCF' || (cashKeys.includes(key) && !hasCash);
    numbers[key] = numeric(values[key],key,['capex','dividends','buybacks','beginningCash','endingCash'].includes(key),optional);
    v[key] = exact(numbers[key]);
  }
  const n = numbers;
  const operating = n.netIncome.plus(n.noncash).plus(n.workingCapital);
  const fcf = operating.minus(n.capex), payments = n.dividends.plus(n.buybacks), residual = fcf.minus(payments);
  const operatingGap = n.reportedOCF === null ? null : operating.minus(n.reportedOCF);
  const cashChange = hasCash && n.reportedOCF !== null ? n.reportedOCF.plus(n.netInvesting).plus(n.netFinancing).plus(n.fx) : null;
  const ending = cashChange === null ? null : n.beginningCash.plus(cashChange);
  const cashGap = ending === null ? null : ending.minus(n.endingCash);
  const metrics = Object.fromEntries(Object.entries({operatingCashFlow:operating,reportedOCF:n.reportedOCF,operatingGap,freeCashFlow:fcf,shareholderCash:payments,residual,cashChange,computedEndingCash:ending,endingCash:n.endingCash,cashGap}).map(([k,d])=>[k,exact(d)]));
  const warnings = [];
  if (operatingGap === null) warnings.push('Reported OCF is missing: the earnings bridge is unchecked and the cash balance bridge is unavailable.');
  else if (!operatingGap.isZero()) warnings.push('The operating bridge does not reconcile. FCF and the residual are scenarios based on entered components; resolve missing rows, signs, scope and source rounding before interpreting them.');
  if (cashGap !== null && !cashGap.isZero()) warnings.push('The cash balance bridge does not reconcile. Check the cash definition, period, currency effects and all reported category totals.');
  if (!hasCash) warnings.push('Cash balance inputs are omitted: no ending-cash reconciliation was calculated.');
  if (operating.lte(0)) warnings.push('Reconstructed OCF is zero or negative. Preserve the sign; a payout ratio would not describe positive cash coverage.');
  if (fcf.lte(0)) warnings.push('User-defined FCF is zero or negative. This worksheet does not divide by that amount or assign a coverage rating.');
  if (residual.lt(0)) warnings.push('The entered dividends and repurchases exceed this FCF definition. The shortfall is arithmetic, not proof of which funding source paid for distributions.');
  else warnings.push('A nonnegative residual does not establish distributable cash: debt service, acquisitions and other obligations may remain.');
  warnings.push('Annual USD million amounts only. FCF is the stated worksheet definition, not a standardized GAAP measure. Matching totals check arithmetic, not source accuracy or future sustainability.');
  const steps = [
    {label:'Net income',amount:exact(n.netIncome),total:exact(n.netIncome),kind:'start'},
    {label:'Noncash / other adjustments',amount:exact(n.noncash),total:exact(n.netIncome.plus(n.noncash)),kind:'change'},
    {label:'Working-capital / other changes',amount:exact(n.workingCapital),total:exact(operating),kind:'change'},
    {label:'Reconstructed OCF',amount:exact(operating),total:exact(operating),kind:'subtotal'},
    {label:'Cash PP&E purchases',amount:exact(n.capex.neg()),total:exact(fcf),kind:'change'},
    {label:'User-defined FCF',amount:exact(fcf),total:exact(fcf),kind:'subtotal'},
    {label:'Cash dividends paid',amount:exact(n.dividends.neg()),total:exact(fcf.minus(n.dividends)),kind:'change'},
    {label:'Cash share repurchases',amount:exact(n.buybacks.neg()),total:exact(residual),kind:'change'},
    {label:'Residual',amount:exact(residual),total:exact(residual),kind:'subtotal'}
  ];
  return {formulaVersion:VERSION,units:'USD million',period:'Annual fiscal year '+v.fiscalYear,provenance:provenance(values),inputs:v,metrics,steps,warnings};
}
function csvCell(value) {
  let s = value === null || value === undefined ? '' : String(value);
  if (/^[\s]*[=+@-]/.test(s) && !/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(s)) s = "'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
}
function compare(current, baseline) {
  return Object.fromEntries(Object.keys(METRICS).map(key=>[key,{baseline:baseline.metrics[key],current:current.metrics[key],delta:baseline.metrics[key]===null||current.metrics[key]===null?null:exact(new D(current.metrics[key]).minus(baseline.metrics[key]))}]));
}
function csv(result, baseline=null) {
  const rows = [['DFB operating cash-flow workbench',result.formulaVersion],['Units',result.units],['Period',result.period],['Status',result.provenance.status],['Source notes / input conventions',result.provenance.sourceNotes],['Verification scope','Arithmetic checks are not source verification'],['FCF definition','Reconstructed OCF minus cash PP&E purchases'],['Section','Measure','Exact decimal value']];
  Object.entries(result.inputs).forEach(([k,v])=>rows.push(['Input',LABELS[k],v]));
  Object.entries(result.metrics).forEach(([k,v])=>rows.push(['Result',METRICS[k],v]));
  rows.push(['Bridge','Step','Signed amount / subtotal','Running total']);
  result.steps.forEach(s=>rows.push(['Bridge',s.label,s.amount,s.total]));
  result.warnings.forEach(w=>rows.push(['Interpretation',w]));
  if (baseline) {
    rows.push(['Baseline context',baseline.inputs.scenarioLabel,baseline.period,baseline.units]);
    rows.push(['Baseline status',baseline.provenance.status],['Baseline source notes / input conventions',baseline.provenance.sourceNotes]);
    Object.entries(baseline.inputs).forEach(([k,v])=>rows.push(['Baseline input',LABELS[k],v]));
    rows.push(['Comparison','Measure','Baseline','Current','Current minus baseline']);
    Object.entries(compare(result,baseline)).forEach(([k,v])=>rows.push(['Comparison',METRICS[k],v.baseline,v.current,v.delta]));
  }
  return rows.map(r=>r.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
const esc = s => String(s === null ? 'Not calculated' : s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function chart(result) {
  let minimum = new D(0), maximum = new D(0);
  for (const s of result.steps) {minimum=D.min(minimum,s.total);maximum=D.max(maximum,s.total);}
  const span=maximum.minus(minimum), scale=span.isZero()?new D(1):span;
  const position=value=>new D(value).minus(minimum).div(scale).times(100).toFixed(4);
  let previous=new D(0);
  return '<ol class="ocf-chart" aria-label="Earnings to cash: proportional bars, exact amounts in the table below">'+result.steps.map(s=>{
    const end=new D(s.total), start=s.kind==='change'?previous:new D(0), left=D.min(start,end), width=end.minus(start).abs().div(scale).times(100).toFixed(4);
    previous=end;
    return '<li class="ocf-chart-row"><span>'+esc(s.label)+'</span><span class="ocf-chart-track" aria-hidden="true"><i class="ocf-chart-zero" style="left:'+position(0)+'%"></i><i class="ocf-chart-bar '+(s.kind==='change'?'ocf-change':'ocf-total')+'" style="left:'+position(left)+'%;width:'+width+'%"></i></span><strong>'+esc(s.amount)+'</strong></li>';
  }).join('')+'</ol>';
}
function render(result) {
  const m=result.metrics;
  const check=(gap,label)=>'<p class="ocf-check"><strong>'+label+': </strong>'+ (gap===null?'Not checked — source input missing.':gap==='0'?'Matches entered totals (gap 0).':'Unreconciled: gap '+esc(gap)+' USD million.')+'</p>';
  return '<p class="small-note">'+esc(result.inputs.scenarioLabel)+' · '+esc(result.period)+' · USD million</p><p class="small-note"><strong>'+esc(result.provenance.status)+'</strong> '+esc(result.provenance.sourceNotes)+'</p>'+check(m.operatingGap,'Operating reconciliation')+check(m.cashGap,'Cash balance reconciliation')+
    '<h3>Earnings → operating cash → shareholder cash</h3>'+chart(result)+
    '<div class="ocf-table-scroll" tabindex="0" role="region" aria-label="Exact cash-flow bridge table"><table class="ocf-table"><caption>Exact bridge values · USD million. Subtotals are checkpoints, not additional changes.</caption><thead><tr><th scope="col">Step</th><th scope="col">Signed change / subtotal</th><th scope="col">Running total</th></tr></thead><tbody>'+result.steps.map(s=>'<tr><th scope="row">'+esc(s.label)+(s.kind==='subtotal'?' (subtotal)':'')+'</th><td>'+esc(s.amount)+'</td><td>'+esc(s.total)+'</td></tr>').join('')+'</tbody></table></div>'+
    '<h3>Cash balance bridge</h3><p>Beginning cash + reported OCF + net investing + net financing + currency / other reconciliation effect. PP&E purchases, dividends and repurchases are already inside the reported category totals; do not subtract them again.</p><p class="small-note">Cash definition: '+esc(result.inputs.cashDefinition)+'</p>'+ (m.computedEndingCash===null?'<p>Not calculated: enter reported OCF and all five cash balance fields.</p>':'<p class="ocf-equation">'+['beginningCash','reportedOCF','netInvesting','netFinancing','fx'].map(k=>'('+esc(result.inputs[k])+')').join(' + ')+' = <strong>'+esc(m.computedEndingCash)+'</strong></p><p>Reported ending cash: <strong>'+esc(m.endingCash)+'</strong>. Calculated less reported: <strong>'+esc(m.cashGap)+'</strong>.</p>')+
    '<details><summary>All exact calculated values</summary><dl class="ocf-metrics">'+Object.entries(m).map(([k,v])=>'<div><dt>'+esc(METRICS[k])+'</dt><dd>'+esc(v)+'</dd></div>').join('')+'</dl></details><h3>Read before interpreting</h3><ul>'+result.warnings.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul><p class="small-note">Decimal precision 80; accepted input lengths keep these additions and subtractions exact. Chart widths alone are rounded. CSV preserves exact result strings. Formula '+VERSION+'.</p>';
}
function comparisonMarkup(current, baseline) {
  if (!baseline) return '<p class="small-note">No baseline retained. Keep a valid scenario, then edit an input to compare. The baseline lasts only in this tab.</p>';
  return '<h3>Current minus retained baseline</h3><p><strong>Baseline:</strong> '+esc(baseline.inputs.scenarioLabel)+' · '+esc(baseline.period)+'. <strong>Current:</strong> '+esc(current.inputs.scenarioLabel)+' · '+esc(current.period)+'. All amounts USD million.</p><p class="small-note">Comparisons show arithmetic differences. Different periods or cash definitions may not be economically comparable. A retained baseline can itself contain reconciliation gaps.</p><div class="ocf-table-scroll" tabindex="0" role="region" aria-label="Baseline comparison exact differences"><table class="ocf-table"><caption>Exact current-minus-baseline deltas; missing values stay uncalculated.</caption><thead><tr><th scope="col">Measure</th><th scope="col">Baseline</th><th scope="col">Current</th><th scope="col">Delta</th></tr></thead><tbody>'+Object.entries(compare(current,baseline)).map(([k,v])=>'<tr><th scope="row">'+esc(METRICS[k])+'</th><td>'+esc(v.baseline)+'</td><td>'+esc(v.current)+'</td><td>'+esc(v.delta)+'</td></tr>').join('')+'</tbody></table></div><details><summary>Retained baseline inputs and cash definition</summary><p class="small-note"><strong>'+esc(baseline.provenance.status)+'</strong> '+esc(baseline.provenance.sourceNotes)+'</p><dl class="ocf-metrics">'+Object.entries(baseline.inputs).map(([k,v])=>'<div><dt>'+esc(LABELS[k])+'</dt><dd>'+esc(v)+'</dd></div>').join('')+'</dl></details>';
}
function mount(form) {
  const controls=form.querySelector('[data-operating-controls]'), output=document.querySelector('[data-operating-result]'), error=form.querySelector('[data-operating-error]'), exportButton=document.querySelector('[data-operating-export]'), status=document.querySelector('[data-operating-status]');
  error.id='operating-error';
  const baselineButton=document.querySelector('[data-operating-baseline]'),clearButton=document.querySelector('[data-operating-clear]'),comparison=document.querySelector('[data-operating-comparison]');
  let last=null, baseline=null, activeSource='Illustrative data, not an issuer', scenarioEdited=false, presets=[{id:'synthetic',label:'Synthetic manufacturer',sourceLabel:'Illustrative data, not an issuer',values:DEFAULT}];
  const embedded=document.getElementById('operating-examples');
  if (embedded) {try {const parsed=JSON.parse(embedded.textContent);if(Array.isArray(parsed)) presets=presets.concat(parsed.filter(p=>p && /^[a-z0-9-]+$/.test(p.id) && p.id!=='synthetic' && typeof p.label==='string' && p.values && typeof p.values==='object'));}catch (_) { /* Synthetic default remains usable. */ }}
  const select=form.querySelector('[data-operating-preset]');
  presets.forEach(p=>{const option=document.createElement('option');option.value=p.id;option.textContent=p.label;select.appendChild(option);});
  function read() {const values={};Object.keys(LABELS).forEach(k=>values[k]=form.elements.namedItem(k).value);values.provenance={sourceNotes:activeSource,status:scenarioEdited?'Edited user scenario; loaded source notes are context, not verification of changed values.':'Loaded example; arithmetic checks do not independently verify the source.'};return values;}
  function compute(focusError=false) {
    Object.keys(LABELS).forEach(key=>{const field=form.elements.namedItem(key);field.removeAttribute('aria-invalid');field.setAttribute('aria-describedby','operating-hint-'+key);});
    try {last=calculate(read());output.innerHTML=render(last);comparison.innerHTML=comparisonMarkup(last,baseline);error.hidden=true;exportButton.disabled=false;baselineButton.disabled=false;status.textContent='Updated. OCF '+last.metrics.operatingCashFlow+'; FCF '+last.metrics.freeCashFlow+'; residual '+last.metrics.residual+' USD million. '+(last.metrics.operatingGap==='0'?'OCF matches.':'OCF reconciliation needs review.')+' '+(last.metrics.cashGap==='0'?'Cash balance matches.':'Cash balance reconciliation needs review.');return true;}
    catch(e){last=null;exportButton.disabled=true;baselineButton.disabled=true;error.textContent=e.message;error.hidden=false;output.textContent='Results cleared. Correct the input; previous output is no longer current.';comparison.textContent=baseline?'Baseline retained; comparison unavailable until current inputs are valid.':'No baseline retained.';status.textContent='Calculation needs attention.';const field=e.field&&form.elements.namedItem(e.field);if(field){field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby','operating-hint-'+e.field+' '+error.id);}if(focusError)(field||error).focus();return false;}
  }
  function load(id) {const p=presets.find(p=>p.id===id)||presets[0];Object.keys(LABELS).forEach(k=>form.elements.namedItem(k).value=p.values[k]===null||p.values[k]===undefined?'':String(p.values[k]));select.value=p.id;activeSource=p.sourceLabel||'Source details supplied with this example.';scenarioEdited=false;form.querySelector('[data-operating-source]').textContent=activeSource;compute();}
  form.addEventListener('submit',e=>{e.preventDefault();compute(true);});
  form.addEventListener('input',e=>{if(e.target.name && Object.hasOwn(LABELS,e.target.name)){scenarioEdited=true;form.querySelector('[data-operating-source]').textContent='Edited user scenario. Recheck every source value before relying on the result. Source context: '+activeSource;compute();}});
  form.querySelector('[data-operating-load]').addEventListener('click',()=>load(select.value));
  form.addEventListener('reset',e=>{e.preventDefault();load('synthetic');status.textContent='Synthetic example restored. '+status.textContent;});
  baselineButton.addEventListener('click',()=>{if(!compute(true)||!last)return;baseline=last;comparison.innerHTML=comparisonMarkup(last,baseline);clearButton.disabled=false;status.textContent='Baseline retained: '+baseline.inputs.scenarioLabel+'. Edit inputs to compare current minus baseline.';});
  clearButton.addEventListener('click',()=>{baseline=null;clearButton.disabled=true;comparison.innerHTML=last?comparisonMarkup(last,null):'No baseline retained.';status.textContent='Baseline cleared.';});
  exportButton.addEventListener('click',()=>{if(!compute(true)||!last)return;const blob=new Blob(['\ufeff'+csv(last,baseline)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='dfb-operating-cash-flow-'+last.inputs.fiscalYear+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  controls.disabled=false;form.querySelector('[data-operating-loading]').hidden=true;
  const requested=new URLSearchParams(root.location.search).get('example');load(presets.some(p=>p.id===requested)?requested:'synthetic');
}
const api={formulaVersion:VERSION,defaultScenario:()=>({...DEFAULT}),calculate,compare,csv,csvCell,labels:LABELS,metricLabels:METRICS};
if(typeof module==='object' && module.exports)module.exports=api;
else {root.DFBOperating=api;document.querySelectorAll('[data-operating-workbench]').forEach(mount);}
})(typeof window!=='undefined'?window:globalThis);
