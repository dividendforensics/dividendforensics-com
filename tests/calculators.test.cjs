const {test} = require('node:test');
const assert = require('node:assert/strict');
const {calculate,format} = require('../calculators.js');
const close = (a,b) => assert.ok(Math.abs(a-b)<1e-7, `${a} != ${b}`);
test('income and target use the same after-withholding basis',()=>{
  const r=calculate('income',{capital:10000,yield:5,tax:15,target:500});
  close(r.metrics[0].value,500); close(r.metrics[1].value,425); close(r.metrics[3].value,6000/.0425);
});
test('zero net yield cannot fund a positive target',()=>{
  assert.equal(calculate('income',{capital:10000,yield:5,tax:100,target:500}).metrics[3].value,null);
  assert.equal(calculate('income',{capital:0,yield:0,tax:0,target:0}).metrics[3].value,0);
});
test('reinvestment agrees with geometric series including month-end contributions',()=>{
  const r=calculate('reinvestment',{capital:10000,contribution:200,yield:6,tax:0,years:10});
  const growth=(1.005)**120, expected=10000*growth+200*(growth-1)/.005;
  close(r.metrics[0].value,expected);close(r.metrics[1].value,34000);
  close(r.metrics[0].value-r.metrics[1].value,r.metrics[2].value);
  assert.equal(r.rows.length,10);
});
test('zero yield reinvestment produces savings only',()=>{
  const r=calculate('reinvestment',{capital:1000,contribution:100,yield:0,tax:0,years:2});
  close(r.metrics[0].value,3400);close(r.metrics[2].value,0);
});
test('payout stress shows undefined ratios and a negative cushion',()=>{
  const r=calculate('payout',{affo:4,dividend:3,decline:15});
  close(r.metrics[0].value,75); close(r.metrics[2].value,3/3.4*100);
  const zero=calculate('payout',{affo:4,dividend:3,decline:100});
  assert.equal(zero.metrics[2].value,null);close(zero.metrics[3].value,-3);
  assert.equal(calculate('payout',{affo:4,dividend:0,decline:0}).metrics[1].value,null);
});
test('FFO bridge handles sale losses and signed issuer adjustments',()=>{
  const r=calculate('bridge',{net:50,depreciation:40,gains:-10,ffoOther:5,capex:8,rent:2,affoOther:-1});
  close(r.metrics[0].value,105);close(r.metrics[1].value,94);
});
test('NAV scale cancellation and negative equity are preserved',()=>{
  const r=calculate('nav',{noi:100,cap:6,debt:600,cash:50,shares:100});
  close(r.metrics[2].value,(100/.06-550)/100);
  assert.ok(calculate('nav',{noi:1,cap:10,debt:100,cash:0,shares:10}).metrics[1].value<0);
});
test('refinancing savings have a negative expense sign',()=>{
  const r=calculate('refinancing',{principal:200,old:5,new:3,shares:100});
  close(r.metrics[2].value,-4);close(r.metrics[3].value,-.04);
});
test('dividends do not hide a negative total return',()=>{
  const r=calculate('return',{start:100,end:90,dividends:6,buyFees:0,sellFees:1});
  close(r.metrics[0].value,-5);
});
test('purchase fees belong in the initial capital denominator',()=>{
  const r=calculate('return',{start:100,end:110,dividends:5,buyFees:2,sellFees:1});
  close(r.metrics[0].value,12/102*100);
});
test('nonfinite inputs fail instead of displaying misleading output',()=>{
  assert.throws(()=>calculate('income',{capital:NaN,yield:5,tax:0,target:500}),/finite/);
});

test('nonpositive AFFO gives no misleading payout or coverage percentage',()=>{
  for (const affo of [0,-1]) {
    const r=calculate('payout',{affo,dividend:2,decline:0});
    assert.deepEqual(r.metrics.slice(0,3).map(m=>m.value),[null,null,null]);
    close(r.metrics[3].value,affo-2);
    assert.match(r.note,/not meaningful/);
  }
});

test('downside stress deepens an AFFO loss rather than reducing it',()=>{
  const r=calculate('payout',{affo:-4,dividend:3,decline:25});
  close(r.rows[1][1],-5);
  close(r.metrics[3].value,-8);
  assert.equal(r.metrics[2].value,null);
  close(calculate('payout',{affo:0,dividend:3,decline:25}).rows[1][1],0);
});

test('zero denominators identify the input problem, not overflow',()=>{
  assert.throws(()=>calculate('nav',{noi:100,cap:6,cash:0,debt:0,shares:0}),/shares must be greater/);
  assert.throws(()=>calculate('nav',{noi:100,cap:0,cash:0,debt:0,shares:100}),/rate must be greater/);
  assert.throws(()=>calculate('refinancing',{principal:100,old:3,new:5,shares:0}),/shares must be greater/);
  assert.throws(()=>calculate('return',{start:0,end:10,dividends:0,buyFees:0,sellFees:0}),/Purchase price/);
  for (const years of [0,0.5,51]) assert.throws(()=>calculate('reinvestment',{capital:100,contribution:0,yield:5,tax:0,years}),/whole number of years/);
});

test('percentage points, money scale and per-share units agree in all seven tools',()=>{
  close(calculate('income',{capital:100,yield:5,tax:0,target:0}).metrics[0].value,5);
  close(calculate('income',{capital:100,yield:0.05,tax:0,target:0}).metrics[0].value,0.05);
  const reinvest=calculate('reinvestment',{capital:100,contribution:0,yield:12,tax:50,years:1});
  close(reinvest.metrics[0].value,100*1.005**12);
  close(calculate('payout',{affo:0.04,dividend:0.03,decline:0}).metrics[0].value,75);
  close(calculate('bridge',{net:0.5,depreciation:0.4,gains:0.1,ffoOther:0,capex:0.08,rent:0.02,affoOther:0}).metrics[1].value,0.7);
  close(calculate('nav',{noi:1,cap:5,debt:0,cash:0,shares:2}).metrics[2].value,10);
  close(calculate('refinancing',{principal:1,old:3,new:5,shares:2}).metrics[3].value,0.01);
  close(calculate('return',{start:1,end:1.1,dividends:0.05,buyFees:0.02,sellFees:0.01}).metrics[0].value,0.12/1.02*100);
});

test('small nonzero results retain their sign and do not round to zero',()=>{
  assert.equal(format(null),'Not defined');
  assert.equal(format(0),'0.00');
  assert.equal(format(0.001),'0.001');
  assert.equal(format(-0.000001,'precise'),'-0.000001');
  assert.equal(format(1e-9,'percent'),'0.000000001%');
});

test('decimal bridge cancellation is exact rather than a visible floating-point residual',()=>{
  for(const values of [{net:0.1,depreciation:0.2,gains:0.3},{net:'0.1',depreciation:'0.2',gains:'0.3'}]){
    const r=calculate('bridge',{...values,ffoOther:0,capex:0,rent:0,affoOther:0});
    assert.equal(r.metrics[0].value,0);
    assert.equal(r.metrics[1].value,0);
    assert.equal(format(r.metrics[0].value),'0.00');
    assert.equal(r.formulaVersion,'original-1.1.2');
  }
});

test('genuine tiny decimal remainders keep both signs and are never epsilon-clamped',()=>{
  const base={net:'0.1',depreciation:'0.2',gains:'0.3',ffoOther:0,capex:0,rent:0};
  for(const affoOther of ['0.000000000000000001','-0.000000000000000001']){
    const r=calculate('bridge',{...base,affoOther});
    assert.equal(r.metrics[0].value,0);
    assert.equal(r.metrics[1].value,Number(affoOther));
    assert.equal(format(r.metrics[1].value),affoOther);
    assert.equal(format(r.metrics[1].value).startsWith('-'),affoOther.startsWith('-'));
  }
});

test('raw entered decimal strings survive the Number precision boundary',()=>{
  const r=calculate('bridge',{net:'0.100000000000000000001',depreciation:'0',gains:'0.1',ffoOther:'0',capex:'0',rent:'0',affoOther:'0'});
  assert.equal(r.metrics[0].value,1e-21);
  assert.equal(format(r.metrics[0].value),'0.000000000000000000001');
  const tiny=calculate('bridge',{net:'1e-400',depreciation:0,gains:0,ffoOther:0,capex:0,rent:0,affoOther:0});
  assert.equal(tiny.metrics[0].value,'1e-400');
  assert.equal(format(tiny.metrics[0].value),'1e-400');
});

test('all original tools use decimal operations without changing fees or withholding',()=>{
  assert.equal(calculate('income',{capital:'0.1',yield:'0.2',tax:'0.3',target:'0'}).metrics[1].value,0.0001994);
  assert.equal(calculate('reinvestment',{capital:'0.1',contribution:'0.2',yield:'0',tax:'0',years:'1'}).metrics[0].value,2.5);
  assert.equal(calculate('payout',{affo:'0.3',dividend:'0.1',decline:'0'}).metrics[3].value,0.2);
  assert.equal(calculate('nav',{noi:'0.001',cap:'1',debt:'0.3',cash:'0.2',shares:'1'}).metrics[1].value,0);
  assert.equal(calculate('refinancing',{principal:'0.1',old:'0.1',new:'0.3',shares:'1'}).metrics[2].value,0.0002);
  const total=calculate('return',{start:'0.1',end:'0.3',dividends:'0',buyFees:'0.1',sellFees:'0.1'});
  assert.equal(total.metrics[0].value,0);
  assert.equal(total.metrics[3].value,100);
});

test('decimal formatting keeps grouping, tiny signs and explicit invalid-input handling',()=>{
  assert.equal(format('1234567.125'),'1,234,567.13');
  assert.equal(format('-1234567.125','precise'),'-1,234,567.1250');
  for(const value of ['', ' ', 'NaN', 'Infinity','0xff','0b11','1e-10001', null, undefined]) assert.throws(()=>calculate('income',{capital:value,yield:5,tax:0,target:500}),/finite/);
  assert.throws(()=>calculate('income',{capital:'1e308',yield:'1e308',tax:0,target:0}),/too large/);
});

test('authoritative exact decimal results round below, at and above the half-cent boundary',()=>{
  const spanish=require('../spanish-calculators.js');
  const cases=[
    ['1024.59999999999999999999','76.84499999999999999999925','76.84','76,84'],
    ['1024.6','76.845','76.85','76,85'],
    ['1024.60000000000000000001','76.84500000000000000000075','76.85','76,85']
  ];
  for(const [capital,exact,en,es] of cases){
    const r=calculate('income',{capital,yield:'7.5',tax:'0',target:'0'});
    assert.equal(r.metrics[0].exactValue,exact);
    assert.equal(r.metrics[1].exactValue,exact);
    assert.equal(r.exactRows[1][1],exact);
    assert.equal(r.numericCells[1][0],false);
    assert.equal(r.numericCells[1][1],true);
    assert.equal(format(r.metrics[0].exactValue),en);
    assert.equal(spanish.format(r.metrics[0].exactValue),es);
    assert.equal(typeof r.metrics[0].value,'number'); // Compatibility convenience only.
    assert.equal(r.arithmetic.precision,80);
  }
  assert.equal(format('-76.84499999999999999999925'),'-76.84');
  assert.equal(format('-76.845'),'-76.85');
  assert.equal(spanish.version,'es-1.0.2');
});

test('all seven calculator result paths retain decimal strings for display and serialization',()=>{
  const cases={
    income:{capital:'0.1',yield:'0.2',tax:'0.3',target:'0'},
    reinvestment:{capital:'0.1',contribution:'0.2',yield:'1',tax:'15',years:'1'},
    payout:{affo:'0.3',dividend:'0.1',decline:'0'},
    bridge:{net:'0.100000000000000000001',depreciation:'0',gains:'0.1',ffoOther:'0',capex:'0',rent:'0',affoOther:'0'},
    nav:{noi:'0.001',cap:'1',debt:'0.3',cash:'0.2',shares:'1'},
    refinancing:{principal:'0.1',old:'0.1',new:'0.3',shares:'1'},
    return:{start:'0.1',end:'0.3',dividends:'0',buyFees:'0.1',sellFees:'0.1'}
  };
  for(const [kind,input] of Object.entries(cases)){
    const r=calculate(kind,input);
    assert.ok(r.metrics.every(m=>m.exactValue===null || typeof m.exactValue==='string'),kind);
    assert.equal(r.exactRows.length,r.rows.length);
    assert.equal(r.numericCells.length,r.rows.length);
    for(let i=0;i<r.rows.length;i++)for(let j=0;j<r.rows[i].length;j++)if(r.numericCells[i][j])assert.equal(typeof r.exactRows[i][j],'string');
  }
  assert.equal(calculate('bridge',cases.bridge).metrics[0].exactValue,'1e-21');
  const spanish=require('../spanish-calculators.js');
  assert.equal(spanish.format('1e-400'),'1e-400');
  assert.equal(spanish.format('-1e-21'),'-0,000000000000000000001');
  assert.equal(spanish.format(null),'No definido');
  assert.equal(spanish.format('141176.470588235294117647'),'141.176,47');
});

test('FFO bridge displayed lines reconcile with displayed subtotals below one cent',()=>{
  const Decimal=require('../vendor/decimal.js/decimal.js');
  for(const amount of ['0.004','0.005','0.0099','0.004000000000000000001']){
    const r=calculate('bridge',Object.fromEntries(['net','depreciation','gains','ffoOther','capex','rent','affoOther'].map(key=>[key,amount])));
    const displayed=r.exactRows.map(row=>format(row[1],'bridge').replaceAll(',',''));
    const subtotal=displayed.slice(0,4).reduce((sum,x)=>sum.plus(x),new Decimal(0));
    assert.equal(subtotal.toString(),new Decimal(displayed[4]).toString());
    assert.equal(displayed.slice(5,8).reduce((sum,x)=>sum.plus(x),subtotal).toString(),new Decimal(displayed[8]).toString());
    assert.equal(format(r.metrics[0].exactValue,r.metrics[0].format),displayed[4]);
    assert.equal(format(r.metrics[1].exactValue,r.metrics[1].format),displayed[8]);
    assert.match(r.note,/without cent rounding/);
    assert.match(r.note,/subtotals, not additional adjustments/);
  }
  assert.equal(format('0.008','bridge'),'0.008');
  assert.equal(format('-0.004','bridge'),'-0.004');
});

test('bridge display bounds extreme precision explicitly while retaining raw CSV values',()=>{
  const raw='0.'+'1'.repeat(100);
  const r=calculate('bridge',{net:raw,depreciation:0,gains:0,ffoOther:0,capex:0,rent:0,affoOther:0});
  assert.equal(r.exactRows[0][1],raw);
  assert.match(format(r.exactRows[0][1],'bridge'),/^≈ /);
  assert.ok(format(r.exactRows[0][1],'bridge').length<90);
  for(const value of ['1e-10000','-1e-10000']){
    assert.equal(format(value,'bridge'),value);
    assert.equal(format(value),value);
  }
});
