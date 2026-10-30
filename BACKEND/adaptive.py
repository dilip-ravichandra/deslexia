"""Persistent opt-in support preferences and reviewed prototype experiments."""
import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

from ML.prototype import PrototypeTrainer
from ML.context import build_context
from ML.contextual_support import explain

def now():return datetime.now(timezone.utc).isoformat()

class AdaptiveService:
    def __init__(self,root):
        self.root=Path(root)
        self.db_path=self.root/'ARTIFACTS'/'learner_state.sqlite3'
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.trainer=PrototypeTrainer(root)
        self.jobs={}
        self.jobs_lock=threading.Lock()
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,created_at TEXT);
            CREATE TABLE IF NOT EXISTS traces(id TEXT PRIMARY KEY,profile_id TEXT,category TEXT,style TEXT,
              payload TEXT,decision TEXT,rating INTEGER,verification TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS reviews(trace_id TEXT PRIMARY KEY,label TEXT,reason TEXT,reviewer TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS visual_traces(id TEXT PRIMARY KEY,profile_id TEXT,style TEXT,payload TEXT,decision TEXT,created_at TEXT);
            CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,event TEXT,payload TEXT,created_at TEXT);
            ''')

    @contextmanager
    def db(self):
        connection=sqlite3.connect(self.db_path,timeout=15)
        connection.row_factory=sqlite3.Row
        try:
            with connection:yield connection
        finally:connection.close()

    def identity(self,key):
        if not key:return None
        if not re.fullmatch(r'[a-f0-9]{64}',key):raise ValueError('Invalid learner key')
        return hashlib.sha256(key.encode()).hexdigest()

    def profile(self,key):
        ident=self.identity(key)
        if not ident:raise ValueError('Enable Remember support to access a profile')
        with self.db() as db:
            rows=db.execute('SELECT category,style,decision,COUNT(*) n FROM traces WHERE profile_id=? AND decision IS NOT NULL GROUP BY category,style,decision',(ident,)).fetchall()
            rows=list(rows)+list(db.execute("SELECT 'VISUAL' category,style,decision,COUNT(*) n FROM visual_traces WHERE profile_id=? AND decision IS NOT NULL GROUP BY style,decision",(ident,)).fetchall())
        scores={}
        for row in rows:
            category=row['category'];style=row['style'];item=scores.setdefault(category,{}).setdefault(style,{'helpful':0,'not_helpful':0,'regenerate':0,'count':0,'score':0})
            names={'accept':'helpful','reject':'not_helpful','regenerate':'regenerate'}
            item[names[row['decision']]]+=row['n'];item['count']+=row['n']
            item['score']+=row['n']*{'accept':1,'reject':-1,'regenerate':-0.25}[row['decision']]
        preferred={}
        for category,styles in scores.items():
            candidates=[(v['score']/v['count'],style) for style,v in styles.items() if v['count']>=2 and v['score']>0]
            preferred[category]=max(candidates)[1] if candidates else 'short'
        return {'preferences':preferred,'feedback':scores,'persistent':True,'method':'Per-category support style from final helpfulness decisions; minimum two positive-net observations.'}

    def forget(self,key):
        ident=self.identity(key)
        if not ident:raise ValueError('Missing learner key')
        with self.db() as db:
            db.execute('DELETE FROM reviews WHERE trace_id IN (SELECT id FROM traces WHERE profile_id=?)',(ident,))
            db.execute('DELETE FROM visual_traces WHERE profile_id=?',(ident,));db.execute('DELETE FROM traces WHERE profile_id=?',(ident,));db.execute('DELETE FROM profiles WHERE id=?',(ident,))
        return {'status':'deleted','note':'Stored profile and feedback deleted. Previously trained weights are not unlearned; train a new version to exclude deleted feedback.'}

    def consent_version(self,key):
        """Capture a consent generation before inference; a key alone is not consent."""
        ident=self.identity(key)
        if not ident:return None
        with self.db() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='learner_surveys'").fetchone():return None
            row=db.execute('SELECT created_at FROM learner_surveys WHERE id=? AND consent=1',(ident,)).fetchone()
            return row['created_at'] if row else None

    def adapt(self,pipe,req,key):
        consent_version=self.consent_version(key)
        if req.document_text and req.text and req.text not in req.document_text:
            raise ValueError('Stored passage must contain the submitted text window')
        from ML.onnx_verification import available as nli_available,ONXNNLIScorer,ONNXEmbeddingScorer
        from ML.neural_features import available as embedding_available
        if nli_available() and os.environ.get('DYSLEXIADAPT_GENERATION','on')!='off':
            pipe.nli=ONXNNLIScorer()
            if embedding_available():pipe.embedder=ONNXEmbeddingScorer()
        if req.mode=='research':
            return pipe.adapt(req.span,req.text,req.span_start,req.context_before,req.context_after,req.category_override,req.variant,want_research=True)
        ctx=build_context(req.text,req.span,req.span_start) if req.text else {'context_before':req.context_before,'context_after':req.context_after,'sentence':req.span}
        probabilities=self.trainer.predict(req.span,ctx['context_before'],ctx['context_after'])
        suggested=max(probabilities,key=probabilities.get) if probabilities else None
        uncertain=bool(probabilities and (suggested=='OTHER_UNCERTAIN' or max(probabilities.values())<self.trainer.uncertainty_threshold))
        primary=[c for c in (probabilities or {}) if c!='OTHER_UNCERTAIN']
        category=req.category_override or (max(primary,key=probabilities.get) if probabilities and uncertain else suggested)
        response=pipe.adapt(req.span,req.text,req.span_start,req.context_before,req.context_after,category,req.variant)
        category=response['category']['category']
        if not req.category_override and probabilities:
            response['category']={'category':category,'suggested_category':suggested,'source':'trained_prototype:validation_selected',
                'probabilities':probabilities,'confidence':None,'is_trained_model_output':True,'needs_choice':uncertain,
                'note':'GPT weak-label prototype; probabilities are not calibrated. You may choose another support type.'}
            response['research_mode']='prototype';response['experiment_id']=self.trainer.active['run_id']
            response['valid_for_research']=False
            response['warnings']=['Prototype trained on GPT-labelled synthetic examples; not a research result.']+[
                w for w in response['warnings'] if not w.startswith('DEMO:')]
        ident=self.identity(key)
        profile=self.profile(key) if ident else None
        style=req.support_style if req.support_style!='auto' else (profile['preferences'].get(category,'short') if profile else 'short')
        response['personalization']={'enabled':bool(consent_version),'style':style,'source':'learner_choice' if req.support_style!='auto' else 'saved_feedback' if profile and category in profile['preferences'] else 'default'}
        response['explanation']=explain(req.span,response['input']['sentence'],ctx['context_before'],ctx['context_after'],style,category)
        # Uncertain model output never automatically rewrites learner content.
        if uncertain and not req.category_override:
            response['presentable']=False
            response['warnings'].append('Support type is uncertain. Choose Word, Sentence, or Idea help to continue.')
        response['explanation']['available']=not uncertain or bool(req.category_override)
        if ident and consent_version:
            document=req.document_text or req.text or ' '.join([req.context_before,req.span,req.context_after])
            payload={'text':req.span,'context_before':ctx['context_before'],'context_after':ctx['context_after'],
                     'document_text':document,'document_id':'feedback_'+hashlib.sha256(document.encode()).hexdigest(),
                     'source_type':'LEARNER_OPT_IN_FEEDBACK','annotation_provenance':'UNREVIEWED_FEEDBACK'}
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1 AND created_at=?',(ident,consent_version)).fetchone():return response
                db.execute('INSERT OR IGNORE INTO profiles VALUES (?,?)',(ident,now()))
                db.execute('INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?)',(response['trace_id'],ident,category,style,json.dumps(payload),None,None,response['verification']['status'],now()))
        return response

    def feedback(self,key,trace_id,decision,rating):
        ident=self.identity(key)
        if not ident:return None
        with self.db() as db:
            row=db.execute('SELECT * FROM traces WHERE id=? AND profile_id=?',(trace_id,ident)).fetchone()
            if not row:return False
            if decision=='accept' and row['verification']=='fail':raise ValueError('Failed adaptation cannot be accepted')
            # Update the final decision, do not count repeated clicks as multiple observations.
            db.execute('UPDATE traces SET decision=?,rating=? WHERE id=?',(decision,rating,trace_id))
        return True

    def record_visual(self,key,style,question,response,consent_version=None):
        ident=self.identity(key)
        if not ident or consent_version is None:return None
        trace_id=uuid.uuid4().hex
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='learner_surveys'").fetchone():return None
            if not db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1 AND created_at=?',(ident,consent_version)).fetchone():return None
            db.execute('INSERT INTO visual_traces VALUES (?,?,?,?,?,?)',(trace_id,ident,style,json.dumps({'question':question,'explanation':response['explanation'],'model':response['model']}),None,now()))
        return trace_id

    def visual_feedback(self,key,trace_id,decision):
        ident=self.identity(key)
        if not ident:raise ValueError('Enable Remember support to save feedback')
        with self.db() as db:
            row=db.execute('SELECT decision FROM visual_traces WHERE id=? AND profile_id=?',(trace_id,ident)).fetchone()
            if row is None:raise LookupError('Visual response not found for this learner')
            if row['decision'] is not None and row['decision']!=decision:raise ValueError('A final decision is already recorded for this answer')
            db.execute('UPDATE visual_traces SET decision=? WHERE id=? AND profile_id=?',(decision,trace_id,ident))
        return {'status':'recorded','note':'Visual style feedback only; this does not train the text classifier or vision model.'}

    def analytics(self):
        with self.db() as db:
            totals=db.execute('SELECT category,style,decision,COUNT(*) count FROM traces WHERE decision IS NOT NULL GROUP BY category,style,decision').fetchall()
            pending=db.execute('SELECT t.* FROM traces t LEFT JOIN reviews r ON r.trace_id=t.id WHERE t.decision IS NOT NULL AND r.trace_id IS NULL ORDER BY t.created_at DESC LIMIT 100').fetchall()
            reviewed=db.execute('SELECT COUNT(*) n FROM reviews').fetchone()['n']
            visual=db.execute('SELECT style,decision,COUNT(*) count FROM visual_traces WHERE decision IS NOT NULL GROUP BY style,decision').fetchall()
        return {'visual_feedback':[dict(r) for r in visual],'feedback':[dict(r) for r in totals],'reviewed_examples':reviewed,
                'review_queue':[{'trace_id':r['id'],'category_suggested':r['category'],'decision':r['decision'],
                                 'verification':r['verification'],**json.loads(r['payload'])} for r in pending],
                'runs':self.trainer.reports(),'active':self.trainer.active,
                'note':'Acceptance is helpfulness feedback, not a class label. Admin review is required before retraining.'}

    def review(self,trace_id,label,reason,reviewer):
        with self.db() as db:
            row=db.execute('SELECT payload FROM traces WHERE id=? AND decision IS NOT NULL',(trace_id,)).fetchone()
            if not row:raise ValueError('Feedback example not found')
            payload=json.loads(row['payload'])
            protected=[r for r in self.trainer.data()['rows'] if r['split']!='TRAIN']
            passage=payload['document_text'].strip()
            if not passage or any(passage in r['document_text'] or r['document_text'] in passage or
                  (payload['text']==r['text'] and payload['context_before']==r['context_before'] and payload['context_after']==r['context_after']) for r in protected):
                raise ValueError('Example overlaps protected validation/test documents')
            db.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?)',(trace_id,label,reason,reviewer,now()))
        return {'status':'reviewed','note':'Reviewer judgement recorded; no model was changed.'}

    def reviewed(self):
        with self.db() as db:
            rows=db.execute('SELECT t.payload,r.label,r.reason,r.reviewer,r.created_at FROM reviews r JOIN traces t ON t.id=r.trace_id').fetchall()
        return [{**json.loads(r['payload']),'category':r['label'],'rationale':r['reason'],'annotator_id':r['reviewer'],
                 'created_at':r['created_at'],'annotation_provenance':'ADMIN_REVIEWED_FEEDBACK'} for r in rows]

    def start_training(self):
        with self.jobs_lock:
            if any(j['status']=='running' for j in self.jobs.values()):raise ValueError('A training job is already running')
            ident=uuid.uuid4().hex;self.jobs[ident]={'job_id':ident,'status':'running'}
        def work():
            try:
                report=self.trainer.train(self.reviewed())
                self.jobs[ident]={'job_id':ident,'status':'completed','run':report}
            except Exception as error:self.jobs[ident]={'job_id':ident,'status':'failed','error':str(error)}
        threading.Thread(target=work,daemon=True).start()
        return self.jobs[ident]
