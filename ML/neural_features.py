"""Real pretrained MiniLM embeddings via CPU ONNX, plus linguistic span features."""
import json
import os
import re
import threading
from pathlib import Path
import numpy as np
from sklearn.base import BaseEstimator,TransformerMixin

ROOT=Path(__file__).resolve().parents[1]
_SESSION=None
_TOKENIZER=None
_LOCK=threading.RLock()
_CACHE={}

def model_directory():return Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))/'minilm'

def available():return (model_directory()/'onnx/model.onnx').exists() and (model_directory()/'tokenizer.json').exists()

def embeddings(texts):
    global _SESSION,_TOKENIZER
    with _LOCK:
        if _SESSION is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            _SESSION=ort.InferenceSession(str(model_directory()/'onnx/model.onnx'),options,providers=['CPUExecutionProvider'])
            _TOKENIZER=Tokenizer.from_file(str(model_directory()/'tokenizer.json'))
            _TOKENIZER.enable_truncation(max_length=256)
            _TOKENIZER.enable_padding()
        missing=list(dict.fromkeys(text for text in texts if text not in _CACHE))
        for start in range(0,len(missing),16):
            batch=missing[start:start+16];enc=_TOKENIZER.encode_batch(batch)
            candidates={'input_ids':np.array([x.ids for x in enc],dtype=np.int64),
                'attention_mask':np.array([x.attention_mask for x in enc],dtype=np.int64),
                'token_type_ids':np.array([x.type_ids for x in enc],dtype=np.int64)}
            feed={inp.name:candidates[inp.name] for inp in _SESSION.get_inputs()}
            output=_SESSION.run(None,feed)[0]
            if output.ndim==3:
                mask=candidates['attention_mask'][...,None];pooled=(output*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1)
            else:pooled=output
            pooled=pooled/np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-9)
            for text,vector in zip(batch,pooled):_CACHE[text]=vector.astype(np.float32)
        return np.stack([_CACHE[text] for text in texts])

def unpack(value):return json.loads(value)

class TextChannel(BaseEstimator,TransformerMixin):
    def __init__(self,channel='combined'):self.channel=channel
    def fit(self,x,y=None):return self
    def transform(self,x):
        rows=[unpack(v) for v in x]
        if self.channel=='span':return [r['text'] for r in rows]
        return [' '.join([r['text']]*3+[r.get('context_before',''),r.get('context_after','')]) for r in rows]

class LinguisticFeatures(BaseEstimator,TransformerMixin):
    def fit(self,x,y=None):return self
    def transform(self,x):
        output=[]
        for value in x:
            r=unpack(value);span=r['text'];words=re.findall(r'\b[\w\'-]+\b',span);n=max(1,len(words))
            sentence=r.get('context_before','')+span+r.get('context_after','')
            clause=len(re.findall(r'\b(?:although|because|unless|if|when|while|which|whose|rather|provided|except)\b',span,re.I))
            output.append([n,len(span),np.mean([len(w) for w in words]) if words else 0,
                span.count(','),span.count(';'),clause,len(re.findall(r'[.!?]',span)),
                int(n<=2),int(n<=5),int(n>=12),int(bool(re.match(r'^(Although|Unless|If|When|Because)\b',span))),
                len(re.findall(r'\b(?:may|must|can|cannot|not|only|unless)\b',span,re.I)),len(sentence.split())])
        return np.asarray(output,dtype=np.float32)

class NeuralFeatures(BaseEstimator,TransformerMixin):
    def __init__(self,channel='span'):self.channel=channel
    def fit(self,x,y=None):return self
    def transform(self,x):
        rows=[unpack(v) for v in x]
        if self.channel=='span':texts=[r['text'] for r in rows]
        else:texts=[r.get('context_before','')+' [selected] '+r['text']+' [/selected] '+r.get('context_after','') for r in rows]
        return embeddings(texts)

def pack(row):return json.dumps({k:row.get(k,'') for k in ['text','context_before','context_after']})

class ProbabilityEnsemble:
    """Validation-selected probability mixture. It retains the incumbent's input convention."""
    _input_version='json_v2'
    _representation='gated_ensemble'
    def __init__(self,incumbent,candidate,weight):
        self.incumbent=incumbent;self.candidate=candidate;self.weight=weight
        self.classes_=candidate.classes_
    def predict_proba(self,x):
        from ML.prototype import encoded
        old_x=x if getattr(self.incumbent,'_input_version',None)=='json_v2' else [encoded(unpack(v)) for v in x]
        a=self.incumbent.predict_proba(old_x)
        b=self.candidate.predict_proba(x)
        indices=[list(self.incumbent.classes_).index(label) for label in self.classes_]
        return (1-self.weight)*a[:,indices]+self.weight*b
    def predict(self,x):return self.classes_[np.argmax(self.predict_proba(x),axis=1)]

def classifier_candidates():
    from sklearn.pipeline import Pipeline,FeatureUnion
    from sklearn.preprocessing import StandardScaler
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    models=[]
    for representation in ['linguistic','hybrid','neural']:
        if representation=='neural' and not available():continue
        for c in [0.1,1.0,10.0]:
            parts=[('structure',Pipeline([('features',LinguisticFeatures()),('scale',StandardScaler())]))]
            if representation in {'hybrid','neural'}:
                parts += [('span_words',Pipeline([('text',TextChannel('span')),('tfidf',TfidfVectorizer(ngram_range=(1,2)))])),
                          ('context',Pipeline([('text',TextChannel()),('tfidf',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True))]))]
            if representation=='neural':
                parts += [('span_embedding',NeuralFeatures('span')),('context_embedding',NeuralFeatures('context'))]
            model=Pipeline([('features',FeatureUnion(parts)),('clf',LogisticRegression(C=c,class_weight='balanced',max_iter=2000,random_state=42))])
            model._input_version='json_v2'
            model._representation=representation
            models.append((f'{representation}_C{c}',c,model))
    return models
