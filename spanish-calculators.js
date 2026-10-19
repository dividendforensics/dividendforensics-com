/* Spanish presentation; the shared decimal arithmetic remains the English model. */
(function(root) {
  'use strict';
  const Decimal=typeof module==='object' && module.exports ? require('./vendor/decimal.js/decimal.js') : root.Decimal;
  const D=Decimal ? Decimal.clone({precision:80,rounding:Decimal.ROUND_HALF_UP}) : null;
  const VERSION='es-1.0.3';
  const labels={
    'Annual gross distributions':'Distribuciones brutas anuales (USD)',
    'Annual after-withholding income':'Ingreso anual después de la retención supuesta (USD)',
    'Monthly equivalent':'Promedio mensual (USD)',
    'Capital for monthly target':'Capital para el objetivo mensual (USD)',
    'Current payout':'Payout actual', 'Current coverage':'Cobertura actual',
    'Stressed payout':'Payout bajo estrés', 'Stressed per-share cushion':'Margen bajo estrés por acción (USD)'
  };
  function shown(value,type){
    if(value===null)return 'No definido';
    const d=new D(String(value)),digits=type==='precise'?4:2;
    let text;
    if(!d.isZero() && d.abs().lt(new D(10).pow(-digits))) {
      const display=d.toSignificantDigits(4);
      text=(display.decimalPlaces()>24?display.toExponential():display.toFixed()).replace('.',',');
    }
    else {
      const [whole,fraction]=d.toFixed(digits).split('.');
      const grouped=whole.replace('-','').length>4 ? whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.') : whole;
      text=grouped+','+fraction;
    }
    return text+(type==='percent'?' %':type==='multiple'?' ×':'');
  }
  if(typeof module==='object' && module.exports)module.exports={format:shown,version:VERSION};
  if(typeof document==='undefined')return;
  document.querySelectorAll('[data-es-calculator]').forEach(form=>{
    const output=document.querySelector('[data-es-result]'),error=form.querySelector('[role=alert]');
    const clear=message=>{output.replaceChildren();const p=document.createElement('p');p.textContent=message;output.append(p);};
    function run(){
      error.hidden=true;
      if(!form.reportValidity()){clear('Revise los valores y límites indicados antes de calcular.');return;}
      if(!window.DFBOriginal || !window.Decimal){clear('No se ha cargado la biblioteca de cálculo. Vuelva a cargar la página.');return;}
      try{
        const input=Object.fromEntries([...form.querySelectorAll('input[name]')].map(el=>[el.name,el.value]));
        const result=DFBOriginal.calculate(form.dataset.esCalculator,input);
        if(result.metrics.some(metric=>!Object.prototype.hasOwnProperty.call(metric,'exactValue'))){clear('La biblioteca de cálculo está desactualizada. Vuelva a cargar esta página.');return;}
        output.replaceChildren();
        const h=document.createElement('h2');h.textContent='Resultado del escenario';output.append(h);
        const dl=document.createElement('dl');dl.className='calculator-metrics';
        result.metrics.forEach(metric=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=labels[metric.label];dd.textContent=shown(metric.exactValue,metric.format);div.append(dt,dd);dl.append(div);});output.append(dl);
        const note=document.createElement('p');note.className='small-note';note.textContent='Ejemplo o hipótesis del usuario; no es una previsión. La retención no determina su impuesto final. No incluye conversión de divisas. Versión de cálculo: '+result.formulaVersion;output.append(note);
      }catch(e){clear('No hay un resultado válido.');error.textContent=e.code==='PRECISION_RANGE'?'Estas entradas están demasiado cerca de un límite de redondeo para el modelo de 80 cifras significativas. Reduzca las cifras de entrada o cambie las hipótesis.':'Introduzca números finitos con punto decimal y revise los límites, períodos y denominadores.';error.hidden=false;}
    }
    form.addEventListener('submit',e=>{e.preventDefault();run();});
    form.addEventListener('reset',()=>setTimeout(()=>{error.hidden=true;clear('Valores iniciales restablecidos. Seleccione Calcular para actualizar el resultado.');},0));
    form.addEventListener('input',()=>{error.hidden=true;clear('Las hipótesis han cambiado. Seleccione Calcular para actualizar el resultado.');});
    if(root.DFBOriginal && D){form.querySelector("[data-calculator-controls]").disabled=false;clear("Seleccione Calcular para ver su escenario.");}
  });
})(typeof globalThis!=='undefined'?globalThis:this);
