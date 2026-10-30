import io
import pytest
from PIL import Image,ImageDraw,ImageFont
from fastapi.testclient import TestClient
from BACKEND.app import app
from BACKEND.documents import extract,MAX_UPLOAD,tesseract_available
import importlib.util
OCR_READY=tesseract_available() or importlib.util.find_spec('rapidocr_onnxruntime') is not None
@pytest.fixture
def client():return TestClient(app)
def png():
 im=Image.new('RGB',(900,220),'white');draw=ImageDraw.Draw(im)
 try:font=ImageFont.truetype('DejaVuSans.ttf',36)
 except OSError:font=ImageFont.load_default(size=36)
 draw.text((35,70),'Plants need sunlight.',font=font,fill='black');out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()
def pdf(scanned=False):
 import pypdfium2 as p
 doc=p.PdfDocument.new()
 for i in range(2):
  page=doc.new_page(500,400)
  if scanned:
   bitmap=p.PdfBitmap.from_pil(Image.open(io.BytesIO(png())));obj=p.PdfImage.new(doc);obj.set_bitmap(bitmap);obj.set_matrix(p.PdfMatrix(450,0,0,110,25,100));page.insert_obj(obj);page.gen_content();bitmap.close()
  page.close()
 out=io.BytesIO();doc.save(out);doc.close();return out.getvalue()
@pytest.mark.skipif(not OCR_READY,reason='Real OCR requires RapidOCR or native Tesseract assets.')
def test_real_image_ocr(client):
 r=client.post('/api/documents/extract',files={'file':('textbook.png',png())});assert r.status_code==200,r.text
 d=r.json();assert 'sunlight' in d['text'].lower();assert d['method']=='OCR';assert d['image'].startswith('data:image/png;base64,');assert d['lines'];assert d['warnings'];assert d['language']=='en'

def test_auto_ocr_retries_english_when_math_creates_indic_noise(monkeypatch):
 import BACKEND.documents as documents
 calls=[]
 def ocr_candidate(image,language):
  calls.append(language)
  text='Kleene Closure special notes. An infinite set of all words. ನನ್ನ' if language=='auto' else 'Kleene Closure special notes. An infinite set of all words.'
  return [{'text':text,'confidence':.9,'box':[[0,0],[1,0],[1,1],[0,1]]}]
 monkeypatch.setattr(documents,'tesseract_available',lambda:True)
 monkeypatch.setattr(documents,'tesseract_ocr',ocr_candidate)
 lines=documents.page_ocr(None,'auto')
 assert calls==['auto','en']
 assert 'Kleene Closure' in lines[0]['text'] and 'ನನ್ನ' not in lines[0]['text']

def test_auto_ocr_keeps_substantial_native_text(monkeypatch):
 import BACKEND.documents as documents
 calls=[]
 def ocr_candidate(image,language):
  calls.append(language)
  return [{'text':'विद्यालय में बच्चे पढ़ते हैं।','confidence':.9,'box':[[0,0],[1,0],[1,1],[0,1]]}]
 monkeypatch.setattr(documents,'tesseract_available',lambda:True)
 monkeypatch.setattr(documents,'tesseract_ocr',ocr_candidate)
 assert documents.page_ocr(None,'auto')[0]['text'].startswith('विद्यालय')
 assert calls==['auto']

def test_rapidocr_auto_ignores_confident_script_noise(monkeypatch):
 import BACKEND.documents as documents
 def ocr_candidate(image,language):
  text='Kleene Closure special notes. An infinite set of all words.'
  if language=='kn':text+=' ನನ್ನ'
  return [{'text':text,'confidence':.99 if language=='kn' else .8,'box':[[0,0],[1,0],[1,1],[0,1]]}]
 monkeypatch.setattr(documents,'tesseract_available',lambda:False)
 monkeypatch.setattr(documents,'ocr',ocr_candidate)
 assert documents.page_ocr(None,'auto')[0]['text']=='Kleene Closure special notes. An infinite set of all words.'
@pytest.mark.skipif(not OCR_READY,reason='Real OCR requires RapidOCR or native Tesseract assets.')
def test_scanned_pdf_ocr(client):
 r=client.post('/api/documents/extract',files={'file':('scan.pdf',pdf(True))},data={'page':2});assert r.status_code==200,r.text
 d=r.json();assert d['page_count']==2;assert d['page']==2;assert 'sunlight' in d['text'].lower()
@pytest.mark.parametrize('name,body',[('bad.pdf',b'fake'),('bad.png',b'fake'),('unsupported.exe',b'fake'),('empty.txt',b'')])
def test_invalid_uploads(client,name,body):assert client.post('/api/documents/extract',files={'file':(name,body)}).status_code==422
@pytest.mark.parametrize('number',[0,3])
def test_page_bounds(client,number):assert client.post('/api/documents/extract',files={'file':('blank.pdf',pdf())},data={'page':number}).status_code==422
@pytest.mark.skipif(not OCR_READY,reason='Forced OCR requires RapidOCR or native Tesseract assets.')
def test_embedded_pdf_and_force_ocr():
 from reportlab.pdfgen.canvas import Canvas
 out=io.BytesIO();c=Canvas(out);c.setFont('Helvetica',22);c.drawString(50,700,'A catalyst helps reactions happen faster.');c.save()
 d=extract(out.getvalue(),'notes.pdf');assert d['method']=='PDF embedded text';assert 'catalyst' in d['text']
 d=extract(out.getvalue(),'notes.pdf',force_ocr=True);assert d['method']=='OCR';assert 'catalyst' in d['text']
def test_filename_not_used_as_path(client):
 r=client.post('/api/documents/extract',files={'file':('../../notes.txt',b'Read me.')});assert r.status_code==200;assert r.json()['text']=='Read me.'
def test_bad_encoding(client):assert client.post('/api/documents/extract',files={'file':('notes.txt',b'\xff\xfe')}).status_code==422
def test_upload_size(client):assert client.post('/api/documents/extract',files={'file':('huge.txt',b'x'*(MAX_UPLOAD+1))}).status_code==422
def test_decoded_size_limit():
 im=Image.new('1',(5000,5000));out=io.BytesIO();im.save(out,format='PNG')
 with pytest.raises(ValueError):extract(out.getvalue(),'large.png')
def test_missing_vision_explicit(client,monkeypatch,tmp_path):
 monkeypatch.setenv('DYSLEXIADAPT_MODELS_DIR',str(tmp_path));r=client.post('/api/documents/explain',files={'file':('picture.png',png())});assert r.status_code==503;assert 'Vision model' in r.json()['detail']
def test_invalid_vision_options(client):assert client.post('/api/documents/explain',files={'file':('picture.png',png())},data={'style':'unknown'}).status_code==422
def test_invalid_picture_kind(client):assert client.post('/api/documents/explain',files={'file':('picture.png',png())},data={'kind':'diagnosis'}).status_code==422
def test_picture_prompts_are_specific_and_cautious():
 from ML.visual_support import build_prompt,screen_graph_answer
 graph=build_prompt('Explain this graph','Speed (m/s)','steps','en','graph')
 biology=build_prompt('Explain this diagram','','short','en','biology')
 geometry=build_prompt('Explain these shapes','','short','en','geometry')
 assert 'axis' in graph and 'Never guess exact values' in graph and 'Speed (m/s)' in graph
 assert 'arrows' in biology and 'Do not invent' in biology
 assert 'shapes' in geometry and 'measurements' in geometry
 cleaned,withheld=screen_graph_answer('A has 2, B has 4, C has 6. The x-axis is labeled Books read. C is largest.','en')
 assert withheld and 'x-axis' not in cleaned and 'C is largest.' in cleaned
 assert 'closer crop' in screen_graph_answer('The y-axis shows A, B, C.','en')[0]
def test_picture_kind_reaches_visual_model(client,monkeypatch):
 import ML.visual_support as vision
 seen={}
 def explain(*args):
  seen['kind']=args[-1]
  return {'explanation':'A line rises from left to right.','model':'test model'}
 monkeypatch.setattr(vision,'explain',explain)
 response=client.post('/api/documents/explain',files={'file':('graph.png',png())},data={'kind':'graph'})
 assert response.status_code==200 and seen['kind']=='graph'
 assert response.json()['explanation']=='A line rises from left to right.'
def test_picture_without_words_prompts_visual_help(client,monkeypatch):
 import BACKEND.documents as documents
 monkeypatch.setattr(documents,'page_ocr',lambda image,language:[])
 result=client.post('/api/documents/extract',files={'file':('shapes.png',png())}).json()
 assert result['text']=='' and result['image'].startswith('data:image/png;base64,')
 assert any('Explain whole picture' in warning for warning in result['warnings'])
 assert not any('language was estimated' in warning for warning in result['warnings'])
def test_invalid_vision_image(client):assert client.post('/api/documents/explain',files={'file':('picture.png',b'fake')}).status_code==422
def test_actual_lab_data(client):
 r=client.get('/api/research/summary');assert r.status_code==200;d=r.json();assert d['prototype_data']['total']==140;assert d['prototype_data']['unresolved']==45;assert d['prototype_data']['archived'];assert d['prototype']['active'] is None;assert isinstance(d['document_status']['ocr_available'],bool)
def test_admin_gate(client,monkeypatch):
 monkeypatch.setenv('DYSLEXIADAPT_ADMIN_TOKEN','private');assert client.get('/api/research/summary').status_code==401;assert client.get('/api/research/summary',headers={'x-admin-token':'private'}).status_code==200


def test_visual_feedback_style_ownership_and_delete(service=None):
    import shutil,tempfile
    from pathlib import Path
    from BACKEND.adaptive import AdaptiveService
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as path:
        p=Path(path);(p/'DATA').mkdir();shutil.copy(root/'DATA/prototype_pilots.json',p/'DATA/prototype_pilots.json')
        svc=AdaptiveService(p);key='a'*64
        from BACKEND.learner import LearnerModel
        learner=LearnerModel(svc.db_path);learner.survey(key,{'consent':True,'difficulties':[],'preferred_style':'short'})
        consent=svc.consent_version(key)
        for i in range(2):
            trace=svc.record_visual(key,'steps','What is shown?',{'explanation':'Two arrows point right.','model':'test fixture'},consent)
            svc.visual_feedback(key,trace,'accept');svc.visual_feedback(key,trace,'accept')
        assert svc.profile(key)['preferences']['VISUAL']=='steps'
        assert svc.analytics()['visual_feedback'][0]['count']==2
        with pytest.raises(LookupError):svc.visual_feedback('b'*64,trace,'accept')
        with pytest.raises(ValueError):svc.visual_feedback(key,trace,'reject')
        svc.forget(key);assert not svc.analytics()['visual_feedback'];assert svc.profile(key)['preferences']=={}
