"""Inference for an admin-activated, evaluated human routing run. No pilot fallback."""
import json,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LOCK=threading.Lock();CACHE=None

def routing_input(span,context,span_start=None):
    from ML.context import build_context
    parts=build_context(context,span,span_start)
    return parts['context_before']+' [SPAN] '+span+' [/SPAN] '+parts['context_after'],parts

def predict(span,context,language,span_start=None):
    global CACHE
    registry=ROOT/'ARTIFACTS/human_routing_active.json'
    if not registry.exists():return None
    active=json.loads(registry.read_text(encoding="utf-8"))
    if language not in active['supported_languages']:return None
    with LOCK:
        import torch,numpy as np
        from ML.fusion import load_fusion,LABELS
        from ML.features import span_context_features
        if CACHE is None or CACHE[0]!=active['run_id']:
            model,tok,cfg=load_fusion(ROOT/'ARTIFACTS/routing_comparison'/active['run_id']/active['selected_arm']/'model');CACHE=(active['run_id'],model,tok,cfg)
        _,model,tok,cfg=CACHE
        text,parts=routing_input(span,context,span_start)
        encoded=tok([text],return_tensors='pt',truncation=True,max_length=cfg['max_len'])
        f=(np.array(span_context_features(span,parts['context_before'],parts['context_after']))-np.array(cfg['scaler_mean']))/np.array(cfg['scaler_std'])
        with torch.inference_mode():scores=torch.softmax(model(**encoded,features=torch.tensor(f[None],dtype=torch.float32)),-1)[0].numpy()
        i=int(scores.argmax());return {'category':LABELS[i],'score':float(scores[i]),'scores':dict(zip(LABELS,map(float,scores))),'run_id':active['run_id'],'source':'Evaluated human-reviewed routing model','uncalibrated':True}

def activate(run_id):
    if len(run_id)!=32 or any(c not in '0123456789abcdef' for c in run_id):raise ValueError('Invalid run identifier.')
    path=ROOT/'ARTIFACTS/routing_comparison'/run_id/'comparison.json'
    if not path.exists():raise ValueError('Completed human routing comparison not found.')
    report=json.loads(path.read_text(encoding="utf-8"));arms={'distilbert':report['distilbert'],'distilbert_features':report['distilbert_features']};name=max(arms,key=lambda n:arms[n]['validation']['macro_f1']);candidate=arms[name]
    if not candidate['valid_for_scientific_claims']:raise ValueError('Pretrained human-data run required.')
    # Predeclared engineering gate, not a claim of student effectiveness.
    majority=report['baseline']['models']['majority']['validation']['macro_f1']
    if candidate['validation']['macro_f1']<max(.6,majority+.05):raise ValueError('Candidate fails the declared validation gate (macro-F1 >= .60 and majority + .05).')
    languages=[lang for lang,metric in candidate.get('per_language',{}).get('validation',{}).items() if metric['macro_f1']>=.6 and metric['n']>=30 and all(metric['per_class'][label]['support']>=5 for label in ['VOCABULARY','SYNTACTIC','CONCEPTUAL'])]
    if not languages:raise ValueError('No language passes the per-language validation gate.')
    registry=ROOT/'ARTIFACTS/human_routing_active.json';old=json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else None
    if old and old['dataset_sha256']!=report['dataset_sha256']:raise ValueError('Different evaluation dataset: compare on the same frozen benchmark before replacing the active model.')
    if old and candidate['validation']['macro_f1']<old['validation_macro_f1']:raise ValueError('Candidate is worse on the shared validation benchmark.')
    record={'run_id':run_id,'selected_arm':name,'supported_languages':languages,'validation_macro_f1':candidate['validation']['macro_f1'],'dataset_sha256':report['dataset_sha256'],'gate':'Engineering validation >=.60 and majority+.05; per-language >=.60 with >=30 validation rows and >=5 per class; not student-effectiveness evidence','previous':old}
    temporary=registry.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2), encoding="utf-8");temporary.replace(registry);return record
