/* DFB browser-local BDC worksheets. Decimal arithmetic; no network or storage. */
(function (scope) {
  'use strict';
  const Decimal = typeof module === 'object' && module.exports ? require('./vendor/decimal.js/decimal.js') : scope.Decimal;
  if(!Decimal)return;
  const D = Decimal.clone({precision: 40, rounding: Decimal.ROUND_HALF_UP});
  const VERSION = 'bdc-1.0.2';
  const formulas = {
    nii:'total=regular+supplemental+special; regularCoverage=nii/regular; totalCoverage=nii/total; PIK/TII=pik/tii; PIK/NII=pik/nii only for nii>0; sensitivity(f)=nii-pik*f; sensitivityCoverage=sensitivity/distributions; f=0,0.25,0.50,1',
    pik:'PIK/TII=pik/tii; PIK/NII=pik/nii only for nii>0',
    'non-accrual':'costShare=nonAccrualCost/portfolioCost; fairValueShare=nonAccrualFv/portfolioFv; markedCost=nonAccrualFv/nonAccrualCost',
    nav:'priceNav=price/nav; signedPremiumDiscount=price/nav-1; difference=price-nav; ratios require nav>0',
    leverage:'gross=debt/equity; cashAdjusted=debt-cash; cashAdjustedRatio=(debt-cash)/equity; ratios require equity>0'
  };
  const fieldNames = {price:'User-entered market price per common share',nav:'Disclosed common NAV per share',nii:'Net investment income',pik:'PIK income',tii:'Total investment income',regular:'Regular common distributions',supplemental:'Supplemental common distributions',special:'Special common distributions',nonAccrualCost:'Non-accrual investments at cost',portfolioCost:'Matching portfolio at cost',nonAccrualFv:'Non-accrual investments at fair value',portfolioFv:'Matching portfolio at fair value',debt:'Debt',equity:'Common equity',cash:'Cash'};
  const availabilityNames = {scenario:'Entered scenario amount',reported:'Copied disclosure (not independently verified)',not_disclosed:'Not disclosed',not_found:'Not found',not_applicable:'Not applicable'};
  function inputError(id, detail) {
    const error=new Error((fieldNames[id] || id)+': '+detail);
    error.field=id;error.detail=detail;return error;
  }
  function missingReason(id, record) {
    if(record && record.decimal != null) return '';
    const status=record && ['not_disclosed','not_found','not_applicable'].includes(record.availability) ? availabilityNames[record.availability] : 'No value entered';
    return (fieldNames[id] || id)+' excluded — '+status;
  }
  const contexts = ['currency','scale','unit','periodStart','periodEnd','asOf','incomeBasis','distributionBasis','scope'];
  function validate(context, inputs, kind) {
    if(kind==='nav' && context) context={...context,incomeBasis:'not_applicable',distributionBasis:'not_applicable'};
    if (!context || !['synthetic','scenario','company'].includes(context.datasetMode)) throw Error('Choose a synthetic example, user scenario or sourced company dataset.');
    if (kind !== 'nav' && !['reported','adjusted'].includes(context.incomeBasis)) throw Error('Choose reported or adjusted NII consistently.');
    if (kind !== 'nav' && !['declared','paid'].includes(context.distributionBasis)) throw Error('Choose declared or paid distributions consistently.');
    if (context.unit !== 'amount' && context.unit !== 'per-share') throw Error('Use a single amount or directly reported per-share basis.');
    if (!['one','thousand','million'].includes(context.scale)) throw Error('Choose currency units, thousands or millions.');
    if (!/^[A-Z]{3}$/.test(context.currency || '')) throw Error('Use a three-letter currency code.');
    for (const key of ['periodStart','periodEnd','asOf']) {
      const value=context[key];
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '') || !Number.isFinite(Date.parse(value+'T00:00:00Z')) || new Date(value+'T00:00:00Z').toISOString().slice(0,10)!==value) throw Error('Enter a valid '+key+' date.');
    }
    if(context.periodStart>context.periodEnd) throw Error('Period start must not be after period end.');
    if(context.asOf<context.periodEnd) throw Error('Analysis as-of date must be on or after the reporting period end.');
    const out = {};
    for (const [id, raw] of Object.entries(inputs)) {
      const supplied = raw && typeof raw === 'object' ? {...raw} : {value:raw, availability:raw == null || raw === '' ? 'not_found' : 'scenario', origin:'manual'};
      const record = {datasetMode:context.datasetMode,currency:context.currency,scale:context.scale,unit:context.unit,periodStart:context.periodStart,periodEnd:context.periodEnd,asOf:context.asOf,incomeBasis:context.incomeBasis,distributionBasis:context.distributionBasis,scope:context.scope,sourceUrl:null,accession:null,sourceLocator:null,retrievedAt:null,reviewedAt:null,reviewedBy:null,note:null,...supplied};
      if (kind === 'nav') {record.incomeBasis='not_applicable';record.distributionBasis='not_applicable';}
      for (const key of contexts) if (record[key] != null && record[key] !== context[key]) throw Error(id + ': mixed ' + key + ' is not comparable.');
      if (record.datasetMode != null && record.datasetMode !== context.datasetMode) throw Error(id + ': mixed dataset modes.');
      if (!['manual','extracted'].includes(record.origin || 'manual')) throw Error(id + ': invalid input origin.');
      if (!['reported','not_disclosed','not_found','not_applicable','scenario'].includes(record.availability)) throw Error(id + ': invalid availability.');
      record.rawValue=record.value == null ? null : String(record.value);
      const missing = ['not_disclosed','not_found','not_applicable'].includes(record.availability);
      if (missing || record.value == null || String(record.value).trim() === '') {out[id] = {...record, value:null, decimal:null}; continue;}
      const value = String(record.value).trim();
      if (value.length > 64 || !/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) throw inputError(id, 'use a decimal without commas or exponent notation (maximum 64 characters).');
      const decimal = new D(value);
      if (!decimal.isFinite() || decimal.abs().gt('1e30')) throw inputError(id, 'magnitude exceeds the worksheet limit.');
      if (context.datasetMode === 'company' && (!record.sourceUrl || !record.sourceLocator || record.availability !== 'reported')) throw Error(id + ': company data needs a source URL, locator and reported availability.');
      if (record.sourceUrl && !/^https:\/\//i.test(record.sourceUrl)) throw Error(id + ': source URLs must use HTTPS.');
      out[id] = {...record, value, decimal};
    }
    return out;
  }
  function calculate(kind, inputs, context) {
    // Income/distribution choices do not apply to a price-to-NAV comparison.
    if(kind==='nav') context={...context,incomeBasis:'not_applicable',distributionBasis:'not_applicable'};
    if(kind==='nav' && (context.unit!=='per-share' || context.scale!=='one')) throw Error('Price/NAV requires directly entered per-share currency units.');
    if(kind!=='nav' && context.unit!=='amount') throw Error('This worksheet uses total amounts, not per-share conversions.');
    const records = validate(context, inputs, kind), warnings = [], rows = [];
    const get = id => records[id] ? records[id].decimal : null;
    const nonnegative = ids => ids.forEach(id => {if(get(id) && get(id).lt(0)) throw inputError(id, 'enter zero or a positive amount.');});
    const text = x => x == null ? null : x.toString();
    const ratio = (n,d) => n == null || d == null || d.isZero() ? null : n.div(d);
    const row = (label, value, unit='amount', reason='Missing input') => rows.push({label,value:text(value),unit,reason:value == null ? reason : null});
    const ratioRow = (label,n,d,unit='multiple') => row(label,ratio(n,d),unit,n == null || d == null ? 'Missing input' : 'Zero denominator');
    const audit = {formulaVersion:VERSION,formula:formulas[kind],inputIds:Object.keys(records),context:{...context},inputs:Object.fromEntries(Object.entries(records).map(([k,v])=>[k,{...v,decimal:undefined}])),rounding:'40 significant-digit decimal arithmetic; display four decimal places, half up. Nonzero values smaller than 0.0001 retain five significant digits. Plain decimals are used through 24 fractional places; longer tiny values use scientific notation. Display rounding does not change the stored results. Arithmetic precision does not increase the accuracy of the source inputs.'};
    if (kind === 'nii' || kind === 'pik') {
      nonnegative(['pik','tii','regular','supplemental','special']);
      const nii=get('nii'), pik=get('pik'), tii=get('tii'), reg=get('regular');
      if (nii && nii.lte(0)) warnings.push('NII is zero or negative. Signed coverage is retained; PIK/NII is not interpreted as an income share.');
      if (pik && tii && pik.gt(tii)) warnings.push('PIK exceeds total investment income. Check definitions, reversals and period alignment.');
      ratioRow('PIK / total investment income',pik,tii,'percent');
      row('PIK / NII',nii && nii.gt(0) ? ratio(pik,nii) : null,'percent','Not interpreted when NII is zero or negative, or inputs are missing');
      if (kind === 'nii') {
        const supp=get('supplemental'), special=get('special');
        const total=reg != null && supp != null && special != null ? reg.plus(supp).plus(special) : null;
        row('Total common distributions',total);
        ratioRow('Regular distribution coverage',nii,reg);
        ratioRow('Total distribution coverage',nii,total);
        [0,25,50,100].forEach(p => {
          const adjusted=nii != null && pik != null ? nii.minus(pik.times(p).div(100)) : null;
          row('Simple sensitivity: '+p+'% PIK deduction',adjusted);
          ratioRow('Simple sensitivity '+p+'%: regular coverage',adjusted,reg);
          ratioRow('Simple sensitivity '+p+'%: total coverage',adjusted,total);
        });
        warnings.push('PIK deduction is a simple sensitivity, not cash earnings, operating cash flow or cash available for distributions. Fees, taxes, collections and other noncash items remain unchanged.');
      }
    } else if (kind === 'non-accrual') {
      nonnegative(['nonAccrualCost','portfolioCost','nonAccrualFv','portfolioFv']);
      if (get('nonAccrualCost') && get('portfolioCost') && get('nonAccrualCost').gt(get('portfolioCost'))) throw Error('Non-accrual cost cannot exceed the matching portfolio cost.');
      if (get('nonAccrualFv') && get('portfolioFv') && get('nonAccrualFv').gt(get('portfolioFv'))) throw Error('Non-accrual fair value cannot exceed matching portfolio fair value.');
      ratioRow('Non-accrual share at cost',get('nonAccrualCost'),get('portfolioCost'),'percent');
      ratioRow('Non-accrual share at fair value',get('nonAccrualFv'),get('portfolioFv'),'percent');
      ratioRow('Non-accrual FV / cost',get('nonAccrualFv'),get('nonAccrualCost'),'percent');
      warnings.push('Use the same investment population in each numerator and denominator. Cost and fair value percentages answer different questions; neither is a default probability or recovery forecast.');
    } else if (kind === 'nav') {
      nonnegative(['price']);
      const price=get('price'), nav=get('nav');
      const missing=['price','nav'].map(id=>missingReason(id,records[id])).filter(Boolean).join('; ');
      const ratioReason=[missing,nav != null && nav.lte(0) ? 'Disclosed common NAV per share must be positive for a ratio' : ''].filter(Boolean).join('; ');
      row('Price / NAV',nav && nav.gt(0) ? ratio(price,nav) : null,'multiple',ratioReason);
      row('Signed premium / (discount)',price != null && nav && nav.gt(0) ? price.div(nav).minus(1) : null,'percent',ratioReason);
      row('Price less NAV',price != null && nav != null ? price.minus(nav) : null,'per-share',missing);
      warnings.push('A negative percentage is a discount; a positive percentage is a premium. User-entered price and disclosed NAV may have different dates. No live price is fetched.');
    } else if (kind === 'leverage') {
      nonnegative(['debt','cash']);
      const debt=get('debt'),cash=get('cash'),equity=get('equity');
      row('Debt / common equity',equity && equity.gt(0) ? ratio(debt,equity) : null,'multiple','Positive common equity and debt input required');
      row('Debt less entered cash',debt != null && cash != null ? debt.minus(cash) : null);
      row('(Debt less cash) / common equity',debt != null && cash != null && equity && equity.gt(0) ? debt.minus(cash).div(equity) : null,'multiple','Positive common equity and debt/cash inputs required');
      warnings.push('This descriptive ratio is not statutory asset coverage or covenant compliance. Preferred securities, exempt debt, SBIC relief, subsidiaries and instrument definitions require separate analysis. Cash is not assumed available to creditors.');
    } else throw Error('Unknown BDC worksheet.');
    return {rows,warnings,audit};
  }
  function format(row) {
    if (row.value == null) return 'Not defined — '+row.reason;
    const value=new D(row.value).times(row.unit === 'percent' ? 100 : 1);
    const display=value.toSignificantDigits(5);
    const shown=!value.isZero() && value.abs().lt('0.0001') ? (display.decimalPlaces()>24 ? display.toExponential() : display.toFixed()) : value.toFixed(4);
    return shown+(row.unit === 'percent' ? '%' : row.unit === 'multiple' ? '×' : '');
  }
  const api={calculate,validate,format,VERSION};
  if(typeof module === 'object' && module.exports) module.exports=api;
  else scope.DFBBdc=api;
  if (typeof document === 'undefined') return;
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  document.querySelectorAll('[data-bdc-tool]').forEach(form => {
    const error=form.querySelector('[data-bdc-error]'), target=document.querySelector('[data-bdc-result]');
    if(!error.id) error.id='bdc-input-error';
    let mode='synthetic';
    const clearInvalid = input => {
      if(!input || !input.hasAttribute('data-bdc-invalid')) return;
      input.removeAttribute('aria-invalid');input.removeAttribute('data-bdc-invalid');
      const descriptions=(input.getAttribute('aria-describedby') || '').split(/\s+/).filter(id=>id && id!==error.id);
      if(descriptions.length) input.setAttribute('aria-describedby',descriptions.join(' '));
      else input.removeAttribute('aria-describedby');
    };
    const clearErrors = () => {
      form.querySelectorAll('[data-bdc-invalid]').forEach(clearInvalid);
      error.hidden=true;error.textContent='';
    };
    const updateStatuses = () => form.querySelectorAll('[data-bdc-input]').forEach(input=>{
      const selected=form.elements.namedItem(input.name+'Availability').value;
      const excluded=['not_disclosed','not_found','not_applicable'].includes(selected);
      const blank=input.value.trim()==='';
      const status=form.querySelector('[data-bdc-status="'+input.name+'"]');
      if(!status) return; // Older cached HTML can still calculate while its assets refresh.
      const text=input.hasAttribute('data-bdc-invalid') ? 'Needs correction — check the input error below.' : excluded ? 'Excluded — '+availabilityNames[selected]+'. Any entered value is retained but not used.' : blank ? 'Excluded — No value entered. Missing is not zero.' : 'Included — '+availabilityNames[selected]+'.';
      if(status.textContent!==text) status.textContent=text;
      status.dataset.excluded=String(excluded || blank);
    });
    form.addEventListener('input',event=>{
      mode='scenario';
      const edited=event.target.name && event.target.name.endsWith('Availability') ? form.elements.namedItem(event.target.name.slice(0,-12)) : event.target;
      if(edited && edited.hasAttribute('data-bdc-invalid')) {clearInvalid(edited);error.hidden=true;error.textContent='';}
      updateStatuses();target.innerHTML='<p>Inputs changed. Select Calculate to update the result and its source record.</p>';
    });
    const run = event => {
      if(event)event.preventDefault();
      clearErrors();updateStatuses();
      try {
        const fd=new FormData(form);
        const context={datasetMode:mode,incomeBasis:fd.get('incomeBasis'),distributionBasis:fd.get('distributionBasis'),currency:fd.get('currency'),scale:fd.get('scale'),unit:form.dataset.bdcTool === 'nav' ? 'per-share':'amount',periodStart:fd.get('periodStart'),periodEnd:fd.get('periodEnd'),asOf:fd.get('asOf'),scope:'common'};
        if(context.periodStart && context.periodEnd && context.periodStart>context.periodEnd) throw Error('Period start must not be after period end.');
        const inputs={};
        form.querySelectorAll('[data-bdc-input]').forEach(input=>{const id=input.name, value=input.value, selected=fd.get(id+'Availability') || 'scenario';inputs[id]={value,availability:value.trim()==='' && ['scenario','reported'].includes(selected) ? 'not_found':selected,origin:'manual',sourceUrl:fd.get(id+'Source') || null,accession:fd.get(id+'Accession') || null,sourceLocator:fd.get(id+'Locator') || null,reviewedAt:null,reviewedBy:null,note:'User-entered; not independently verified'};});
        const result=calculate(form.dataset.bdcTool,inputs,context);
        error.hidden=true;error.textContent='';
        target.innerHTML='<p><strong>'+esc(mode==='synthetic'?'Synthetic example — not company results':'User scenario — not verified company results')+'</strong></p><p>'+esc(context.currency+' / '+context.scale+' / '+context.unit+' / '+context.periodStart+' to '+context.periodEnd+'; as of '+context.asOf+(form.dataset.bdcTool==='nav'?'':'; '+context.incomeBasis+' NII; '+context.distributionBasis+' distributions'))+'</p><div class="table-scroll" style="overflow-x:auto;max-height:none"><table><caption>Calculated values — formula '+VERSION+'</caption><thead><tr><th scope="col">Measure</th><th scope="col">Value</th></tr></thead><tbody>'+result.rows.map(r=>'<tr><th scope="row">'+esc(r.label)+'</th><td>'+esc(format(r))+'</td></tr>').join('')+'</tbody></table></div>'+result.warnings.map(w=>'<p>'+esc(w)+'</p>').join('')+'<p class="small-note">'+esc(result.audit.rounding)+'</p><details><summary>Input sources and calculation record</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+esc(JSON.stringify(result.audit,null,2))+'</pre></details>';
      }catch(e){
        const input=e.field ? [...form.querySelectorAll('[data-bdc-input]')].find(el=>el.name===e.field) : null;
        const label=input && form.querySelector('label[for="'+input.id+'"]');
        error.textContent=label && e.detail ? label.textContent.trim()+': '+e.detail : e.message;
        error.hidden=false;
        if(input) {
          input.setAttribute('aria-invalid','true');input.setAttribute('data-bdc-invalid','true');
          const descriptions=new Set((input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));descriptions.add(error.id);
          input.setAttribute('aria-describedby',[...descriptions].join(' '));
          updateStatuses();input.focus();
        }
        target.innerHTML='<p>No current result. Correct the input error to calculate again.</p>';
      }
    };
    form.addEventListener('submit',run);
    form.addEventListener('reset',()=>{mode='synthetic';setTimeout(run,0);});
    form.querySelector('[data-bdc-clear]').addEventListener('click',()=>{form.querySelectorAll('[data-bdc-input]').forEach(input=>input.value='');mode='scenario';run();});
    form.querySelector('[data-bdc-print]').addEventListener('click',()=>window.print());
    let printState=[];
    scope.addEventListener('beforeprint',()=>{printState=[...form.querySelectorAll('details'),...target.querySelectorAll('details')].map(el=>[el,el.open]);printState.forEach(([el])=>{el.open=true;});});
    scope.addEventListener('afterprint',()=>{printState.forEach(([el,open])=>{el.open=open;});printState=[];});
    form.querySelector("[data-calculator-controls]").disabled=false;
    run();
  });
})(typeof globalThis === 'undefined' ? this : globalThis);
