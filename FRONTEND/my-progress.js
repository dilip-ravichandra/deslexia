(()=>{'use strict';
const by=id=>document.getElementById(id);
const keyName='da_learner_key_v1';
const names={VOCABULARY:'Word meanings',SYNTACTIC:'Sentence structure',CONCEPTUAL:'Ideas',PRONUNCIATION:'Pronunciation',VISUAL:'Reading presentation'};
let report=null,selected=null;
function node(tag,value,className){const element=document.createElement(tag);element.textContent=value;if(className)element.className=className;return element;}
function key(){try{return localStorage.getItem(keyName);}catch{return null;}}
async function fetchReport(candidate){const headers=candidate?{'x-learner-key':candidate}:{};const response=await fetch('/api/learner/report',{headers});const result=await response.json();if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Could not load this profile.');return result;}
function bar(parent,label,value,maximum,suffix=''){const row=node('div','', 'bar'),head=node('div','', 'bar-head'),track=node('span','', 'track'),fill=node('span','', 'fill');head.append(node('span',label),node('strong',String(value)+suffix));fill.style.width=(maximum?Math.max(0,Math.min(100,100*value/maximum)):0)+'%';track.append(fill);row.append(head,track);parent.append(row);}
function compare(event){
 const box=by('comparison');box.replaceChildren();
 if(!event){box.append(node('p','No saved support choice yet. Ask for help in the reading room first.'));return;}
 box.append(node('p',new Date(event.created_at).toLocaleString()+' · '+event.kind),node('p',event.reason));
 const beforeState=event.before_state||{},afterState=event.after_state||{};
 const changed=[];
 for(const [field,prefix] of [['need_estimates',''],['style_estimates','Explanation style: ']]){
  const before=beforeState[field]||{},after=afterState[field]||{};
  for(const category of Object.keys(after))if(Math.round((before[category]||0)*100)!==Math.round(after[category]*100))changed.push({field,category,label:prefix+(names[category]||category)});
 }
 const styleChanged=beforeState.preferred_style!==afterState.preferred_style;
 if(!changed.length&&!styleChanged){box.append(node('p','No visible support-preference change from this event. This is normal; it does not mean the help request was ignored.'));return;}
 box.append(node('p','Internal suggestion weights changed, not reading-ability scores.'));
 if(styleChanged)box.append(node('p','Preferred explanation style: '+(beforeState.preferred_style||'unknown')+' → '+(afterState.preferred_style||'unknown')+'.'));
 if(!changed.length)return;
 const grid=node('div','', 'compare');
 for(const [title,state] of [['Before',beforeState],['After',afterState]]){const cell=node('div','');cell.append(node('strong',title));for(const item of changed)cell.append(node('p',item.label+': '+Math.round(((state[item.field]||{})[item.category]||0)*100)+'%'));grid.append(cell);}
 box.append(grid);
}
function render(){if(!report)return;by('missing').hidden=true;by('report').hidden=false;by('alias').textContent=report.profile.alias;by('created').textContent='Starting profile saved '+new Date(report.profile.created_at).toLocaleDateString()+'. This date is not your latest activity.';by('last-activity').textContent=report.events.length?'Latest recorded activity: '+new Date(report.events[0].created_at).toLocaleString()+'.':'No reading activity recorded yet.';by('profile-id').textContent='Private profile ID: '+report.profile.id.slice(0,8)+'…';by('survey').textContent='Your starting choices (saved once): '+(report.survey.difficulties.map(category=>names[category]||category).join(', ')||'No help types chosen')+'. Starting explanation style: '+report.survey.preferred_style+'. See your current preference below.';
 const metrics=report.metrics;by('metrics').replaceChildren();for(const [value,label] of [[metrics.sessions,'Reading sessions'],[metrics.support_decisions,'Support decisions'],[Object.values(metrics.explicit_requests).reduce((total,count)=>total+count,0),'Explicit help requests'],[metrics.feedback.helped+metrics.feedback.not_helpful,'Optional feedback responses']]){const card=node('div','', 'metric');card.append(node('strong',value),node('span',label));by('metrics').append(card);}
 const counts=metrics.explicit_requests;const maximum=Math.max(1,...Object.values(counts));by('choices').replaceChildren();for(const [category,count] of Object.entries(counts))bar(by('choices'),names[category],count,maximum);
 const state=report.states[by('language').value];by('preferences').replaceChildren();if(state){by('preferences').append(node('p','Current preferred explanation style: '+state.preferred_style+'. Based on your survey and explicit feedback; this is not a diagnosis.'));for(const [style,value] of Object.entries(state.style_estimates))bar(by('preferences'),style,Math.round(value*100),100,'%');}
 const events=report.events.filter(event=>by('show-activity').checked||!['dwell','reread','session_start','session_end'].includes(event.kind));
 const active=events.find(event=>event.id===selected)||events[0];selected=active?.id||null;
 by('events').replaceChildren();if(!events.length)by('events').append(node('p','No saved support choice yet. Make a help choice in the reader, then refresh.'));
 for(const event of events){const button=node('button',event.kind.replaceAll('_',' ')+' · '+event.language,'event');button.type='button';button.setAttribute('aria-pressed',String(event.id===selected));button.append(node('small',new Date(event.created_at).toLocaleString()+(event.payload.span?' · '+event.payload.span:'')));button.onclick=()=>{selected=event.id;render();};by('events').append(button);}compare(active);
 by('decision').replaceChildren();const latest=report.routes[0];if(latest)by('decision').append(node('p',(names[latest.selected]||latest.selected)+' · '+latest.style+' style · '+latest.language),node('p','For: '+latest.span),node('p','Help shown: '+(latest.evidence.explanation_quality?.summary||'Not recorded for this earlier request.')),node('p','Chosen by: '+latest.evidence.source+'. '+latest.evidence.reasons.join(' ')));else by('decision').append(node('p','No support decision recorded yet.'));
}
async function load(){let account=null;try{const response=await fetch('/api/account');account=await response.json();}catch{}if(account?.signed_in&&account.setup_complete===false){location.replace('profile-setup.html');return;}const signed=!!account?.signed_in;by('account-name').textContent=signed?'Signed in as '+account.username+'.':'Older profile connected with a recovery key.';by('recovery-controls').hidden=signed;by('reconnect-section').hidden=signed;const candidate=signed?null:sessionStorage.getItem('da_legacy_active')==='1'?key():null;if(!candidate&&!signed){report=null;by('report').hidden=true;by('missing').hidden=false;by('status').textContent='No profile selected. Sign in, create a separate account, or reconnect your older profile with its recovery key.';return;}try{report=await fetchReport(candidate);by('language').value=report.survey.preferred_language||'en';by('status').textContent='Saved profile loaded from the local helper. Report refreshed '+new Date().toLocaleTimeString()+'.';render();}catch(error){report=null;by('report').hidden=true;by('missing').hidden=false;by('status').textContent=error.message+' If you changed browser, sign in or use your recovery key below.';}}
by('refresh').onclick=load;
by('language').onchange=render;
by('show-activity').onchange=render;
by('show-key').onclick=()=>{if(!key())return;by('recovery-key').textContent=key();by('recovery-key').hidden=false;by('copy-key').hidden=false;};
by('copy-key').onclick=async()=>{try{await navigator.clipboard.writeText(key());by('status').textContent='Recovery key copied. Keep it private.';}catch{by('status').textContent='Copy unavailable. Select the visible recovery key instead.';}};
by('reconnect').onclick=async()=>{const candidate=by('reconnect-key').value.trim().toLowerCase();if(!/^[a-f0-9]{64}$/.test(candidate)){by('reconnect-status').textContent='Enter the full 64-character recovery key.';return;}try{const restored=await fetchReport(candidate);if(key()&&key()!==candidate&&!window.confirm('Replace the profile connected to this browser? The old profile remains on the helper.'))return;localStorage.setItem(keyName,candidate);sessionStorage.setItem('da_legacy_active','1');by('reconnect-key').value='';by('reconnect-status').textContent='Reconnected to '+restored.profile.alias+'.';report=restored;selected=null;render();by('status').textContent='Profile reconnected. Return to the reading room to continue.';}catch(error){by('reconnect-status').textContent=error.message+' Check that you are using the same local helper and data folder.';}};
by('delete-profile').onclick=async()=>{if(!window.confirm('Permanently delete this profile, its linked account, sessions and saved support history?'))return;const headers=sessionStorage.getItem('da_legacy_active')==='1'&&key()?{'x-learner-key':key()}:{};const response=await fetch('/api/profile',{method:'DELETE',headers});if(!response.ok){by('status').textContent='Deletion failed. Your profile was not removed.';return;}localStorage.removeItem(keyName);sessionStorage.removeItem('da_legacy_active');by('recovery-key').textContent='';by('recovery-key').hidden=true;by('copy-key').hidden=true;await load();by('status').textContent='Profile, linked account and saved history deleted.';};
load();
})();
