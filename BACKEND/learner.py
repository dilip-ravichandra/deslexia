"""Interpretable online learner model. No behavioural event is a gold difficulty label."""
import hashlib,json,math,re,sqlite3,uuid
from datetime import datetime,timezone
from contextlib import contextmanager
CATEGORIES=['VOCABULARY','SYNTACTIC','CONCEPTUAL','PRONUNCIATION','VISUAL']
STYLES=['short','steps','example']
LANGUAGES=['en','hi','kn','ta']
KINDS={'help_request','style_choice','reread','attention_return','dwell','undo','regenerate','settings_change','optional_feedback','session_end'}

def now():return datetime.now(timezone.utc).isoformat()
def identity(key):
    if not key or not re.fullmatch('[a-f0-9]{64}',key):raise ValueError('A valid learner capability is required.')
    return hashlib.sha256(key.encode()).hexdigest()
def groups(span):
    import unicodedata
    text=unicodedata.normalize('NFKC',span).strip().casefold()
    # Buckets describe text shape, not linguistic or clinical causes.
    letters=sum(unicodedata.category(c).startswith('L') for c in text)
    result=['term:'+hashlib.sha256(text.encode()).hexdigest()[:16]] if text else []
    if len(text.split())>1:result.append('multiword')
    elif letters>=8:result.append('long_word')
    else:result.append('short_word')
    if any(c.isdigit() for c in text):result.append('contains_numbers')
    return result

class LearnerModel:
    def __init__(self,path):
        self.path=path
        with self.db() as db:db.executescript("""
        CREATE TABLE IF NOT EXISTS learner_surveys(id TEXT PRIMARY KEY,alias TEXT,survey TEXT,consent INTEGER,created_at TEXT);
        CREATE TABLE IF NOT EXISTS learner_sessions(id TEXT PRIMARY KEY,profile_id TEXT,language TEXT,started_at TEXT,ended_at TEXT);
        CREATE TABLE IF NOT EXISTS learner_events(id TEXT PRIMARY KEY,client_id TEXT,profile_id TEXT,session_id TEXT,language TEXT,kind TEXT,payload TEXT,created_at TEXT,UNIQUE(profile_id,client_id));
        CREATE TABLE IF NOT EXISTS learner_updates(event_id TEXT PRIMARY KEY,profile_id TEXT,before_state TEXT,after_state TEXT,reason TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS learner_routes(id TEXT PRIMARY KEY,profile_id TEXT,session_id TEXT,language TEXT,span TEXT,requested TEXT,selected TEXT,style TEXT,evidence TEXT,created_at TEXT);
        """)
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
    def survey(self,key,values):
        ident=identity(key)
        if not values['consent']:raise ValueError('Behavioural learning requires opt-in consent; reading remains available without it.')
        with self.db() as db:
            old=db.execute('SELECT id FROM learner_surveys WHERE id=?',(ident,)).fetchone()
            if old:raise ValueError('A starting survey already exists. Delete the learner history before starting a new profile.')
            db.execute('INSERT INTO learner_surveys VALUES (?,?,?,?,?)',(ident,values.get('alias') or 'Reader '+ident[:6],json.dumps(values),1,now()))
        return self.state(key)
    def enrolled(self,key):
        if not key:return False
        ident=identity(key)
        with self.db() as db:return db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1',(ident,)).fetchone() is not None
    def start(self,key,language):
        ident=identity(key)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1',(ident,)).fetchone():raise ValueError('Complete the optional profile setup before saving session signals.')
            active=db.execute('SELECT id FROM learner_sessions WHERE profile_id=? AND language=? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1',(ident,language)).fetchone()
            if active:return {'session_id':active['id'],'language':language,'status':'resumed'}
            sid=uuid.uuid4().hex
            db.execute('INSERT INTO learner_sessions VALUES (?,?,?,?,?)',(sid,ident,language,now(),None))
        return {'session_id':sid,'language':language,'status':'started'}
    def _state(self,db,ident,language='en',span='',clock=None):
        row=db.execute('SELECT * FROM learner_surveys WHERE id=?',(ident,)).fetchone()
        if row is None:return {'enrolled':False,'revision':0,'note':'No survey or session evidence is saved.'}
        survey=json.loads(row['survey']);buckets=groups(span)
        presentation=dict(survey.get('reading_settings',{}));alpha={c:1.0 for c in CATEGORIES};style_alpha={s:1.0 for s in STYLES};evidence=[];ambiguous=0
        relevant_request_scores={category:0.0 for category in CATEGORIES}
        relevant_request_counts={category:0 for category in CATEGORIES}
        category_style_parameters={category:{style:1.0 for style in STYLES} for category in CATEGORIES}
        category_style_feedback={category:0 for category in CATEGORIES}
        for category in survey.get('difficulties',[]):alpha[category]+=.5
        preference=survey.get('preferred_style','short');style_alpha[preference]+=.5
        events=db.execute('SELECT * FROM learner_events WHERE profile_id=? ORDER BY created_at,id',(ident,)).fetchall()
        dedup=set();clock=clock or datetime.now(timezone.utc)
        for event in events:
            p=json.loads(event['payload']);age=max(0,(clock-datetime.fromisoformat(event['created_at'])).total_seconds()/86400);decay=2**(-age/30)
            if event['language']!=language:continue
            overlap=set(buckets)&set(p.get('groups',[]));specificity=1.0 if any(x.startswith('term:') for x in overlap) else .35 if overlap else .1
            category=p.get('category');style=p.get('style');kind=event['kind'];effect='Recorded only; no difficulty label inferred.';counted=False
            if kind=='help_request' and category in CATEGORIES:
                marker=(event['session_id'],p.get('span','').casefold(),category)
                if marker in dedup:effect='Repeated request in the same session; not counted again.'
                else:
                    dedup.add(marker);alpha[category]+=decay*specificity;counted=True
                    if specificity>=.35:
                        relevant_request_scores[category]+=decay*specificity
                        relevant_request_counts[category]+=1
                    effect='Explicit support request updates need evidence; it does not prove the response helped.'
            elif kind=='style_choice' and style in STYLES:
                style_alpha[style]+=.5*decay;effect='Direct style preference; not comprehension evidence.'
            elif kind in {'undo','regenerate'} and style in STYLES:
                style_alpha[style]=max(.1,style_alpha[style]-.25*decay);effect='Weak negative evidence about the previous support style.'
                if category in CATEGORIES:
                    category_style_parameters[category][style]=max(.1,category_style_parameters[category][style]-.25*decay)
                    category_style_feedback[category]+=1
            elif kind=='optional_feedback' and style in STYLES:
                style_alpha[style]=max(.1,style_alpha[style]+(.75 if p.get('decision')=='accept' else -.75)*decay);effect='Optional helpfulness feedback; not a training category label.'
                if category in CATEGORIES:
                    category_style_parameters[category][style]=max(.1,category_style_parameters[category][style]+(.75 if p.get('decision')=='accept' else -.75)*decay)
                    category_style_feedback[category]+=1
            elif kind=='settings_change':presentation[p['setting']]=p.get('value');effect='Explicit presentation preference updated; no difficulty inferred.'
            else:ambiguous+=1
            if kind in {'help_request','style_choice','undo','regenerate','optional_feedback','settings_change'}:evidence.append({'event_id':event['id'],'kind':kind,'category':category,'language':language,'effect':effect,'relevance':specificity,'recency_weight':round(decay,4),'counted_need':counted})
        total=sum(alpha.values());styles_total=sum(style_alpha.values());need={c:round(v/total,5) for c,v in alpha.items()};styles={s:round(v/styles_total,5) for s,v in style_alpha.items()}
        return {'enrolled':True,'alias':row['alias'],'survey':survey,'language':language,'groups':buckets,'revision':len(events),'need_parameters':alpha,'need_estimates':need,'style_parameters':style_alpha,'style_estimates':styles,
                'relevant_request_scores':{category:round(score,4) for category,score in relevant_request_scores.items()},
                'relevant_request_counts':relevant_request_counts,
                'category_style_parameters':category_style_parameters,
                'category_style_feedback':category_style_feedback,
                'presentation_preferences':presentation,'preferred_style':max(styles,key=styles.get),'evidence':evidence[-30:],'ambiguous_observations':ambiguous,'note':'Dirichlet-style online evidence model; scores are uncalibrated estimates of requested support, not diagnosis or proof of learning.'}
    def state(self,key,language='en',span=''):
        ident=identity(key)
        with self.db() as db:return self._state(db,ident,language,span)
    def paragraph_requests(self,key,language,paragraph):
        ident=identity(key)
        scores={category:0.0 for category in CATEGORIES}
        counts={category:0 for category in CATEGORIES}
        seen=set();text=paragraph.casefold();clock=datetime.now(timezone.utc)
        with self.db() as db:
            events=db.execute("SELECT * FROM learner_events WHERE profile_id=? AND language=? AND kind='help_request' ORDER BY created_at,id",(ident,language)).fetchall()
        for event in events:
            payload=json.loads(event['payload']);category=payload.get('category');span=payload.get('span','').strip().casefold()
            marker=(event['session_id'],span,category)
            if category not in scores or not span or marker in seen:continue
            seen.add(marker)
            if not re.search(r'(?<!\w)'+re.escape(span)+r'(?!\w)',text):continue
            age=max(0,(clock-datetime.fromisoformat(event['created_at'])).total_seconds()/86400)
            scores[category]+=2**(-age/30);counts[category]+=1
        return {'scores':scores,'counts':counts}
    def record(self,key,event):
        ident=identity(key);kind=event['kind'];language=event['language'];sid=event['session_id'];p=event.get('payload',{})
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            session=db.execute('SELECT * FROM learner_sessions WHERE id=? AND profile_id=?',(sid,ident)).fetchone()
            if session is None:raise ValueError('Session not found for this learner.')
            if not db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1',(ident,)).fetchone():raise ValueError('Reading-signal consent is not active.')
            old=db.execute('SELECT id FROM learner_events WHERE profile_id=? AND client_id=?',(ident,event['client_id'])).fetchone()
            if old:return {'event_id':old['id'],'duplicate':True,'state':self._state(db,ident,language,p.get('span',''))}
            if session['ended_at']:raise ValueError('This session is already closed.')
            if language!=session['language']:raise ValueError('Start a new session after changing document language.')
            p={k:v for k,v in p.items() if k in {'span','category','style','decision','duration_ms','setting','value','paragraph_id','route_id'}}
            if not isinstance(p.get('span',''),str):raise ValueError('Selected span must be text.')
            if p.get('duration_ms') is not None and (not isinstance(p['duration_ms'],(int,float)) or isinstance(p['duration_ms'],bool) or not math.isfinite(p['duration_ms']) or not 0<=p['duration_ms']<=60000):raise ValueError('Duration must be between 0 and 60000 milliseconds.')
            if len(str(p.get('span','')))>300:raise ValueError('Selected span is too long.')
            if p.get('category') is not None and p['category'] not in CATEGORIES:raise ValueError('Unknown support category.')
            if p.get('style') is not None and p['style'] not in STYLES:raise ValueError('Unknown support style.')
            if p.get('decision') is not None and p['decision'] not in {'accept','reject'}:raise ValueError('Invalid decision.')
            if kind=='help_request' and p.get('category') not in CATEGORIES:raise ValueError('An explicit help request requires its selected category.')
            if kind=='style_choice' and p.get('style') not in STYLES:raise ValueError('Style choice requires a supported style.')
            if kind=='optional_feedback' and p.get('decision') not in {'accept','reject'}:raise ValueError('Feedback requires a decision.')
            if kind in {'undo','regenerate','optional_feedback'}:
                route=db.execute('SELECT * FROM learner_routes WHERE id=? AND profile_id=? AND session_id=?',(p.get('route_id',''),ident,sid)).fetchone()
                if route is None:raise ValueError('A prior support route in this session is required.')
                p.update(span=route['span'],style=route['style'],category=route['selected'])
            if kind=='settings_change' and p.get('setting') not in {'s-bg','s-contrast','s-size','s-lh','s-ls','s-font','s-focus','s-width','reading-ruler'}:raise ValueError('Unknown reading setting.')
            p['groups']=groups(str(p.get('span','')));stamp=now();clock=datetime.fromisoformat(stamp);before=self._state(db,ident,language,p.get('span',''),clock);eid=uuid.uuid4().hex
            db.execute('INSERT INTO learner_events VALUES (?,?,?,?,?,?,?,?)',(eid,event['client_id'],ident,sid,language,kind,json.dumps(p),stamp))
            after=self._state(db,ident,language,p.get('span',''),clock)
            changed=before.get('need_parameters')!=after.get('need_parameters') or before.get('style_parameters')!=after.get('style_parameters') or before.get('presentation_preferences')!=after.get('presentation_preferences')
            reason=(after['evidence'][-1]['effect'] if after['evidence'] and after['evidence'][-1]['event_id']==eid else 'Ambiguous observation; no category or style preference update.')
            db.execute('INSERT INTO learner_updates VALUES (?,?,?,?,?,?)',(eid,ident,json.dumps(before),json.dumps(after),reason,stamp))
            if kind=='session_end':db.execute('UPDATE learner_sessions SET ended_at=? WHERE id=?',(stamp,sid))
        return {'event_id':eid,'duplicate':False,'parameters_changed':changed,'reason':reason,'state':after}
    def choose(self,key,sid,language,span,requested=None,style='auto',public_prediction=None,routing_prediction=None,variant=0):
        state=self.state(key,language,span) if key and self.enrolled(key) else {'enrolled':False,'revision':0}
        reason=[];selected=requested;needs_choice=False;source='learner_choice' if requested else 'clarification'
        if requested:reason.append('Current explicit request overrides history.')
        elif state.get('enrolled'):
            scores=state['relevant_request_scores'];ranked=sorted(scores,key=scores.get,reverse=True);first=ranked[0]
            if state['relevant_request_counts'][first]>=2 and scores[first]-scores[ranked[1]]>=.35:
                selected=first;source='learner_history';reason.append('Repeated relevant support requests informed this suggestion; usefulness remains unverified.')
        if not selected and state.get('enrolled') and len(state['survey'].get('difficulties',[]))==1:
            selected=state['survey']['difficulties'][0];source='starting_survey';reason.append('Starting survey suggests this support; later relevant observations can revise it. This is self-report, not a detected difficulty.')
        if not selected and routing_prediction and routing_prediction.get('score',0)>=.7:
            selected=routing_prediction['category'];source='human_routing_model';reason.append('Evaluated human routing model suggests support; its probability is uncalibrated and your choice takes priority.')
        if not selected and public_prediction and language=='en' and public_prediction.get('score',0)>=.4:
            selected='VOCABULARY';source='public_lexical_model';reason.append('Human-data lexical complexity model suggests vocabulary help; this is not a full routing classifier.')
        if not selected:selected='OTHER_UNCERTAIN';needs_choice=True;reason.append('Insufficient evidence to choose a category. Ask the learner; do not force a label.')
        chosen_style=style if style in STYLES else state.get('preferred_style','short')
        if style not in STYLES and selected in CATEGORIES and state.get('category_style_feedback',{}).get(selected,0):
            category_styles=state['category_style_parameters'][selected]
            chosen_style=max(STYLES,key=lambda candidate:category_styles[candidate])
            reason.append('Your optional feedback for this support type influenced the explanation style; this is preference evidence, not a reading score.')
        if variant:
            chosen_style=STYLES[(STYLES.index(chosen_style)+1)%len(STYLES)];reason.append('A one-off alternative explanation style was requested.')
        route={'route_id':None,'selected':selected,'source':source,'style':chosen_style,'needs_choice':needs_choice,'reasons':reason,'profile_revision':state.get('revision',0),'learner_state':state,'public_word_prediction':public_prediction,'routing_prediction':routing_prediction,
               'decision_factors':{'starting_needs':state.get('survey',{}).get('difficulties',[]),
                                   'relevant_request_counts':state.get('relevant_request_counts',{}),
                                   'relevant_request_scores':state.get('relevant_request_scores',{}),
                                   'style_feedback_count':state.get('category_style_feedback',{}).get(selected,0),
                                   'current_request_overrode_history':bool(requested)}}
        if key and state.get('enrolled'):
            ident=identity(key)
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute('SELECT 1 FROM learner_surveys WHERE id=? AND consent=1',(ident,)).fetchone():return {**route,'route_id':None}
                if not db.execute('SELECT 1 FROM learner_sessions WHERE id=? AND profile_id=? AND language=? AND ended_at IS NULL',(sid,ident,language)).fetchone():raise ValueError('Start an active reading session in this language before saving a decision.')
                rid=uuid.uuid4().hex;route['route_id']=rid
                db.execute('INSERT INTO learner_routes VALUES (?,?,?,?,?,?,?,?,?,?)',(rid,ident,sid,language,span,requested,selected,chosen_style,json.dumps(route),now()))
        return route
    def forget(self,key):
        ident=identity(key)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'reviews' in tables and 'traces' in tables:db.execute('DELETE FROM reviews WHERE trace_id IN (SELECT id FROM traces WHERE profile_id=?)',(ident,))
            for table in ['visual_traces','traces','profiles']:
                if table in tables:db.execute('DELETE FROM '+table+' WHERE '+('id' if table=='profiles' else 'profile_id')+'=?',(ident,))
            for table in ['learner_updates','learner_events','learner_routes','learner_sessions']:db.execute('DELETE FROM '+table+' WHERE profile_id=?',(ident,))
            db.execute('DELETE FROM learner_surveys WHERE id=?',(ident,))

    def record_quality(self,key,route_id,quality):
        """Attach screening metadata only to a still-existing consented decision."""
        if not key or not route_id:return
        ident=identity(key)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT evidence FROM learner_routes WHERE id=? AND profile_id=? AND EXISTS (SELECT 1 FROM learner_surveys WHERE id=? AND consent=1)',(route_id,ident,ident)).fetchone()
            if row:
                value=json.loads(row['evidence']);value['explanation_quality']=quality
                db.execute('UPDATE learner_routes SET evidence=? WHERE id=?',(json.dumps(value),route_id))
    def dashboard(self,profile_id=None):
        with self.db() as db:
            profiles=[dict(r) for r in db.execute('SELECT id,alias,created_at FROM learner_surveys WHERE consent=1 ORDER BY created_at')]
            if not profile_id:return {'profiles':profiles,'selected':None,'note':'Only actual consented learner records are shown. No demo learners are generated.'}
            row=db.execute('SELECT * FROM learner_surveys WHERE id=?',(profile_id,)).fetchone()
            if row is None or not row['consent']:raise LookupError('Learner profile not found.')
            events=[]
            for r in db.execute('SELECT e.*,u.before_state,u.after_state,u.reason FROM learner_events e JOIN learner_updates u ON u.event_id=e.id WHERE e.profile_id=? ORDER BY e.created_at DESC LIMIT 100',(profile_id,)):
                item=dict(r)
                for k in ['payload','before_state','after_state']:item[k]=json.loads(item[k])
                events.append(item)
            sessions=[dict(r) for r in db.execute('SELECT * FROM learner_sessions WHERE profile_id=? ORDER BY started_at DESC',(profile_id,))]
            routes=[dict(r) for r in db.execute('SELECT * FROM learner_routes WHERE profile_id=? ORDER BY created_at DESC LIMIT 20',(profile_id,))]
            for route in routes:route['evidence']=json.loads(route['evidence'])
            kinds={kind:count for kind,count in db.execute('SELECT kind,COUNT(*) FROM learner_events WHERE profile_id=? GROUP BY kind',(profile_id,))}
            categories={category:0 for category in CATEGORIES}
            feedback={'helped':0,'not_helpful':0}
            for event in db.execute("SELECT kind,payload FROM learner_events WHERE profile_id=? AND kind IN ('help_request','optional_feedback')",(profile_id,)):
                payload=json.loads(event['payload'])
                if event['kind']=='help_request' and payload.get('category') in categories:categories[payload['category']]+=1
                elif event['kind']=='optional_feedback':
                    feedback['helped' if payload.get('decision')=='accept' else 'not_helpful']+=1
            metrics={'sessions':len(sessions),'support_decisions':db.execute('SELECT COUNT(*) FROM learner_routes WHERE profile_id=?',(profile_id,)).fetchone()[0],
                     'events':sum(kinds.values()),'event_kinds':kinds,'explicit_requests':categories,'feedback':feedback}
            return {'profiles':profiles,'selected':profile_id,'profile':{'alias':row['alias'],'created_at':row['created_at'],'id':profile_id},
                    'survey':json.loads(row['survey']),'sessions':sessions,'events':events,'routes':routes,'metrics':metrics,
                    'states':{language:self._state(db,profile_id,language) for language in LANGUAGES},'note':'Activity is evidence of interaction; it is not independently verified learning or clinical data.'}
    def overview(self):
        with self.db() as db:
            consented='SELECT id FROM learner_surveys WHERE consent=1'
            profiles=db.execute('SELECT COUNT(*) FROM learner_surveys WHERE consent=1').fetchone()[0]
            sessions=db.execute(f'SELECT COUNT(*) FROM learner_sessions WHERE profile_id IN ({consented})').fetchone()[0]
            responses=db.execute(f'SELECT COUNT(*) FROM learner_routes WHERE profile_id IN ({consented})').fetchone()[0]
            requests={category:0 for category in CATEGORIES}
            feedback={'helped':0,'not_helpful':0}
            rows=db.execute(f"SELECT kind,payload FROM learner_events WHERE profile_id IN ({consented}) AND kind IN ('help_request','optional_feedback')")
            for row in rows:
                payload=json.loads(row['payload'])
                if row['kind']=='help_request' and payload.get('category') in requests:
                    requests[payload['category']]+=1
                elif row['kind']=='optional_feedback' and payload.get('decision') in ('accept','reject'):
                    feedback['helped' if payload['decision']=='accept' else 'not_helpful']+=1
            return {'profiles':profiles,'sessions':sessions,'support_responses':responses,'explicit_requests':requests,'optional_feedback':feedback,
                    'note':'Counts include only consented local profiles. Requests are learner choices, not detected errors; feedback is voluntary, not a learning outcome.'}
    def report(self,key):
        ident=identity(key)
        result=self.dashboard(ident)
        result.pop('profiles')
        return result
