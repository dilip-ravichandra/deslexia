"""Actual pretrained NLI and sentence similarity, with exposed non-guarantee status."""
import json
import os
import threading
from pathlib import Path
import numpy as np
from ML.neural_features import embeddings

ROOT=Path(__file__).resolve().parents[1]
_SESSION=None
_TOKENIZER=None
_LABELS=None
_LOCK=threading.RLock()

def available():return (Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))/'nli/onnx/model.onnx').exists()

class ONNXEmbeddingScorer:
    name='pretrained_minilm_embedding'
    available=True
    def score(self,a,b):
        vectors=embeddings([a,b]);return float(np.dot(vectors[0],vectors[1]))

class ONXNNLIScorer:
    name='pretrained_minilm_nli'
    available=True
    def probs(self,premise,hypothesis):
        global _SESSION,_TOKENIZER,_LABELS
        with _LOCK:
            if _SESSION is None:
                import onnxruntime as ort
                from tokenizers import Tokenizer
                directory=Path(os.environ.get('DYSLEXIADAPT_MODELS_DIR',ROOT/'MODELS'))/'nli'
                options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
                _SESSION=ort.InferenceSession(str(directory/'onnx/model.onnx'),options,providers=['CPUExecutionProvider'])
                _TOKENIZER=Tokenizer.from_file(str(directory/'tokenizer.json'));_TOKENIZER.enable_truncation(max_length=512);_TOKENIZER.enable_padding()
                _LABELS=json.loads((directory/'config.json').read_text(encoding="utf-8"))['id2label']
            enc=_TOKENIZER.encode(premise,hypothesis)
            values={'input_ids':np.array([enc.ids],dtype=np.int64),'attention_mask':np.array([enc.attention_mask],dtype=np.int64),
                    'token_type_ids':np.array([enc.type_ids],dtype=np.int64)}
            logits=_SESSION.run(None,{i.name:values[i.name] for i in _SESSION.get_inputs()})[0][0]
            exp=np.exp(logits-logits.max());probs=exp/exp.sum()
            return {_LABELS[str(i)]:float(p) for i,p in enumerate(probs)}

def verify_explanation(source,explanation):
    """Explanations may add definitions, so require no contradiction, not bidirectional entailment."""
    from ML.semantic_verifier import numbers
    result=ONXNNLIScorer().probs(source,explanation)
    import re
    # Numbered-list labels are presentation, not new educational quantities.
    quantity_text=re.sub(r'(?m)^\s*\d+[.)]\s+','',explanation)
    source_numbers=set(numbers(source));new_numbers=set(numbers(quantity_text))-source_numbers
    # New quantities are not source facts. An example must be separately labelled hypothetical.
    flags=[]
    if new_numbers:flags.append('New quantities not present in the source: '+', '.join(sorted(new_numbers)))
    if re.search(r'\b(?:always|guaranteed|guarantee|necessarily)\b',explanation,re.I) and not re.search(r'\b(?:always|guaranteed|guarantee|necessarily)\b',source,re.I):
        if not re.search(r'\b(?:not|never|no)\b.{0,25}\b(?:always|guaranteed|guarantee|necessarily)\b',explanation,re.I):
            flags.append('An unsupported universal or guaranteed outcome was added')
    if result['contradiction']>=0.65:flags.append('Pretrained NLI detected possible contradiction')
    return {'status':'fail' if flags else 'review' if result['entailment']<0.4 else 'pass',
            'nli':result,'flags':flags,'meaning_preservation_guaranteed':False,
            'thresholds_validated':False,'checks_run':['pretrained_minilm_nli','new_numbers'],
            'note':'Supplementary explanations may add background knowledge. NLI does not verify that added knowledge is true.'}
