"""Pinned visual weights and an OCR startup check. No remote code execution."""
import json
import os
from pathlib import Path
from ML.model_setup import sha256,ROOT

def setup():
    from huggingface_hub import hf_hub_download
    manifest=json.loads((ROOT/'MODELS/vision-manifest.json').read_text(encoding="utf-8"))
    target=Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))/'vision-qwen'
    target.mkdir(parents=True,exist_ok=True)
    print('Preparing local vision model, about 2.8 GB. One-time download.',flush=True)
    for item in manifest['files']:
        path=target/item['path']
        if path.exists() and path.stat().st_size==item['size'] and sha256(path)==item['sha256']:continue
        print('Downloading '+item['path'],flush=True)
        path=hf_hub_download(manifest['repo'],item['path'],revision=manifest['revision'],local_dir=target)
        if sha256(path)!=item['sha256']:raise RuntimeError('Vision model hash mismatch: '+item['path'])
    license_path=hf_hub_download(manifest['original_repo'],'LICENSE',revision=manifest['original_revision'],local_dir=target)
    if sha256(license_path)!=manifest['original_license_sha256']:raise RuntimeError('Original vision license hash mismatch')
    (target/'NOTICE').write_text((ROOT/'MODELS/VISION_NOTICE.txt').read_text(encoding="utf-8"), encoding="utf-8")
    from BACKEND.documents import ocr
    from PIL import Image
    ocr(Image.new('RGB',(128,128),'white'))
    print('Vision weights verified and OCR engine ready.',flush=True)

if __name__=='__main__':setup()
