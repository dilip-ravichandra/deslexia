"""Bounded page extraction; raw uploads are not retained after processing."""
import base64
import io
import threading
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 25 * 1024 * 1024
MAX_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
_OCR = {}
_LOCK = threading.Lock()

def image_url(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()

def decode_image(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image is too large. Use a photo under 20 megapixels.")
            image.load()
            return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ValueError("This image could not be opened. Use PNG, JPG or WEBP.") from e

def ocr(image,language="en"):
    if tesseract_available():return tesseract_ocr(image,language)
    from ML.multilingual import models
    files={'hi':'devanagari_PP-OCRv4_rec_mobile.onnx','kn':'ka_PP-OCRv4_rec_mobile.onnx','ta':'ta_PP-OCRv4_rec_mobile.onnx'}
    with _LOCK:
        if language not in _OCR:
            from rapidocr_onnxruntime import RapidOCR
            params={'det_limit_side_len':1600,'det_limit_type':'max','intra_op_num_threads':2,'inter_op_num_threads':1}
            if language!='en':
                path=models()/'ocr'/files[language]
                if not path.exists():raise LookupError('OCR model missing for '+language+'. Run multilingual setup.')
                params['rec_model_path']=str(path)
            _OCR[language]=RapidOCR(**params)
        result,_=_OCR[language](image_url_bytes(image))
    lines = []
    for box, text, score in result or []:
        lines.append({"text": str(text), "confidence": float(score), "box": [[float(x), float(y)] for x, y in box]})
    return lines

def image_url_bytes(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()

def extract(data, filename, page=1, force_ocr=False,language="auto"):
    if not data: raise ValueError("Choose a non-empty file.")
    if len(data) > MAX_UPLOAD: raise ValueError("Choose a file smaller than 25 MB.")
    if language not in {'auto','en','hi','kn','ta'}:raise ValueError('Unsupported document language.')
    name = filename.lower()
    lines, count, method = [], 1, "OCR"
    if name.endswith('.txt'):
        if page != 1: raise ValueError("Text files have one page.")
        try: text = data.decode('utf-8-sig')
        except UnicodeDecodeError as e: raise ValueError("Save the text file using UTF-8 encoding.") from e
        if len(text) > 50000: raise ValueError("Text is too long. Import a smaller section under 50,000 characters.")
        return {"page": 1, "page_count": 1, "text": text, "method": "UTF-8 text", "image": None, "lines": [], "warnings": [], "language":language if language!='auto' else __import__("ML.multilingual",fromlist=["detect"]).detect(text)}
    if name.endswith('.pdf'):
        if not data.startswith(b'%PDF-'): raise ValueError("This file is not a valid PDF.")
        import pypdfium2 as pdfium
        try:
            doc = pdfium.PdfDocument(data)
        except Exception as e: raise ValueError("Cannot open this PDF. It may be damaged or password protected.") from e
        try:
            count = len(doc)
            if count > 500: raise ValueError("Use a PDF with 500 pages or fewer.")
            if page < 1 or page > count: raise ValueError("Page number is outside this document.")
            sheet = doc[page - 1]
            try:
                scale = min(2.0, 1800 / max(sheet.get_size()))
                bitmap = sheet.render(scale=scale)
                try: image = bitmap.to_pil().convert('RGB').copy()
                finally: bitmap.close()
                textpage = sheet.get_textpage()
                try: text = textpage.get_text_range().strip()
                finally: textpage.close()
            finally: sheet.close()
        finally: doc.close()
        if not force_ocr and len(text) >= 20:
            method = "PDF embedded text"
        else:
            lines = page_ocr(image,language)
            text = '\n'.join(x['text'] for x in lines)
    elif name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        if page != 1: raise ValueError("Images have one page.")
        image = decode_image(data)
        image.thumbnail((1800,1800))
        lines = page_ocr(image,language)
        text = '\n'.join(x['text'] for x in lines)
    else: raise ValueError("Use PDF, TXT, PNG, JPG or WEBP.")
    warnings = []
    if not text.strip(): warnings.append("No words found. OCR reads text, not diagrams or graphs. Choose Explain whole picture to ask about the image.")
    if text.strip() and method=='OCR' and language=='auto':warnings.append('OCR language was estimated. Confirm the document language and rerun OCR if it is wrong.')
    if text.strip() and method == 'OCR': warnings.append("Check the extracted words before reading aloud. OCR can misread columns, equations, superscripts and small labels; correct math symbols in the text box.")
    if any(x['confidence'] < .8 for x in lines): warnings.append("Some text has low OCR confidence. Compare it with the original page.")
    if len(text) > 50000: warnings.append("This page has too much text. Only the first 50,000 characters were extracted.")
    return {"page": page, "page_count": count, "text": text[:50000], "method": method, "ocr_engine": "Tesseract tessdata_best" if method=="OCR" and tesseract_available() else "RapidOCR ONNX" if method=="OCR" else "PDF embedded text", "image": image_url(image), "width": image.width, "height": image.height, "lines": lines, "warnings": warnings,"language": language if language!='auto' else __import__("ML.multilingual",fromlist=["detect"]).detect(text)}

def page_ocr(image,language):
    from ML.multilingual import detect
    if tesseract_available():
        if language!='auto':return tesseract_ocr(image,language)
        mixed=tesseract_ocr(image,'auto')
        return mixed if detect(' '.join(line['text'] for line in mixed))!='en' else tesseract_ocr(image,'en')
    if language!='auto':return ocr(image,language)
    english=ocr(image,'en')
    candidates=[]
    for lang in ['hi','kn','ta']:
        try:
            lines=ocr(image,lang)
            if detect(' '.join(line['text'] for line in lines))!=lang:continue
            score=sum(x['confidence']*len(x['text']) for x in lines)/max(1,sum(len(x['text']) for x in lines))
            candidates.append((score,lines))
        except LookupError:continue
    english_score=sum(x['confidence']*len(x['text']) for x in english)/max(1,sum(len(x['text']) for x in english))
    return max(candidates,key=lambda c:c[0])[1] if candidates and max(candidates,key=lambda c:c[0])[0]>english_score+.05 else english

def tesseract_command():
    import os,shutil
    command=os.environ.get('TESSERACT_CMD') or shutil.which('tesseract')
    if command:return command
    path=__import__('pathlib').Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tesseract-OCR/tesseract.exe'
    return str(path) if path.exists() else None

def tesseract_available():
    from ML.multilingual import models
    return bool(tesseract_command()) and all((models()/'ocr-tesseract'/name).exists() for name in ['eng.traineddata','hin.traineddata','kan.traineddata','tam.traineddata'])

def tesseract_ocr(image,language):
    import subprocess,os,csv
    from ML.multilingual import models
    lang={'en':'eng','hi':'hin+eng','kn':'kan+eng','ta':'tam+eng','auto':'eng+hin+kan+tam'}[language]
    command=[tesseract_command(),'stdin','stdout','--tessdata-dir',str(models()/'ocr-tesseract'),'-l',lang,'--oem','1','--psm','6','-c','tessedit_create_tsv=1']
    result=subprocess.run(command,input=image_url_bytes(image),capture_output=True,timeout=40,env={**os.environ,'OMP_THREAD_LIMIT':'2'})
    if result.returncode:raise ValueError('The native OCR engine could not read this page.')
    grouped={}
    for row in csv.DictReader(io.StringIO(result.stdout.decode('utf-8')),delimiter='\t'):
        if not row.get('text','').strip() or float(row['conf'])<0:continue
        key=(row['block_num'],row['par_num'],row['line_num']);grouped.setdefault(key,[]).append(row)
    lines=[]
    for words in grouped.values():
        x=min(int(w['left']) for w in words);y=min(int(w['top']) for w in words);right=max(int(w['left'])+int(w['width']) for w in words);bottom=max(int(w['top'])+int(w['height']) for w in words)
        lines.append({'text':' '.join(w['text'] for w in words),'confidence':sum(float(w['conf']) for w in words)/len(words)/100,'box':[[x,y],[right,y],[right,bottom],[x,bottom]],'engine':'Tesseract LSTM tessdata_best'})
    return lines
