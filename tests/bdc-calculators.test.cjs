const {test}=require('node:test');
const assert=require('node:assert/strict');
const {calculate,validate,format}=require('../bdc-calculators.js');
const context={datasetMode:'synthetic',incomeBasis:'reported',distributionBasis:'declared',currency:'USD',scale:'million',unit:'amount',periodStart:'2026-07-01',periodEnd:'2026-09-30',asOf:'2026-09-30',scope:'common'};
const fixture={nii:'120',pik:'18',tii:'180',regular:'100',supplemental:'10',special:'5'};
const result=(kind='nii',inputs=fixture,ctx=context)=>calculate(kind,inputs,ctx);
const row=(r,label)=>r.rows.find(r=>r.label===label);
const val=(r,label)=>row(r,label).value;
test('ZIP fixture: totals, both denominators, both PIK ratios',()=>{
 const r=result();
 assert.equal(val(r,'Total common distributions'),'115');
 assert.equal(val(r,'Regular distribution coverage'),'1.2');
 assert.equal(format(row(r,'Total distribution coverage')),'1.0435×');
 assert.equal(format(row(r,'PIK / total investment income')),'10.0000%');
 assert.equal(format(row(r,'PIK / NII')),'15.0000%');
});
test('ZIP fixture: all 0/25/50/100 sensitivity columns',()=>{
 const r=result();
 for(const [p,amount,regular,total] of [[0,'120','1.2000×','1.0435×'],[25,'115.5','1.1550×','1.0043×'],[50,'111','1.1100×','0.9652×'],[100,'102','1.0200×','0.8870×']]){
  assert.equal(val(r,'Simple sensitivity: '+p+'% PIK deduction'),amount);
  assert.equal(format(row(r,'Simple sensitivity '+p+'%: regular coverage')),regular);
  assert.equal(format(row(r,'Simple sensitivity '+p+'%: total coverage')),total);
 }
});
test('unknown supplemental does not become zero; regular survives',()=>{
 const r=result('nii',{...fixture,supplemental:null});
 assert.equal(val(r,'Total common distributions'),null);
 assert.equal(val(r,'Regular distribution coverage'),'1.2');
 assert.equal(r.audit.inputs.supplemental.availability,'not_found');
 const z=result('nii',{...fixture,supplemental:'0'});
 assert.equal(val(z,'Total common distributions'),'105');
 assert.equal(z.audit.inputs.supplemental.value,'0');
});
test('missing PIK leaves reported coverage but disables sensitivities',()=>{
 const r=result('nii',{...fixture,pik:null});
 assert.equal(val(r,'Regular distribution coverage'),'1.2');
 assert.equal(val(r,'PIK / NII'),null);
 assert.equal(val(r,'Simple sensitivity: 0% PIK deduction'),null);
});
test('missing TII disables only its ratio',()=>{
 const r=result('nii',{...fixture,tii:null});
 assert.equal(val(r,'PIK / total investment income'),null);
 assert.equal(val(r,'PIK / NII'),'0.15');
 assert.equal(val(r,'Simple sensitivity: 100% PIK deduction'),'102');
});
test('negative NII preserves signed coverage, not PIK share interpretation',()=>{
 const r=result('nii',{...fixture,nii:'-10'});
 assert.equal(val(r,'Regular distribution coverage'),'-0.1');
 assert.equal(val(r,'PIK / NII'),null);
 assert.equal(val(r,'Simple sensitivity: 100% PIK deduction'),'-28');
 assert.ok(r.warnings.some(w=>w.includes('negative')));
});
test('zero denominators are explained undefined results',()=>{
 const r=result('nii',{...fixture,regular:'0',supplemental:'0',special:'0',nii:'0',tii:'0'});
 for(const label of ['Regular distribution coverage','Total distribution coverage','PIK / NII','PIK / total investment income']) assert.equal(val(r,label),null);
 assert.match(format(row(r,'Regular distribution coverage')),/^Not defined/);
});
test('currency, scale, unit, period, basis and scope mismatches rejected',()=>{
 for(const [key,value] of Object.entries({currency:'EUR',scale:'one',unit:'per-share',periodStart:'2026-01-01',periodEnd:'2026-06-30',asOf:'2026-06-30',incomeBasis:'adjusted',distributionBasis:'paid',scope:'preferred'})){
  assert.throws(()=>result('nii',{...fixture,pik:{value:'18',availability:'reported',origin:'manual',[key]:value}}),/mixed/);
 }
});
test('invalid decimal syntax, nonfinite values and oversized strings rejected',()=>{
 for(const value of ['1,000','1e3','NaN','Infinity','--2','4abc','2'.repeat(65),'10000000000000000000000000000001']) assert.throws(()=>result('nii',{...fixture,nii:value}));
});
test('empty, whitespace and unavailable statuses stay missing',()=>{
 for(const value of ['', '   ',null]) assert.equal(val(result('nii',{...fixture,nii:value}),'Regular distribution coverage'),null);
 const r=result('nii',{...fixture,supplemental:{value:'99',availability:'not_disclosed',origin:'extracted'}});
 assert.equal(val(r,'Total common distributions'),null);
 assert.equal(r.audit.inputs.supplemental.availability,'not_disclosed');
});
test('negative PIK and distributions rejected without silently fixing them',()=>{
 for(const id of ['pik','tii','regular','supplemental','special']) assert.throws(()=>result('nii',{...fixture,[id]:'-1'}),/positive/);
});
test('manual/extracted use same decimal validation; company sources required',()=>{
 for(const origin of ['manual','extracted']) assert.throws(()=>result('nii',{...fixture,pik:{value:'1e3',availability:'reported',origin}}));
 assert.throws(()=>result('nii',fixture,{...context,datasetMode:'company'}),/source URL/);
 const records=Object.fromEntries(Object.entries(fixture).map(([id,value])=>[id,{value,availability:'reported',origin:'manual',sourceUrl:'https://www.sec.gov/Archives/example',sourceLocator:'Synthetic source test only'}]));
 const r=result('nii',records,{...context,datasetMode:'company'});
 assert.equal(r.audit.inputs.nii.reviewedAt,null);
});
test('decimal precision is retained through addition and sensitivity',()=>{
 const r=result('nii',{...fixture,nii:'0.3',pik:'0.1',regular:'0.1',supplemental:'0.1',special:'0.1'});
 assert.equal(val(r,'Total common distributions'),'0.3');
 assert.equal(val(r,'Total distribution coverage'),'1');
 assert.equal(val(r,'Simple sensitivity: 25% PIK deduction'),'0.275');
});
test('very small nonzero output does not print zero',()=>{
 assert.match(format({value:'0.000000001',unit:'amount'}),/e-/);
 assert.equal(format({value:'0',unit:'amount'}),'0.0000');
});
test('PIK standalone ratio denominator distinction',()=>{
 const r=result('pik',{nii:'60',pik:'18',tii:'180'});
 assert.equal(val(r,'PIK / NII'),'0.3');
 assert.equal(val(r,'PIK / total investment income'),'0.1');
});
test('non-accrual cost and fair value have matching separate denominators',()=>{
 const r=result('non-accrual',{nonAccrualCost:'50',portfolioCost:'1000',nonAccrualFv:'20',portfolioFv:'950'});
 assert.equal(format(row(r,'Non-accrual share at cost')),'5.0000%');
 assert.equal(format(row(r,'Non-accrual share at fair value')),'2.1053%');
 assert.equal(format(row(r,'Non-accrual FV / cost')),'40.0000%');
 assert.throws(()=>result('non-accrual',{nonAccrualCost:'1001',portfolioCost:'1000'}),/exceed/);
});
test('non-accrual zero fair value retained; missing is not zero',()=>{
 const r=result('non-accrual',{nonAccrualCost:'50',portfolioCost:'1000',nonAccrualFv:'0',portfolioFv:'950'});
 assert.equal(val(r,'Non-accrual share at fair value'),'0');
 assert.equal(val(result('non-accrual',{nonAccrualCost:null,portfolioCost:'1000'}),'Non-accrual share at cost'),null);
});
test('NAV discount and premium have correct sign and denominator',()=>{
 const ctx={...context,unit:'per-share',scale:'one'};
 assert.equal(format(row(result('nav',{price:'18',nav:'20'},ctx),'Signed premium / (discount)')),'-10.0000%');
 assert.equal(format(row(result('nav',{price:'22',nav:'20'},ctx),'Signed premium / (discount)')),'10.0000%');
 for(const nav of ['0','-20']) assert.equal(val(result('nav',{price:'18',nav},ctx),'Price / NAV'),null);
});
test('debt/equity gross and optional cash-adjusted measures remain distinct',()=>{
 const r=result('leverage',{debt:'800',equity:'1000',cash:'50'});
 assert.equal(val(r,'Debt / common equity'),'0.8');
 assert.equal(val(r,'Debt less entered cash'),'750');
 assert.equal(val(r,'(Debt less cash) / common equity'),'0.75');
 assert.equal(val(result('leverage',{debt:'800',equity:'0',cash:'50'}),'Debt / common equity'),null);
 assert.equal(val(result('leverage',{debt:'800',equity:'-10',cash:'50'}),'Debt / common equity'),null);
});
test('formula version and unrounded raw inputs trace every result',()=>{
 const r=result();
 assert.equal(r.audit.formulaVersion,'bdc-1.0.1');
 assert.equal(r.audit.inputs.pik.value,'18');
 assert.equal(r.audit.inputs.pik.reviewedAt,null);
 assert.equal(r.audit.inputs.pik.periodStart,'2026-07-01');
 assert.deepEqual(r.audit.inputIds,Object.keys(fixture));
 assert.match(r.audit.formula,/sensitivity/);
 assert.equal(r.audit.context.datasetMode,'synthetic');
 assert.match(r.audit.rounding,/40/);
 assert.ok(r.warnings.some(w=>w.includes('not cash earnings')));
});
test('malformed dates, reversed periods and invalid common units are blocked',()=>{
 for(const patch of [{periodStart:'2026-02-30'},{periodStart:'2026-10-01'},{currency:'US dollars'},{scale:'billions'}]) assert.throws(()=>result('nii',fixture,{...context,...patch}));
 assert.throws(()=>result('nii',fixture,{...context,unit:'per-share'}),/total amounts/);
 assert.throws(()=>result('nav',{price:'18',nav:'20'},context),/per-share/);
});
test('analysis as-of before reporting period end is rejected by every worksheet',()=>{
 const cases={nii:fixture,pik:{nii:'120',pik:'18',tii:'180'},'non-accrual':{nonAccrualCost:'50',portfolioCost:'1000',nonAccrualFv:'20',portfolioFv:'950'},nav:{price:'18',nav:'20'},leverage:{debt:'800',equity:'1000',cash:'50'}};
 for(const [kind,inputs] of Object.entries(cases)){
  const ctx={...context,asOf:'2026-09-29',...(kind==='nav'?{unit:'per-share',scale:'one'}:{})};
  assert.throws(()=>result(kind,inputs,ctx),/as-of date must be on or after/);
  assert.throws(()=>validate(ctx,inputs),/as-of date must be on or after/);
 }
});
test('analysis as-of equals period end or is later without rewriting source dates',()=>{
 for(const asOf of ['2026-09-30','2026-10-18']){
  const r=result('nii',fixture,{...context,asOf});
  assert.equal(val(r,'Total common distributions'),'115');
  assert.equal(r.audit.context.asOf,asOf);
  assert.equal(r.audit.inputs.nii.periodEnd,'2026-09-30');
 }
 const r=result('nav',{price:{value:'18',availability:'scenario',origin:'manual',sourceLocator:'Market quote observed 2026-10-17'},nav:{value:'20',availability:'scenario',origin:'manual',sourceLocator:'Common NAV snapshot 2026-09-30'}},{...context,asOf:'2026-10-18',unit:'per-share',scale:'one'});
 assert.equal(r.audit.inputs.price.sourceLocator,'Market quote observed 2026-10-17');
 assert.equal(r.audit.inputs.nav.sourceLocator,'Common NAV snapshot 2026-09-30');
 assert.equal(val(r,'Price / NAV'),'0.9');
});
test('manual and extracted source overrides cannot bypass chronology or matching context',()=>{
 for(const origin of ['manual','extracted']){
  const input={value:'18',availability:'reported',origin,sourceUrl:'https://www.sec.gov/Archives/example',sourceLocator:'Synthetic source validation fixture'};
  assert.throws(()=>result('nii',{...fixture,pik:{...input,asOf:'2026-09-29'}}),/mixed asOf/);
  assert.throws(()=>result('nii',{...fixture,pik:{...input,periodEnd:'2026-10-01'}}),/mixed periodEnd/);
  assert.throws(()=>result('nii',{...fixture,pik:{...input,asOf:'2026-10-18',periodEnd:'2026-09-29'}},{...context,asOf:'2026-09-29'}),/as-of date must be on or after/);
 }
});
