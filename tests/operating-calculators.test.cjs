const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../operating-calculators.js');
const scenario = changes => ({...C.defaultScenario(),...changes});
test('Synthetic bridge reconciles earnings and cash while allocation residual is negative',()=>{
 const r=C.calculate(scenario());
 assert.deepEqual(r.metrics,{operatingCashFlow:'135',reportedOCF:'135',operatingGap:'0',freeCashFlow:'80',shareholderCash:'95',residual:'-15',cashChange:'3',computedEndingCash:'103',endingCash:'103',cashGap:'0'});
 assert.equal(r.formulaVersion,'operating-1.0.0');
 assert.equal(r.steps[5].total,'80');
});
test('Earnings and cash mismatches are independent and never hidden',()=>{
 const r=C.calculate(scenario({workingCapital:'25',endingCash:'110'}));
 assert.equal(r.metrics.operatingGap,'50');assert.equal(r.metrics.operatingCashFlow,'185');
 assert.equal(r.metrics.computedEndingCash,'103');assert.equal(r.metrics.cashGap,'-7');
 assert.ok(r.warnings.some(x=>x.includes('operating bridge does not reconcile')));
 assert.ok(r.warnings.some(x=>x.includes('cash balance bridge does not reconcile')));
});
test('Cash PP&E and shareholder payments do not get subtracted twice in cash balance',()=>{
 const r=C.calculate(scenario({capex:'1000',buybacks:'2000',dividends:'3000'}));
 assert.equal(r.metrics.computedEndingCash,'103');assert.equal(r.metrics.residual,'-5865');
});
test('Decimal cancellation, tiny signs and digits beyond Number retain exact strings',()=>{
 const r=C.calculate(scenario({netIncome:'9007199254740993.3',noncash:'0.1',workingCapital:'-9007199254740993.2',reportedOCF:'0.2',capex:'0.1',dividends:'0.1',buybacks:'0.0000000000000001'}));
 assert.equal(r.metrics.operatingCashFlow,'0.2');assert.equal(r.metrics.operatingGap,'0');assert.equal(r.metrics.residual,'-0.0000000000000001');
 const large=C.calculate(scenario({netIncome:'999999999999999999999999999999.9999999999999999',noncash:'0.0000000000000001',workingCapital:'0'}));
 assert.equal(large.metrics.operatingCashFlow,'1000000000000000000000000000000');
});
test('No ratios or undefined behavior for negative or zero operating cash',()=>{
 for(const netIncome of ['0','-100']){
  const r=C.calculate(scenario({netIncome,noncash:'0',workingCapital:'0',reportedOCF:netIncome,capex:'0',dividends:'0',buybacks:'0'}));
  assert.equal(r.metrics.residual,netIncome);assert.ok(r.warnings.some(w=>w.includes('zero or negative')));
 }
});
test('Missing reported OCF is unknown and withholds balance bridge',()=>{
 const r=C.calculate(scenario({reportedOCF:''}));
 assert.equal(r.metrics.operatingGap,null);assert.equal(r.metrics.computedEndingCash,null);assert.equal(r.metrics.cashGap,null);assert.equal(r.metrics.freeCashFlow,'80');
});
test('Cash balance group may be wholly omitted but partial fields fail',()=>{
 const empty={beginningCash:'',netInvesting:'',netFinancing:'',fx:'',endingCash:''};
 assert.equal(C.calculate(scenario(empty)).metrics.computedEndingCash,null);
 assert.throws(()=>C.calculate(scenario({...empty,beginningCash:'100'})),/investing cash flow/i);
});
test('Required values, unsigned cash amounts, malformed decimals and long input reject',()=>{
 for(const value of ['',' ','NaN','Infinity','1e6','1,000','1.2.3','9'.repeat(31),'0.00000000000000001'])assert.throws(()=>C.calculate(scenario({netIncome:value})));
 for(const key of ['capex','dividends','buybacks','beginningCash','endingCash'])assert.throws(()=>C.calculate(scenario({[key]:'-1'})));
 assert.throws(()=>C.calculate(scenario({fiscalYear:'24'})));
 assert.throws(()=>C.calculate(scenario({cashDefinition:''})));
 assert.throws(()=>C.calculate(scenario({buybacks:'-1'})),error=>error.field==='buybacks');
 assert.throws(()=>C.calculate(scenario({fiscalYear:'24'})),error=>error.field==='fiscalYear');
 assert.throws(()=>C.calculate(scenario({scenarioLabel:''})),error=>error.field==='scenarioLabel');
});
test('Changes compare exact deltas and preserve a full baseline input trail',()=>{
 const base=C.calculate(scenario()), current=C.calculate(scenario({scenarioLabel:'Lower repurchase scenario',buybacks:'20'}));
 const comparison=C.compare(current,base);
 assert.deepEqual(comparison.residual,{baseline:'-15',current:'30',delta:'45'});
 assert.equal(comparison.operatingCashFlow.delta,'0');assert.equal(comparison.cashGap.delta,'0');
 assert.equal(base.inputs.buybacks,'65');
 const text=C.csv(current,base);assert.match(text,/Baseline input/);assert.match(text,/Current minus baseline/);assert.match(text,/"-15","30","45"/);
 assert.equal(C.compare(C.calculate(scenario({reportedOCF:''})),base).operatingGap.delta,null);
});
test('CSV quotes content and neutralizes formula text while retaining canonical negative numbers',()=>{
 for(const s of ['=1+1','  =1+1','\t@SUM(1)','+SUM(1)','-cmd'])assert.equal(C.csvCell(s),'"\''+s+'"');
 assert.equal(C.csvCell('-0.0000000000000001'),'"-0.0000000000000001"');assert.equal(C.csvCell('a,"b"'),'"a,""b"""');
 const result=C.calculate(scenario({scenarioLabel:'=HYPERLINK("https://example.com")'}));
 assert.match(C.csv(result),/"'=HYPERLINK/);
});
test('Engine isolates Decimal context from other calculators',()=>{
 const D=require('../vendor/decimal.js/decimal.js');D.set({precision:3});
 assert.equal(C.calculate(scenario({netIncome:'12345.6789',noncash:'.0001',workingCapital:'0'})).metrics.operatingCashFlow,'12345.679');
 D.set({precision:40});
});
test('Verified Apple annual totals reproduce the independently sourced arithmetic',()=>{
 const r=C.calculate(scenario({netIncome:'93736',noncash:'20867',workingCapital:'3651',reportedOCF:'118254',capex:'9447',dividends:'15234',buybacks:'94949',beginningCash:'30737',netInvesting:'2935',netFinancing:'-121983',fx:'0',endingCash:'29943'}));
 assert.equal(r.metrics.freeCashFlow,'108807');assert.equal(r.metrics.residual,'-1376');assert.equal(r.metrics.cashChange,'-794');assert.equal(r.metrics.operatingGap,'0');assert.equal(r.metrics.cashGap,'0');
});
test('Source qualifications and edited status survive current and baseline exports',()=>{
 const notes='Apple FY2024: FX 0 is a worksheet convention, not a separately reported fact.';
 const base=C.calculate({...scenario(),provenance:{sourceNotes:notes,status:'Loaded historical example'}});
 const current=C.calculate({...scenario({buybacks:'20'}),provenance:{sourceNotes:notes,status:'Edited user scenario'}});
 const text=C.csv(current,base);
 assert.match(text,/Edited user scenario/);assert.match(text,/Baseline status","Loaded historical example/);
 assert.equal(text.split(notes).length-1,2);
 assert.throws(()=>C.calculate({...scenario(),provenance:{sourceNotes:'x'.repeat(2401)}}));
});
