const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../capital-calculators.js');
const meta={asOf:'2026-09-30',currency:'USD',scale:'million',basis:'principal'};
const jv=()=>({meta:{...meta},consolidatedDebt:'800',guarantees:'100',jvs:[{...meta,name:'JV A',debt:'500',ownership:'40',consolidated:false},{...meta,name:'JV B',debt:'400',ownership:'25',consolidated:false}]});
const liq=()=>({meta:{...meta},horizonEnd:'2027-09-30',maturityBasis:'dated',cash:'40',restricted:'15',commitment:'100',drawn:'60',lc:'10',availability:'30',mandatory:'10',conditionsConfirmed:true,facilityExpiry:'2028-09-30',maturities:[{...meta,date:'2027-03-31',amount:'90',scope:'Consolidated'}]});
const pref=()=>({meta:{...meta},periodStart:'2026-01-01',periodEnd:'2026-09-30',earningsBasis:'before-preferred',distributionBasis:'declared',earnings:'120',preferred:'10',common:'90'});
test('JV fixture has200+100,1100total and guarantee not added',()=>{const r=C.calculateJv(jv());assert.equal(r.metrics['Consolidated debt + proportionate unconsolidated JV debt'],'1100');assert.equal(r.rows[0][3],'200');assert.equal(r.rows[1][3],'100');assert.equal(r.metrics['Separate guarantee amount (not added)'],'100');assert.match(r.warnings.join(' '),/only unconsolidated JV additions/);});
test('Consolidated JV is explicitly excluded',()=>{const v=jv();v.jvs[0].consolidated=true;assert.equal(C.calculateJv(v).metrics['Consolidated debt + proportionate unconsolidated JV debt'],'900');});
test('Unknown ownership is incomplete, zero is zero',()=>{const v=jv();v.jvs[0].ownership=null;assert.equal(C.calculateJv(v).metrics['Consolidated debt + proportionate unconsolidated JV debt'],null);v.jvs[0].ownership='0';assert.equal(C.calculateJv(v).metrics['Consolidated debt + proportionate unconsolidated JV debt'],'900');});
test('Ownership percentage points not fractions',()=>{const v=jv();v.jvs[0].ownership='0.40';assert.equal(C.calculateJv(v).rows[0][3],'2');v.jvs[0].ownership='101';assert.throws(()=>C.calculateJv(v));});
test('Mixed date/currency/scale/basis and duplicated JV rejected',()=>{for(const k of ['asOf','currency','scale','basis']){const v=jv();v.jvs[0][k]='mismatch';assert.throws(()=>C.calculateJv(v));}const v=jv();v.jvs.push(v.jvs[0]);assert.throws(()=>C.calculateJv(v));});
test('Liquidity fixture70,-20,-30 excludes restricted and total commitments',()=>{const r=C.calculateLiquidity(liq());assert.equal(r.metrics['Available liquidity'],'70');assert.equal(r.metrics['Residual after maturities'],'-20');assert.equal(r.metrics['Residual after mandatory spend'],'-30');});
test('Unconfirmed or expired facility never declared full funding',()=>{const v=liq();v.conditionsConfirmed=false;assert.equal(C.calculateLiquidity(v).metrics['Available liquidity'],null);v.conditionsConfirmed=true;v.facilityExpiry='2027-01-01';assert.equal(C.calculateLiquidity(v).metrics['Available liquidity'],null);});
test('Availability cannot exceed headroom',()=>{const v=liq();v.availability='31';assert.throws(()=>C.calculateLiquidity(v));v.availability='30';v.drawn='101';assert.throws(()=>C.calculateLiquidity(v));});
test('Exact maturity cutoff and missing principal',()=>{const v=liq();v.maturities.push({...meta,date:'2027-10-01',amount:'999'});assert.equal(C.calculateLiquidity(v).metrics['Complete supplied maturity subtotal'],'90');v.maturities[0].amount='';assert.equal(C.calculateLiquidity(v).metrics['Residual after maturities'],null);});
test('Fiscal buckets retain fiscal warning and reject dated labels',()=>{const v=liq();v.maturityBasis='fiscal';v.resourceDate='2027-09-30';assert.throws(()=>C.calculateLiquidity(v));v.maturities[0].date='2027';assert.match(C.calculateLiquidity(v).warnings.join(' '),/not a rolling/);});
test('Carrying amounts do not silently become maturity principal',()=>{const v=liq();v.meta={...meta,basis:'carrying'};assert.throws(()=>C.calculateLiquidity(v));});
test('Before preferred and already-common bridge do not double deduct',()=>{const v=pref();assert.equal(C.calculatePreferred(v).metrics['Common-attributed measure'],'110');v.earningsBasis='already-common';assert.equal(C.calculatePreferred(v).metrics['Common-attributed measure'],'120');});
test('Unknown preferred preserves already-common but not total; negative earnings preserved',()=>{const v=pref();v.preferred=null;assert.equal(C.calculatePreferred(v).metrics['Common-attributed measure'],null);v.earningsBasis='already-common';v.earnings='-10';const r=C.calculatePreferred(v);assert.equal(r.metrics['Common-attributed measure'],'-10');assert.equal(r.metrics['Total distributions'],null);assert.equal(r.metrics['Common measure less common distributions'],'-100');});
test('Decimal precision maintained',()=>{const v=pref();v.earnings='0.3';v.preferred='0.1';assert.equal(C.calculatePreferred(v).metrics['Common-attributed measure'],'0.2');});
test('Invalid decimals and inputs rejected instead of coerced',()=>{for(const bad of ['1,000','1e6','NaN','Infinity',' ','9'.repeat(49),'-1']){const v=jv();v.consolidatedDebt=bad;assert.throws(()=>C.calculateJv(v));}const v=pref();v.periodStart='2027-01-01';assert.throws(()=>C.calculatePreferred(v));});
test('CSV quoted cells, CRLF, invalid quotes and bounds',()=>{assert.deepEqual(C.parseCsv('"a,b",2\r\n"c""d",3'),[['a,b','2'],['c"d','3']]);assert.throws(()=>C.parseCsv('"abc'));assert.throws(()=>C.parseCsv('"a"x'));assert.throws(()=>C.parseCsv('x'.repeat(100001)));});
test('CSV neutralizes formulas while keeping numeric negative results',()=>{const r=C.csv([['=HYPERLINK("x")','@formula','-20','-cmd','+1']]);assert.match(r,/"'=HYPERLINK/);assert.match(r,/"-20"/);assert.match(r,/"'-cmd"/);});

test("Empty debt schedules are unknown, not zero",()=>{const v=liq();v.maturities=[];assert.throws(()=>C.calculateLiquidity(v));const j=jv();j.jvs=[];assert.throws(()=>C.calculateJv(j));});

test('Preferred metadata uses date/currency/scale and earnings attribution, never debt basis',()=>{const v=pref();delete v.meta.basis;v.earningsDefinition='Synthetic nine-month earnings attributable to parent';const r=C.calculatePreferred(v);assert.equal(r.metrics['Common-attributed measure'],'110');assert.equal(Object.hasOwn(r.inputs.meta,'basis'),false);assert.deepEqual(r.inputs.meta,{asOf:'2026-09-30',currency:'USD',scale:'million'});assert.equal(r.inputs.earningsDefinition,v.earningsDefinition);assert.equal(r.rows[0][1],v.earningsDefinition);v.meta={...v.meta,basis:'irrelevant-input'};assert.equal(C.calculatePreferred(v).inputs.meta.basis,undefined);});
test('Fiscal2027and2028buckets all included, separate resource date and residual labels exported',()=>{const v=liq();v.maturityBasis='fiscal';v.resourceDate='2027-09-30';delete v.horizonEnd;v.maturities=[{...meta,date:'2027',amount:'90',scope:'Consolidated'},{...meta,date:'2028',amount:'100',scope:'Consolidated'}];const r=C.calculateLiquidity(v);assert.equal(r.metrics['Complete supplied maturity subtotal'],'190');assert.equal(r.metrics['Available liquidity'],null);assert.equal(r.metrics['Residual after supplied fiscal buckets'],null);assert.equal(r.metrics['Residual after supplied fiscal buckets and mandatory spend'],null);assert.equal(r.metrics['Facility amount at resource date (informational only)'],'30');assert.equal(Object.hasOwn(r.metrics,'Residual after maturities'),false);assert.equal(r.inputs.resourceDate,'2027-09-30');assert.equal(r.inputs.horizonEnd,undefined);assert.deepEqual(r.inputs.meta,meta);assert.match(r.warnings.join(' '),/does not select maturity buckets/);const exported=C.csv([['Input JSON',JSON.stringify(r.inputs)],...Object.entries(r.metrics)]);assert.match(exported,/resourceDate/);assert.doesNotMatch(exported,/horizonEnd/);assert.match(exported,/Residual after supplied fiscal buckets/);v.resourceDate='2029-09-30';assert.equal(C.calculateLiquidity(v).metrics['Available liquidity'],null);});
test('Fiscal resource date required and independent from unused dated cutoff',()=>{const v=liq();v.maturityBasis='fiscal';v.maturities[0].date='2027';assert.throws(()=>C.calculateLiquidity(v),/Resource eligibility date/);v.resourceDate='2027-09-30';v.horizonEnd='not-used';assert.equal(C.calculateLiquidity(v).metrics['Complete supplied maturity subtotal'],'90');v.resourceDate='2026-09-01';assert.throws(()=>C.calculateLiquidity(v),/must follow/);});

test('Fiscal2030cannot use2027resource check to claim complete funding',()=>{const v=liq();v.maturityBasis='fiscal';v.resourceDate='2027-09-30';v.facilityExpiry='2028-09-30';v.maturities[0].date='2030';const r=C.calculateLiquidity(v);assert.equal(r.metrics['Known maturity subtotal'],'90');assert.equal(r.metrics['Complete supplied maturity subtotal'],'90');assert.equal(r.metrics['Facility amount at resource date (informational only)'],'30');assert.equal(r.metrics['Available liquidity'],null);assert.equal(r.metrics['Residual after supplied fiscal buckets'],null);assert.equal(r.metrics['Residual after supplied fiscal buckets and mandatory spend'],null);assert.match(r.warnings.join(' '),/withheld in fiscal mode/);});
test('Maturity CSV canonical decimals include +90roundtrip and preserve unknown',()=>{const rows=[['2027-03-31','+90','=USER_TEXT','2026-09-30'],['2028-03-31','000.10','ordinary','2026-09-30'],['2028-06-30','','unknown','2026-09-30']];const normalized=C.normalizeMaturityRows(rows);assert.equal(normalized[0][1],'90');assert.equal(normalized[1][1],'0.1');assert.equal(normalized[2][1],'');const text=C.csv(normalized);assert.doesNotMatch(text,/'\+90/);assert.match(text,/'=USER_TEXT/);const imported=C.normalizeMaturityRows(C.parseCsv(text));assert.equal(imported[0][1],'90');assert.equal(imported[1][1],'0.1');assert.equal(imported[2][1],'');const v=liq();v.maturities=imported.slice(0,1).map(r=>({...meta,date:r[0],amount:r[1],scope:r[2]}));assert.equal(C.calculateLiquidity(v).metrics['Complete supplied maturity subtotal'],'90');assert.throws(()=>C.normalizeMaturityRows([['x','=1+2','scope','x']]));});

test('Capital display preserves small signed amounts and shortfalls across rounding boundaries',()=>{
 for(const [raw,shown] of [['0','0'],['0.00001','1.0000e-5'],['-0.00001','-1.0000e-5'],['0.000049999','4.9999e-5'],['0.00005','0.0001'],['-0.00005','-0.0001'],['1e-20','1.0000e-20']])assert.equal(C.format(raw),shown);
 assert.equal(C.format(null),'Not defined / incomplete');
 assert.equal(C.format('Not supplied'),'Not supplied');
 const v=pref();v.earnings='0.00001';v.preferred='0';v.common='0.00002';
 const r=C.calculatePreferred(v);
 assert.equal(C.format(r.metrics['Common-attributed measure']),'1.0000e-5');
 assert.equal(C.format(r.metrics['Common measure less common distributions']),'-1.0000e-5');
 v.earnings='0.3';v.preferred='0.1';v.common='0.2';
 assert.equal(C.format(C.calculatePreferred(v).metrics['Common measure less common distributions']),'0');
});

test('Capital results identify the precision-display and CSV revision',()=>{
 assert.equal(C.formulaVersion,'capital-1.0.2');
 for(const result of [C.calculateJv(jv()),C.calculateLiquidity(liq()),C.calculatePreferred(pref())])assert.equal(result.formulaVersion,C.formulaVersion);
});

test('CSV accepts BOM and CR, LF or CRLF without corrupting quoted line breaks',()=>{
 const header='date,amount,scope,asOf';
 const row='2027-03-31,+90,"Bond, ""A""\r\nSecond line",2026-09-30';
 for(const eol of ['\r','\n','\r\n']){
  const parsed=C.parseCsv('\ufeff'+header+eol+row+eol);
  assert.deepEqual(parsed[0],['date','amount','scope','asOf']);
  assert.deepEqual(parsed[1],['2027-03-31','+90','Bond, "A"\r\nSecond line','2026-09-30']);
  assert.deepEqual(C.parseCsv(C.csv(parsed)),[parsed[0],['2027-03-31',"'+90",parsed[1][2],'2026-09-30']]);
 }
 assert.throws(()=>C.parseCsv('"a"\rb"c'),/quote/);
});

test('CSV neutralizes leading whitespace formulas and keeps negative decimal results numeric',()=>{
 const values=['=1+1','  =1+1','\t=1+1','\n=1+1','\r@SUM(1)',' +SUM(1)',' -cmd','ordinary','-20','-1e-20'];
 const escaped=C.parseCsv(C.csv([values]))[0];
 assert.deepEqual(escaped,values.map((value,i)=>i<7?"'"+value:value));
 assert.deepEqual(C.parseCsv(C.csv([escaped]))[0],escaped);
});
