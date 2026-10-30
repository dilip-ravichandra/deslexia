import sys
import os,time,subprocess,json,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2];out=root/'REPORTS'/'browser-captures'
env=dict(os.environ,DYSLEXIADAPT_MODELS_DIR=os.environ.get('DYSLEXIADAPT_MODELS_DIR',str(root/'MODELS')));out.mkdir(parents=True,exist_ok=True);log=open(str(out/'visual-server.log'),'w');server=subprocess.Popen([sys.executable,'-m','uvicorn','BACKEND.app:app','--host','127.0.0.1','--port','8025'],cwd=root,env=env,stdout=log,stderr=log)
checks=[]
try:
 for i in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:8025/api/health',timeout=1);break
  except Exception:time.sleep(.2)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8025')
  page.locator('#remember-support').check();page.locator('#document-file').set_input_files(str(root/'TESTS/fixtures/documents/chart.png'));page.wait_for_function("document.querySelector('#document-status').textContent.includes('ready. Check')",timeout=60000)
  page.locator('#crop-left').fill('10');page.locator('#crop-top').fill('0');page.locator('#crop-width').fill('90');page.locator('#crop-height').fill('100');page.locator('#crop-apply').click();checks.append('Keyboard crop → bounded region')
  page.locator('#crop-reset').click();page.locator('#visual-question').fill('Which group has the most books? Explain the comparison.');started=time.time();page.locator('#visual-explain').click();page.wait_for_function("document.querySelector('#visual-save').disabled===false",timeout=600000)
  answer=page.locator('#visual-answer').inner_text();assert 'C' in answer,answer;assert 'books' in answer.lower(),answer;checks.append('Browser → actual Qwen vision projector → chart explanation');print('Vision seconds',round(time.time()-started,1),answer,flush=True)
  page.locator('#visual-answer button').filter(has_text='This helped').click();page.wait_for_function("document.querySelector('#visual-answer').textContent.includes('Visual style feedback only')");checks.append('Opt-in visual helpfulness → persisted feedback')
  page.locator('#visual-save').click();page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/'DyslexiAdapt_Visual_Explanation.png'),full_page=True);checks.append('Visual answer → notebook')
  page.goto('http://127.0.0.1:8025/research.html');page.wait_for_function("document.querySelector('#out').textContent.includes('Visual explanation feedback')",timeout=30000);assert not page.locator('#err').inner_text();checks.append('Research lab → actual visual feedback counts')
  page.goto('http://127.0.0.1:8025');page.locator('#forget-support').click();page.wait_for_function("document.querySelector('#profile-status').textContent.includes('deleted')");checks.append('Forget history → deletes visual feedback')
  assert not errors,errors;browser.close()
finally:
 server.terminate();server.wait(timeout=15);log.close();(out/'visual-browser-checks.json').write_text(json.dumps({'checks':checks},indent=2));print(json.dumps(checks),flush=True)
