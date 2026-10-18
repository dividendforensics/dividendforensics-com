const test=require('node:test'),assert=require('node:assert/strict');
const {parse,format}=require('../international-calculators.js');
const engine=require('../calculators.js');
test('German decimal input does not pass through Number',()=>{
 assert.equal(parse('1024,59999999999999999999','de'),'1024.59999999999999999999');
 assert.throws(()=>parse('1024.5','de'));
 assert.throws(()=>parse('10.000','de'));
 assert.equal(parse('10000,50','de'),'10000.50');
 for(const bad of ['1.234,5','1,234.5','1 234','Infinity','0x10','1e3',''])assert.throws(()=>parse(bad,'de'));
 for(const lang of ['ja','zh-Hant']){assert.equal(parse('1024.5',lang),'1024.5');assert.throws(()=>parse('1,000',lang));}
});
test('all locale outputs preserve exact half-cent boundary and tiny signed values',()=>{
 const result=engine.calculate('income',{capital:'1024.59999999999999999999',yield:'7.5',tax:'0',target:'0'});
 assert.equal(result.metrics[0].exactValue,'76.84499999999999999999925');
 assert.equal(format(result.metrics[0].exactValue,'de','?'),'76,84');
 for(const locale of ['ja','zh-Hant'])assert.equal(format(result.metrics[0].exactValue,locale,'?'),'76.84');
 assert.equal(format('-0.000000001','de','?'),'-0,000000001');
 assert.equal(format(null,'de','Nicht definiert'),'Nicht definiert');
});
test('documented income example and goal reproduce without currency conversion',()=>{
 const r=engine.calculate('income',{capital:'10000',yield:'5',tax:'15',target:'500'});
 assert.deepEqual(r.metrics.map(m=>format(m.exactValue,'de','?')),['500,00','425,00','35,42','141.176,47']);
 assert.deepEqual(r.metrics.map(m=>format(m.exactValue,'ja','?')),['500.00','425.00','35.42','141,176.47']);
});
