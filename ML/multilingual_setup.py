"""Download the approved, revision-pinned research stack; verify every SHA-256."""
import json,os,argparse,urllib.request
from pathlib import Path
from ML.model_setup import ROOT,sha256

def setup(vision=False):
    from huggingface_hub import hf_hub_download
    base=Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))
    manifest=json.loads((ROOT/'MODELS/multilingual-manifest.json').read_text(encoding="utf-8"))
    generator=json.loads((ROOT/'MODELS/generator-candidate.json').read_text(encoding="utf-8"))
    old=json.loads((ROOT/'MODELS/manifest.json').read_text(encoding="utf-8"))
    entries=manifest['models']+[generator]+[m for m in old['models'] if m['folder']!='qwen']
    print('Preparing pinned multilingual DistilBERT, Qwen3, speech and meaning-check models. Several GB; first download only.',flush=True)
    def valid(path,item):return path.exists() and path.stat().st_size==item['size'] and sha256(path)==item['sha256']
    for model in entries:
        folder=base/model['folder'];folder.mkdir(parents=True,exist_ok=True)
        for item in model['files']:
            path=folder/item['path']
            if valid(path,item):continue
            print('Downloading '+model['folder']+'/'+item['path'],flush=True)
            path=Path(hf_hub_download(model['repo'],item['path'],revision=model['revision'],local_dir=folder))
            if not valid(path,item):raise RuntimeError('Model file hash mismatch: '+item['path'])
    native=json.loads((ROOT/'MODELS/tesseract-manifest.json').read_text(encoding="utf-8"))
    for folder,items in [('ocr',manifest['ocr']),('ocr-tesseract',native['files'])]:
        for item in items:
            path=base/folder/item['path'];path.parent.mkdir(parents=True,exist_ok=True)
            if valid(path,item):continue
            print('Downloading '+folder+'/'+item['path'],flush=True)
            temporary=path.with_suffix(path.suffix+'.download')
            with urllib.request.urlopen(item['url'],timeout=120) as response,temporary.open('wb') as output:
                import shutil;shutil.copyfileobj(response,output)
            if not valid(temporary,item):temporary.unlink();raise RuntimeError('OCR file hash mismatch: '+item['path'])
            temporary.replace(path)
    if vision:
        from ML.document_setup import setup as vision_setup
        vision_setup()
    from BACKEND.documents import tesseract_available
    print('Pinned assets verified. Native Tesseract ready: '+str(tesseract_available())+'. Install the Tesseract executable for best Indic OCR; RapidOCR remains available as a fallback.',flush=True)
    (base/'multilingual-verified.json').write_text(json.dumps({'verified':True,'manifest_sha256':sha256(ROOT/'MODELS/multilingual-manifest.json'),'generator_sha256':sha256(ROOT/'MODELS/generator-candidate.json'),'vision_requested':vision}), encoding="utf-8")
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--vision',action='store_true');args=parser.parse_args();setup(args.vision)
