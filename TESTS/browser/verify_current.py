"""Isolated browser engineering fixtures; never save review decisions as real research data."""
import json,sys,threading,time,uuid,shutil,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'REPORTS/software-fixes-2026-10-15';OUT.mkdir(exist_ok=True)
if (OUT/'browser-checks.json').exists():shutil.copyfile(OUT/'browser-checks.json',OUT/('browser-previous-'+uuid.uuid4().hex[:8]+'.json'))
TEMP=ROOT/'.audit-tmp'/('browser-fixes-'+uuid.uuid4().hex);(TEMP/'DATA').mkdir(parents=True)
shutil.copyfile(ROOT/'DATA/public_sources.json',TEMP/'DATA/public_sources.json')
import BACKEND.app as mod
from BACKEND.adaptive import AdaptiveService
from BACKEND.learner import LearnerModel
from ML import human_review
mod.adaptive=AdaptiveService(TEMP);mod.learner=LearnerModel(mod.adaptive.db_path);mod.ROOT=TEMP;human_review.ROOT=TEMP
import uvicorn
from playwright.sync_api import sync_playwright,expect
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
server=uvicorn.Server(uvicorn.Config(mod.app,host='127.0.0.1',port=port,log_level='warning'))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
for _ in range(100):
    if server.started:break
    time.sleep(.05)
base=f'http://127.0.0.1:{port}';result={'fixture':'Authored browser checks, not human review or student results','checks':[],'errors':[]}
def passed(name):result['checks'].append(name)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000})
        page=context.new_page()
        page.on('pageerror',lambda e:result['errors'].append(str(e)))
        page.goto(base);page.locator('#survey-skip').click()
        for text,span,start,category,expected in [
            ('A catalyst speeds up a chemical reaction.','chemical reaction',23,'CONCEPTUAL','substances change'),
            ('I left money at the bank. We sat beside the river bank.','bank',50,'VOCABULARY','land along the edge'),
            ('🌿 word','word',3,'PRONUNCIATION','Listen to selected text')]:
            page.evaluate('([text,span,start])=>{DA.startReading(text);DA.setSelection({span,start});}',[text,span,start])
            page.locator(f'input[name=mode][value={category}]').check();page.locator('#go').click()
            expect(page.locator('#result')).to_contain_text(expected)
            passed('Browser support: '+span+' / '+category)
        page.screenshot(path=str(OUT/'reader-fixed.png'),full_page=True)
        page.locator('#profile-setup').click();page.locator('#survey-alias').fill('ENGINEERING FIXTURE ONLY')
        page.locator('input[name=survey-need][value=PRONUNCIATION]').check();page.locator('#survey-consent').check();page.locator('#survey-save').click()
        expect(page.locator('#survey-panel')).to_be_hidden()
        page.evaluate("DA.startReading('Select this word.');DA.setSelection({span:'word',start:12});")
        page.locator('input[name=mode][value=PRONUNCIATION]').check();page.locator('#go').click()
        expect(page.locator('#result')).to_contain_text('Listen to selected text')
        page.locator('#result details').filter(has=page.locator('summary',has_text='Optional feedback')).locator('summary').click()
        page.locator('#helpful').click();expect(page.locator('#helpful')).to_be_disabled()
        passed('Consented survey, session, actual support route and optional feedback')
        lab=page.context.new_page();lab.on('pageerror',lambda e:result['errors'].append(str(e)))
        lab.goto(base+'/learner-lab.html');lab.wait_for_function("document.querySelector('#learner').options.length===2")
        lab.locator('#learner').select_option(index=1);expect(lab.locator('#event-count')).to_contain_text('latest events')
        expect(lab.locator('#timeline')).to_contain_text('help_request');expect(lab.locator('#timeline')).to_contain_text('optional_feedback')
        expect(lab.locator('#route')).to_contain_text('Pronunciation')
        lab.screenshot(path=str(OUT/'lab-fixture.png'),full_page=True)
        passed('Browser → API → database → evidence lab')
        page.locator('#forget-support').click();expect(page.locator('#profile-status')).to_contain_text('deleted')
        assert page.evaluate("localStorage.getItem('da_learner_key_v1')") is None
        lab.locator('#learner').select_option('');lab.locator('#refresh').click()
        lab.wait_for_function("document.querySelector('#learner').options.length===1")
        passed('Forget removes saved evidence and browser capability')
        exports=[]
        for reviewer,category in [('engineering_a','VOCABULARY'),('engineering_b','CONCEPTUAL')]:
            review=browser.new_page();review.on('pageerror',lambda e:result['errors'].append(str(e)))
            review.goto(base+'/human-review.html');expect(review.locator('#begin')).to_be_enabled()
            review.locator('#reviewer').fill(reviewer);review.locator('#competent').check();review.locator('#independent').check();review.locator('#begin').click()
            expect(review.locator('#category')).to_have_value('')
            review.locator('#category').select_option(category);review.locator('#confidence').select_option('3');review.locator('#rationale').fill('ENGINEERING FIXTURE ONLY. Not an actual human review.')
            review.locator('#save').click();expect(review.locator('#progress')).to_contain_text('1 completed')
            review.reload();review.locator('#reviewer').fill(reviewer);review.locator('#competent').check();review.locator('#independent').check();review.locator('#begin').click();expect(review.locator('#progress')).to_contain_text('1 completed')
            with review.expect_download() as download:review.locator('#export').click()
            path=TEMP/(reviewer+'.json');download.value.save_as(path);exports.append(str(path))
            review.close()
        passed('Independent blank sessions, save/restore and separate JSON exports')
        lab.locator('#review-files').set_input_files(exports);lab.locator('#review-merge').click()
        expect(lab.locator('#review-message')).to_contain_text('disagreement')
        expect(lab.locator('#review-downloads')).to_contain_text('Download reviewed.csv')
        with lab.expect_download() as download:lab.get_by_role('button',name='Download reviewed.csv',exact=True).click()
        path=TEMP/'reviewed-fixture.csv';download.value.save_as(path)
        assert 'OTHER_UNCERTAIN' in path.read_text(encoding='utf-8')
        assert not (ROOT/'ARTIFACTS/human_routing_active.json').exists()
        passed('Admin merge/download retains disagreement; no training or activation')
        for language in ['hi','kn','ta']:
            response=page.request.get(base+'/api/admin/public-materials',params={'language':language})
            assert response.status==200
        passed('All three Indic public-material APIs work in normal Windows encoding')
        mobile=browser.new_page(viewport={'width':390,'height':844})
        mobile.goto(base+'/human-review.html');mobile.locator('#reviewer').fill('engineering_mobile');mobile.locator('#language').select_option('kn');mobile.locator('#competent').check();mobile.locator('#independent').check();mobile.locator('#begin').click();expect(mobile.locator('#work')).to_be_visible()
        assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
        mobile.screenshot(path=str(OUT/'review-mobile-kn.png'),full_page=True)
        passed('Kannada source display and mobile review layout')
        assert not result['errors'],result['errors']
        browser.close();result['status']='passed'
except Exception as e:
    result.update(status='failed',error=type(e).__name__+': '+str(e));raise
finally:
    server.should_exit=True;thread.join(timeout=5)
    (OUT/'browser-checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
