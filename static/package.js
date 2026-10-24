// A package lives only in this tab. The server never retains document sessions.
let packagePages=[], packageOriginal=null, packageName='', packageWorking=false, packageStop=false;
let packageActive=null, packageRestoring=false;
const packageSection=document.createElement('section');
packageSection.id='package-workspace';
packageSection.setAttribute('aria-labelledby','package-title');
packageSection.innerHTML=`
  <div class="package-heading"><div><span class="section-label">DOCUMENT WORKSPACE</span><h2 id="package-title">Every page. One clear next step.</h2><p>Upload a PDF or a set of photos. We will show you which pages need attention.</p></div><span class="package-limit">UP TO 20 PAGES</span></div>
  <div class="package-upload" id="package-drop"><div><h3>Start with the whole document.</h3><p>PDF up to 20 MB, or up to 20 JPG, PNG and WebP photos, 12 MB each.</p></div><div class="package-upload-actions"><button id="package-upload" class="primary">Choose document</button><button id="package-demo" class="text-action">Try a three-page sample</button></div><input id="package-input" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" multiple hidden></div>
  <p id="package-error" role="alert" hidden></p>
  <div id="package-content" hidden>
    <div class="package-toolbar"><div><h3 id="package-name"></h3><p id="package-progress" aria-live="polite"></p></div><div class="package-buttons"><button id="package-run" class="primary">Inspect pages</button><button id="package-stop" hidden>Stop after this page</button><button id="package-export">Export reviewed PDF</button><button id="package-report">Download report</button></div></div>
    <progress id="package-meter" value="0" max="20" aria-label="Page inspection progress"></progress>
    <div id="package-counts" class="package-counts"></div>
    <div class="package-list-heading"><p>Prioritized by attention needed. Export keeps the original page order.</p><label>Show <select id="package-filter"><option value="all">All pages</option><option value="attention">Needs attention</option><option value="improved">Improved</option><option value="ready">Ready for review</option></select></label></div>
    <div id="package-pages"></div>
    <p class="package-footnote">Results are visual estimates, not verification of document content. Unchanged digital PDF pages retain their original text and graphics. Your package stays in this tab; refreshing clears it.</p>
  </div>`;
document.querySelector('.workspace-intro').before(packageSection);
const packageBar=document.createElement('div');
packageBar.id='package-editor-bar';
packageBar.hidden=true;
packageBar.innerHTML='<button id="package-back">Back to all pages</button><strong id="package-current"></strong><label><input type="checkbox" id="package-use-result"> Use this result in the exported PDF</label>';
$('workbench').before(packageBar);
document.body.classList.add('package-mode');

function packageError(message){ $('package-error').textContent=tr(message); $('package-error').hidden=!message; }
function packageShouldUseResult(data){
  return data.status!=='retake'||!!data.recovered_count||!!data.issues?.some(issue=>issue.action==='Diperbaiki');
}
function packageState(page){
  if(page.error)return 'error';
  if(page.manual?.length)return 'retake';
  if(page.digital)return 'digital';
  if(!page.data)return 'pending';
  if(page.data.status==='retake')return 'retake';
  if(page.data.regions?.some(r=>r.status==='unresolved')||page.data.issues?.some(i=>i.action==='Perlu ditinjau'))return 'retake';
  return page.data.recovered_count || page.data.issues?.some(i=>i.action==='Diperbaiki') ? 'improved' : 'ready';
}
const packageLabels={error:'Inspection failed',digital:'Digital original',pending:'Waiting',retake:'Needs attention',improved:'Improved',ready:'Ready for review'};
function packageTargets(page){
  const data=page.data;
  if(!data)return [];
  const targets=(data.regions||[]).flatMap((region,index)=>region.status==='unresolved'?[{
    label:tr('Area {0}: {1}',[index+1,tr(region.label)]),box:region.box,note:region.note||region.label,
  }]:[]);
  (page.manual||[]).forEach((box,index)=>targets.push({label:tr('Your selection {0}',[index+1]),
    box:box.map((v,i)=>v*(i%2?data.height:data.width)),note:tr('Include surrounding text so the photos can be matched.')}));
  const wholePage=(data.issues||[]).some(issue=>['blur','page-boundary'].includes(issue.kind)&&issue.action==='Perlu foto ulang');
  if(wholePage||(!targets.length&&data.status==='retake'))targets.unshift({label:tr('Retake the whole page'),box:null,note:data.instruction});
  return targets;
}
function packageOpenTarget(page,target){
  packageOpen(page);
  if(packageActive!==page||busy||packageWorking)return;
  recoverySection.scrollIntoView({block:'start'});
  if(target.box){showSource(target.box,tr('Page {0}',[page.number])+' / '+target.label,tr(target.note));$('close-source').focus({preventScroll:true});}
  else $('add-photo').focus({preventScroll:true});
}
function packageRender(){
  packageSection.classList.toggle('package-filled',!!packagePages.length);
  $('package-upload').textContent=tr(packagePages.length?'Replace package':'Choose document');
  $('package-upload').classList.toggle('primary',!packagePages.length);
  $('package-content').hidden=!packagePages.length;
  $('package-name').textContent=packageOriginal?packageName:tr('Photo package');
  const counts={pending:0,retake:0,error:0,improved:0,ready:0,digital:0};
  packagePages.forEach(p=>counts[packageState(p)]++);
  const done=packagePages.length-counts.pending;
  $('package-progress').textContent=tr('{0} of {1} pages checked',[done,packagePages.length]);
  $('package-meter').max=Math.max(1,packagePages.length); $('package-meter').value=done;
  $('package-meter').hidden=!packageWorking;
  $('package-run').hidden=!counts.pending&&!counts.error&&!packageStop;
  $('package-stop').hidden=!packageWorking;
  $('package-stop').disabled=packageStop;
  for(const id of ['package-upload','package-demo','package-run','package-export','package-report','package-input'])$(id).disabled=packageWorking || busy;
  $('package-export').disabled=packageWorking||busy||!!counts.pending||!!counts.error;
  $('package-export').classList.toggle('primary',!$('package-export').disabled);
  $('package-counts').replaceChildren();
  for(const [label,count] of [['Needs attention',counts.retake+counts.error],['Improved',counts.improved],['Ready for review',counts.ready+counts.digital],['Waiting',counts.pending]]){
    if(label==='Waiting'&&!count)continue;
    const item=document.createElement('div'), value=document.createElement('strong'), caption=document.createElement('span');
    value.textContent=count;caption.textContent=tr(label);item.append(value,caption);$('package-counts').append(item);
  }
  $('package-pages').replaceChildren();
  const rank={error:0,retake:1,pending:2,improved:3,ready:4,digital:5},filter=$('package-filter').value;
  const visible=packagePages.filter(p=>filter==='all'||(filter==='attention'?['retake','error'].includes(packageState(p)):filter==='ready'?['ready','digital'].includes(packageState(p)):packageState(p)===filter));
  visible.sort((a,b)=>rank[packageState(a)]-rank[packageState(b)]||a.number-b.number);
  visible.forEach(page=>{
    const state=packageState(page),row=document.createElement('article');row.className='package-page';row.dataset.state=state;
    const img=document.createElement('img');img.src=page.data?.result||page.thumbnail;img.alt=tr('Page {0}',[page.number]);
    const details=document.createElement('div'),title=document.createElement('h4'),badge=document.createElement('span'),note=document.createElement('p');
    title.textContent=tr('Page {0}',[page.number]);badge.className='package-status';badge.textContent=tr(packageLabels[state]);
    note.textContent=page.error?tr(page.error):page.digital?tr('Original text and graphics preserved. Review this page visually.'):page.data?tr(page.data.instruction):tr('Queued for automatic quality checks.');
    details.append(title,badge,note);
    if(page.related?.length){const related=document.createElement('p');related.className='package-related';related.textContent=tr('Other views in this PDF: {0}',[page.related.map(p=>p.number).join(', ')]);details.append(related);}
    if(page.recoveryFrom){const recovered=document.createElement('p');recovered.textContent=tr('Recovered using page {0}. Review the copied regions.',[page.recoveryFrom]);details.append(recovered);}
    if(page.recoveryNote){const notice=document.createElement('p');notice.textContent=tr(page.recoveryNote);details.append(notice);}
    const extra=document.createElement('details'),summary=document.createElement('summary');extra.className='package-disclosure';summary.textContent=tr('View issues and areas');extra.append(summary);
    if(page.data?.issues?.length){const tags=document.createElement('div');tags.className='package-tags';page.data.issues.forEach(issue=>{const tag=document.createElement('span');tag.textContent=tr(issue.label)+' · '+tr(issue.action);tags.append(tag);});extra.append(tags);}
    const targets=packageTargets(page);
    if(targets.length){
      const group=document.createElement('div');group.className='package-targets';
      const heading=document.createElement('strong');heading.textContent=tr('Review or photograph again — page {0}',[page.number]);group.append(heading);
      const hint=document.createElement('p');hint.textContent=tr('Open an area to inspect the evidence. If it is unreadable, add a clearer photo of this same page.');group.append(hint);
      targets.forEach(target=>{const button=document.createElement('button');button.textContent=target.label;button.disabled=packageWorking||busy;button.addEventListener('click',()=>packageOpenTarget(page,target));group.append(button);});
      extra.append(group);
    }
    if(extra.children.length>1)details.append(extra);
    const action=document.createElement('button');action.textContent=tr(state==='digital'?'Preview original':state==='retake'?'Review and recover':'Open page');action.disabled=packageWorking||busy||state==='pending'||state==='error';action.addEventListener('click',()=>packageOpen(page));
    if(state==='error'){action.disabled=packageWorking||busy;action.textContent=tr('Retry page');action.addEventListener('click',()=>packageRun(page));}
    row.append(img,details,action);$('package-pages').append(row);
  });
  if(!visible.length){const p=document.createElement('p');p.className='package-empty';p.textContent=tr('No pages in this category.');$('package-pages').append(p);}
  if(packageActive){$('package-current').textContent=tr('Page {0} of {1}',[packageActive.number,packagePages.length]);$('package-use-result').checked=!!packageActive.useResult;}
}
function packageSaveActive(){
  if(!packageActive||packageActive.digital)return;
  packageActive.manual=[...manualRegions];
  packageActive.second=secondPhoto;packageActive.secondName=secondPhotoName;
}
function packageHome(){
  if(busy||packageWorking)return;
  packageSaveActive(); packageActive=null;
  $('error').hidden=true;
  document.body.classList.add('package-mode');document.body.classList.remove('package-editing');
  packageBar.hidden=true;packageSection.hidden=false;packageRender();packageSection.scrollIntoView({block:'start'});
}
function packageOpen(page){
  if(packageWorking||busy||page.error)return;
  packageSaveActive();packageActive=page;
  if(page.digital){
    const dialog=$('package-native-preview');
    $('package-native-title').textContent=tr('Page {0}',[page.number]);$('package-native-image').src=page.thumbnail;
    $('package-native-text').textContent=page.text;
    dialog.showModal();return;
  }
  if(!page.data)return;
  packageRestoring=true;
  registerFirstPhoto(page.file,false);secondPhoto=page.second||null;secondPhotoName=page.secondName||'';
  manualRegions=page.manual||[];
  singleDisplay(page.data,tr('Page {0}',[page.number]),false);
  phase('review');
  $('second-name').textContent=secondPhoto?tr('Foto kedua: {0}',[secondPhotoName]):'';
  packageRestoring=false;
  document.body.classList.remove('package-mode');document.body.classList.add('package-editing');
  packageBar.hidden=false;packageSection.hidden=true;packageRender();packageBar.scrollIntoView({block:'start'});
}
const singleDisplay=display;
display=function(data,name,isSample){
  singleDisplay(data,name,isSample);
  if(packageActive&&!packageRestoring&&!refreshingLanguage){
    const page=packageActive;
    if(firstPhoto!==page.file){page.file=firstPhoto;page.frame=false;page.replaced=true;page.related=[];page.recoveryAttempts=[];page.recoveryFrom=null;page.recoveryNote='';}
    if(secondPhoto!==page.second){page.recoveryFrom=null;page.recoveryNote='';}
    page.data=data;page.error=null;page.digital=false;
    page.useResult=packageShouldUseResult(data);
    packageSaveActive();packageRender();
  }
};
const nativeDialog=document.createElement('dialog');nativeDialog.id='package-native-preview';
nativeDialog.innerHTML='<div><h3 id="package-native-title"></h3><button id="package-native-close">Close preview</button></div><p>Digital original preserved. Text extraction is shown for review, not as a quality guarantee.</p><img id="package-native-image" alt="Original PDF page"><pre id="package-native-text"></pre>';
document.body.append(nativeDialog);$('package-native-close').addEventListener('click',()=>nativeDialog.close());
$('package-back').addEventListener('click',packageHome);
$('package-use-result').addEventListener('change',()=>{if(packageActive)packageActive.useResult=$('package-use-result').checked;});
async function packageImport(files){
  if(packageWorking||busy||!files.length)return;
  packageError('');
  if(files.length>20){packageError('A package must contain 1 to 20 pages.');return;}
  packageWorking=true;packageStop=false;setBusy(true);packageRender();
  try{
    const pdfs=files.filter(f=>f.type==='application/pdf'||/\.pdf$/i.test(f.name));
    if(pdfs.length&&(pdfs.length!==1||files.length!==1))throw Error('Choose one PDF or a set of photos, not both.');
    let pages=[],original=null;
    if(pdfs.length){
      original=pdfs[0];if(original.size>20*1024*1024)throw Error('PDF size must not exceed 20 MB.');
      const form=new FormData();form.append('file',original);
      const response=await fetch('/api/package/import',{method:'POST',body:form}),data=await response.json();
      if(!response.ok)throw Error(data.detail||'The PDF could not be read.');
      pages=await Promise.all(data.pages.map(async p=>({...p,thumbnail:p.image,file:await (await fetch(p.image)).blob(),frame:true,useResult:false,manual:[]})));
    }else{
      for(const file of files){
        if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw Error('Choose JPG, PNG or WebP photos.');
        if(file.size>12*1024*1024)throw Error('Each photo must not exceed 12 MB.');
        const url=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('The photo could not be read.'));reader.readAsDataURL(file);});
        pages.push({number:pages.length+1,file,thumbnail:url,digital:false,frame:false,useResult:false,manual:[]});
      }
    }
    packagePages=pages;packageOriginal=original;packageName=original?.name||tr('Photo package');packageActive=null;
    $('package-filter').value='all';
  }catch(error){packageError(error.message);}
  finally{packageWorking=false;setBusy(false);packageRender();}
  if(packagePages.length&&!$('package-error').textContent)await packageRun();
}
async function packageRun(onlyPage=null){
  if(packageWorking||busy)return;
  packageWorking=true;packageStop=false;setBusy(true);packageError('');packageRender();
  const queue=onlyPage?[onlyPage]:packagePages.filter(p=>!p.digital&&(!p.data||p.error));
  for(const page of queue){
    if(packageStop)break;
    $('package-progress').textContent=tr('Inspecting page {0} of {1}…',[page.number,packagePages.length]);
    try{
      const form=new FormData();form.append('file',page.file,'page.jpg');form.append('page_frame',String(!!page.frame));
      const response=await fetch('/api/analyze',{method:'POST',body:form}),data=await response.json();
      if(!response.ok)throw Error(data.detail||'Page inspection failed.');
      page.data=data;page.error=null;page.useResult=packageShouldUseResult(data);
      page.related=[];page.recoveryAttempts=[];page.recoveryFrom=null;page.recoveryNote='';
    }catch(error){page.error=error.message;}
    packageRender();
  }
  try{if(!packageStop && packagePages.every(p=>p.digital||p.data))await packageFindEvidence();}
  catch(error){packageError(error.message);}
  finally{packageWorking=false;setBusy(false);packageRender();}
}
async function packageFindEvidence(){
  const pages=packagePages.filter(p=>!p.digital&&p.data);
  if(pages.length<2)return;
  $('package-progress').textContent=tr('Looking for other views of the same document…');
  const form=new FormData();
  for(const page of pages)form.append('images',await(await fetch(page.data.original)).blob(),'page.jpg');
  const response=await fetch('/api/package/matches',{method:'POST',body:form}),matches=await response.json();
  if(!response.ok)throw Error(matches.detail||'Page matching failed.');
  pages.forEach(p=>p.related=[]);
  for(const pair of matches.pairs){pages[pair.first].related.push(pages[pair.second]);pages[pair.second].related.push(pages[pair.first]);}
  for(const page of pages){
    if(packageStop)break;
    if(page.data.recovered_count||!page.data.regions.some(r=>r.status==='unresolved'))continue;
    page.recoveryAttempts??=[];
    for(const other of page.related.slice(0,2)){
      if(packageStop)break;
      if(page.recoveryAttempts.includes(other.number))continue;
      page.recoveryAttempts.push(other.number);
      $('package-progress').textContent=tr('Checking page {0} as evidence for page {1}…',[other.number,page.number]);
      const recovery=new FormData();recovery.append('first',page.file,'first.jpg');recovery.append('second',other.file,'second.jpg');
      recovery.append('first_page_frame',String(!!page.frame));recovery.append('regions',JSON.stringify(page.manual||[]));
      const res=await fetch('/api/recover',{method:'POST',body:recovery}),data=await res.json();
      if(!res.ok){page.recoveryNote=tr('Page {0} could not be used: {1}',[other.number,tr(data.detail||'Page matching failed.')]);continue;}
      if(!data.recovered_count){page.recoveryNote=tr('Page {0} matches, but does not provide clearer evidence for the marked areas.',[other.number]);continue;}
      page.data=data;page.second=other.file;page.secondName=tr('Page {0}',[other.number]);page.recoveryFrom=other.number;
      page.manual=[];page.useResult=true;page.recoveryNote='';break;
    }
    packageRender();
  }
}
function packageReport(){
  return {name:packageName,language,created_at:new Date().toISOString(),page_count:packagePages.length,
    note:tr('Results require review. Unresolved pages are retained, not silently removed.'),
    pages:packagePages.map(p=>({page:p.number,state:packageState(p),export:p.useResult?'processed':'original',digital:p.digital,error:p.error||null,related_pages:p.related?.map(q=>q.number)||[],recovered_from_page:p.recoveryFrom||null,follow_up:packageTargets(p),manual_regions:p.manual||[],second_photo:p.secondName||null,replacement_photo:p.replaced?(p.file.name||'replacement-photo'):null,
      ...(p.data?{instruction:tr(p.data.instruction),issues:p.data.issues?.map(i=>({...i,label:tr(i.label),action:tr(i.action)})),regions:p.data.regions.map(r=>({...r,label:tr(r.label),...(r.note?{note:tr(r.note)}:{})})),
        recovered_count:p.data.recovered_count||0,registration:p.data.registration,lines:p.data.lines}: {})}))};
}
async function packageExport(){
  if(packageWorking||busy)return;
  packageWorking=true;setBusy(true);packageRender();packageError('');
  try{
    const form=new FormData(),manifest=[];let index=0;
    if(packageOriginal)form.append('original',packageOriginal);
    for(const p of packagePages){
      let blob=null;
      if(p.useResult&&p.data){
        // Use the same review outlines as the single-page PDF export.
        const img=new Image();img.src=p.data.result;await img.decode();
        const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;
        const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);ctx.strokeStyle='#ad6200';ctx.lineWidth=3;
        p.data.regions.filter(r=>r.status==='unresolved').forEach(r=>ctx.strokeRect(...r.box));
        (p.manual||[]).forEach(([x,y,w,h])=>ctx.strokeRect(x*img.width,y*img.height,w*img.width,h*img.height));
        blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.94));
      }else if(!packageOriginal){blob=p.data?.original?await(await fetch(p.data.original)).blob():p.file;}
      if(blob){form.append('images',blob,'page-'+p.number+'.jpg');manifest.push({page:p.number-1,image:index++});}
      else manifest.push({page:p.number-1,image:null});
    }
    form.append('manifest',JSON.stringify(manifest));form.append('report',JSON.stringify(packageReport()));
    const response=await fetch('/api/package/export',{method:'POST',body:form});
    if(!response.ok){const data=await response.json();throw Error(data.detail||'The package could not be exported.');}
    saveBlob(await response.blob(),'scanpilot-final.pdf');
  }catch(error){packageError(error.message);}
  finally{packageWorking=false;setBusy(false);packageRender();}
}
$('package-upload').addEventListener('click',()=>{$('package-input').value='';$('package-input').click();});
$('package-input').addEventListener('change',event=>packageImport([...event.target.files]));
$('package-run').addEventListener('click',()=>packageRun());
$('package-stop').addEventListener('click',()=>{packageStop=true;packageRender();});
$('package-filter').addEventListener('change',packageRender);
$('package-export').addEventListener('click',packageExport);
$('package-report').addEventListener('click',()=>saveBlob(new Blob([JSON.stringify(packageReport(),null,2)],{type:'application/json'}),'scanpilot-package-review.json'));
async function packageDemo(){
  if(packageWorking||busy)return;
  try {
  const files=[];
  for(const kind of ['clear','shadow','covered']){
    const response=await fetch('/api/sample/'+kind+'?lang='+language);if(!response.ok){packageError('Sample pages could not be loaded.');return;}
    files.push(new File([await response.blob()],kind+'.jpg',{type:'image/jpeg'}));
  }
  await packageImport(files);
  } catch(error){packageError(error.message);}
}
$('package-demo').addEventListener('click',packageDemo);
for(const id of ['hero-upload','hero-example','preview-try'])$(id).addEventListener('click',event=>{event.stopImmediatePropagation();if(busy||packageWorking)return;packageHome();id==='hero-upload'?$('package-upload').click():packageDemo();},true);
$('package-drop').addEventListener('dragover',e=>e.preventDefault());
$('package-drop').addEventListener('drop',e=>{e.preventDefault();e.stopPropagation();packageImport([...e.dataTransfer.files]);});
document.querySelector('a[href="#workbench"]').addEventListener('click',event=>{event.preventDefault();packageHome();});
document.querySelector('a[href="#sample-library"]').addEventListener('click',event=>{event.preventDefault();if(busy||packageWorking)return;packageHome();packageDemo();});
const priorSetLanguage=setLanguage;
setLanguage=function(value){priorSetLanguage(value);packageRender();};
window.packageWorkspace={get frame(){return !!packageActive?.frame;}};

// Keep the primary workflow short; expose supporting evidence on demand.
const finish=document.createElement('div');finish.className='package-finish';
finish.innerHTML='<div><h3>Download your document</h3><p>All pages stay in their original order. Areas needing review remain marked.</p></div>';
$('package-pages').after(finish);finish.append($('package-export'));
$('package-export').textContent=tr('Download final PDF');
const more=document.createElement('details');more.className='package-disclosure';
more.innerHTML='<summary>Download report</summary>';
finish.after(more);more.append($('package-report'));
for(const selector of ['.reading-section','.export-section']){
  const section=document.querySelector(selector),details=document.createElement('details'),summary=document.createElement('summary');
  details.className='package-disclosure';summary.textContent=tr(selector==='.reading-section'?'Recognized text':'Page downloads');
  section.before(details);details.append(summary,section);
}
document.querySelector('.skip-link').href='#package-upload';
document.querySelector('.skip-link').textContent=tr('Skip to document upload');
