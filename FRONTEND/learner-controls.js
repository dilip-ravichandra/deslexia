/* Consented, local signals. No synthetic learner records or inferred clinical labels. */
(()=>{'use strict';function setup(){const by=id=>document.getElementById(id);let sid=null,lang='en',fingerprint='',chain=Promise.resolve(),audio=null,audioUrl=null,stopped=false,enrolled=false,finishSpeech=null;let readingClock=0,lastPara=null,seen=new Set();
 const key=()=>window.daReaderKey?window.daReaderKey():localStorage.getItem('da_learner_key_v1');const status=t=>by('learner-live-status').textContent=t;
 async function call(path,body){const h={'Content-Type':'application/json'};if(key())h['x-learner-key']=key();const r=await fetch(path,body?{method:'POST',headers:h,body:JSON.stringify(body)}:{headers:h});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Request failed');return d;}
 function detect(text){const letters=text.match(/\p{L}/gu)||[];const counts=[['hi',letters.filter(c=>/[\u0900-\u097f]/u.test(c)).length],['kn',letters.filter(c=>/[\u0c80-\u0cff]/u.test(c)).length],['ta',letters.filter(c=>/[\u0b80-\u0bff]/u.test(c)).length]].sort((a,b)=>b[1]-a[1]);const share=counts[0][1]/Math.max(1,letters.length);return (counts[0][1]>=3&&share>=.35)||(letters.length<=2&&share>=.8)?counts[0][0]:'en';}
 async function prepare(text){return chain=chain.catch(()=>{}).then(async()=>{const chosen=by('document-language').value;const next=chosen==='auto'?detect(text):chosen;const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));const hash=Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');if(hash===fingerprint&&next===lang&&sid)return;const enrolled=(await call('/api/learner/state')).enrolled;
 if(sid&&enrolled)await rawSignal('session_end',{});sid=null;lang=next;by('reader').lang=lang;by('extracted-text').lang=lang;fingerprint=hash;seen.clear();lastPara=null;
 if(enrolled){const s=await call('/api/learner/session',{language:lang});sid=s.session_id;status('Session '+s.status+' · '+lang+' · consented choices can update your learner model.');}else status('Document language: '+lang+'. Reading signals are not being saved.');});}
 async function rawSignal(kind,payload){if(!sid)return null;if(['undo','regenerate','optional_feedback'].includes(kind)&&!payload.route_id)return null;const d=await call('/api/learner/event',{client_id:crypto.randomUUID(),session_id:sid,language:lang,kind,payload});status(d.parameters_changed?'Learner evidence updated. '+d.reason:'Signal recorded. '+d.reason);return d;}
 function signal(kind,payload={}){return chain=chain.catch(()=>{}).then(()=>rawSignal(kind,payload));}
 async function browserSpeak(text,language){
  if(!window.speechSynthesis||!window.SpeechSynthesisUtterance)throw Error('Browser voice is unavailable.');
  const utterance=new SpeechSynthesisUtterance(text);
  utterance.lang={en:'en-US',hi:'hi-IN',kn:'kn-IN',ta:'ta-IN'}[language]||language;
  utterance.rate=Number(by('speech-rate').value);
  const voice=window.speechSynthesis.getVoices().find(candidate=>candidate.lang.toLowerCase().startsWith(language.toLowerCase()));
  if(voice)utterance.voice=voice;
  await new Promise((resolve,reject)=>{let settled=false;const finish=error=>{if(settled)return;settled=true;clearTimeout(watchdog);finishSpeech=null;error?reject(error):resolve();};const watchdog=setTimeout(()=>{window.speechSynthesis.cancel();finish(Error('Browser voice did not start. Check your device audio or choose Local voice (slower).'));},10000);finishSpeech=()=>finish();utterance.onstart=()=>clearTimeout(watchdog);utterance.onend=()=>finish();utterance.onerror=()=>finish(Error('Browser voice could not play. Check your device audio or choose Local voice (slower).'));try{window.speechSynthesis.speak(utterance);}catch(error){finish(error);}});
 }
 async function speak(text,language,options={}){
  if(!text.trim())return;
  if((options.source||by('voice-source').value)==='browser'){
   try{await browserSpeak(text,language);return;}
   catch(error){if(stopped)return;throw error;}
  }
  if(audio)audio.pause();
  if(audioUrl)URL.revokeObjectURL(audioUrl);
  if(window.speechSynthesis)window.speechSynthesis.cancel();
  try{
   const response=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,language})});
   if(!response.ok){const detail=await response.json().catch(()=>({}));throw Error(detail.detail||'Offline speech is unavailable.');}
   if(stopped)return;
   audioUrl=URL.createObjectURL(await response.blob());
   audio=by('speech-player');
   audio.src=audioUrl;
   audio.hidden=false;
   audio.playbackRate=Number(by('speech-rate').value);
   await new Promise((resolve,reject)=>{audio.onended=resolve;audio.onpause=()=>{if(stopped)resolve();};audio.onerror=()=>reject(Error('Audio could not play.'));audio.play().catch(error=>{if(error.name==='NotAllowedError'){audio.hidden=false;audio.focus();reject(Error('Voice is ready. Press Play in the audio controls.'));}else reject(error);});});
  }catch(error){
   if(stopped)return;
   if(error.message==='Voice is ready. Press Play in the audio controls.'){status(error.message);throw error;}
   if(audio)audio.hidden=true;
   if(!window.speechSynthesis||!window.SpeechSynthesisUtterance)throw error;
   status('Offline speech unavailable. Trying your browser voice.');
   await browserSpeak(text,language);
  }
 }
 function stopAudio(){stopped=true;if(audio){audio.pause();audio.hidden=true;}if(window.speechSynthesis)window.speechSynthesis.cancel();if(finishSpeech)finishSpeech();by('speech-stop').classList.add('hidden');if(by('speak').disabled)by('read-aloud-status').textContent='Read aloud stopped.';}
 async function speakSelection(text,language,options){stopAudio();stopped=false;by('speech-stop').classList.remove('hidden');try{await speak(text,language,options);}finally{by('speech-stop').classList.add('hidden');}}
 by('survey-save').onclick=async()=>{try{if(localStorage.getItem('da_learner_key_v1')&&!key()){window.location.href='account.html?create=1';return;}if(enrolled||(await call('/api/learner/state')).enrolled){enrolled=true;window.location.href='my-progress.html';return;}if(!document.querySelector('[name=survey-study]:checked'))throw Error('Choose at least one language you study in.');if(!by('survey-consent').checked)throw Error('Choose consent to save a profile, or use Read without a profile.');if(!key()){const bytes=crypto.getRandomValues(new Uint8Array(32));localStorage.setItem('da_learner_key_v1',Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join(''));sessionStorage.setItem('da_legacy_active','1');}await call('/api/learner/survey',{consent:true,reading_settings:{'s-bg':look.bg,'s-font':look.font,'s-size':look.size,'s-lh':look.lh,'s-ls':look.ls,'s-contrast':look.contrast},alias:by('survey-alias').value,preferred_language:by('survey-language').value,study_languages:Array.from(document.querySelectorAll('[name=survey-study]:checked'),x=>x.value),preferred_style:by('survey-style').value,difficulties:Array.from(document.querySelectorAll('[name=survey-need]:checked'),x=>x.value)});enrolled=true;by('explanation-language').value=by('survey-language').value;by('survey-panel').classList.add('hidden');by('remember-support').checked=true;sid=null;fingerprint='';await prepare(S.text);if(new URLSearchParams(location.search).has('setup')){window.location.href='account.html';return;}status('Starting profile saved. Open My progress to see your report and recovery key.');}catch(e){by('survey-message').textContent=e.message;}};
 by('survey-skip').onclick=()=>{by('survey-panel').classList.add('hidden');status('Reading without a new profile.');};by('profile-setup').onclick=()=>{window.location.href=enrolled?'my-progress.html':'account.html?create=1';};
 by('document-language').onchange=()=>prepare(S.text).catch(e=>status(e.message));by('end-session').onclick=()=>signal('session_end').then(()=>{sid=null;fingerprint='';status('Session finished. The next support request starts another session.');}).catch(e=>status(e.message));
 by('support-style').addEventListener('change',()=>{const style=by('support-style').value;if(style!=='auto')signal('style_choice',{style}).catch(e=>status(e.message));});
 document.querySelectorAll('#comfort-view input,#comfort-view select').forEach(c=>c.addEventListener('change',()=>signal('settings_change',{setting:c.id,value:c.type==='checkbox'?c.checked:c.value}).catch(e=>status(e.message))));
 by('reader').addEventListener('focusin',e=>{const p=e.target.closest('.para');if(!p)return;const index=Array.from(by('reader').children).indexOf(p);if(lastPara===index)return;if(seen.has(index))signal('reread',{paragraph_id:index}).catch(e=>status(e.message));seen.add(index);lastPara=index;readingClock=performance.now();});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){readingClock=0;stopAudio();}else if(document.activeElement&&by('reader').contains(document.activeElement)){signal('attention_return',{}).catch(e=>status(e.message));readingClock=performance.now();}});
 setInterval(()=>{if(!document.hidden&&document.hasFocus()&&readingClock&&performance.now()-readingClock>=15000){signal('dwell',{duration_ms:Math.min(60000,Math.round(performance.now()-readingClock)),paragraph_id:lastPara}).catch(e=>status(e.message));readingClock=performance.now();}},5000);
 by('undo').addEventListener('click',()=>{if(S.result?.routing?.route_id)signal('undo',{route_id:S.result.routing.route_id}).catch(e=>status(e.message));});
 by('speak').onclick=async()=>{if(!S.text.trim()){window.WORKSPACE?.toast('Open a passage first.');return;}const voiceStatus=by('read-aloud-status');try{stopped=false;by('speech-stop').classList.remove('hidden');by('speak').disabled=true;by('speak').textContent='Preparing voice…';voiceStatus.textContent=by('voice-source').value==='local'?'Preparing local voice. On a CPU this can take about a minute.':'Starting browser voice…';status(voiceStatus.textContent);await prepare(S.text);const chunks=[];for(let start=0;start<S.text.length;){let end=Math.min(start+350,S.text.length);if(end<S.text.length){const breakAt=S.text.lastIndexOf(' ',end);if(breakAt>start+170)end=breakAt+1;}chunks.push(S.text.slice(start,end));start=end;}for(const chunk of chunks){if(stopped)break;voiceStatus.textContent='Reading aloud…';await speak(chunk,lang);}if(!stopped){voiceStatus.textContent='Read aloud finished.';status(voiceStatus.textContent);}}catch(e){voiceStatus.textContent=e.message;status(e.message);window.WORKSPACE?.toast(e.message);}finally{by('speech-stop').classList.add('hidden');by('speak').disabled=false;by('speak').textContent='▷ Read aloud';}};
 by('speech-stop').onclick=stopAudio;
 window.addEventListener('learner-forgotten',()=>{sid=null;fingerprint='';enrolled=false;stopped=true;S.requestId++;S.result=null;by('result').replaceChildren();by('result').classList.add('hidden');if(audio){audio.pause();audio.hidden=true;}status('History deleted. Reading signals are no longer saved.');});
 window.LEARNER={prepare,signal,speak:speakSelection,stopSpeech:stopAudio,language:()=>lang,session:()=>sid};
 call('/api/learner/state').then(state=>{enrolled=state.enrolled;by('survey-panel').classList.add('hidden');if(enrolled){by('explanation-language').value=state.survey.preferred_language;status('Welcome back, '+state.alias+'. Your saved profile is ready. Open My progress for your report.');}prepare(S.text).catch(e=>status(e.message));}).catch(e=>status(e.message));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);else setup();
})();
