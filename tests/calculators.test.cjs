const {test} = require('node:test');
const assert = require('node:assert/strict');
const {calculate} = require('../calculators.js');
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
