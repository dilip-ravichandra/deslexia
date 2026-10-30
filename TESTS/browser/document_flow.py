import sys
import os,sys,subprocess,time,json,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2];out=root/'REPORTS'/'browser-captures';out.mkdir(exist_ok=True)
env=dict(os.environ,DYSLEXIADAPT_MODELS_DIR=os.environ.get('DYSLEXIADAPT_MODELS_DIR',str(root/'MODELS')))
out.mkdir(parents=True,exist_ok=True);log=open(str(out/'doc-server.log'),'w');server=subprocess.Popen([sys.executable,'-m','uvicorn','BACKEND.app:app','--host','127.0.0.1','--port','8024'],cwd=root,env=env,stdout=log,stderr=log)
checks=[]
try:
 for i in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:8024/api/health',timeout=1);break
  except Exception:time.sleep(.2)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8024');page.wait_for_function("document.querySelector('#connection').textContent==='Trained prototype'")
  page.locator('#document-file').set_input_files(str(root/'TESTS/fixtures/documents/textbook.png'));page.wait_for_function("document.querySelector('#document-status').textContent.includes('ready. Check')",timeout=60000)
  assert 'catalyst' in page.locator('#extracted-text').input_value();checks.append('Image upload → actual OCR → editable text')
  page.locator('#extracted-text').fill('A catalyst helps a chemical reaction happen faster without being used up.')
  page.locator('#read-extracted').click();assert 'catalyst' in page.locator('#reader').inner_text();checks.append('Reviewed OCR text → reader')
  page.locator('.keyboard-help summary').click();page.locator('#typed').fill('catalyst');page.locator('#typed-go').click();page.locator('#m-v').check();page.locator('#go').click();page.wait_for_function("document.querySelector('#result').textContent.includes('Understanding')",timeout=90000);checks.append('Uploaded text → selected word → actual support API')
  page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/'DyslexiAdapt_Upload_Preview.png'));page.screenshot(path=str(out/'DyslexiAdapt_Upload_Reader.png'),full_page=True)
  page.goto('http://127.0.0.1:8024/research.html');page.wait_for_function("document.querySelector('#out').textContent.includes('Actual reader models')",timeout=30000)
  assert not page.locator('#err').inner_text(),page.locator('#err').inner_text();assert '140' in page.locator('#out').inner_text();assert '45' in page.locator('#out').inner_text();assert page.locator('.evidence-row').count()>0;assert 'Practice rules active' not in page.locator('#readiness').inner_text();checks.append('Research overview → actual active model, data and validation charts')
  page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/'DyslexiAdapt_Lab_Preview.png'));page.screenshot(path=str(out/'DyslexiAdapt_Research_Evidence.png'),full_page=True)
  page.locator('#dl-report').click();checks.append('Research report export control')
  page.goto('http://127.0.0.1:8024/learning.html');page.wait_for_function("document.querySelector('#active').textContent.includes('Active version')");assert page.locator('#runs .queue').count()>=2;checks.append('Training lab → active registry and evaluated versions')
  # narrow viewport: visible upload and operable stacked page workspace
  page.goto('http://127.0.0.1:8024');page.set_viewport_size({'width':390,'height':844});page.locator('#document-file').set_input_files(str(root/'TESTS/fixtures/documents/textbook.png'));page.wait_for_function("document.querySelector('#document-status').textContent.includes('ready. Check')",timeout=60000)
  assert page.locator('#document-workspace').is_visible();assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1');checks.append('Mobile viewport → page preview, editable OCR and no horizontal overflow')
  assert not errors,errors;checks.append('No browser JavaScript exceptions')
  browser.close()
finally:
 server.terminate();server.wait(timeout=10);log.close();(out/'browser-checks.json').write_text(json.dumps({'checks':checks},indent=2));print(json.dumps(checks),flush=True)
