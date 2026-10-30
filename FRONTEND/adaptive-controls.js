/* Opt-in persistent feedback, not authentication. Random capability stays in this browser. */
(()=>{
 function setup(){
  const go=document.getElementById('go');if(!go)return;
  const controls=document.createElement('section');controls.className='quick-comfort';
  const control1=document.createElement("label");
  control1.setAttribute("for","support-style");
  controls.append(control1);
  control1.append(document.createTextNode("How would you like it explained?"));
  const control2=document.createElement("select");
  control2.setAttribute("id","support-style");
  controls.append(control2);
  const control3=document.createElement("option");
  control3.setAttribute("value","auto");
  control2.append(control3);
  control3.append(document.createTextNode("Follow what helps me"));
  const control4=document.createElement("option");
  control4.setAttribute("value","short");
  control2.append(control4);
  control4.append(document.createTextNode("Short explanation"));
  const control5=document.createElement("option");
  control5.setAttribute("value","steps");
  control2.append(control5);
  control5.append(document.createTextNode("Step by step"));
  const control6=document.createElement("option");
  control6.setAttribute("value","example");
  control2.append(control6);
  control6.append(document.createTextNode("Example from my passage"));
  const control7=document.createElement("label");
  control7.setAttribute("class","checkbox");
  control7.setAttribute("for","remember-support");
  controls.append(control7);
  const control8=document.createElement("input");
  control8.setAttribute("id","remember-support");
  control8.setAttribute("type","checkbox");
  control7.append(control8);
  control7.append(document.createTextNode(" Save my learner history"));
  const privacyLead=document.createElement("p");
  privacyLead.className="small muted";
  privacyLead.textContent="Optional local history. No external AI service.";
  controls.append(privacyLead);
  const privacy=document.createElement("details");
  privacy.className="privacy-details";
  const privacySummary=document.createElement("summary");
  privacySummary.textContent="What is saved? Manage history";
  privacy.append(privacySummary);
  controls.append(privacy);
  const control9=document.createElement("p");
  control9.setAttribute("class","small muted");
  privacy.append(control9);
  control9.append(document.createTextNode("Optional: saves your starting profile, selected spans, support choices, explanations shown, session observations, settings and optional feedback to your local helper. Picture questions and answers can also be saved. Raw uploaded files and page images are not retained. No text is sent to an external AI service. Turn off to delete stored feedback."));
  const control10=document.createElement("button");
  control10.setAttribute("id","forget-support");
  control10.setAttribute("type","button");
  privacy.append(control10);
  control10.append(document.createTextNode("Forget my support history"));
  const control11=document.createElement("p");
  control11.setAttribute("id","profile-status");
  control11.setAttribute("class","small");
  control11.setAttribute("role","status");
  controls.append(control11);
  go.before(controls);
  const check=document.getElementById('remember-support'),status=document.getElementById('profile-status');
  const readKey=()=>window.daReaderKey?window.daReaderKey():localStorage.getItem('da_learner_key_v1');
  check.checked=!!readKey();
  async function forget(){
   const key=readKey();
   const headers=key?{'x-learner-key':key}:{};
   const state=await fetch('/api/learner/state',{headers}).then(response=>response.json());
   if(state.enrolled){if(!confirm('Delete this learner profile, linked local account and all saved support history?'))return false;const response=await fetch('/api/profile',{method:'DELETE',headers});if(!response.ok)throw Error('Could not delete history. Please retry.');}
   localStorage.removeItem('da_learner_key_v1');sessionStorage.removeItem('da_legacy_active');window.dispatchEvent(new Event('learner-forgotten'));check.checked=false;status.textContent='Stored support history deleted. New requests will not be saved. Your learner model has been reset.';
   return true;
  }
  check.onchange=async()=>{try{
   if(check.checked){const account=await fetch('/api/account').then(response=>response.json());if(readKey()||account.signed_in){document.getElementById('profile-setup').click();return;}if(localStorage.getItem('da_learner_key_v1')){check.checked=false;location.href='account.html';return;}const bytes=crypto.getRandomValues(new Uint8Array(32));const key=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');localStorage.setItem('da_learner_key_v1',key);sessionStorage.setItem('da_legacy_active','1');status.textContent='Remember support is on. Complete My starting profile to enable session-signal learning.';}
   else if(await forget()===false)check.checked=true;
  }catch(error){check.checked=!!readKey();status.textContent=error.message;}};
  document.getElementById('forget-support').onclick=()=>forget().catch(e=>{status.textContent=e.message;});
  fetch('/api/learner/state',{headers:readKey()?{'x-learner-key':readKey()}:{}}).then(r=>r.json()).then(p=>{check.checked=!!p.enrolled;status.textContent=p.enrolled?'Saved learner profile: '+p.alias+'. Open My progress for your report.':'No saved learner profile connected. Complete the starting profile or sign in.';}).catch(()=>{status.textContent='Could not check saved profile. Is the local helper running?';});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);else setup();
})();
