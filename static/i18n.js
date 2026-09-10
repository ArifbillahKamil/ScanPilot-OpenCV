// No automatic translation of OCR, filenames, or arbitrary DOM mutations.
let language = 'en';
try { language = localStorage.getItem('scanpilot-language') === 'id' ? 'id' : 'en'; } catch {}
document.documentElement.lang = language;
let refreshingLanguage = false;
const normalizeCopy = value => value.replace(/\s+/g, ' ').trim();
const copyEntries = Object.entries(window.SCANPILOT_COPY).map(([id,en]) => [normalizeCopy(id),normalizeCopy(en)]);
const copyLookup = new Map();
copyEntries.forEach(pair => pair.forEach(value => copyLookup.set(value,pair)));
const escapePattern = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const copyPatterns = [];
copyEntries.filter(([id]) => /\{\d+\}/.test(id)).forEach(pair => {
  pair.forEach(value => {
    const slots=[];let offset=0,pattern='';
    for(const match of value.matchAll(/\{(\d+)\}/g)){
      pattern+=escapePattern(value.slice(offset,match.index))+'([\\s\\S]*?)';
      slots.push(Number(match[1]));offset=match.index+match[0].length;
    }
    pattern+=escapePattern(value.slice(offset));
    copyPatterns.push({pattern:new RegExp('^'+pattern+'$'),slots,pair});
  });
});

function tr(source, values=[]) {
  if(typeof source!=='string')return source;
  const key=normalizeCopy(source), index=language==='en'?1:0;
  const edgeStart=source.match(/^\s*/)[0],edgeEnd=source.match(/\s*$/)[0];
  const direct=copyLookup.get(key);
  if(direct)return edgeStart+direct[index].replace(/\{(\d+)\}/g,(token,n)=>n in values?String(values[n]):token)+edgeEnd;
  for(const entry of copyPatterns){
    const match=key.match(entry.pattern);
    if(match){
      const args=[];entry.slots.forEach((slot,i)=>args[slot]=match[i+1]);
      return edgeStart+entry.pair[index].replace(/\{(\d+)\}/g,(_,n)=>args[n])+edgeEnd;
    }
  }
  // Quality instructions can be a concatenation of independently known messages.
  let rest=key,parts=[];
  const plain=copyEntries.filter(([id])=>!id.includes('{')).flatMap(pair=>pair.map(value=>({value,pair}))).sort((a,b)=>b.value.length-a.value.length);
  while(rest){
    const entry=plain.find(item=>rest===item.value||rest.startsWith(item.value+' '));
    if(!entry)return source;
    parts.push(entry.pair[index]);rest=rest.slice(entry.value.length).trimStart();
  }
  return edgeStart+parts.join(' ')+edgeEnd;
}

const staticCopy=[];
function bindStaticCopy(root=document.documentElement){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){
    if(node.parentElement.closest('script,style,option[value="en"],option[value="id"]'))return NodeFilter.FILTER_REJECT;
    return copyLookup.has(normalizeCopy(node.nodeValue))?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;
  }});
  while(walker.nextNode()){
    const node=walker.currentNode;staticCopy.push({node,source:node.nodeValue});
  }
  root.querySelectorAll('[aria-label],[alt],[title]').forEach(node=>{
    for(const attr of ['aria-label','alt','title']){
      const source=node.getAttribute(attr);
      if(source&&copyLookup.has(normalizeCopy(source)))staticCopy.push({node,source,attr});
    }
  });
}
function translateStaticCopy(){
  for(const item of staticCopy){
    if(!item.node.isConnected)continue;
    if(item.attr)item.node.setAttribute(item.attr,tr(item.source));
    else item.node.nodeValue=tr(item.source);
  }
}
function updateSamplePreviews(){
  document.querySelectorAll('img[src^="/api/sample/"]').forEach(img=>{
    img.src=img.getAttribute('src').split('?')[0]+'?lang='+language;
  });
}
function localizedEvidence(data){
  // Human-facing fields only. OCR text, IDs, coordinates and hashes are untouched.
  return {
    ...data,
    language,
    instruction:tr(data.instruction),
    issues:(data.issues||[]).map(issue=>({...issue,label:tr(issue.label),action:tr(issue.action)})),
    regions:data.regions.map(r=>({...r,label:tr(r.label),...(r.note?{note:tr(r.note)}:{})})),
    trace:data.trace.map(step=>({...step,title:tr(step.title),detail:tr(step.detail)})),
    sources:data.sources?.map(source=>({...source,label:tr(source.label)}))
  };
}

function setLanguage(value){
  if(!['en','id'].includes(value)||busy)return;
  const view=currentView,aligned=alignedView,splitValue=$('compare-range').value;
  const reading=$('reading-view').value, scroll=[scrollX,scrollY];
  const source=selectedBox?{box:selectedBox,title:$('source-title').textContent,note:$('source-note').textContent}:null;
  const filename=$('filename').textContent,secondName=$('second-name').textContent;
  const error=$('error').hidden?null:$('error').textContent;
  const selectionHelp=$('selection-help').textContent;
  language=value;document.documentElement.lang=value;
  $('language-select').value=value;
  try{localStorage.setItem('scanpilot-language',value);}catch{}
  refreshingLanguage=true;
  translateStaticCopy();
  updateSamplePreviews();
  if(currentData){
    display(currentData,firstIsSample?tr(filename):filename,firstIsSample);
    currentView=view;alignedView=aligned;$('compare-range').value=splitValue;updateComparison();
    if(reading==='first'){
      $('reading-view').value='first';renderRecovery({...currentData,lines:currentData.before_lines||[]},true);
    }
    $('second-name').textContent=secondPhoto?tr('Foto kedua: {0}',[secondIsSample?tr(secondPhotoName):secondPhotoName]):'';
    if(source){
      const i=currentData.regions.findIndex(r=>r.box.every((v,j)=>v===source.box[j]));
      const title=i>=0?tr('Area {0}: {1}',[i+1,tr(currentData.regions[i].status==='recovered'?'Dari foto 2':'Perlu bukti')]):tr(source.title);
      showSource(source.box,title,tr(source.note));
    }
  }
  if(error)$('error').textContent=lastErrorMessage?tr(lastErrorMessage)+(currentData?tr(' Hasil dokumen sebelumnya tetap ditampilkan.'):''):tr(error);
  $('selection-help').textContent=tr(selectionHelp);
  if(!currentData&&runtimeMode)updateRuntimeCopy();
  else if(runtimeMode)updateRuntimeCopy(false);
  refreshingLanguage=false;
  window.scrollTo(...scroll);
  $('language-announcement').textContent=value==='en'?'Language changed to English.':'Bahasa diubah ke Indonesia.';
}

document.addEventListener('DOMContentLoaded',()=>{
  const label=document.createElement('label');label.className='language-picker';
  label.innerHTML='<span class="language-icon" aria-hidden="true">◎</span><select id="language-select" aria-label="Language / Bahasa"><option value="en">English</option><option value="id">Indonesia</option></select>';
  document.querySelector('header').insertBefore(label,document.getElementById('about-button'));
  const announce=document.createElement('span');announce.id='language-announcement';announce.className='visually-hidden';announce.setAttribute('aria-live','polite');label.append(announce);
  $('language-select').value=language;$('language-select').addEventListener('change',event=>setLanguage(event.target.value));
  bindStaticCopy();translateStaticCopy();updateSamplePreviews();
});
