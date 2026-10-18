/* DFB capital worksheets v1.0.2. Decimal arithmetic, browser-local scenarios only. */
(function(root){
'use strict';
const Decimal = typeof module === 'object' && module.exports ? require('./vendor/decimal.js/decimal.js') : root.Decimal;
if(!Decimal)return;
Decimal.set({precision:40});
const VERSION='capital-1.0.2';
function dec(value,name,negative=false){
 if(value===null||value===undefined||String(value).trim()==='') return null;
 const s=String(value).trim();
 if(s.length>48||!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(s))throw Error(name+': use a decimal number, without commas or exponent notation.');
 const d=new Decimal(s);if(!d.isFinite()||(!negative&&d.lt(0)))throw Error(name+': use a finite '+(negative?'':'nonnegative ')+'number.');return d;
}
function required(v,n,negative=false){const d=dec(v,n,negative);if(d===null)throw Error(n+': required; blank is unknown, not zero.');return d;}
const out=d=>d===null?null:d.toString();
function day(s,n){if(!/^\d{4}-\d{2}-\d{2}$/.test(s||'')||new Date(s+'T00:00:00Z').toISOString().slice(0,10)!==s)throw Error(n+': use a valid YYYY-MM-DD date.');return s;}
function context(m,debt=true){if(!m)throw Error('Metadata is required.');day(m.asOf,'As-of date');if(!/^[A-Z]{3}$/.test(m.currency||'')||!['unit','thousand','million'].includes(m.scale))throw Error('Choose a three-letter currency and monetary scale.');if(debt&&!['principal','carrying'].includes(m.basis))throw Error('Choose principal or carrying amount.');return debt?m:{asOf:m.asOf,currency:m.currency,scale:m.scale};}
function same(m,row){for(const k of ['asOf','currency','scale','basis'])if(row[k]!==m[k])throw Error('Mixed '+k+': align source dates, currency, scale and basis before calculating.');}
function result(metrics,rows,warnings,inputs){return {formulaVersion:VERSION,metrics,rows,warnings,inputs,datasetMode:'user scenario / synthetic default'};}
function calculateJv(v){
 const meta=context(v.meta),base=required(v.consolidatedDebt,'Consolidated debt'),guarantee=dec(v.guarantees,'Guarantees');let total=base,complete=true;const warnings=[],rows=[];const names=new Set();
 if(!Array.isArray(v.jvs)||v.jvs.length===0||v.jvs.length>50)throw Error('Use 1 to 50 JV rows. Enter explicit zero when no debt is disclosed, rather than an empty table.');
 for(const j of v.jvs){same(meta,j);if(!j.name||names.has(j.name))throw Error('JV names must be present and unique.');names.add(j.name);const debt=dec(j.debt,j.name+' debt'),share=dec(j.ownership,j.name+' ownership');if(share&&share.gt(100))throw Error('Ownership must be between 0 and 100; 40 means 40%, 0.40 means 0.40%.');if(j.consolidated!==true&&j.consolidated!==false)throw Error('Identify whether each JV is already consolidated.');
 if(j.consolidated){warnings.push(j.name+': already consolidated; excluded to prevent double counting.');rows.push([j.name,out(debt),out(share),'Excluded: already consolidated']);continue;}
 const prop=debt!==null&&share!==null?debt.mul(share).div(100):null;if(prop===null){complete=false;warnings.push(j.name+': debt or ownership unknown; total is incomplete.');}else total=total.add(prop);rows.push([j.name,out(debt),out(share),out(prop)]);
 }
 warnings.push('Proportionate exposure is not a legal payment obligation. Guarantees are shown separately and are never added automatically.');
 warnings.push('The combined total covers the entered rows, not a verified complete issuer dataset. Consolidated debt remains on its reported accounting perimeter; only unconsolidated JV additions use the entered ownership percentages.');
 return result({'Consolidated debt':out(base),'Known subtotal (consolidated plus proportionate unconsolidated JV debt)':out(total),'Consolidated debt + proportionate unconsolidated JV debt':complete?out(total):null,'Separate guarantee amount (not added)':out(guarantee)},rows,warnings,v);
}
function calculateLiquidity(v){
 const m=context(v.meta);if(m.basis!=='principal')throw Error('Use principal maturities; carrying debt cannot be silently substituted.');if(!['dated','fiscal'].includes(v.maturityBasis))throw Error('Select exact dated maturities or fiscal-year buckets.');const fiscal=v.maturityBasis==='fiscal',end=day(fiscal?v.resourceDate:v.horizonEnd,fiscal?'Resource eligibility date':'Horizon end');if(end<=m.asOf)throw Error((fiscal?'Resource eligibility date':'Horizon end')+' must follow the as-of date.');
 const cash=required(v.cash,'Unrestricted cash'),restricted=dec(v.restricted,'Restricted cash'),commit=dec(v.commitment,'Commitment'),drawn=dec(v.drawn,'Drawn'),lc=dec(v.lc,'Letters of credit'),confirmed=dec(v.availability,'Confirmed availability'),spend=required(v.mandatory,'Mandatory spend');let capacity=commit!==null&&drawn!==null&&lc!==null?commit.sub(drawn).sub(lc):null;
 if(capacity&&capacity.lt(0))throw Error('Drawn amounts plus letters of credit exceed total commitment.');if(confirmed!==null&&capacity!==null&&confirmed.gt(capacity))throw Error('Confirmed availability exceeds commitment less draws and letters of credit.');
 let eligible=confirmed!==null&&v.conditionsConfirmed===true&&day(v.facilityExpiry,'Facility expiry')>=end;
 const warnings=[];if(!eligible)warnings.push('Availability is unconfirmed, constrained, or expires before the selected resource eligibility date. No facility amount is treated as confirmed funding; the complete residual is not calculated.');if(capacity===null)warnings.push('Commitment headroom cannot be checked: one facility component is unknown.');
 if(!Array.isArray(v.maturities)||v.maturities.length===0||v.maturities.length>100)throw Error('Use 1 to 100 maturity rows; an empty schedule is not evidence of zero maturities.');let debt=new Decimal(0),complete=true;const rows=[];
 for(const row of v.maturities){same(m,row);let included;if(v.maturityBasis==='dated'){day(row.date,'Maturity date');included=row.date>m.asOf&&row.date<=end;}else{if(!/^\d{4}$/.test(row.date))throw Error('Fiscal buckets require a four-digit fiscal year.');included=true;}const amount=dec(row.amount,'Maturity amount');if(included){if(amount===null)complete=false;else debt=debt.add(amount);}rows.push([row.date,row.scope||'Not specified',out(amount),included?'Included':'Outside horizon']);}
 if(v.maturityBasis==='fiscal')warnings.push('Fiscal-year bucket analysis only. These rows are not a rolling next-12-month amount. All supplied fiscal buckets are included, without a date cutoff. The resource eligibility date checks facility expiry only; it does not select maturity buckets or demonstrate cash availability throughout those years. Complete liquidity and residuals are withheld in fiscal mode because exact cash-flow and maturity dates are not established; enter reconciled exact dates in dated mode for a funding bridge.');
 const liquidity=!fiscal&&eligible?cash.add(confirmed):null;const residual=liquidity!==null&&complete?liquidity.sub(debt):null;
 warnings.push('Restricted cash is excluded. Refinancing, asset sales, future operating cash flow and facility extensions are not assumed. A funding gap is not a bankruptcy or dividend-cut prediction.');
 return result({'Known unrestricted cash':out(cash),'Restricted cash (excluded)':out(restricted),'Commitment headroom (not added)':out(capacity),[fiscal?'Facility amount at resource date (informational only)':'Confirmed usable facility']:eligible?out(confirmed):null,'Available liquidity':out(liquidity),'Known maturity subtotal':out(debt),'Complete supplied maturity subtotal':complete?out(debt):null,[fiscal?'Residual after supplied fiscal buckets':'Residual after maturities']:out(residual),[fiscal?'Residual after supplied fiscal buckets and mandatory spend':'Residual after mandatory spend']:residual===null?null:out(residual.sub(spend))},rows,warnings,{...v,...(fiscal?{horizonEnd:undefined,resourceDate:end}:{resourceDate:undefined,horizonEnd:end})});
}
function calculatePreferred(v){
 const meta=context(v.meta,false);if(v.earningsDefinition!==undefined&&(typeof v.earningsDefinition!=='string'||v.earningsDefinition.length>500))throw Error('Earnings definition must be text up to 500 characters.');day(v.periodStart,'Period start');day(v.periodEnd,'Period end');if(v.periodStart>v.periodEnd||v.periodEnd>v.meta.asOf)throw Error('The earnings period must be ordered and end on or before the as-of date.');if(!['before-preferred','already-common'].includes(v.earningsBasis))throw Error('Select the earnings attribution basis.');if(!['declared','paid'].includes(v.distributionBasis))throw Error('Select declared or paid distributions.');
 const earnings=required(v.earnings,'Period earnings measure',true),preferred=dec(v.preferred,'Preferred distributions'),common=dec(v.common,'Common distributions');const attributed=v.earningsBasis==='already-common'?earnings:preferred===null?null:earnings.sub(preferred);const total=preferred!==null&&common!==null?preferred.add(common):null;
 return result({'Selected period earnings':out(earnings),'Common-attributed measure':out(attributed),'Preferred distributions':out(preferred),'Common distributions':out(common),'Total distributions':out(total),'Common measure less common distributions':attributed!==null&&common!==null?out(attributed.sub(common)):null},[['Selected earnings definition',v.earningsDefinition?.trim()||'Not supplied — preserve the source definition before interpreting'],['Selected earnings basis',v.earningsBasis],['Distribution basis',v.distributionBasis],['Preferred deducted in this bridge',v.earningsBasis==='already-common'?'No: already attributed':out(preferred)]],['This is an attribution bridge, not cash flow, a solvency test or a legal liquidation waterfall. Preferred rights, cumulative arrears, redemption and payment restrictions require the actual security documents. Already-common earnings do not have preferred distributions deducted again.'],{...v,meta});
}
function parseCsv(text){
 if(typeof text!=='string'||text.length>100000)throw Error('CSV exceeds 100 KB.');
 // Clipboard input may retain a BOM even when a browser's File.text() removes it.
 if(text.charCodeAt(0)===0xFEFF)text=text.slice(1);
 const rows=[];let row=[],cell='',quoted=false,closed=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){if(c==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(c==='"'){quoted=false;closed=true;}else cell+=c;}
  else if(c==='"'){if(cell||closed)throw Error('Invalid CSV quote.');quoted=true;}
  else if(c===','||c==='\n'||c==='\r'){
   row.push(cell);cell='';closed=false;
   if(c!==','){rows.push(row);row=[];if(c==='\r'&&text[i+1]==='\n')i++;}
  }else{if(closed)throw Error('Unexpected content after CSV quote.');cell+=c;}
 }
 if(quoted)throw Error('Unclosed CSV quote.');
 if(cell||row.length||closed){row.push(cell);rows.push(row);}
 return rows.filter(r=>r.some(c=>c!==''));
}
function csv(rows){return rows.map(r=>r.map(v=>{let s=v===null||v===undefined?'Not defined':String(v);const start=s.trimStart();if(/^[=+@]/.test(start)||/^[\t\r\n]/.test(s)||(/^[-]/.test(start)&&!/^[-]\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(start)))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}).join(',')).join('\r\n');}
function normalizeMaturityRows(rows){if(!Array.isArray(rows)||rows.length===0||rows.length>100)throw Error('Use 1 to 100 maturity rows.');return rows.map((r,i)=>{if(!Array.isArray(r)||r.length!==4)throw Error('Maturity CSV row '+(i+1)+' needs date,amount,scope,asOf.');const amount=dec(r[1],'Maturity amount');return [r[0],amount===null?'':amount.toFixed(),r[2],r[3]];});}
function format(value){
 if(value===null)return 'Not defined / incomplete';
 if(!/^-?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(String(value)))return String(value);
 const d=new Decimal(value);
 // A real small amount or shortfall must not be presented as an exact zero.
 return !d.isZero()&&d.abs().lt('0.00005')?d.toExponential(4):d.toDecimalPlaces(4).toString();
}
const api={normalizeMaturityRows,calculateJv,calculateLiquidity,calculatePreferred,parseCsv,csv,format,formulaVersion:VERSION};if(typeof module==='object'&&module.exports)module.exports=api;else root.DFBCapital=api;
if(typeof document==='undefined')return;
const esc=s=>String(s===null?'Not defined / incomplete':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=format;
function download(name,rows){const url=URL.createObjectURL(new Blob([csv(rows)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500);}
for(const form of document.querySelectorAll('[data-capital-tool]')){
 const kind=form.dataset.capitalTool,resultEl=document.querySelector('[data-capital-result]'),error=form.querySelector('[role=alert]');let last=null;
 if((kind==='liquidity'&&!form.elements.resourceDate)||(kind==='preferred'&&!form.elements.earningsDefinition)){error.textContent='This cached worksheet uses an older layout. Reload this page to use the current calculator.';error.hidden=false;form.addEventListener('submit',e=>e.preventDefault());form.querySelector('[type=submit]').disabled=true;document.querySelectorAll('[data-capital-export],[data-capital-print]').forEach(b=>b.disabled=true);continue;}
 const fields=()=>Object.fromEntries(new FormData(form));
 const get=()=>{const f=fields(),meta={asOf:f.asOf,currency:f.currency,scale:f.scale,...(kind==='preferred'?{}:{basis:f.basis})};
 if(kind==='jv')return {meta,consolidatedDebt:f.consolidatedDebt,guarantees:f.guarantees,jvs:parseCsv(f.rows).map((r,i)=>{if(r.length!==5)throw Error('JV CSV row '+(i+1)+' needs name,debt,ownership,consolidated,asOf.');if(!['true','false'].includes(r[3]))throw Error('Consolidated must be true or false.');return {...meta,name:r[0],debt:r[1],ownership:r[2],consolidated:r[3]==='true',asOf:r[4]};})};
 if(kind==='liquidity')return {...f,meta,conditionsConfirmed:f.conditionsConfirmed==='yes',maturities:parseCsv(f.rows).map((r,i)=>{if(r.length!==4)throw Error('Maturity CSV row '+(i+1)+' needs date,amount,scope,asOf.');return {...meta,date:r[0],amount:r[1],scope:r[2],asOf:r[3]};})};return {...f,meta};};
 function run(){try{const data=get();last=kind==='jv'?calculateJv(data):kind==='liquidity'?calculateLiquidity(data):calculatePreferred(data);const table=(caption,headers,rows)=>'<div class="table-scroll"><table><caption>'+esc(caption)+'</caption><thead><tr>'+headers.map(x=>'<th scope="col">'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map((c,i)=>'<'+(i?'td':'th scope="row"')+'>'+esc(number(c))+'</'+(i?'td':'th')+'>').join('')+'</tr>').join('')+'</tbody></table></div>';
 resultEl.innerHTML='<p><strong>User scenario / synthetic default · '+esc(data.meta.currency)+' '+esc(data.meta.scale)+' · as of '+esc(data.meta.asOf)+'</strong></p>'+(kind==='liquidity'?'<p>'+esc(data.maturityBasis==='fiscal'?'All supplied fiscal buckets; resource / facility eligibility date: '+data.resourceDate:'Dated maturity cutoff and resource eligibility date: '+data.horizonEnd)+'</p>':'')+table('Calculated results · '+VERSION,['Measure','Value'],Object.entries(last.metrics))+table('Input detail',kind==='jv'?['JV','Gross debt','Ownership %','Proportionate debt']:kind==='liquidity'?['Maturity','Scope','Amount',data.maturityBasis==='fiscal'?'Supplied-bucket treatment':'Dated cutoff treatment']:['Item','Value'],last.rows)+'<ul>'+last.warnings.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul><p class="small-note">Rounded for display only, up to four decimal places; small nonzero values use scientific notation. CSV retains full arithmetic precision. No score or investment recommendation.</p>';error.hidden=true;return true;}catch(e){last=null;error.textContent=e.message;error.hidden=false;resultEl.textContent='Result cleared. Correct the inputs; previous output is not current.';return false;}}
 for(const event of ['input','change'])form.addEventListener(event,()=>{last=null;resultEl.textContent='Inputs changed. Select Calculate to update this scenario.';error.hidden=true;});
 function updateTemporalMode(){if(kind!=='liquidity')return;const fiscal=form.elements.maturityBasis.value==='fiscal';for(const [name,active] of [['horizonEnd',!fiscal],['resourceDate',fiscal]]){form.elements[name].disabled=!active;form.querySelector('label[for=capital-'+name+']').hidden=!active;}form.querySelector('[data-fiscal-hint]').hidden=!fiscal;form.querySelector('[data-dated-hint]').hidden=fiscal;}
 if(kind==='liquidity'){form.elements.maturityBasis.addEventListener('change',updateTemporalMode);updateTemporalMode();}
 form.addEventListener('submit',e=>{e.preventDefault();run();});form.addEventListener('reset',()=>setTimeout(()=>{updateTemporalMode();last=null;resultEl.textContent='Synthetic inputs restored. Select Calculate to update the result.';error.hidden=true;},0));
 document.querySelector('[data-capital-print]').addEventListener('click',()=>{if(run())window.print();});document.querySelector('[data-capital-export]').addEventListener('click',()=>{if(run())download('dfb-'+kind+'-results.csv',[['DFB user scenario / synthetic default',VERSION],['Input JSON',JSON.stringify(last.inputs)],...Object.entries(last.metrics),[],...last.rows,...last.warnings.map(w=>['Limit',w])]);});
 if(kind==='liquidity'){const file=form.querySelector('[data-maturity-file]');file.addEventListener('change',async()=>{try{const selected=file.files[0];if(!selected)return;if(selected.size>100000)throw Error('File exceeds 100 KB.');const rows=parseCsv(await selected.text());if(rows[0]?.join(',')!=='date,amount,scope,asOf')throw Error('CSV header must be date,amount,scope,asOf.');form.elements.rows.value=csv(normalizeMaturityRows(rows.slice(1)));run();}catch(e){error.textContent=e.message;error.hidden=false;last=null;resultEl.textContent='Import rejected. No current result.';}});form.querySelector('[data-maturity-export]').addEventListener('click',()=>{try{calculateLiquidity(get());download('dfb-maturity-input.csv',[['date','amount','scope','asOf'],...normalizeMaturityRows(parseCsv(form.elements.rows.value))]);}catch(e){error.textContent=e.message;error.hidden=false;}});}
 form.querySelector("[data-calculator-controls]").disabled=false;
 resultEl.textContent="Select Calculate to run the synthetic example.";
}
})(typeof globalThis!=='undefined'?globalThis:this);
