// jsdom end-to-end checks. Needs a running backend: BASE=http://127.0.0.1:PORT node --test ui_e2e.test.js
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const BASE = process.env.BASE || "http://127.0.0.1:8000";
const TEXT = "Although the reaction was slow, the catalyst eventually accelerated it.\n\nPlants use photosynthesis to turn sunlight into food, which allows them to grow.";

async function page(path = "/") {
  const browserPath = path === "/" ? "/?guest=1" : path === "/research.html" ? "/research-history.html" : path;
  const html = await (await fetch(BASE + browserPath)).text();
  const calls = [];
  const dom = new JSDOM(html, { url: BASE + browserPath, runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(w) { w.fetch = (u, o) => { calls.push({ url: String(u), body: o && o.body ? JSON.parse(o.body) : null });
      return fetch(new URL(u, BASE), o); }; } });
  const ready = () => {
    const d = dom.window.document;
    if (d.readyState === "loading") return false;
    if (path === "/") return Boolean(dom.window.WORKSPACE && d.getElementById("connection").textContent !== "Checking helper…" && d.getElementById("banner").textContent);
    if (path === "/research.html") return Boolean(d.getElementById("out").textContent || d.getElementById("err").textContent);
    return true;
  };
  const deadline = Date.now() + 10000;
  while (!ready() && Date.now() < deadline) await new Promise(r => setTimeout(r, 20));
  assert.ok(ready(), "page never reached its actual ready state: " + path);
  return { dom, w: dom.window, d: dom.window.document, calls };
}
const wait = ms => new Promise(r => setTimeout(r, ms));
async function selectText(w, d, needle, useLast = false) {
  const reader = d.getElementById("reader"), full = reader.textContent, i = useLast ? full.lastIndexOf(needle) : full.indexOf(needle);
  let pos = 0, s, e;
  const walker = d.createTreeWalker(reader, 4);
  for (let n; (n = walker.nextNode());) {
    const len = n.textContent.length;
    if (!s && i < pos + len) s = [n, i - pos];
    if (!e && i + needle.length <= pos + len) { e = [n, i + needle.length - pos]; break; }
    pos += len;
  }
  const r = d.createRange(); r.setStart(...s); r.setEnd(...e);
  const sel = w.getSelection(); sel.removeAllRanges(); sel.addRange(r);
  reader.dispatchEvent(new w.Event("mouseup", { bubbles: true }));
  await wait(30);   // the app reads the selection on the next tick, as real browsers require
}

test("banner is honest about practice mode and disclaimer is shown", async () => {
  const { d } = await page();
  assert.match(d.getElementById("banner").textContent, /Choose the help you need|prototype|Local models need setup/);
  assert.match(d.getElementById("disclaimer").textContent.toLowerCase(), /does not diagnose/);
});

test("select a word, get support, request carries ONLY text fields (no visual settings)", async () => {
  const { w, d, calls } = await page();
  // change every visual setting first
  for (const [id, v] of [["s-bg", "dark"], ["s-contrast", "strong"], ["s-size", "30"], ["s-lh", "2.2"], ["s-ls", "0.1"], ["s-font", "serif"]]) {
    const e = d.getElementById(id); e.value = v; e.dispatchEvent(new w.Event("input", { bubbles: true }));
  }
  d.getElementById("s-focus").checked = true; d.getElementById("s-focus").dispatchEvent(new w.Event("change", { bubbles: true }));
  w.DA.startReading(TEXT);
  await selectText(w, d, "catalyst");
  assert.equal(w.DA.S.sel.span, "catalyst");
  assert.equal(TEXT.slice(w.DA.S.sel.start, w.DA.S.sel.start + 8), "catalyst");
  await w.DA.requestSupport(); await wait(400);
  const req = calls.find(c => c.url.endsWith("/api/adapt")).body;
  const allowed = new Set(["span", "text", "span_start", "category_override", "variant", "context_before", "context_after", "mode", "support_style"]);
  assert.ok(Object.keys(req).every(k => allowed.has(k)), "unexpected keys: " + Object.keys(req));
  assert.equal(req.span, "catalyst");
  const result = d.getElementById("result");
  assert.ok(!result.classList.contains("hidden"));
  assert.match(result.textContent, /Suggested: Explain a word \(a simple rule, not a trained model\)/);
  assert.match(result.textContent, /Original/); assert.match(result.textContent, /Easier version/);
  assert.match(d.getElementById("adapted-box").textContent, /a substance that makes a reaction go faster/);
  assert.ok(d.querySelector("#adapted-box mark"), "changed words are highlighted");
});

test("visual settings apply to the page and persist, independent of the helper", async () => {
  const { w, d } = await page();
  const s = d.getElementById("s-size"); s.value = "30"; s.dispatchEvent(new w.Event("input", { bubbles: true }));
  assert.equal(d.documentElement.style.getPropertyValue("--size"), "30px");
  const b = d.getElementById("s-bg"); b.value = "dark"; b.dispatchEvent(new w.Event("input", { bubbles: true }));
  assert.equal(d.documentElement.style.getPropertyValue("--bg").toLowerCase(), "#15181c");
  assert.equal(JSON.parse(w.localStorage.getItem("da_guest_look_v1")).bg, "dark");
  d.getElementById("s-reset").click();
  assert.equal(d.documentElement.style.getPropertyValue("--size"), "22px");
});

test("right-click selected text offers the same support choices and requests help", async () => {
  const { w, d, calls } = await page();
  w.DA.startReading(TEXT);
  const reader = d.getElementById("reader"), menu = d.getElementById("selection-menu");
  const unselected = new w.MouseEvent("contextmenu", { bubbles: true, cancelable: true });
  reader.dispatchEvent(unselected);
  assert.equal(unselected.defaultPrevented, false);
  assert.ok(menu.classList.contains("hidden"));
  await selectText(w, d, "catalyst");
  const selected = new w.MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 100, clientY: 100 });
  reader.dispatchEvent(selected);
  assert.equal(selected.defaultPrevented, true);
  assert.equal(menu.classList.contains("hidden"), false);
  menu.querySelector('[data-selection-mode="m-p"]').click();
  await wait(400);
  assert.ok(menu.classList.contains("hidden"));
  assert.equal(d.getElementById("m-p").checked, true);
  assert.ok(calls.some(call => call.url.endsWith("/api/support") && call.body.category_override === "PRONUNCIATION"));
  const result = d.getElementById("result");
  assert.equal(result.parentElement.id, "reader-area");
  assert.match(result.textContent, /Listen to selected text/);
  assert.match(result.querySelector(".help-context").textContent, /catalyst/);
  assert.equal(result.querySelector(".support-details").open, false);
  assert.equal(result.querySelector("#regen"), null);
  assert.ok([...result.querySelectorAll("button")].some(button => button.textContent === "Back to selected text"));
  [...result.querySelectorAll("button")].find(button => button.textContent === "Close help").click();
  assert.ok(result.classList.contains("hidden"));
});

test("English understanding help returns quick source-based text without waiting for AI", async () => {
  const { w, d, calls } = await page();
  w.DA.startReading(TEXT);
  await selectText(w, d, "photosynthesis");
  d.getElementById("m-c").checked = true;
  d.getElementById("go").click();
  for (let attempt = 0; attempt < 100 && !d.getElementById("result").textContent.includes("Quick help from the passage"); attempt++) await wait(50);
  const request = calls.filter(call => call.url.endsWith("/api/support")).at(-1);
  assert.equal(request.body.response_mode, "quick");
  const result = d.getElementById("result");
  assert.match(result.textContent, /Quick help from the passage or glossary/);
  assert.match(result.textContent, /light energy/);
  assert.equal(result.querySelector("#regen"), null);
});

test("every background x contrast combination keeps text readable (WCAG >= 4.5:1)", async () => {
  const { w } = await page();
  const bad = [];
  for (const name of Object.keys(w.DA.PRESETS)) for (const lvl of ["soft", "standard", "strong"]) {
    const c = w.DA.colours(name, lvl), r = w.DA.ratio(c.bg, c.text);
    if (r < 4.5) bad.push(`${name}/${lvl}: ${r.toFixed(2)}`);
  }
  assert.deepEqual(bad, []);
});

test("accept replaces the sentence in the reading text and undo restores it", async () => {
  const { w, d } = await page();
  w.DA.startReading(TEXT);
  await selectText(w, d, "catalyst");
  await w.DA.requestSupport(); await wait(400);
  d.getElementById("accept").click(); await wait(300);
  assert.match(w.DA.S.text, /catalyst \(a substance that makes a reaction go faster\)/);
  assert.equal(d.getElementById("undo").disabled, false);
  d.getElementById("undo").click();
  assert.equal(w.DA.S.text, TEXT);
});

test("accept modifies the selected repeated sentence, leaving the first one intact", async () => {
  const { w, d } = await page();
  const sentence = "The catalyst speeds the reaction.";
  w.DA.startReading(sentence + " " + sentence);
  await selectText(w, d, "catalyst", true);
  await w.DA.requestSupport(); await wait(400);
  d.getElementById("accept").click(); await wait(300);
  assert.ok(w.DA.S.text.startsWith(sentence + " The catalyst ("));
  d.getElementById("undo").click();
  assert.equal(w.DA.S.text, sentence + " " + sentence);
});

test("learner can override the support type; scaffold-only is stated honestly", async () => {
  const { w, d } = await page();
  w.DA.startReading(TEXT);
  await selectText(w, d, "Plants use photosynthesis to turn sunlight into food");
  d.getElementById("m-c").checked = true;
  await w.DA.requestSupport(); await wait(400);
  const t = d.getElementById("result").textContent;
  assert.match(t, /You chose: Help with the idea/);
  assert.match(t, /Understanding this part/);
  assert.equal(d.getElementById("accept"), null, "nothing to replace for scaffold-only");
});

test("regenerate flips the variant and feedback is posted", async () => {
  const { w, d, calls } = await page();
  w.DA.startReading(TEXT);
  await selectText(w, d, "accelerated");
  await w.DA.requestSupport(); await wait(400);
  d.getElementById("regen").click(); await wait(600);
  const adapts = calls.filter(c => c.url.endsWith("/api/adapt")).map(c => c.body.variant);
  assert.deepEqual(adapts, [0, 1]);
  assert.ok(calls.some(c => c.url.endsWith("/api/feedback") && c.body.decision === "regenerate"));
});

test("typed fallback selection works and unknown text is rejected politely", async () => {
  const { w, d } = await page();
  w.DA.startReading(TEXT);
  d.getElementById("typed").value = "photosynthesis"; d.getElementById("typed-go").click();
  assert.equal(w.DA.S.sel.span, "photosynthesis");
  d.getElementById("typed").value = "not in the text"; d.getElementById("typed-go").click();
  assert.equal(w.DA.S.sel.span, "photosynthesis");
});

test("accessibility basics: labelled controls, live region, language", async () => {
  const { d } = await page();
  assert.equal(d.documentElement.lang, "en");
  assert.equal(d.getElementById("live").getAttribute("aria-live"), "polite");
  for (const id of ["src", "s-bg", "s-contrast", "s-size", "s-lh", "s-ls", "s-font", "typed"])
    assert.ok(d.querySelector(`label[for=${id}]`), "no label for " + id);
  assert.ok(d.getElementById("reader").getAttribute("aria-label"));
});

test("Research Lab renders empty states from the real (empty) artifact set, no placeholders", async () => {
  const { d } = await page("/research.html");
  const t = d.getElementById("out").textContent;
  assert.match(t, /No research-grade runs/);
  assert.match(t, /No agreement report/);
  assert.match(t, /No frozen split manifest/);
  assert.match(t, /research model available: false/);
  assert.ok(!/macro-F1 0\.\d/.test(t), "no metrics should be shown when none exist");
});

test("Research Lab separates research-grade from smoke runs (render fixture, not real results)", async () => {
  const { w, d } = await page("/research.html");
  const cm = { labels: ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"], matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] };
  const m = { n: 3, accuracy: 1, macro_f1: 1, per_class: { VOCABULARY: { precision: 1, recall: 1, "f1-score": 1, support: 1 } }, confusion_matrix: cm };
  const run = (id, ds) => ({ experiment_id: id, kind: "fusion", arch: "fusion_on", weights: "w", data_status: ds, test: m, validation: m, split_sizes: { train: 1 }, warnings: [] });
  w.LAB.render({ model_status: { mode: "demo", research_model_available: false, warning: "w", research_model: {} }, dataset_split: null, agreement: [],
    runs: [run("RENDER_FIXTURE_research", "research")], non_research_runs: [run("RENDER_FIXTURE_smoke", "fixture_not_research")], ablations: [], traces: { present: false }, notes: [],
    experiments: [], non_research_experiments: [{ experiment_id: "EXP_FIXTURE", status: "partial", data_status: "fixture_not_research", smoke: true, seeds: [1], steps: { baselines: "ok", distilbert: "unavailable" }, unavailable_steps: ["distilbert"], failed_steps: [], dataset: { sha256: "x" }, code_sha256: "c", config_sha256: "g", reproduce: "cmd" }],
    error_analyses: [], non_research_error_analyses: [{ path: "EA_FIXTURE", split_analysed: "test", caveat: "contaminates the test set", models: { m: { n: 3, macro_f1: 0.5, accuracy: 0.5,
      macro_f1_ci95: { low: 0.1, high: 0.9, kind: "document-clustered", n_clusters: 2 }, warnings: ["only 2 bootstrap clusters; the interval is unreliable"],
      top_confusions: [{ true: "VOCABULARY", pred: "SYNTACTIC", count: 1, rate_of_true_class: 0.5 }], confidence: { available: false, reason: "no probability columns" },
      examples: { selection_rule: "span_id order (no probabilities available)", by_confusion_pair: {} }, slices: {} } } }] });
  const t = d.getElementById("out").textContent;
  assert.match(t, /RENDER_FIXTURE_research.*research-grade/s);
  assert.match(t, /RENDER_FIXTURE_smoke/); assert.match(t, /NOT RESEARCH/);
  assert.match(t, /No research-grade experiments/); assert.match(t, /No research-grade error analysis/);
  assert.match(t, /1 non-research experiment\(s\) and 1 non-research error analysis/);
  assert.match(t, /Unavailable steps \(not run\): distilbert/); assert.match(t, /interval is unreliable/); assert.match(t, /not evidence about the task/);
  const nonResearch = [...d.querySelectorAll("details")].find(x => x.textContent.includes("non-research run"));
  assert.ok(nonResearch, "smoke runs live inside a collapsed section");
});

test("adjudication page renders hostile CSV content as text, never as markup", async () => {
  const { w, d } = await page("/adjudication.html");
  const evil = 'span_id,reason,labels,text,context_before,context_after,note\ns1,disagreement,"A|B","<img src=x onerror=window.__pwned=1>","\\"><script>window.__pwned=2</script>","after",""\n';
  const input = d.getElementById("f");
  Object.defineProperty(input, "files", { value: [{ text: async () => evil }] });
  input.dispatchEvent(new w.Event("change"));
  await wait(100);
  assert.equal(w.__pwned, undefined, "injected script/handler must not run");
  assert.equal(d.querySelectorAll("#view img, #view script").length, 0);
  assert.match(d.getElementById("view").textContent, /<img src=x onerror/);
});

test('workspace navigation, library save and reopen preserve the passage', async()=>{
 const {w,d}=await page();
 w.WORKSPACE.openText('A passage worth keeping.','My passage');
 d.getElementById('save-passage').click();
 assert.equal(JSON.parse(w.localStorage.getItem('da_passages_v2'))[0].title,'My passage');
 d.querySelector('[data-view="library-view"]').click();
 assert.equal(d.getElementById('library-view').classList.contains('hidden'),false);
 d.querySelector('#library-list .primary').click();
 assert.equal(w.DA.S.text,'A passage worth keeping.');
 assert.equal(d.getElementById('h-read').textContent,'My passage');
 assert.equal(d.getElementById('reader-view').classList.contains('hidden'),false);
 w.close();
});

test('notebook uses literal text, and delete removes the saved record', async()=>{
 const {w,d}=await page();
 w.WORKSPACE.saveNote('<img src=x onerror=window.pwned=1>','<script>window.pwned=1</script>');
 assert.equal(w.pwned,undefined);
 assert.equal(d.querySelector('#notes-list img, #notes-list script'),null);
 assert.match(d.getElementById('notes-list').textContent,/<script>/);
 d.querySelector('#notes-list button').click();
 assert.deepEqual(JSON.parse(w.localStorage.getItem('da_notes_v2')),[]);
 w.close();
});

test('quick themes, text-size bounds and focus synchronize full settings',async()=>{
 const {w,d}=await page();
 d.querySelector('[data-theme="green"]').click();
 assert.equal(d.getElementById('s-bg').value,'green');
 assert.equal(d.querySelector('[data-theme="green"]').getAttribute('aria-pressed'),'true');
 for(let i=0;i<20;i++)d.getElementById('size-up').click();
 assert.equal(w.DA.look().size,34);
 assert.equal(d.getElementById('s-size').value,'34');
 d.getElementById('focus-toggle').click();
 assert.equal(d.getElementById('s-focus').checked,true);
 assert.ok(d.querySelector('#reader .para.active'));
 assert.equal(d.getElementById('focus-toggle').getAttribute('aria-pressed'),'true');
 w.close();
});

test('a request for an old selection never displays after the selection changes',async()=>{
 const {w,d}=await page();
 w.DA.startReading(TEXT);w.DA.setSelection({span:'catalyst',start:TEXT.indexOf('catalyst')});
 const fetchOriginal=w.fetch;
 let unblock;const blocker=new Promise(r=>unblock=r);
 w.fetch=async(u,o)=>{if(String(u)==='/api/adapt')await blocker;return fetchOriginal(u,o);};
 const pending=w.DA.requestSupport();
 w.DA.setSelection({span:'photosynthesis',start:TEXT.indexOf('photosynthesis')});
 unblock();await pending;
 assert.equal(w.DA.S.result,null);
 assert.equal(d.getElementById('result').classList.contains('hidden'),true);
 w.close();
});

test('accept applies the selected sentence correctly beyond the API context window',async()=>{
 const {w,d}=await page();
 const first='The catalyst speeds the reaction.';
 const text=first+' '+('A simple sentence provides some context. '.repeat(110))+first;
 w.DA.startReading(text);await selectText(w,d,'catalyst',true);
 await w.DA.requestSupport();
 assert.ok(w.DA.S.result._windowStart>0);
 d.getElementById('accept').click();
 assert.ok(w.DA.S.text.startsWith(first+' '));
 assert.match(w.DA.S.text.slice(-120),/catalyst \(a substance/);
 d.getElementById('undo').click();assert.equal(w.DA.S.text,text);
 w.close();
});

test('same word selected in a new location updates the selection offset',async()=>{
 const {w,d}=await page();const text='The catalyst works. The catalyst works.';
 w.DA.startReading(text);await selectText(w,d,'catalyst');const first=w.DA.S.sel.start;
 await selectText(w,d,'catalyst',true);
 assert.ok(w.DA.S.sel.start>first);
 w.close();
});

test('typed selection can choose the last occurrence and rejects oversized support spans',async()=>{
 const {w,d,calls}=await page();
 const text='The catalyst works. The catalyst works.';w.DA.startReading(text);
 d.getElementById('typed').value='catalyst';d.getElementById('typed-occurrence').value='last';d.getElementById('typed-go').click();
 assert.equal(w.DA.S.sel.start,text.lastIndexOf('catalyst'));
 const long='word '.repeat(70);w.DA.startReading(long);w.DA.setSelection({span:long.trim(),start:0});await w.DA.requestSupport();
 assert.match(d.getElementById('result').textContent,/shorter part/);
 assert.equal(calls.some(x=>x.url.endsWith('/api/adapt')),false);
 w.close();
});

test('saved support note captures actual response, never a fabricated explanation',async()=>{
 const {w,d}=await page();w.DA.startReading(TEXT);w.DA.setSelection({span:'catalyst',start:TEXT.indexOf('catalyst')});await w.DA.requestSupport();await wait(20);
 d.getElementById('save-support-note').click();
 const n=JSON.parse(w.localStorage.getItem('da_notes_v2'))[0];
 assert.match(n.text,/A substance that speeds up a chemical reaction/);assert.match(n.text,/Mode: demo/);
 w.close();
});

test('read aloud has an honest fallback when browser speech is unavailable',async()=>{
 const {w,d}=await page();d.getElementById('speak').click();
 assert.match(d.getElementById('toast').textContent,/not available in this browser/);
 assert.equal(d.getElementById('speech-stop').classList.contains('hidden'),true);
 w.close();
});

test('Research Lab prepares real local commands without silently relaxing data guards',async()=>{
 const {w,d,calls}=await page('/research.html');
 const commands=w.LAB.commands();
 assert.ok(commands.startsWith('.\\.venv\\Scripts\\python.exe -m ML.data_validation'));
 assert.match(commands,/--mode research/);assert.match(commands,/ML.group_split/);assert.match(commands,/ML.train_baselines/);
 assert.doesNotMatch(commands,/allow-fixture|--smoke|--force/);
 d.getElementById('cmd-model').value='distilbert';d.getElementById('build-command').click();
 assert.match(d.getElementById('commands').value,/distilbert\/distilbert-base-uncased/);
 assert.equal(calls.some(c=>/train|jobs/.test(c.url)),false);
 w.close();
});

test('Research Lab command builder rejects shell injection and parent paths',async()=>{
 const {w,d}=await page('/research.html');
 d.getElementById('cmd-csv').value='DATA/gold.csv; Remove-Item *';
 assert.throws(()=>w.LAB.commands(),/relative project path/);
 d.getElementById('build-command').click();assert.equal(d.getElementById('commands').value,'');assert.equal(d.getElementById('cmd-error').hidden,false);
 d.getElementById('cmd-csv').value='../secret.csv';assert.throws(()=>w.LAB.commands(),/relative project path/);
 d.getElementById('cmd-csv').value='DATA/gold.csv';d.getElementById('cmd-version').value='v1 && echo';assert.throws(()=>w.LAB.commands(),/version name/);
 w.close();
});

test('Research notes export does not invent scores or include smoke metrics',async()=>{
 const {w}=await page('/research.html');
 const text=w.LAB.report({model_status:{mode:'demo',research_model_available:false},dataset_split:null,runs:[],agreement:[],non_research_runs:[{experiment_id:'fixture',test:{accuracy:.999,macro_f1:.999}}]});
 assert.match(text,/No research-grade model results/);assert.match(text,/Automatic retraining enabled: false/);
 assert.doesNotMatch(text,/0\.999|fixture \|/);assert.match(text,/generator/);
 w.close();
});

test('Research views switch while preserving actual evidence and readiness',async()=>{
 const {w,d}=await page('/research.html');
 assert.match(d.getElementById('readiness').textContent,/Practice rules active/);
 assert.match(d.getElementById('readiness').textContent,/No research results yet/);
 d.querySelector('[data-lab-tab="training"]').click();assert.equal(d.getElementById('training').hidden,false);assert.equal(d.getElementById('evidence').hidden,true);
 d.querySelector('[data-lab-tab="learning"]').click();assert.match(d.getElementById('learning').textContent,/Evaluated prototype retraining is available/);
 d.querySelector('[data-lab-tab="evidence"]').click();assert.match(d.getElementById('out').textContent,/No research-grade runs/);
 w.close();
});

test('admin dashboard defaults to dark and stores its theme separately from learner comfort',async()=>{
 const {w,d}=await page('/research.html');
 assert.equal(d.body.dataset.labTheme,'dark');
 d.getElementById('lab-theme-toggle').click();assert.equal(d.body.dataset.labTheme,'light');
 d.getElementById('lab-palette').value='violet';d.getElementById('lab-palette').dispatchEvent(new w.Event('change'));
 assert.equal(d.body.style.getPropertyValue('--lab-accent'),'#6845b4');
 assert.equal(JSON.parse(w.localStorage.getItem('da_lab_theme_v1')).palette,'violet');
 assert.equal(w.localStorage.getItem('da_look_v1'),null);
 d.querySelector('[data-section="training"]').click();assert.equal(d.getElementById('training').hidden,false);
 w.close();
});

test('evidence inspector displays server artifact content as literal text',async()=>{
 const {w,d}=await page('/research.html');
 d.querySelector('[data-section="report"]').click();assert.equal(d.getElementById('lab-inspector').hidden,false);
 const original=w.fetch;w.fetch=(u,o)=>String(u).includes('/api/research/artifact')?Promise.resolve({ok:true,json:async()=>({path:'REPORTS/example.md',sha256:'fixture-only',content:'<img src=x onerror=window.pwned=1><script>window.pwned=1</script>'})}):original(u,o);
 await d.getElementById('inspect-load').onclick();
 assert.equal(w.pwned,undefined);assert.equal(d.querySelector('#inspect-text img, #inspect-text script'),null);assert.match(d.getElementById('inspect-text').textContent,/<img/);
 d.getElementById('inspect-close').click();assert.equal(d.getElementById('lab-inspector').hidden,true);
 w.close();
});

test('saved learner report and live research demo show the same real interaction',async()=>{
 const cryptoNode=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
 const key=cryptoNode.randomBytes(32).toString('hex'),profileId=cryptoNode.createHash('sha256').update(key).digest('hex');
 const headers={'Content-Type':'application/json','x-learner-key':key};
 const post=async(url,body)=>{const response=await fetch(BASE+url,{method:'POST',headers,body:JSON.stringify(body)});const data=await response.json();assert.equal(response.status,200,url+': '+JSON.stringify(data));return data;};
 const waitFor=async(check)=>{const deadline=Date.now()+12000;while(Date.now()<deadline){if(check())return;await wait(50);}assert.fail('Page did not show the saved learner data.');};
 const openScriptPage=async(name,script,learnerKey)=>{const html=await(await fetch(BASE+'/'+name)).text();const dom=new JSDOM(html,{url:BASE+'/'+name,runScripts:'dangerously',pretendToBeVisual:true});dom.window.fetch=(url,options)=>fetch(new URL(url,BASE),options);if(learnerKey){dom.window.localStorage.setItem('da_learner_key_v1',learnerKey);dom.window.sessionStorage.setItem('da_legacy_active','1');}dom.window.eval(fs.readFileSync(path.join(__dirname,script),'utf8'));return dom;};
 let reportDom,reconnectedDom,labDom;
 try{
  await post('/api/learner/survey',{consent:true,alias:'Browser demo learner',preferred_language:'en',study_languages:['en'],preferred_style:'short',difficulties:['PRONUNCIATION']});
  const session=await post('/api/learner/session',{language:'en'});
  await post('/api/support',{text:'Plants use photosynthesis to make food.',span:'photosynthesis',category_override:'PRONUNCIATION',document_language:'en',session_id:session.session_id,request_id:cryptoNode.randomUUID()});
  reportDom=await openScriptPage('my-progress.html','../../FRONTEND/my-progress.js',key);
  await waitFor(()=>reportDom.window.document.getElementById('alias').textContent==='Browser demo learner');
  assert.match(reportDom.window.document.getElementById('metrics').textContent,/1Support decisions/);
  assert.match(reportDom.window.document.getElementById('choices').textContent,/Pronunciation1/);
  reconnectedDom=await openScriptPage('my-progress.html','../../FRONTEND/my-progress.js');
  assert.equal(reconnectedDom.window.document.getElementById('missing').hidden,false);
  reconnectedDom.window.document.getElementById('reconnect-key').value=key;
  reconnectedDom.window.document.getElementById('reconnect').click();
  await waitFor(()=>reconnectedDom.window.document.getElementById('alias').textContent==='Browser demo learner');
  assert.equal(reconnectedDom.window.localStorage.getItem('da_learner_key_v1'),key);
  labDom=await openScriptPage('research-demo.html','../../FRONTEND/research-demo.js');
  await waitFor(()=>[...labDom.window.document.getElementById('learner').options].some(option=>option.value===profileId));
  const select=labDom.window.document.getElementById('learner');select.value=profileId;select.dispatchEvent(new labDom.window.Event('change'));
  await waitFor(()=>labDom.window.document.getElementById('name').textContent.includes('Browser demo learner'));
  assert.match(labDom.window.document.getElementById('route').textContent,/Decision source: learner_choice/);
  assert.match(labDom.window.document.getElementById('requests').textContent,/Pronunciation1/);
  assert.match(labDom.window.document.getElementById('shown').textContent,/Support shownListen to this selected word or phrase/);
 }finally{
  reportDom?.window.close();reconnectedDom?.window.close();labDom?.window.close();
  await fetch(BASE+'/api/profile',{method:'DELETE',headers:{'x-learner-key':key}});
 }
});
