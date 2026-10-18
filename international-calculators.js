/* Localized presentation only. Keep the shared model's exact decimal strings. */
(function(root){
 'use strict';
 const Decimal=typeof module==='object'&&module.exports?require('./vendor/decimal.js/decimal.js'):root.Decimal;
 const D=Decimal?Decimal.clone({precision:80,rounding:Decimal.ROUND_HALF_UP}):null;
 function parse(value,locale){
   const s=String(value).trim();
   const pattern=locale==='de'?/^[+-]?(?:\d+(?:,\d*)?|,\d+)$/:/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
   if(s.length>128||!pattern.test(s))throw Error('invalid number');
   return s.replace(',','.');
 }
 function format(value,locale,undefinedText){
   if(value===null)return undefinedText;
   const d=new D(value),comma=locale==='de';
   if(!d.isZero()&&d.abs().lt('0.005'))return d.toSignificantDigits(4).toFixed().replace('.',comma?',':'.');
   const [whole,fraction]=d.toFixed(2).split('.');
   return whole.replace(/\B(?=(\d{3})+(?!\d))/g,comma?'.':',')+(comma?',':'.')+fraction;
 }
 if(typeof module==='object'&&module.exports)module.exports={parse,format};
 if(typeof document==='undefined')return;
 document.querySelectorAll('[data-international-calculator]').forEach(form=>{
   const locale=form.dataset.internationalCalculator,output=document.querySelector('[data-international-result]');
   const messages=JSON.parse(document.getElementById('calculator-translations').textContent),error=form.querySelector('[role=alert]');
   error.id='calculator-input-error';
   function clearInvalid(){form.querySelectorAll('[aria-invalid]').forEach(x=>{x.removeAttribute('aria-invalid');x.removeAttribute('aria-describedby');});}
   function clear(message){output.replaceChildren();const p=document.createElement('p');p.textContent=message;output.append(p);}
   form.addEventListener('submit',e=>{
     e.preventDefault();error.hidden=true;clearInvalid();
     if(!form.reportValidity()){clear(messages.error);return;}
     if(!root.DFBOriginal||!D){clear(messages.unavailable);return;}
     try{
       const input={};
       const bounds={capital:'1000000000000',yield:'100',tax:'100',target:'1000000000'};
       for(const field of form.querySelectorAll('input[name]')){
         try{
           const value=parse(field.value,locale);
           if(new D(value).lt(0)||new D(value).gt(bounds[field.name]))throw Error(messages.range.replace('{max}',bounds[field.name]));
           input[field.name]=value;
         }catch(e){
           field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby',error.id);
           error.textContent=messages.labelsInput?.[field.name]||field.closest('label').firstChild.textContent.trim();
           error.textContent+=': '+(e.message==='invalid number'?messages.error:e.message);
           error.hidden=false;output.replaceChildren();field.focus();return;
         }
       }
       const result=root.DFBOriginal.calculate('income',input);
       if(result.metrics.length!==4||result.metrics.some(m=>!Object.hasOwn(m,'exactValue')))throw Error('version');
       output.replaceChildren();const h=document.createElement('h2');h.textContent=messages.heading;output.append(h);
       const dl=document.createElement('dl');dl.className='calculator-metrics';
       result.metrics.forEach((metric,i)=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=messages.labels[i];dd.textContent=format(metric.exactValue,locale,messages.undefined);div.append(dt,dd);dl.append(div);});output.append(dl);
       const p=document.createElement('p');p.textContent=messages.note;output.append(p);
     }catch(_){output.replaceChildren();error.textContent=messages.unavailable;error.hidden=false;}
   });
   form.addEventListener('input',()=>{error.hidden=true;clearInvalid();clear(messages.changed);});
   form.addEventListener('reset',()=>{error.hidden=true;clearInvalid();clear(messages.pending);});
   if(root.DFBOriginal && D){form.querySelector('[data-calculator-controls]').disabled=false;clear(messages.pending);}
 });
})(typeof globalThis!=='undefined'?globalThis:this);
