"""Genuine human-data lexical comparison, separate from support-category routing.
Three arms share targets and frozen partitions. LoRA fine-tunes actual multilingual
DistilBERT attention adapters on CPU; the frozen backbone is not substituted by MiniLM.
"""
import hashlib,json,os,time,uuid,threading,gc
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
# OS lock prevents separate admin/CLI processes training the same comparison concurrently.
from filelock import FileLock,Timeout
PROCESS_LOCK=FileLock(str(ROOT/'ARTIFACTS/human_lexical_training.lock'))
_CACHE=None

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def base_directory():return Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))/'distilmbert'
def inputs(rows):return ['Selected: '+r['token']+' Context: '+r['sentence'] for r in rows]
def features(rows):
    from ML.features import span_context_features
    return np.asarray([span_context_features(r['token'],'',r['sentence']) for r in rows],dtype=np.float32)
def prepare(max_train=512):
    folder=ROOT/'DATA/public/CompLex';paths={'train':folder/'train/lcp_single_train.tsv','validation':folder/'trial/lcp_single_trial.tsv','test':folder/'test-labels/lcp_single_test.tsv'}
    data={}
    for split,path in paths.items():
        if not path.exists():raise ValueError('Verified CompLex files are required.')
        df=pd.read_csv(path,sep='\t').fillna('')
        data[split]=[{'id':str(row['id']),'token':str(row['token']),'sentence':str(row['sentence']),'genre':str(row.get('corpus',row.get('subcorpus','unprovided'))),'target':float(row['complexity'])} for row in df.to_dict('records')]
    # Preserve official token splits; remove exact-context overlap from training/development.
    test_context={r['sentence'].strip().casefold() for r in data['test']};validation_context={r['sentence'].strip().casefold() for r in data['validation']}
    removed={}
    for split,protected in [('train',test_context|validation_context),('validation',test_context)]:
        n=len(data[split]);data[split]=[r for r in data[split] if r['sentence'].strip().casefold() not in protected];removed[split]=n-len(data[split])
    data['train']=sorted(data['train'],key=lambda r:hashlib.sha256(r['id'].encode()).hexdigest())[:max_train]
    manifest={'task':'English lexical complexity regression (not 3-category routing)','source':'MMU-TDMLab/CompLex','license':'CC-BY-4.0','annotation':'Published human aggregate complexity ratings','max_train':max_train,'seed':42,'source_hashes':{s:sha(p) for s,p in paths.items()},'partitions':{s:[r['id'] for r in rows] for s,rows in data.items()},'exact_context_overlap_removed':removed,'synthetic_rows':0,'test_used_for_selection':False}
    path=ROOT/'DATA'/('human_lexical_split_'+str(max_train)+'.json')
    if path.exists() and json.loads(path.read_text(encoding="utf-8"))!=manifest:raise ValueError('Frozen manifest differs. Create a separately versioned dataset; do not overwrite its split.')
    if not path.exists():path.write_text(json.dumps(manifest,indent=2), encoding="utf-8")
    return data,manifest

def score(actual,predicted):
    from sklearn.metrics import mean_absolute_error,mean_squared_error
    from scipy.stats import pearsonr,spearmanr
    actual=np.asarray(actual);predicted=np.clip(np.asarray(predicted),0,1)
    return {'n':len(actual),'mae':float(mean_absolute_error(actual,predicted)),'rmse':float(mean_squared_error(actual,predicted)**.5),
            'pearson':float(pearsonr(actual,predicted).statistic) if np.std(predicted)>0 else None,
            'spearman':float(spearmanr(actual,predicted).statistic) if np.std(predicted)>0 else None,'predictions':predicted.tolist()}

def new_neural(use_features):
    import torch
    from transformers import DistilBertModel
    from peft import LoraConfig,get_peft_model,TaskType
    torch.manual_seed(42)
    encoder=DistilBertModel.from_pretrained(base_directory(),local_files_only=True)
    encoder=get_peft_model(encoder,LoraConfig(r=8,lora_alpha=16,target_modules=['q_lin','v_lin'],lora_dropout=.05,bias='none',task_type=TaskType.FEATURE_EXTRACTION))
    class Regressor(torch.nn.Module):
        def __init__(self):
            super().__init__();self.encoder=encoder;self.head=torch.nn.Sequential(torch.nn.Linear(768+(10 if use_features else 0),128),torch.nn.ReLU(),torch.nn.Dropout(.1),torch.nn.Linear(128,1));self.use_features=use_features
        def forward(self,tokens,f):
            h=self.encoder(**tokens).last_hidden_state[:,0]
            if self.use_features:h=torch.cat([h,f],dim=1)
            return torch.sigmoid(self.head(h)).squeeze(-1)
    return Regressor()

def neural_predict(model,tokenizer,rows,mean,std,batch=8):
    import torch
    model.eval();values=[];all_features=(features(rows)-mean)/std
    with torch.inference_mode():
        for i in range(0,len(rows),batch):
            tokens=tokenizer(inputs(rows[i:i+batch]),return_tensors='pt',padding=True,truncation=True,max_length=96)
            values.extend(model(tokens,torch.tensor(all_features[i:i+batch])).numpy().tolist())
    return values

def train(progress=None,max_train=512,epochs=2):
    try:PROCESS_LOCK.acquire(timeout=0)
    except Timeout:raise ValueError('A human-data comparison is already running in another process.')
    if not LOCK.acquire(blocking=False):
        PROCESS_LOCK.release();raise ValueError('A human-data comparison is already running.')
    import torch
    from transformers import AutoTokenizer
    from safetensors.torch import save_file,load_file
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    try:
        if not (base_directory()/'model.safetensors').exists():raise LookupError('Pinned multilingual DistilBERT weights missing. Run multilingual setup.')
        torch.set_num_threads(4);torch.manual_seed(42);np.random.seed(42)
        data,manifest=prepare(max_train);run_id=uuid.uuid4().hex;out=ROOT/'ARTIFACTS/human_lexical'/run_id;out.mkdir(parents=True)
        log=out/'training_log.jsonl';report={'run_id':run_id,'task':manifest['task'],'data_status':'PUBLIC_HUMAN_LEXICAL_ONLY','routing_claims_allowed':False,'synthetic_rows':0,'language':'en','manifest':manifest,'epochs':epochs,'max_length':96,'adaptation':'LoRA r=8 on actual multilingual DistilBERT q_lin/v_lin; shared backbone checkpoint and matched regression heads','arms':{},'status':'running','created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
        def emit(value):
            value['elapsed_seconds']=round(time.monotonic()-started,2)
            with log.open('a') as f:f.write(json.dumps(value)+'\n')
            if progress:progress({'run_id':run_id,**value})
        def write():
            path=out/'results.json';temporary=out/'results.tmp';temporary.write_text(json.dumps(report,indent=2), encoding="utf-8");temporary.replace(path)
        started=time.monotonic();write();target={s:[r['target'] for r in rows] for s,rows in data.items()}
        best=None
        for alpha in [.1,1,10]:
            model=Pipeline([('tfidf',TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=15000)),('ridge',Ridge(alpha=alpha))]);model.fit(inputs(data['train']),target['train']);v=score(target['validation'],model.predict(inputs(data['validation'])))
            if best is None or v['mae']<best[0]:best=(v['mae'],model,v,alpha)
        _,model,val,alpha=best;directory=out/'tfidf';directory.mkdir();joblib.dump(model,directory/'model.joblib');report['arms']['tfidf']={'validation':val,'test':score(target['test'],model.predict(inputs(data['test']))),'alpha':alpha,'train_rows':len(data['train'])};emit({'arm':'tfidf','stage':'completed','validation_mae':val['mae']});write();del model,best
        tokenizer=AutoTokenizer.from_pretrained(base_directory(),local_files_only=True);F=features(data['train']);mean=F.mean(0);std=np.maximum(F.std(0),1e-6)
        for name,use_features in [('distilbert',False),('distilbert_features',True)]:
            model=new_neural(use_features);optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=3e-4);directory=out/name;directory.mkdir();best_mae=float('inf');best_epoch=None
            for epoch in range(1,epochs+1):
                model.train();order=np.random.default_rng(42+epoch).permutation(len(data['train']));losses=[]
                for start in range(0,len(order),8):
                    ix=order[start:start+8];rows=[data['train'][i] for i in ix];tokens=tokenizer(inputs(rows),return_tensors='pt',padding=True,truncation=True,max_length=96);f=torch.tensor((F[ix]-mean)/std);actual=torch.tensor([r['target'] for r in rows]);optimizer.zero_grad();prediction=model(tokens,f);loss=torch.nn.functional.mse_loss(prediction,actual);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step();losses.append(loss.item())
                    if start%64==0:emit({'arm':name,'stage':'training','epoch':epoch,'processed':min(start+8,len(order)),'training_rows':len(order),'loss':float(np.mean(losses))})
                val=score(target['validation'],neural_predict(model,tokenizer,data['validation'],mean,std));emit({'arm':name,'stage':'validation','epoch':epoch,'loss':float(np.mean(losses)),'validation_mae':val['mae']})
                if val['mae']<best_mae:
                    best_mae=val['mae'];best_epoch=epoch;model.encoder.save_pretrained(directory/'adapter');save_file({k:v.detach().contiguous().cpu() for k,v in model.head.state_dict().items()},str(directory/'head.safetensors'));best_val=val
            # Restore validation-selected adapters and head, then evaluate test once.
            from peft import set_peft_model_state_dict
            set_peft_model_state_dict(model.encoder,load_file(str(directory/'adapter/adapter_model.safetensors')));model.head.load_state_dict(load_file(str(directory/'head.safetensors')))
            test=score(target['test'],neural_predict(model,tokenizer,data['test'],mean,std));config={'use_features':use_features,'mean':mean.tolist(),'std':std.tolist(),'base_revision':json.loads((ROOT/'MODELS/multilingual-manifest.json').read_text(encoding="utf-8"))['models'][0]['revision']};(directory/'config.json').write_text(json.dumps(config), encoding="utf-8");report['arms'][name]={'validation':best_val,'test':test,'best_epoch':best_epoch,'train_rows':len(data['train']),'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad)};emit({'arm':name,'stage':'completed','validation_mae':best_val['mae']});write();del model,optimizer;gc.collect()
        selected=min(report['arms'],key=lambda name:report['arms'][name]['validation']['mae']);report.update(status='completed',selected_arm=selected,selection='Lowest validation MAE; test not used for selection',elapsed_seconds=round(time.monotonic()-started,2));write()
        registry=ROOT/'ARTIFACTS/human_word_active.json'
        if registry.exists():
            old=json.loads(registry.read_text(encoding="utf-8"));previous=json.loads((ROOT/'ARTIFACTS/human_lexical'/old['run_id']/'results.json').read_text(encoding="utf-8"));old_mae=previous['arms'][old['selected_arm']]['validation']['mae']
            if report['arms'][selected]['validation']['mae']>old_mae:report['activation']='Candidate not activated: worse validation MAE';write();return report
        registry.write_text(json.dumps({'run_id':run_id,'selected_arm':selected,'task':manifest['task'],'validation_mae':report['arms'][selected]['validation']['mae'],'previous':json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else None},indent=2), encoding="utf-8");report['activation']='Validation-selected lexical model activated; routing classifier unchanged';write();return report
    finally:LOCK.release();PROCESS_LOCK.release()

def reports():
    paths=sorted((ROOT/'ARTIFACTS/human_lexical').glob('*/results.json'))
    output=[]
    for p in paths:
        value=json.loads(p.read_text(encoding="utf-8"));log=p.parent/'training_log.jsonl';value['training_log']=[json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.startswith('{')] if log.exists() else [];output.append(value)
    return output
def predict_word(span,context):
    global _CACHE
    if len(span.split())!=1 or not any(c.isalpha() for c in span) or len(span)>80:return None
    registry=ROOT/'ARTIFACTS/human_word_active.json'
    if not registry.exists():return None
    active=json.loads(registry.read_text(encoding="utf-8"));name=active['selected_arm'];folder=ROOT/'ARTIFACTS/human_lexical'/active['run_id']/name;row={'token':span,'sentence':context}
    if name=='tfidf':
        if _CACHE is None or _CACHE[0]!=active['run_id']:_CACHE=(active['run_id'],joblib.load(folder/'model.joblib'))
        value=float(np.clip(_CACHE[1].predict(inputs([row]))[0],0,1))
    else:
        import torch
        from transformers import AutoTokenizer
        from safetensors.torch import load_file
        from peft import set_peft_model_state_dict
        if _CACHE is None or _CACHE[0]!=active['run_id']:
            cfg=json.loads((folder/'config.json').read_text(encoding="utf-8"));model=new_neural(cfg['use_features']);set_peft_model_state_dict(model.encoder,load_file(str(folder/'adapter/adapter_model.safetensors')));model.head.load_state_dict(load_file(str(folder/'head.safetensors')));_CACHE=(active['run_id'],model,AutoTokenizer.from_pretrained(base_directory(),local_files_only=True),cfg)
        value=float(neural_predict(_CACHE[1],_CACHE[2],[row],np.array(_CACHE[3]['mean']),np.array(_CACHE[3]['std']))[0])
    return {'score':value,'task':'English lexical complexity only','model':name,'run_id':active['run_id'],'source':'Public human CompLex annotations','not_support_category_classifier':True}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--max-train',type=int,default=512);parser.add_argument('--epochs',type=int,default=2);args=parser.parse_args()
    print(json.dumps(train(lambda x:print(json.dumps(x),flush=True),args.max_train,args.epochs),indent=2))
