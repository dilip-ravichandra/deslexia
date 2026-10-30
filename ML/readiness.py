"""Inspectable local readiness. This never downloads or substitutes a model."""
import importlib.util
import importlib.metadata
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def public_datasets(root=ROOT):
    manifest=json.loads((root/'DATA/public_sources.json').read_text(encoding='utf-8'))
    sources=[]
    for source in manifest['sources']:
        files=source.get('files',[])
        dataset_files=[entry for entry in files if Path(entry['path']).name!='.DS_Store']
        checked=0
        problems=[]
        for entry in dataset_files:
            path=(root/entry['path']).resolve()
            if not path.is_relative_to(root.resolve()):
                problems.append(entry['path']+': outside project')
                continue
            if not path.is_file():
                problems.append(entry['path']+': missing')
                continue
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(chunk)
            if path.stat().st_size!=entry.get('bytes', entry.get('size')) or digest.hexdigest()!=entry['sha256']:
                problems.append(entry['path']+': differs from pinned source')
            else:
                checked+=1
        sources.append({'id':source['id'],'role':source['role'],'manifest_status':source['status'],
                        'verified_files':checked,'expected_files':len(dataset_files),
                        'ignored_os_metadata_files':len(files)-len(dataset_files),
                        'ready':bool(dataset_files) and not problems,
                        'problems':problems[:5]})
    return {'sources':sources,'bundled_routing_labels_available':False,
            'note':'Bundled public data are task-specific references, not validated dyslexia learner data or four-language support-routing labels. Human-reviewed imports are evaluated separately.'}

def services():
    from ML.multilingual import models
    from BACKEND.documents import tesseract_available
    base=models()
    def dependency_issues(dependencies):
        from packaging.requirements import Requirement
        problems=[]
        for package in dependencies:
            if importlib.util.find_spec(package) is None:continue
            try:requirements=importlib.metadata.requires(package) or []
            except importlib.metadata.PackageNotFoundError:continue
            for declared in requirements:
                requirement=Requirement(declared)
                if requirement.marker and not requirement.marker.evaluate({'extra':''}):continue
                try:version=importlib.metadata.version(requirement.name)
                except importlib.metadata.PackageNotFoundError:
                    problems.append(str(requirement)+' is missing');continue
                if requirement.specifier and version not in requirement.specifier:problems.append(str(requirement)+'; installed '+version)
        return problems
    def status(folder,files,dependencies):
        missing=[str(Path(folder)/f) for f in files if not (base/folder/f).is_file()]
        packages=[name for name in dependencies if importlib.util.find_spec(name) is None]
        issues=dependency_issues(dependencies)
        return {'ready':not missing and not packages and not issues,'missing_files':missing,'missing_packages':packages,'dependency_issues':issues}
    result={'local_accounts':status('',[],['cryptography']),
        'generation':status('qwen3',['Qwen3-4B-Q4_K_M.gguf'],['llama_cpp']),
        'routing_backbone':status('distilmbert',['model.safetensors','config.json','tokenizer.json'],['torch','transformers']),
        'vision':status('vision-qwen',['Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf','mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf'],['llama_cpp']),
        'semantic_checks':status('nli',['onnx/model.onnx','tokenizer.json','config.json'],['onnxruntime','tokenizers']),
        'speech':{},'native_ocr':{'ready':tesseract_available()},'python':sys.version.split()[0],
        'supported_research_python':sys.version_info[:2] in {(3,11),(3,12)},
        'setup':'Run SETUP_RESEARCH_WINDOWS.bat with Python 3.12; downloads are explicit and may take several GB. The pinned RapidOCR package does not support Python 3.13.'}
    for language in ['en','hi','kn','ta']:
        entry=next(m for m in json.loads((ROOT/'MODELS/multilingual-manifest.json').read_text(encoding='utf-8'))['models'] if m['folder']=='tts-'+language)
        result['speech'][language]=status(entry['folder'],[f['path'] for f in entry['files']],['torch','transformers','uroman'])
    return result
