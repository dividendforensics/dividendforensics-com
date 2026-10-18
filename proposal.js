/* Conditional proposal validation. No tracking/storage; sends only on a visitor's submit. */
(() => {
  const form=document.getElementById('proposal-form');if(!form)return;
  const type=form.querySelector('#rd-t'),terms=form.querySelector('[data-proposal-terms]'),status=form.querySelector('.proposal-status'),button=form.querySelector('[type=submit]');
  const budgetState=form.querySelector('#rd-budget-state'),budget=form.querySelector('#rd-budget'),currency=form.querySelector('#rd-currency');
  const projectTypes=new Set(['Paid article or column','Commissioned REIT/BDC research','Content licensing','Written-content collaboration']);
  let pending=false;
  function budgetValidity(){
    budget.setCustomValidity('');
    if(budget.disabled||!budget.value.trim())return;
    const pieces=budget.value.trim().match(/^(\d+(?:\.\d{1,2})?)(?:\s*[-–]\s*(\d+(?:\.\d{1,2})?))?$/);
    if(!pieces||!(Number(pieces[1])>0)||!Number.isFinite(Number(pieces[1]))||(pieces[2]&&(!Number.isFinite(Number(pieces[2]))||Number(pieces[2])<Number(pieces[1]))))budget.setCustomValidity('Use a positive ungrouped amount or an increasing range, such as 1500-2500.');
  }
  function update(){
    const project=projectTypes.has(type.value);terms.hidden=!project;
    terms.querySelectorAll('input,textarea,select').forEach(el=>{el.disabled=!project;el.required=project&&el.hasAttribute('data-project-required');});
    const specified=project&&budgetState.value==='specified';form.querySelector('[data-budget-fields]').hidden=!specified;
    budget.disabled=currency.disabled=!specified;budget.required=currency.required=specified;
    button.textContent=project?'Submit project proposal':type.value==='Question or correction'?'Send question or correction':'Submit inquiry';budgetValidity();
  }
  type.addEventListener('change',update);budgetState.addEventListener('change',update);budget.addEventListener('input',budgetValidity);update();
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(pending)return;
    budgetValidity();if(!form.checkValidity()){form.reportValidity();return;}
    pending=true;button.disabled=true;form.setAttribute('aria-busy','true');status.hidden=false;status.textContent='Submitting to the form service… Email delivery has not been confirmed.';
    const data=new FormData(form);data.append('Submission reference',globalThis.crypto?.randomUUID?.()||String(Date.now()));
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
    try{
      const response=await fetch(form.dataset.ajaxAction,{method:'POST',body:data,headers:{Accept:'application/json'},signal:controller.signal});
      const result=await response.json();
      if(!response.ok||!(result.success===true||result.success==='true'))throw new Error('Service did not confirm acceptance.');
      status.textContent='The form service accepted your submission. This does not confirm email delivery or project acceptance. Your entries remain here for reference; avoid resubmitting the same proposal.';
    }catch(error){status.textContent='We could not confirm your submission. Your entries have been kept. A timed-out request may already have reached the service; please avoid duplicate submissions and use dividendforensics@gmail.com if needed.';}
    finally{clearTimeout(timeout);pending=false;button.disabled=false;form.removeAttribute('aria-busy');status.focus();}
  });
})();
