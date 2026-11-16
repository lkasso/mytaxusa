// Reload restored browser-history pages so deleted returns and attachments cannot reappear.
window.addEventListener('pageshow', event => { if (event.persisted) window.location.reload(); });

// Show diagnostic and browser validation errors beside the affected controls.
const form = document.querySelector('[data-field-errors]');
if (form) {
  const errors = JSON.parse(form.dataset.fieldErrors);
  function showError(control, message) {
    control.classList.add('field-invalid');
    control.setAttribute('aria-invalid', 'true');
    const id = `${control.id}-error`;
    let hint = document.getElementById(id);
    if (!hint) {
      hint = document.createElement('span');
      hint.id = id;
      hint.className = 'field-error';
      control.after(hint);
    }
    hint.textContent = message;
    control.setAttribute('aria-describedby', id);
    const group = control.closest('details');
    if (group) group.open = true;
  }
  for (const control of form.querySelectorAll('input:not([type="hidden"]), select')) {
    control.id = control.name;
    if (errors[control.name]) showError(control, errors[control.name]);
    control.addEventListener('invalid', () => showError(control, control.validationMessage));
    control.addEventListener('input', () => {
      if (control.validity.valid) {
        control.classList.remove('field-invalid');
        control.removeAttribute('aria-invalid');
        control.removeAttribute('aria-describedby');
        document.getElementById(`${control.id}-error`)?.remove();
      }
    });
  }
  function revealTarget() {
    const hash = decodeURIComponent(location.hash.slice(1));
    let target = document.getElementById(hash);
    if (!target && hash === 'personal') target = form.querySelector('.field-invalid');
    if (!target && /^dependents\[\d+\]/.test(hash)) {
      const n = hash.match(/\d+/)[0];
      target = form.querySelector(`[name^="dependent_${n}_"].field-invalid`);
    }
    if (!target && /^w2s\[\d+\]/.test(hash)) {
      const n = hash.match(/\d+/)[0];
      target = form.querySelector(`[name^="w2_${n}_"].field-invalid`);
    }
    if (target) {
      const group = target.closest('details');
      if (group) group.open = true;
      target.focus();
      target.scrollIntoView({block: 'center'});
    }
  }
  revealTarget();
  window.addEventListener('hashchange', revealTarget);
}

// Require all questions and document facts once a repeated row is started.
if (form) {
  function updateRequirements() {
    const spouseRequired = form.querySelector('[name="status"]')?.value === 'Married Filing Jointly';
    for (const key of ['spouse', 'spouse_ssn', 'spouse_dob']) {
      const control = form.querySelector(`[name="${key}"]`);
      if (control) control.required = spouseRequired;
    }
    for (const [prefix, required] of [
      ['dependent', ['name','ssn','dob','relationship','months','student','own_support','resident','joint_return']],
      ['w2', ['employer','ein','address','wages','withheld']]
    ]) {
      for (let n = 0; n < 6; n++) {
        const controls = [...form.querySelectorAll(`[name^="${prefix}_${n}_"]`)];
        const active = ['dependent','w2'].includes(prefix) ? controls.some(control => !control.closest('fieldset')?.disabled) : controls.some(control => control.value.trim() !== '');
        for (const control of controls) {
          control.required = active && required.includes(control.name.slice(`${prefix}_${n}_`.length));
        }
      }
    }
  }
  updateRequirements();
  form.addEventListener('input', updateRequirements);
  form.addEventListener('change', updateRequirements);
}

// Attach supporting forms without submitting or discarding unsaved tax entries.
for (const upload of document.querySelectorAll('.document-upload')) {
  upload.addEventListener('submit', async event => {
    event.preventDefault();
    const status = upload.querySelector('.upload-status');
    const button = upload.querySelector('button');
    button.disabled = true;
    status.textContent = 'Uploading…';
    try {
      const response = await fetch(upload.action, {method:'POST', body:new FormData(upload), headers:{Accept:'application/json'}});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Upload failed. Try again.');
      const list = upload.parentElement.querySelector('.attachment-list');
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = `/documents/${result.document.id}`;
      link.textContent = result.document.name;
      item.append(link);list.append(item);
      status.classList.remove('field-error');
      status.textContent = 'Uploaded. Review the extraction below before applying values.';
      reviewExtraction(result);
      upload.querySelector('[type="file"]').value = '';
    } catch(error) {
      status.classList.add('field-error');
      status.textContent = error.message;
    } finally {button.disabled = false;}
  });
}

function reviewExtraction(result) {
  if (result.document.form_type==='W-2') { populateUploadedW2(result); return; }
  const panel = document.getElementById('extraction-review');
  if (!panel) return;
  panel.replaceChildren();
  const heading = document.createElement('h3');
  heading.textContent = `Review ${result.document.form_type}: ${result.document.name}`;
  panel.append(heading);
  for (const warning of result.extraction.warnings) {
    const p = document.createElement('p');p.className='notice';p.textContent=warning;panel.append(p);
  }
  const entries = Object.entries(result.extraction.fields);
  if (!entries.length) return;
  const fieldLabels={employer:'Box C — Employer name',ein:'Box B — Employer EIN',address:'Box C — Employer address',employee_name:'Box E — Employee name',employee_address:'Box F — Employee address',wages:'Box 1 — Wages',withheld:'Box 2 — Federal income tax withheld',ss_wages:'Box 3 — Social Security wages',ss_tax:'Box 4 — Social Security tax withheld',medicare_wages:'Box 5 — Medicare wages',medicare_tax:'Box 6 — Medicare tax withheld',interest:'Box 1 — Interest income',interest_withheld:'Box 4 — Federal income tax withheld',unemployment:'Box 1 — Unemployment compensation',unemployment_withheld:'Box 4 — Federal income tax withheld'};
  const reviewFields=document.createElement('div');reviewFields.className='fields';panel.append(reviewFields);
  const controls=[];
  for (const [key,value] of entries) {
    const label=document.createElement('label');label.textContent=fieldLabels[key] || key.replaceAll('_',' ');
    const input=document.createElement('input');input.value=value;input.type=['employer','ein','address','employee_name','employee_address'].includes(key)?'text':'number';if(input.type==='number'){input.min='0';input.step='0.01';}label.append(input);reviewFields.append(label);controls.push([key,input]);
  }
  const apply=document.createElement('button');apply.type='button';apply.textContent='Apply reviewed values to form';
  apply.onclick=()=>{
    const targets=controls.map(([key,input])=>[form.elements.namedItem(key),input.value]).filter(([target])=>target);
    if (targets.some(([target,value])=>target.value && target.value!==value) && !window.confirm('Replace the existing values in the selected form fields?')) return;
    if (document.getElementById('choose-manual')) showEntryMethod('manual');
    if (['1099-INT','1099-G'].includes(result.document.form_type)) {
      const topic=result.document.form_type==='1099-INT'?'interest':'unemployment';
      form.elements.namedItem('has_'+topic).value='Yes';
      showIncomeMethod(topic,'manual');
    }
    for (const [target,value] of targets) {
      target.value=value;target.dispatchEvent(new Event('input',{bubbles:true}));
      const group=target.closest('details');if (group) group.open=true;
    }
    const reviewPanel=document.getElementById('extraction-review');
    if (reviewPanel) {form.after(reviewPanel);reviewPanel.hidden=false;}
    apply.disabled=true;apply.textContent='Applied — use Save and Continue to save';
    targets[0]?.[0].scrollIntoView({block:'center'});
    document.getElementById('extraction-review').scrollIntoView({block:'center'});
  };
  panel.append(apply);
}
for (const button of document.querySelectorAll('.extract-document')) {
  button.addEventListener('click',async()=>{
    button.disabled=true;
    try {
      const data=new FormData();data.append('csrf',form.elements.namedItem('csrf').value);
      const response=await fetch(`/documents/${button.dataset.documentId}/extract`,{method:'POST',body:data});
      if (!response.ok) throw new Error('Unable to extract this document.');
      reviewExtraction(await response.json());
    } catch(error) {window.alert(error.message);}
    finally {button.disabled=false;}
  });
}

// Reveal one dependent at a time; inactive cards never participate in submission.
const addDependent = document.getElementById('add-dependent');
if (addDependent) {
  const cards = [...form.querySelectorAll('.dependent-card')];
  const refresh = () => {
    const full = cards.every(card => !card.hidden);
    addDependent.disabled = full;
    document.getElementById('dependent-limit').textContent = full ? 'Maximum of six dependents reached.' : '';
  };
  addDependent.addEventListener('click', () => {
    const card = cards.find(card => card.hidden);
    if (!card) return;
    card.hidden = false; card.disabled = false;
    form.dispatchEvent(new Event('change', {bubbles:true}));
    card.querySelector('input:not([type="hidden"])').focus();
    refresh();
  });
  for (const card of cards) {
    card.querySelector('.remove-dependent').addEventListener('click', () => {
      for (const control of card.querySelectorAll('input:not([type="hidden"]), select')) {
        control.value = ''; control.required = false;
        control.classList.remove('field-invalid');
        control.removeAttribute('aria-invalid');control.removeAttribute('aria-describedby');
      }
      card.querySelectorAll('.field-error').forEach(hint => hint.remove());
      card.hidden = true; card.disabled = true;
      form.dispatchEvent(new Event('change', {bubbles:true}));
      refresh();addDependent.focus();
    });
  }
  refresh();
}

// Entry method is a UI choice; both paths use the same validation and saved values.
function showEntryMethod(method) {
  const upload=document.getElementById('method-upload');
  if (upload) upload.hidden=method!=='upload';
  for (const kind of ['manual','upload']) document.getElementById(`choose-${kind}`)?.setAttribute('aria-pressed',String(method===kind));
  document.querySelector('.w2-entry-help')?.classList.toggle('method-muted',method==='upload');
}
function revealEmployer(n) {
  const card=document.querySelector(`.w2-card[data-index="${n}"]`);
  if (!card) return;
  card.hidden=false;card.disabled=false;
  form.dispatchEvent(new Event('change',{bubbles:true}));
  refreshEmployers();
}
function refreshEmployers() {
  const cards=[...document.querySelectorAll('.w2-card')];
  const full=cards.length>0 && cards.every(card=>!card.hidden);
  const add=document.getElementById('add-employer');
  if (add) add.disabled=full;
  const limit=document.getElementById('employer-limit');
  if (limit) limit.textContent=full?'Maximum of six employers reached.':'';
}
const manualChoice=document.getElementById('choose-manual');
if (manualChoice) {
  const hasEmployers=Boolean(document.querySelector('.w2-card:not([hidden])'));
  showEntryMethod(hasEmployers ? 'manual':'none');
  manualChoice.addEventListener('click',()=>{
    showEntryMethod('manual');
    if (document.getElementById('add-employer') && !document.querySelector('.w2-card:not([hidden])')) revealEmployer(0);
  });
  document.getElementById('choose-upload').addEventListener('click',()=>{
    showEntryMethod('upload');
    document.getElementById('method-upload').scrollIntoView({block:'start',behavior:'smooth'});
  });
}
const addEmployer=document.getElementById('add-employer');
if (addEmployer) {
  addEmployer.addEventListener('click',()=>{
    showEntryMethod('manual');
    const card=document.querySelector('.w2-card[hidden]');
    if (card) {revealEmployer(Number(card.dataset.index));card.querySelector('input:not([type="hidden"])').focus();}
  });
  for (const card of document.querySelectorAll('.w2-card')) {
    card.querySelector('.remove-employer').addEventListener('click',()=>{
      for (const input of card.querySelectorAll('input:not([type="hidden"])')) {
        input.value='';input.required=false;input.classList.remove('field-invalid');
        input.removeAttribute('aria-invalid');input.removeAttribute('aria-describedby');
      }
      card.querySelectorAll('.field-error').forEach(hint=>hint.remove());
      card.querySelector('[name$="_document_id"]').value='';
      card.querySelector('.w2-import-status')?.remove();
      card.hidden=true;card.disabled=true;
      refreshEmployers();form.dispatchEvent(new Event('change',{bubbles:true}));addEmployer.focus();
    });
  }
  refreshEmployers();
}

function showIncomeMethod(topic, method) {
  const section=document.querySelector(`.income-topic[data-topic="${topic}"]`);
  if (!section) return;
  const yes=section.querySelector('select').value==='Yes';
  section.querySelector('.income-options').hidden=!yes;
  const values=section.querySelector('.income-values');
  values.hidden=!yes || method!=='manual';
  // Keep existing values enabled during upload to avoid losing them on a save.
  values.disabled=!yes;
  values.querySelectorAll('input').forEach(input=>input.required=yes && !values.hidden);
  const upload=document.querySelector(`.income-upload[data-topic="${topic}"]`);
  upload.hidden=!yes || method!=='upload';
  const container=document.getElementById('method-upload');
  if (container) container.hidden=![...container.querySelectorAll('.income-upload')].some(item=>!item.hidden);
  for (const button of section.querySelectorAll('.income-method')) button.setAttribute('aria-pressed',String(yes && button.dataset.method===method));
}
for (const section of document.querySelectorAll('.income-topic')) {
  const topic=section.dataset.topic;
  const answer=section.querySelector('select');
  showIncomeMethod(topic,'manual');
  answer.addEventListener('change',()=>{
    if (answer.value==='No') section.querySelectorAll('.income-values input').forEach(input=>input.value='');
    showIncomeMethod(topic,'manual');
  });
  for (const button of section.querySelectorAll('.income-method')) button.addEventListener('click',()=>{
    showIncomeMethod(topic,button.dataset.method);
    if (button.dataset.method==='upload') document.getElementById('method-upload').scrollIntoView({block:'start'});
  });
}

function populateUploadedW2(result) {
  const cards=[...document.querySelectorAll('.w2-card')];
  let card=cards.find(card=>card.querySelector('[name$="_document_id"]')?.value===result.document.id);
  if (!card) card=cards.find(card=>[...card.querySelectorAll('input:not([type="hidden"])')].every(input=>!input.value));
  if (!card) {window.alert('All six employer forms are in use. Remove an employer before importing another W-2.');return;}
  const index=card.dataset.index;
  const targets=Object.entries(result.extraction.fields).map(([key,value])=>[form.elements.namedItem(`w2_${index}_${key}`),value]).filter(([input])=>input);
  if (!targets.length) {
    const panel=document.getElementById('extraction-review');panel.replaceChildren();
    for (const message of result.extraction.warnings) {const p=document.createElement('p');p.className='notice';p.textContent=message;panel.append(p);}
    return;
  }
  if (targets.some(([input,value])=>input.value && input.value!==value) && !window.confirm('Replace values previously imported from this W-2?')) return;
  revealEmployer(Number(index));showEntryMethod('manual');
  for (const [input,value] of targets) {input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));}
  card.querySelector('[name$="_document_id"]').value=result.document.id;
  card.querySelector('.w2-import-status')?.remove();
  const status=document.createElement('div');status.className='notice w2-import-status';status.setAttribute('role','status');
  const title=document.createElement('strong');title.textContent=`Imported ${result.document.name} into W-2 · Employer ${Number(index)+1}. Review the fields below, then Save and Continue.`;status.append(title);
  for (const message of result.extraction.warnings) {const p=document.createElement('p');p.textContent=message;status.append(p);}
  for (const [key,label] of [['employer','employer name'],['ein','employer EIN'],['address','employer address'],['employee_name','employee name'],['employee_address','employee address']]) {
    const input=form.elements.namedItem(`w2_${index}_${key}`);
    if (!input.value) {
      const p=document.createElement('p');p.textContent=`Could not read ${label}; enter it manually.`;status.append(p);
      input.classList.add('field-invalid');input.setAttribute('aria-invalid','true');
    }
  }
  card.querySelector('summary').after(status);
  card.scrollIntoView({block:'start',behavior:'smooth'});
}
