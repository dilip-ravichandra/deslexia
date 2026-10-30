/* Local document workspace: no automatic saving of raw files or page images. */
(()=>{'use strict';
 const by=id=>document.getElementById(id);let file=null,page=null,img=null,crop=null,answer='',busy=false,anchor=null,speechRevision=0,visualStop=null,visualAudio=null,visualAudioUrl=null,visualAudioStatus=null,visualVoice=null;
 const controls=['document-prev','document-next','document-jump','document-reocr','document-file','document-close'];
 const pictureGuide=document.createElement('div');pictureGuide.className='picture-guide hidden';
 const pictureTitle=document.createElement('strong');pictureTitle.textContent='Understand this picture';
 const pictureTip=document.createElement('p');pictureTip.textContent='OCR reads words only. For diagrams, shapes and graphs, ask the picture model instead.';
 const pictureActions=document.createElement('div');pictureActions.className='row';
 const pictureKind=document.createElement('select');pictureKind.id='picture-kind';pictureKind.setAttribute('aria-label','Picture type');
 for(const [value,label] of [['general','General picture'],['biology','Biology diagram'],['graph','Physics or other graph'],['geometry','Shapes and geometry']]){const option=document.createElement('option');option.value=value;option.textContent=label;pictureKind.append(option);}
 const pictureButton=document.createElement('button');pictureButton.type='button';pictureButton.className='button primary';pictureButton.textContent='Explain whole picture';
 pictureActions.append(pictureKind,pictureButton);pictureGuide.append(pictureTitle,pictureTip,pictureActions);
 by('document-workspace').querySelector('.document-grid').before(pictureGuide);
 const pictureQuestions={general:'What is visible in this picture? Explain the important parts simply.',biology:'What parts are visible in this biology diagram, and how do the labels and arrows connect?',graph:'What does this graph or chart show? Explain the visible categories and main trend or comparison.',geometry:'What shapes are visible, and how are they arranged? Do not guess measurements.'};
 pictureKind.onchange=()=>{by('visual-question').value=pictureQuestions[pictureKind.value];};
 pictureButton.onclick=()=>{if(!img||busy)return;resetCrop();by('visual-explain').click();};
 function status(t){by('document-status').textContent=t;}
 async function post(url,body){const key=window.daReaderKey?.();const r=await fetch(url,{method:'POST',body,headers:key?{'x-learner-key':key}:{}});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Request failed.');return data;}
 function lock(value){busy=value;controls.forEach(id=>by(id).disabled=value);by('visual-explain').disabled=value||!img;pictureButton.disabled=value||!img;pictureKind.disabled=value||!img;['crop-apply','crop-reset','visual-question','visual-style','crop-left','crop-top','crop-width','crop-height'].forEach(id=>by(id).disabled=value||!img);}
 function stopVisualPlayback(message=''){
  speechRevision++;window.LEARNER?.stopSpeech();
  if(visualAudio){visualAudio.pause();visualAudio.hidden=true;visualAudio.removeAttribute('src');}
  if(visualAudioUrl){URL.revokeObjectURL(visualAudioUrl);visualAudioUrl=null;}
  if(visualStop)visualStop.classList.add('hidden');
  if(visualAudioStatus)visualAudioStatus.textContent=message;
 }
 function clearAnswer(){stopVisualPlayback();answer='';by('visual-answer').replaceChildren();by('visual-save').disabled=true;by('visual-speak').disabled=true;}
 function draw(){const c=by('document-preview'),ctx=c.getContext('2d');if(!img)return;c.width=img.naturalWidth;c.height=img.naturalHeight;ctx.drawImage(img,0,0);if(crop){ctx.strokeStyle='#2F5D50';ctx.lineWidth=Math.max(3,c.width/250);ctx.strokeRect(crop.x,crop.y,crop.w,crop.h);}}
 function resetCrop(){crop=null;['left','top'].forEach(k=>by('crop-'+k).value=0);['width','height'].forEach(k=>by('crop-'+k).value=100);draw();clearAnswer();}
 function setCrop(x,y,w,h){if(!img)return;crop={x:Math.max(0,x),y:Math.max(0,y),w,h};['left','top','width','height'].forEach((k,i)=>by('crop-'+k).value=([crop.x/img.naturalWidth,crop.y/img.naturalHeight,crop.w/img.naturalWidth,crop.h/img.naturalHeight][i]*100).toFixed(1));draw();clearAnswer();}
 async function load(number=1,force=false){
  if(!file||busy)return;
  lock(true);clearAnswer();status('Reading your page… First OCR use can take a little longer.');
  try{
   const body=new FormData();body.append('file',file);body.append('page',number);body.append('force_ocr',force);body.append('language',by('document-language')?.value||'auto');
   const data=await post('/api/documents/extract',body);
   page=data;img=null;crop=null;
   by('uploaded-name').textContent=file.name;by('document-page').value=data.page;by('document-page').max=data.page_count;by('document-count').textContent='of '+data.page_count;
   by('extracted-text').value=data.text;by('extracted-text').rows=data.text.trim()?12:3;
   by('extraction-method').textContent=data.method+(data.ocr_engine?' · '+data.ocr_engine:'');
   by('extraction-warning').textContent=data.warnings.join(' ');by('read-extracted').disabled=!data.text.trim();
   const lines=by('ocr-lines');lines.replaceChildren();
   for(const line of data.lines){const p=document.createElement('p');p.textContent=line.text+' · OCR score '+Math.round(line.confidence*100)+'%';lines.append(p);}
   if(!data.lines.length)lines.textContent='No OCR lines for this page.';
   by('document-workspace').classList.remove('hidden');
   if(data.image){img=new Image();img.src=data.image;await img.decode();resetCrop();}
   else{const canvas=by('document-preview');canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height);}
   pictureGuide.classList.toggle('hidden',!img);
   by('document-workspace').classList.toggle('picture-only',!!img&&!data.text.trim());
   status(img&&!data.text.trim()?'No words found. Use Explain whole picture for shapes, diagrams or graphs.':'Page '+data.page+' ready. Check the text or ask about a picture.');
  }catch(error){status(error.message);}
  finally{lock(false);by('document-prev').disabled=!page||page.page<=1;by('document-next').disabled=!page||page.page>=page.page_count;}
 }
 by('document-file').addEventListener('change',e=>{const selected=e.target.files?.[0];if(!selected)return;if(selected.size>25*1024*1024){status('Choose a file smaller than 25 MB.');e.target.value='';return;}file=selected;page=null;img=null;by('document-workspace').classList.add('hidden');load();e.target.value='';});
 by('document-prev').onclick=()=>load(page.page-1);by('document-next').onclick=()=>load(page.page+1);by('document-jump').onclick=()=>load(Number(by('document-page').value));by('document-reocr').onclick=()=>load(page.page,true);
 by('document-language').addEventListener('change',()=>{if(file&&page&&page.method==='OCR')status('Language changed. Choose Read page with OCR again to update the text. This replaces edits in the text box.');});
 by('document-close').onclick=()=>{file=null;page=null;img=null;crop=null;clearAnswer();by('document-workspace').classList.add('hidden');pictureGuide.classList.add('hidden');by('extracted-text').value='';by('ocr-lines').replaceChildren();by('document-preview').width=0;status('Document closed. Upload another page whenever you like.');};
 by('read-extracted').onclick=()=>{const text=by('extracted-text').value.trim();if(!text)return;window.WORKSPACE.openText(text,file.name+' · page '+page.page,'UPLOADED PAGE');by('reader').scrollIntoView({behavior:'smooth',block:'start'});};
 by('extracted-text').oninput=()=>by('read-extracted').disabled=!by('extracted-text').value.trim();
 by('crop-reset').onclick=()=>{if(!busy)resetCrop();};by('crop-apply').onclick=()=>{if(!img||busy)return;const [x,y,w,h]=['left','top','width','height'].map(k=>Number(by('crop-'+k).value));if(![x,y,w,h].every(Number.isFinite)||x<0||y<0||w<=0||h<=0||x+w>100.1||y+h>100.1){status('Choose a region inside the page. Left + width and top + height must be at most 100%.');return;}setCrop(x/100*img.naturalWidth,y/100*img.naturalHeight,w/100*img.naturalWidth,h/100*img.naturalHeight);};
 const canvas=by('document-preview');function point(e){const b=canvas.getBoundingClientRect();return{x:Math.max(0,Math.min(canvas.width,(e.clientX-b.left)*canvas.width/b.width)),y:Math.max(0,Math.min(canvas.height,(e.clientY-b.top)*canvas.height/b.height))};}
 canvas.onpointerdown=e=>{if(!img||busy)return;anchor=point(e);canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!anchor)return;const p=point(e);crop={x:Math.min(anchor.x,p.x),y:Math.min(anchor.y,p.y),w:Math.abs(p.x-anchor.x),h:Math.abs(p.y-anchor.y)};draw();};canvas.onpointerup=e=>{if(!anchor)return;anchor=null;if(crop?.w>5&&crop?.h>5)setCrop(crop.x,crop.y,crop.w,crop.h);else resetCrop();};canvas.onpointercancel=()=>{anchor=null;resetCrop();};
 by('visual-explain').onclick=async()=>{if(!img||busy)return;lock(true);clearAnswer();const started=performance.now();const waiting=by('visual-answer');waiting.textContent='Looking at the selected picture… The local model can take a minute or more on a CPU.';const timer=setInterval(()=>{if(!answer)waiting.textContent='Still analyzing locally · '+Math.round((performance.now()-started)/1000)+' seconds. You can keep this page open.';},1000);waiting.scrollIntoView({block:'nearest'});try{const c=document.createElement('canvas');const box=crop||{x:0,y:0,w:img.naturalWidth,h:img.naturalHeight};c.width=Math.round(box.w);c.height=Math.round(box.h);c.getContext('2d').drawImage(img,box.x,box.y,box.w,box.h,0,0,c.width,c.height);const blob=await new Promise(resolve=>c.toBlob(resolve,'image/png'));if(!blob)throw Error('Could not prepare the selected image.');const form=new FormData();form.append('file',blob,'region.png');form.append('question',by('visual-question').value);form.append('style',by('visual-style').value);form.append('kind',pictureKind.value);
 const labels=page.lines.filter(line=>{if(!crop)return true;const xs=line.box.map(p=>p[0]),ys=line.box.map(p=>p[1]);return Math.min(...xs)>=box.x&&Math.max(...xs)<=box.x+box.w&&Math.min(...ys)>=box.y&&Math.max(...ys)<=box.y+box.h;}).map(l=>l.text).join('\n');form.append('labels',labels.slice(0,5000));form.append('language',document.getElementById('explanation-language').value==='same'?(document.getElementById('document-language').value==='auto'?(page?.language||window.LEARNER?.language()||'en'):document.getElementById('document-language').value):document.getElementById('explanation-language').value);const result=await post('/api/documents/explain',form);answer=result.explanation;const p=document.createElement('p');p.style.whiteSpace='pre-wrap';p.textContent=answer;const note=document.createElement('p');note.className='muted small';note.textContent=result.warning+' Model: '+result.model;by('visual-answer').replaceChildren(p,note);if(result.trace_id){for(const [label,decision] of [['This helped','accept'],['Not helpful','reject']]){const b=document.createElement('button');b.className='button';b.textContent=label;b.onclick=async()=>{try{const key=window.daReaderKey?.();const res=await fetch('/api/documents/feedback',{method:'POST',headers:{'Content-Type':'application/json','x-learner-key':key||''},body:JSON.stringify({trace_id:result.trace_id,decision})});const data=await res.json();if(!res.ok)throw Error(data.detail);note.textContent=data.note;by('visual-answer').querySelectorAll('button').forEach(btn=>btn.disabled=true);}catch(e){note.textContent=e.message;}};by('visual-answer').append(b);}}else{note.textContent+=' Enable Remember which support helps me before requesting an explanation to save feedback.';}by('visual-save').disabled=false;by('visual-speak').disabled=false;by('visual-answer').focus();}catch(e){by('visual-answer').textContent=e.message;}finally{clearInterval(timer);lock(false);}};
 by('visual-save').onclick=()=>{if(answer)window.WORKSPACE.saveNote('Picture: '+file.name+' · page '+page.page,'Question: '+by('visual-question').value+'\n\n'+answer+'\n\nUnverified visual explanation. Compare with the original page.');};
 visualVoice=document.createElement('select');visualVoice.id='visual-voice';visualVoice.setAttribute('aria-label','Explanation voice');
 for(const [value,label] of [['browser','Fast browser voice'],['local','Local voice (slower)']]){const option=document.createElement('option');option.value=value;option.textContent=label;visualVoice.append(option);}
 visualStop=document.createElement('button');visualStop.className='button hidden';visualStop.textContent='Stop audio';
 by('visual-speak').after(visualStop,visualVoice);
 visualAudio=document.createElement('audio');visualAudio.controls=true;visualAudio.hidden=true;visualAudio.setAttribute('aria-label','Picture explanation audio');
 visualAudioStatus=document.createElement('p');visualAudioStatus.className='visual-audio-status';visualAudioStatus.setAttribute('role','status');
 by('visual-speak').parentElement.after(visualAudio,visualAudioStatus);
 visualStop.onclick=()=>{stopVisualPlayback('Explanation audio stopped.');by('visual-speak').disabled=!answer;};
 function speechChunks(text){const chunks=[];for(let start=0;start<text.length;){let end=Math.min(start+350,text.length);if(end<text.length){const space=text.lastIndexOf(' ',end);if(space>start+170)end=space+1;}chunks.push(text.slice(start,end));start=end;}return chunks;}
 async function localAudio(chunk,language,revision){
  visualAudioStatus.textContent='Preparing local voice. This may take a minute on a CPU.';
  const started=performance.now();
  const timer=setInterval(()=>{if(revision===speechRevision)visualAudioStatus.textContent='Preparing local voice · '+Math.round((performance.now()-started)/1000)+' seconds. You can stop or wait.';},1000);
  let response;
  try{response=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:chunk,language})});}
  finally{clearInterval(timer);}
  if(!response.ok){const detail=await response.json().catch(()=>({}));throw Error(detail.detail||'Local voice is unavailable.');}
  const blob=await response.blob();if(revision!==speechRevision)return;
  if(visualAudioUrl)URL.revokeObjectURL(visualAudioUrl);
  visualAudioUrl=URL.createObjectURL(blob);visualAudio.src=visualAudioUrl;visualAudio.hidden=false;visualAudio.playbackRate=Number(by('speech-rate').value);
  visualAudioStatus.textContent='Playing local voice. Use the audio controls if it does not start.';
  await new Promise((resolve,reject)=>{visualAudio.onended=resolve;visualAudio.onpause=()=>{if(revision!==speechRevision)resolve();};visualAudio.onerror=()=>reject(Error('Audio could not play.'));visualAudio.play().catch(()=>reject(Error('Press Play in the audio controls below.')));});
 }
 by('visual-speak').onclick=async()=>{
  if(!answer)return;
  stopVisualPlayback();const revision=speechRevision;
  const selected=by('explanation-language').value,documentLanguage=by('document-language').value;
  const language=selected==='same'?(documentLanguage==='auto'?(page?.language||window.LEARNER?.language()||'en'):documentLanguage):selected;
  const source=visualVoice.value;
  by('visual-speak').disabled=true;visualStop.classList.remove('hidden');
  visualAudioStatus.textContent=source==='browser'?'Starting fast browser voice…':'Preparing local voice. This may take a minute on a CPU.';
  try{
   for(const chunk of speechChunks(answer)){
    if(revision!==speechRevision)break;
    if(source==='browser')await window.LEARNER.speak(chunk,language,{source:'browser',fallback:false});
    else await localAudio(chunk,language,revision);
   }
   if(revision===speechRevision)visualAudioStatus.textContent='Explanation audio finished.';
  }catch(error){if(revision===speechRevision)visualAudioStatus.textContent=error.message+(source==='browser'?' Try Local voice (slower) or check your device volume.':'');}
  finally{if(revision===speechRevision)visualStop.classList.add('hidden');by('visual-speak').disabled=!answer;}
 };
 lock(false);fetch('/api/document-status').then(r=>r.json()).then(s=>status('Upload PDF, photo or notes. OCR '+(s.ocr_available?'ready':'needs setup')+' · picture model '+(s.vision_available?'installed':'needs setup')+'.')).catch(()=>status('Local helper offline. Start the project before uploading.'));
})();
