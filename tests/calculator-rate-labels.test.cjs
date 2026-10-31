const {test}=require('node:test');
const assert=require('node:assert/strict');
const {calculate}=require('../calculators.js');

test('Income scenario labels retain tiny nonzero yields in display and CSV rows',()=>{
 const r=calculate('income',{capital:'1000000',yield:'0.001',tax:'0',target:'1'});
 const labels=['0.00075%','0.001%','0.00125%'];
 assert.deepEqual(r.rows.map(row=>row[0]),labels);
 assert.deepEqual(r.exactRows.map(row=>row[0]),labels);
 assert.deepEqual(r.exactRows.map(row=>row[1]),['7.5','10','12.5']);
 assert.equal(r.metrics[0].exactValue,'10');
});

test('NAV scenario labels identify the exact cap rates used, including CSV',()=>{
 const r=calculate('nav',{noi:'100',cap:'6.004',debt:'0',cash:'0',shares:'100'});
 const labels=['5.004%','6.004%','7.004%'];
 assert.deepEqual(r.rows.map(row=>row[0]),labels);
 assert.deepEqual(r.exactRows.map(row=>row[0]),labels);
 for(const row of r.exactRows){
  const same=calculate('nav',{noi:'100',cap:row[0].slice(0,-1),debt:'0',cash:'0',shares:'100'});
  assert.equal(row[1],same.metrics[0].exactValue);
  assert.equal(row[3],same.metrics[2].exactValue);
 }
});

test('Exact two-decimal rate labels retain established presentation',()=>{
 const income=calculate('income',{capital:10000,yield:5,tax:0,target:500});
 assert.deepEqual(income.exactRows.map(row=>row[0]),['3.75%','5.00%','6.25%']);
 const nav=calculate('nav',{noi:100,cap:6,debt:600,cash:50,shares:100});
 assert.deepEqual(nav.exactRows.map(row=>row[0]),['5.00%','6.00%','7.00%']);
});

test('Extreme tiny rate labels stay nonzero and bounded with scientific notation',()=>{
 const r=calculate('income',{capital:'1',yield:'1e-10000',tax:'0',target:'0'});
 assert.deepEqual(r.exactRows.map(row=>row[0]),['7.5e-10001%','1e-10000%','1.25e-10000%']);
 assert.ok(r.exactRows.every(row=>row[0].length<25));
});
