/* Spanish presentation; the shared decimal arithmetic remains the English model. */
(() => {
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
    const d=new Decimal(String(value));
    let text=!d.isZero() && d.abs().lt('0.005') ? d.toExponential(3).replace('.',',') : new Intl.NumberFormat('es',{minimumFractionDigits:2,maximumFractionDigits:2}).format(d.toNumber());
    return text+(type==='percent'?' %':type==='multiple'?' ×':'');
  }
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
        output.replaceChildren();
        const h=document.createElement('h2');h.textContent='Resultado del escenario';output.append(h);
        const dl=document.createElement('dl');dl.className='calculator-metrics';
        result.metrics.forEach(metric=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=labels[metric.label];dd.textContent=shown(metric.value,metric.format);div.append(dt,dd);dl.append(div);});output.append(dl);
        const note=document.createElement('p');note.className='small-note';note.textContent='Ejemplo o hipótesis del usuario; no es una previsión. La retención no determina su impuesto final. No incluye conversión de divisas. Versión de cálculo: '+result.formulaVersion;output.append(note);
      }catch(_){clear('No hay un resultado válido.');error.textContent='Introduzca números finitos con punto decimal y revise los límites, períodos y denominadores.';error.hidden=false;}
    }
    form.addEventListener('submit',e=>{e.preventDefault();run();});
    form.addEventListener('reset',()=>setTimeout(()=>{error.hidden=true;clear('Ejemplo restablecido. Seleccione Calcular para actualizar el resultado.');},0));
    form.addEventListener('input',()=>{error.hidden=true;clear('Las hipótesis han cambiado. Seleccione Calcular para actualizar el resultado.');});
  });
})();
