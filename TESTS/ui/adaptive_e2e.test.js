const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const BASE=process.env.BASE||'http://127.0.0.1:8000';
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function ready(fn){for(let i=0;i<2400;i++){if(fn())return;await wait(25);}throw Error('UI never became ready');}
async function page(path='/'){
 const html=await(await fetch(BASE+path)).text();
 const dom=new JSDOM(html,{url:BASE+path,runScripts:'dangerously',pretendToBeVisual:true,beforeParse(w){w.fetch=(u,o)=>fetch(new URL(u,BASE),o);}});
 const w=dom.window,d=w.document;
 await ready(()=>d.readyState!=='loading');
 if(path==='/'){
   w.eval(await(await fetch(BASE+'/adaptive-controls.js')).text());
   await ready(()=>w.DA&&d.getElementById('support-style'));
 }
 return {dom,w,d};
}
async function support(w,d,style='steps'){
 w.DA.startReading('A catalyst can speed up a chemical reaction.');
 d.getElementById('typed').value='catalyst';d.getElementById('typed-go').click();
 d.getElementById('m-c').checked=true;d.getElementById('support-style').value=style;
 await w.DA.requestSupport();await ready(()=>d.getElementById('helpful'));
}
test('trained prototype banner and opt-in controls are visible',async()=>{
 const {dom,d}=await page();await ready(()=>d.getElementById('banner').textContent.includes('trained'));
 assert.match(d.getElementById('banner').textContent,/prototype/);
 assert.equal(d.getElementById('remember-support').checked,false);
 assert.match(d.getElementById('profile-status').parentElement.textContent,/selected text/);dom.window.close();
});
test('contextual explanation renders safely and notebook saves its actual content',async()=>{
 const {dom,w,d}=await page();await support(w,d);
 assert.match(d.getElementById('result').textContent,/Understanding this part/);
 assert.match(d.getElementById('result').textContent,/chemical reaction/);
 d.getElementById('save-support-note').click();await wait(50);
 const notes=JSON.parse(w.localStorage.getItem('da_notes_v2')||'[]');
 assert.ok(notes.some(n=>JSON.stringify(n).includes('chemical reaction')));dom.window.close();
});
test('helpful decisions alter next style and forgetting removes stored feedback',async()=>{
 const {dom,w,d}=await page();const toggle=d.getElementById('remember-support');toggle.checked=true;toggle.dispatchEvent(new w.Event('change'));
 const key=w.localStorage.getItem('da_learner_key_v1');assert.match(key,/^[a-f0-9]{64}$/);
 for(let i=0;i<2;i++){await support(w,d,'steps');d.getElementById('helpful').click();await ready(()=>d.getElementById('helpful').disabled);}
 await support(w,d,'auto');assert.equal(w.DA.S.result.personalization.style,'steps');
 assert.match(d.getElementById('result').textContent,/Your support style: steps/);
 d.getElementById('forget-support').click();await ready(()=>!w.localStorage.getItem('da_learner_key_v1'));
 const result=await(await fetch(BASE+'/api/profile',{headers:{'x-learner-key':key}})).json();assert.deepEqual(result.feedback,{});dom.window.close();
});
test('admin page displays actual model metrics and can evaluate, activate and roll back',async()=>{
 const {dom,d}=await page('/learning.html');await ready(()=>d.getElementById('runs').textContent.includes('Validation macro-F1'));
 assert.match(d.getElementById('runs').textContent,/CONCEPTUAL/);
 d.getElementById('train').click();await ready(()=>d.getElementById('message').textContent.includes('Candidate evaluated'));
 await ready(()=>d.querySelector('#runs button:not(:disabled)'));
 d.querySelector('#runs button:not(:disabled)').click();await ready(()=>d.getElementById('message').textContent.includes('Candidate activated'));
 d.getElementById('rollback').click();await ready(()=>d.getElementById('message').textContent.includes('Previous model restored'));dom.window.close();
});
