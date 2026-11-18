/* DiaWise — Vanilla JavaScript SPA. No CDN or cloud API required. */
'use strict';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const requestJson = window.DiaWiseHttp.fetchJson;
const state = { page: 'predict', model: 'pima', generalMode: 'nonlab', foodMode: 'lookup' };
const pima = [
  {key:'Pregnancies',label:'Pregnancies',unit:'Number of pregnancies',placeholder:'e.g. 2',type:'number',min:0,max:25,step:1},
  {key:'Glucose',label:'Glucose',unit:'mg/dL · zero = unknown',placeholder:'e.g. 120',type:'number',min:0,max:400},
  {key:'BloodPressure',label:'Blood pressure',unit:'mmHg · zero = unknown',placeholder:'e.g. 72',type:'number',min:0,max:250},
  {key:'SkinThickness',label:'Skin thickness',unit:'mm · zero = unknown',placeholder:'e.g. 25',type:'number',min:0,max:110},
  {key:'Insulin',label:'Insulin',unit:'μU/mL · zero = unknown',placeholder:'e.g. 88',type:'number',min:0,max:1000},
  {key:'BMI',label:'Body mass index',unit:'kg/m² · zero = unknown',placeholder:'e.g. 28.4',type:'number',min:0,max:100},
  {key:'DiabetesPedigreeFunction',label:'Diabetes pedigree function',unit:'Family-history-based numerical score',placeholder:'e.g. 0.42',type:'number',min:0,max:5},
  {key:'Age',label:'Age',unit:'Years · original PIMA population aged 21+',placeholder:'e.g. 38',type:'number',min:1,max:120},
];
const genderChoices = [['Female','Female'],['Male','Male'],['Other','Other']];
const smokeChoices = [['No Info','No Info'],['never','Never'],['former','Former'],['current','Current'],['ever','Ever'],['not current','Not current']];
const yesNo = [['0','No'],['1','Yes']];
const general = [
  {key:'gender',label:'Gender',unit:'Dataset category',type:'select',choices:genderChoices},
  {key:'age',label:'Age',unit:'Years',type:'number',min:0,max:120,placeholder:'e.g. 45'},
  {key:'hypertension',label:'Hypertension',unit:'Previously reported diagnosis',type:'select',choices:yesNo},
  {key:'heart_disease',label:'Heart disease',unit:'Previously reported diagnosis',type:'select',choices:yesNo},
  {key:'smoking_history',label:'Smoking history',unit:'Select one category',type:'select',choices:smokeChoices},
  {key:'bmi',label:'BMI',unit:'Body mass index (kg/m²)',type:'number',min:.1,max:100,placeholder:'e.g. 26.5'},
  {key:'HbA1c_level',label:'HbA1c level',unit:'% · Required only for full model',type:'number',min:0,max:20,placeholder:'e.g. 5.8'},
  {key:'blood_glucose_level',label:'Blood glucose',unit:'mg/dL · Required only for full model',type:'number',min:0,max:700,placeholder:'e.g. 110'},
];
const foodLookup = [{key:'food_name',label:'Food name',unit:'Search by name (for example, Mango or Almonds)',placeholder:'Type a food name...',type:'text',span:true}];
const foodCustom = [
  {key:'food_name',label:'Food name',unit:'Optional (for display)',placeholder:'Homemade Snack',type:'text',span:true,optional:true},
  {key:'serving_size_g',label:'Serving size',unit:'grams, must be greater than zero',placeholder:'e.g. 200',type:'number',min:.01,max:10000},
  {key:'carbohydrate_g',label:'Carbohydrates',unit:'total grams in this serving',placeholder:'e.g. 60',type:'number',min:0,max:10000},
  {key:'sugar_g',label:'Sugar',unit:'total grams in this serving',placeholder:'e.g. 12',type:'number',min:0,max:10000},
  {key:'fiber_g',label:'Fiber',unit:'total grams in this serving',placeholder:'e.g. 8',type:'number',min:0,max:10000},
  {key:'fat_g',label:'Fat',unit:'total grams in this serving',placeholder:'e.g. 6',type:'number',min:0,max:10000},
  {key:'glycemic_index',label:'Glycemic index',unit:'index 0–100 (do not scale by portion)',placeholder:'e.g. 55',type:'number',min:0,max:100},
];
const example = {
  pima:{Pregnancies:2,Glucose:125,BloodPressure:72,SkinThickness:25,Insulin:88,BMI:28.4,DiabetesPedigreeFunction:.42,Age:38},
  general:{gender:'Female',age:47,hypertension:'0',heart_disease:'0',smoking_history:'never',bmi:29.7,HbA1c_level:6.3,blood_glucose_level:140},
  food:{lookup:{food_name:'Mango'},custom:{food_name:'Homemade Snack',serving_size_g:200,carbohydrate_g:60,sugar_g:12,fiber_g:8,fat_g:6,glycemic_index:55}}
};

function currentFields(){
  if(state.model==='pima') return pima;
  if(state.model==='general') return state.generalMode==='full'?general:general.slice(0,6);
  return state.foodMode==='lookup'?foodLookup:foodCustom;
}
function element(type,className,text){const e=document.createElement(type);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;}
function createField(field){
  const wrap=element('div','input-field'+(field.span?' field-span-full':''));
  const id='f-'+field.key;
  const label=element('label',null,field.label);label.htmlFor=id;wrap.append(label);
  const frame=field.key==='food_name'&&state.foodMode==='lookup'?element('div','autocomplete-wrap'):wrap;
  let control;
  if(field.type==='select'){
    control=element('select','field-control');const please=element('option',null,'Select an option');please.value='';please.disabled=true;please.selected=true;control.append(please);
    for(const [value,text] of field.choices){const option=element('option',null,text);option.value=value;control.append(option);}
  }else{
    control=element('input','field-control');control.type=field.type==='number'?'number':'text';control.placeholder=field.placeholder||'';
    if(field.type==='number'){control.step=String(field.step||'any');if(field.min!==undefined)control.min=String(field.min);if(field.max!==undefined)control.max=String(field.max);}
  }
  control.name=field.key;control.id=id;control.required=!field.optional;control.autocomplete='off';
  frame.append(control);
  if(frame!==wrap){const suggestions=element('div','autocomplete-results');suggestions.id='food-suggestions';suggestions.hidden=true;frame.append(suggestions);wrap.append(frame);bindAutocomplete(control,suggestions);}
  wrap.append(element('small',null,field.unit||''));return wrap;
}
function render(){
  const isPima=state.model==='pima',isGen=state.model==='general';
  $('#form-kicker').textContent=isPima?'MODEL 01 · PIMA':isGen?'MODEL 02 · GENERAL':'MODEL 03 · FOOD';
  $('#form-title').textContent=isPima?'PIMA Diabetes Classification':isGen?'General Diabetes Analysis':'Food Suitability Research';
  $('#form-subtitle').textContent=isPima?'Provide 8 clinical inputs; preprocessing and feature engineering are applied automatically.':isGen?'Choose Full (8) or Non-Lab (6) features to explore the research workflow.':'Search the food catalog or enter nutrition values for an ML prediction.';
  const toggle=$('#mode-toggle');toggle.replaceChildren();toggle.hidden=isPima;
  if(!isPima){
    const modes=isGen?[['full','Full · 8 features'],['nonlab','Non-lab · 6 features']]:[['lookup','Known food lookup'],['custom','Unknown food · ML']];
    const active=isGen?state.generalMode:state.foodMode;
    for(const [val,text] of modes){const b=element('button','mode-button'+(active===val?' active':''),text);b.type='button';b.setAttribute('aria-pressed',active===val?'true':'false');b.addEventListener('click',()=>{if(isGen)state.generalMode=val;else state.foodMode=val;render();});toggle.append(b);}
  }
  const fields=$('#form-fields');fields.replaceChildren();currentFields().forEach(f=>fields.append(createField(f)));
  $('#form-help').textContent=isPima?'The source PIMA dataset represents a specific population; this prediction is not a diagnosis.':isGen?(state.generalMode==='full'?'Eight features, including laboratory measurements, will be used. HbA1c and blood glucose are required.':'Only six non-laboratory features will be used. This research model has low positive precision and must not be treated as screening evidence.'):(state.foodMode==='lookup'?'Known foods return the author-curated dataset label directly; this is not an ML prediction.':'Carbohydrate, sugar, fiber, and fat are normalized to 100 g. Glycemic index remains unchanged. Results between 25% and 75% are reported as uncertain.');
  $('#submit-label').textContent=state.model==='food'&&state.foodMode==='lookup'?'Find food':'Show prediction';
  $('#result-placeholder').hidden=false;$('#result-panel').hidden=true;$('#form-errors').hidden=true;
}
function selectModel(name){state.model=name;$$('.model-option').forEach(b=>{const on=b.dataset.model===name;b.classList.toggle('selected',on);b.setAttribute('aria-selected',String(on));});render();}
function navigate(page){state.page=page;$$('.main-tab').forEach(b=>{const yes=b.dataset.page===page;b.classList.toggle('is-active',yes);b.setAttribute('aria-selected',String(yes));});$('#view-predict').hidden=page!=='predict';$('#view-learn').hidden=page!=='learn';}
function extractPayload(){
  const fields=currentFields(),payload={};
  for(const f of fields){const control=document.getElementById('f-'+f.key);if(!control.checkValidity()){control.reportValidity();return null;}const raw=control.value.trim();if(f.optional && raw==='')continue;payload[f.key]=f.type==='number'?Number(raw):raw;}
  if(state.model==='general'){payload.hypertension=Number(payload.hypertension);payload.heart_disease=Number(payload.heart_disease);payload.mode=state.generalMode;}
  return payload;
}
function failure(message){const box=$('#form-errors');box.textContent=message;box.hidden=false;}
function percent(v){return `${(v*100).toFixed(1)}%`;}
function showResult(result){
  $('#form-errors').hidden=true;$('#result-placeholder').hidden=true;$('#result-panel').hidden=false;
  const isFood=result.model==='food';const fromCatalog=result.source==='dataset_lookup';const uncertain=result.classification===null;
  const good=isFood?result.classification===1:result.classification===0;
  const icon=$('#result-icon');icon.className='result-icon '+(uncertain?'uncertain':good?'negative':'positive');icon.textContent=uncertain?'?':good?'✓':'!';
  let title,description;
  if(fromCatalog){title=result.classification===1?'Recommended in dataset':'Not recommended in dataset';description=`${result.food_name} · ${result.category} · Dataset lookup (no model inference)`;}
  else if(isFood){title=uncertain?'Result is uncertain':result.classification===1?'Leans recommended':'Leans not recommended';description=`${result.food_name} · XGBoost output based on author-curated labels`;
  }else{title=result.classification===1?'Diabetes-positive classification':'Diabetes-negative classification';description=result.model==='pima'?'PIMA Random Forest model · threshold 0.48':`LightGBM + SMOTENC · ${result.mode==='full'?'8 features (full)':'6 features (non-lab)'}`;}
  $('#result-title').textContent=title;$('#result-detail').textContent=description;
  const prob=$('#probability-wrap');prob.hidden=fromCatalog;
  if(!fromCatalog){$('#result-probability').textContent=percent(result.probability);$('#probability-fill').style.width=percent(result.probability);$('#probability-label').textContent=isFood?'Predicted probability of Score = 1':'Predicted probability of diabetes-positive class';$('#probability-note').textContent=isFood?'Model score is not individualized nutrition advice.':'Model probability is not a diagnosis or a verified personal medical risk.';}
  const extras=$('#result-extras');extras.replaceChildren();
  const notes=[...(result.notes||[])];
  if(result.per_100g){notes.unshift('Nutrients per 100g: '+Object.entries(result.per_100g).map(([k,v])=>`${k}: ${v}`).join(' · '));}
  for(const note of notes){const row=element('div','result-extra');row.append(element('b',null,'• '));row.append(document.createTextNode(note));extras.append(row);}
  $('#result-disclaimer').textContent=result.disclaimer||'Research prototype only.';
  if(window.innerWidth<831){$('#result-panel').scrollIntoView({behavior:'smooth',block:'nearest'});}
}
function setBusy(busy){$('#submit-button').disabled=busy;$('#submit-label').textContent=busy?'Processing...':state.model==='food'&&state.foodMode==='lookup'?'Find food':'Show prediction';}
async function submitPrediction(evt){
  evt.preventDefault();$('#form-errors').hidden=true;const payload=extractPayload();if(!payload)return;
  const api=state.model;setBusy(true);
  try{const data=await requestJson('/api/predict/'+api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});showResult(data);}catch(err){failure('Prediction could not complete: '+err.message);}finally{setBusy(false);}
}
let suggestionTimeout=null;
function bindAutocomplete(control,list){
  control.addEventListener('input',()=>{clearTimeout(suggestionTimeout);const value=control.value.trim();if(value.length<2){list.hidden=true;return;}suggestionTimeout=setTimeout(async()=>{try{const json=await requestJson('/api/foods?query='+encodeURIComponent(value),{},5000);if(control.value.trim()!==value)return;list.replaceChildren();for(const food of json.matches){const option=element('button','autocomplete-result');option.type='button';option.append(element('span',null,food.name),element('small',null,food.category));option.addEventListener('click',()=>{control.value=food.name;list.hidden=true;});list.append(option);}list.hidden=!json.matches.length;}catch{list.hidden=true;}},180);});
  control.addEventListener('blur',()=>setTimeout(()=>{list.hidden=true;},170));
}
function fillDemo(){const preset=state.model==='food'?example.food[state.foodMode]:example[state.model];for(const [k,v] of Object.entries(preset)){const input=document.getElementById('f-'+k);if(input){input.value=String(v);input.dispatchEvent(new Event('change'));}}$('#form-errors').hidden=true;}
async function loadMetrics(){try{const info=await requestJson('/api/models');$('#metric-full').textContent=percent(info.metrics.general_full.accuracy);$('#metric-nonlab').textContent=percent(info.metrics.general_nonlab.accuracy);}catch{/* offline preview fallback */}}
function start(){
  $$('.main-tab').forEach(button=>button.addEventListener('click',()=>navigate(button.dataset.page)));
  $$('.model-option').forEach(button=>button.addEventListener('click',()=>selectModel(button.dataset.model)));
  $('#prediction-form').addEventListener('submit',submitPrediction);
  $('#demo-button').addEventListener('click',fillDemo);
  $('#reset-button').addEventListener('click',()=>render());
  $('#result-again').addEventListener('click',()=>{$('#result-panel').hidden=true;$('#result-placeholder').hidden=false;$('#prediction-form').scrollIntoView({behavior:'smooth',block:'nearest'});});
  selectModel('pima');navigate('predict');loadMetrics();
}
document.addEventListener('DOMContentLoaded',start);
