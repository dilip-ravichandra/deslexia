"""Download pinned public pretrained weights and verify their exact file hashes."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda:file.read(4*1024*1024),b''):digest.update(chunk)
        if hasattr(os,'posix_fadvise') and Path(path).stat().st_size>64*1024*1024:
            os.posix_fadvise(file.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    return digest.hexdigest()

def setup():
    from huggingface_hub import hf_hub_download
    directory=Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))
    manifest=json.loads((ROOT/'MODELS'/'manifest.json').read_text(encoding="utf-8"))
    total=sum(f['size'] for model in manifest['models'] for f in model['files'])
    print(f'Preparing pretrained CPU models ({total/1e9:.2f} GB). This is a one-time download; no API key required.',flush=True)
    for model in manifest['models']:
        local=directory/model['folder'];local.mkdir(parents=True,exist_ok=True)
        for item in model['files']:
            path=local/item['path']
            if path.exists() and path.stat().st_size==item['size'] and sha256(path)==item['sha256']:
                print('Verified cached '+model['folder']+'/'+item['path'],flush=True);continue
            print('Downloading '+model['repo']+'/'+item['path'],flush=True)
            downloaded=hf_hub_download(model['repo'],item['path'],revision=model['revision'],local_dir=local)
            if sha256(downloaded)!=item['sha256']:
                raise RuntimeError('Downloaded model hash does not match pinned manifest: '+item['path'])
    marker=directory/'verified.json'
    marker.write_text(json.dumps({'manifest_sha256':sha256(ROOT/'MODELS'/'manifest.json'),'status':'verified'}), encoding="utf-8")
    print('All model weights verified. Reader can now use real local inference.',flush=True)
    return directory

if __name__=='__main__':
    setup()
