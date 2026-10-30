"""Weak-label prototype training. Separate from research model registry."""
import hashlib
import json
import threading
import uuid
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, f1_score

LABELS = ['VOCABULARY', 'SYNTACTIC', 'CONCEPTUAL', 'OTHER_UNCERTAIN']
LOCK = threading.RLock()

def encoded(row):
    # Explicit span channels help avoid classifying the entire context instead of the selection.
    return ' '.join(['SPAN '+row['text']]*3 + [row.get('context_before',''), row.get('context_after','')])

def metrics(model, rows):
    actual = [r['category'] for r in rows]
    from ML.neural_features import pack
    predicted = model.predict([pack(r) if getattr(model,'_input_version',None)=='json_v2' else encoded(r) for r in rows]).tolist()
    return {'macro_f1': float(f1_score(actual, predicted, labels=LABELS, average='macro', zero_division=0)),
            'per_class': classification_report(actual, predicted, labels=LABELS, output_dict=True, zero_division=0),
            'confusion_matrix': {'labels': LABELS, 'matrix': confusion_matrix(actual, predicted, labels=LABELS).tolist()},
            'rows': len(rows), 'predictions': predicted}

class PrototypeTrainer:
    def __init__(self, root):
        self.root = Path(root)
        self.directory = self.root/'ARTIFACTS'/'prototype'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.data_path = self.root/'DATA'/'prototype_pilots.json'
        self.model = None
        self.active = None
        self.uncertainty_threshold=0.45
        self.reload()

    def reload(self):
        registry = self.directory/'active.json'
        if registry.exists():
            self.active = json.loads(registry.read_text(encoding="utf-8"))
            self.model = joblib.load(self.directory/self.active['run_id']/'model.joblib')
            report=json.loads((self.directory/self.active['run_id']/'results.json').read_text(encoding="utf-8"))
            self.uncertainty_threshold=report.get('uncertainty_threshold',0.45)

    def data(self):
        return json.loads(self.data_path.read_text(encoding="utf-8"))

    def predict(self, text, before='', after=''):
        if self.model is None:
            return None
        if 'neural' in getattr(self.model,'_representation',''):
            from ML.neural_features import available
            if not available():raise LookupError('Pretrained classifier weights are missing. Run START_WINDOWS.bat or python -m ML.model_setup first.')
        from ML.neural_features import pack
        row={'text':text,'context_before':before,'context_after':after}
        value=pack(row) if getattr(self.model,'_input_version',None)=='json_v2' else encoded(row)
        p = self.model.predict_proba([value])[0]
        return dict(zip(self.model.classes_, map(float,p)))

    def train(self, reviewed=()):
        with LOCK:
            data = self.data()
            train = [r for r in data['rows'] if r['split']=='TRAIN' and r['category']]
            validation = [r for r in data['rows'] if r['split']=='VALIDATION' and r['category']]
            protected = [r for r in data['rows'] if r['split']!='TRAIN']
            for r in reviewed:
                passage = r.get('document_text','').strip()
                if not passage or any(passage in p['document_text'] or p['document_text'] in passage or
                     (r['text']==p['text'] and r.get('context_before','')==p.get('context_before','') and r.get('context_after','')==p.get('context_after','')) for p in protected):
                    raise ValueError('Reviewed sample overlaps protected validation/test material')
                if r['category'] not in LABELS:
                    raise ValueError('Unknown reviewed label')
                train.append(r)
            if len(set(r['category'] for r in train)) != len(LABELS):
                raise ValueError('Training partition must contain all four categories')
            candidates=[]
            for c in [0.5,1.0,2.0]:
                model=Pipeline([('tfidf',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),
                                ('clf',LogisticRegression(C=c,class_weight='balanced',max_iter=1500,random_state=42))])
                model.fit([encoded(r) for r in train],[r['category'] for r in train])
                score=metrics(model,validation)
                candidates.append((score['macro_f1'],c,model,score))
            from ML.neural_features import classifier_candidates, pack, ProbabilityEnsemble
            for name,c,model in classifier_candidates():
                model.fit([pack(r) for r in train],[r['category'] for r in train])
                score=metrics(model,validation)
                candidates.append((score['macro_f1'],c,model,score))
            incumbent=metrics(self.model,validation) if self.model else None
            if self.model:
                anchor=self.model
                while isinstance(anchor,ProbabilityEnsemble):anchor=anchor.incumbent
                feature_candidates=[x for x in candidates if getattr(x[2],'_input_version',None)=='json_v2']
                for _,c,candidate,_ in feature_candidates:
                    for weight in [0.1,0.25,0.5]:
                        ensemble=ProbabilityEnsemble(anchor,candidate,weight)
                        ensemble._representation='gated_ensemble_'+candidate._representation+'_weight'+str(weight)
                        score=metrics(ensemble,validation)
                        candidates.append((score['macro_f1'],c,ensemble,score))
            eligible_candidates=[x for x in candidates if incumbent is None or
                (x[0]>=incumbent['macro_f1'] and all(x[3]['per_class'][l]['recall']>=incumbent['per_class'][l]['recall']
                 for l in LABELS if x[3]['per_class'][l]['support']>0))]
            _,c,model,score=max(eligible_candidates or candidates,key=lambda x:x[0])
            supported=[label for label in LABELS if score['per_class'][label]['support']>0]
            eligible=incumbent is None or (score['macro_f1']>=incumbent['macro_f1'] and
                all(score['per_class'][label]['recall']>=incumbent['per_class'][label]['recall'] for label in supported))
            run_id=uuid.uuid4().hex
            run_dir=self.directory/run_id
            run_dir.mkdir()
            joblib.dump(model,run_dir/'model.joblib')
            import numpy as np
            values=[pack(r) if getattr(model,'_input_version',None)=='json_v2' else encoded(r) for r in validation]
            probs=model.predict_proba(values);predicted=model.classes_[np.argmax(probs,axis=1)]
            actual=np.array([r['category'] for r in validation]);threshold_options=[]
            for threshold in [0.25,0.30,0.35,0.40,0.45,0.50]:
                selected=(probs.max(axis=1)>=threshold)&(predicted!='OTHER_UNCERTAIN')
                count=int(selected.sum());accuracy=float((predicted[selected]==actual[selected]).mean()) if count else None
                threshold_options.append({'threshold':threshold,'accepted_validation_rows':count,'provisional_label_accuracy':accuracy})
            usable=[x for x in threshold_options if x['accepted_validation_rows']>=3 and x['provisional_label_accuracy']>=0.9]
            chosen=max(usable,key=lambda x:x['accepted_validation_rows']) if usable else {'threshold':0.45}
            report={'run_id':run_id,'model':getattr(model,'_representation','tfidf')+' + Logistic Regression','selected_C':c,
                'training_rows':len(train),'reviewed_rows':len(reviewed),'data_status':'AI_WEAK_LABEL_PROTOTYPE',
                'valid_for_scientific_claims':False,'validation':score,'incumbent_validation':incumbent,
                'promotion_eligible':eligible,'selection_rule':'validation macro-F1 and supported-class recall must not decrease',
                'dataset_sha256':hashlib.sha256(self.data_path.read_bytes()).hexdigest(),
                'uncertainty_threshold':chosen['threshold'],'abstention_validation':threshold_options,
                'abstention_rule':'Maximise accepted validation examples with at least 3 examples and >=90% provisional-label accuracy. This is a small-sample engineering policy, not calibrated confidence.',
                'training_sha256':hashlib.sha256(json.dumps(train,sort_keys=True).encode()).hexdigest(),
                'validation_sha256':hashlib.sha256(json.dumps(validation,sort_keys=True).encode()).hexdigest(),
                'candidate_validation':[{'representation':getattr(x[2],'_representation','tfidf'),'C':x[1],'macro_f1':x[0]} for x in candidates],
                'limitations':['Small synthetic targeted sample; agreement is between GPT passes, not humans.',
                              'Scores measure agreement with provisional labels, not dyslexia benefit.',
                              'Raw probabilities and abstention threshold are not calibrated.']}
            (run_dir/'results.json').write_text(json.dumps(report,indent=2), encoding="utf-8")
            return report

    def promote(self,run_id):
        with LOCK:
            if len(run_id)!=32 or any(c not in '0123456789abcdef' for c in run_id):
                raise ValueError('Invalid run ID')
            report=json.loads((self.directory/run_id/'results.json').read_text(encoding="utf-8"))
            if not report['promotion_eligible']:
                raise ValueError('Candidate failed promotion evaluation')
            candidate=joblib.load(self.directory/run_id/'model.joblib')
            validation=[r for r in self.data()['rows'] if r['split']=='VALIDATION' and r['category']]
            validation_hash=hashlib.sha256(json.dumps(validation,sort_keys=True).encode()).hexdigest()
            if report['validation_sha256']!=validation_hash:
                raise ValueError('Validation partition changed since candidate evaluation')
            if self.model:
                new,old=metrics(candidate,validation),metrics(self.model,validation)
                if new['macro_f1']<old['macro_f1'] or any(new['per_class'][l]['recall']<old['per_class'][l]['recall'] for l in LABELS if new['per_class'][l]['support']):
                    raise ValueError('Candidate no longer meets current incumbent gate')
            record={'run_id':run_id,'previous_run_id':self.active['run_id'] if self.active else None}
            tmp=self.directory/'active.tmp'
            tmp.write_text(json.dumps(record), encoding="utf-8")
            tmp.replace(self.directory/'active.json')
            self.reload()
            return record

    def reports(self):
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.directory.glob('*/results.json'),key=lambda p:p.stat().st_mtime,reverse=True)]

    def rollback(self):
        with LOCK:
            if not self.active or not self.active.get('previous_run_id'):
                raise ValueError('No previous active version')
            prior=self.active['previous_run_id']
            joblib.load(self.directory/prior/'model.joblib')
            record={'run_id':prior,'previous_run_id':self.active['run_id']}
            tmp=self.directory/'active.tmp';tmp.write_text(json.dumps(record), encoding="utf-8");tmp.replace(self.directory/'active.json')
            self.reload();return record

    def initial_test(self):
        # One initial descriptive test. Re-training/promotion never uses this score.
        path=self.directory/'initial_test.json'
        if not path.exists():
            rows=[r for r in self.data()['rows'] if r['split']=='TEST' and r['category']]
            path.write_text(json.dumps({'run_id':self.active['run_id'],'data_status':'AI_WEAK_LABEL_PROTOTYPE',
                'evaluation':metrics(self.model,rows),'valid_for_scientific_claims':False},indent=2), encoding="utf-8")
        return json.loads(path.read_text(encoding="utf-8"))
