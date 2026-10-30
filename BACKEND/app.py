"""DyslexiAdapt API.

Learner endpoints take TEXT inputs only (extra fields are rejected), so visual/presentation settings
cannot influence classification. Research endpoints are admin-gated.
Run:  uvicorn BACKEND.app:app --port 8000   then open http://127.0.0.1:8000/
"""
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from BACKEND.pipeline import Pipeline, DISCLAIMER
from BACKEND.research import research_summary, read_artifact, list_traces
from BACKEND.adaptive import AdaptiveService
from BACKEND.accounts import AccountStore, COOKIE

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="DyslexiAdapt API", version="0.4.0")
pipe = Pipeline()
adaptive = AdaptiveService(ROOT)
from BACKEND.learner import LearnerModel
learner = LearnerModel(adaptive.db_path)
accounts = AccountStore(adaptive.db_path)


class AdaptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")   # visual settings etc. are rejected with 422
    span: str = Field(min_length=1, max_length=300)
    text: Optional[str] = Field(default=None, max_length=5000)
    span_start: Optional[int] = Field(default=None, ge=0)
    context_before: str = Field(default="", max_length=2000)
    context_after: str = Field(default="", max_length=2000)
    category_override: Optional[Literal["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]] = None
    variant: int = Field(default=0, ge=0, le=1)
    mode: Literal["demo", "research"] = "demo"
    support_style: Literal['auto','short','steps','example'] = 'auto'
    document_text: Optional[str] = Field(default=None,max_length=50000)


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trace_id: str = Field(min_length=8, max_length=64)
    decision: Literal["accept", "reject", "regenerate"]
    comfort_rating: Optional[int] = Field(default=None, ge=1, le=5)


def admin(request: Request):
    """Private research view. If DYSLEXIADAPT_ADMIN_TOKEN is set it is required; otherwise only local access."""
    token = os.environ.get("DYSLEXIADAPT_ADMIN_TOKEN")
    if token:
        if not hmac.compare_digest(request.headers.get("x-admin-token", ""), token):
            raise HTTPException(401, "admin token required")
    elif (request.client.host if request.client else "") not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(403, "research endpoints are local-only unless DYSLEXIADAPT_ADMIN_TOKEN is set")


def local_account_access(request: Request):
    if (request.client.host if request.client else '') not in {'127.0.0.1', '::1', 'localhost', 'testclient'}:
        raise HTTPException(403, 'Local accounts require the local helper.')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin account requests are not allowed.')


def learner_key(request: Request):
    session = accounts.current(request.cookies.get(COOKIE))
    if session:
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            local_account_access(request)
        return session['learner_key'] if session['setup_complete'] else None
    return request.headers.get('x-learner-key')


class AccountRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=12, max_length=128)


class NewAccountRequest(AccountRequest):
    alias: str = Field(default='', max_length=60)
    preferred_language: Literal['en', 'hi', 'kn', 'ta'] = 'en'
    study_languages: list[Literal['en', 'hi', 'kn', 'ta']] = Field(default_factory=lambda: ['en'], min_length=1, max_length=4)
    preferred_style: Literal['short', 'steps', 'example'] = 'short'
    difficulties: list[Literal['VOCABULARY', 'SYNTACTIC', 'CONCEPTUAL', 'PRONUNCIATION', 'VISUAL']] = Field(default_factory=list, max_length=5)
    consent: Literal[True]


class ProfileSetupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    alias: str = Field(default='', max_length=60)
    preferred_language: Literal['en', 'hi', 'kn', 'ta'] = 'en'
    study_languages: list[Literal['en', 'hi', 'kn', 'ta']] = Field(min_length=1, max_length=4)
    preferred_style: Literal['short', 'steps', 'example'] = 'short'
    difficulties: list[Literal['VOCABULARY', 'SYNTACTIC', 'CONCEPTUAL', 'PRONUNCIATION', 'VISUAL']] = Field(default_factory=list, max_length=5)
    consent: Literal[True]


def account_cookie(response: Response, request: Request, token: str):
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict',
                        secure=request.url.scheme == 'https', path='/')
    response.headers['Cache-Control'] = 'no-store'


@app.post('/api/account/signup')
def signup_account(values: AccountRequest, request: Request, response: Response):
    local_account_access(request)
    key = secrets.token_hex(32)
    try:
        token = accounts.register(values.username, values.password, key, learner, pending=True)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    accounts.logout(request.cookies.get(COOKIE))
    account_cookie(response, request, token)
    return {'signed_in': True, 'setup_complete': False,
            'username': values.username.strip().casefold(), 'recovery_key': key}


@app.post('/api/account/profile-setup')
def setup_account_profile(values: ProfileSetupRequest, request: Request, response: Response):
    local_account_access(request)
    session = accounts.current(request.cookies.get(COOKIE))
    if not session:
        raise HTTPException(401, 'Sign in before setting up your reading profile.')
    if session['setup_complete']:
        raise HTTPException(409, 'This reading profile is already set up.')
    try:
        learner.survey(session['learner_key'], {
            'consent': True, 'alias': values.alias.strip(),
            'preferred_language': values.preferred_language,
            'study_languages': values.study_languages,
            'preferred_style': values.preferred_style,
            'difficulties': values.difficulties,
            'reading_settings': {},
        })
        accounts.complete_setup(session['learner_key'], learner)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    response.headers['Cache-Control'] = 'no-store'
    return {'signed_in': True, 'setup_complete': True,
            'username': session['username'], 'profile_id': session['profile_id']}


@app.post('/api/account/create')
def create_account(values: NewAccountRequest, request: Request, response: Response):
    local_account_access(request)
    key = secrets.token_hex(32)
    try:
        learner.survey(key, {
            'consent': True, 'alias': values.alias.strip(),
            'preferred_language': values.preferred_language,
            'study_languages': values.study_languages,
            'preferred_style': values.preferred_style,
            'difficulties': values.difficulties,
            'reading_settings': {},
        })
        token = accounts.register(values.username, values.password, key, learner)
    except ValueError as error:
        learner.forget(key)
        raise HTTPException(422, str(error)) from error
    except Exception:
        learner.forget(key)
        raise
    accounts.logout(request.cookies.get(COOKIE))
    account_cookie(response, request, token)
    return {'signed_in': True, 'username': values.username.strip().casefold(), 'recovery_key': key}


@app.post('/api/account/register')
def register_account(values: AccountRequest, request: Request, response: Response):
    local_account_access(request)
    key = request.headers.get('x-learner-key')
    if not key:
        raise HTTPException(422, 'Create or reconnect a learner profile before creating an account.')
    try:
        token = accounts.register(values.username, values.password, key, learner)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    account_cookie(response, request, token)
    return {'signed_in': True, 'username': values.username.strip().casefold()}


@app.post('/api/account/login')
def login_account(values: AccountRequest, request: Request, response: Response):
    local_account_access(request)
    try:
        token = accounts.login(values.username, values.password, learner)
    except ValueError as error:
        raise HTTPException(401, str(error)) from error
    account_cookie(response, request, token)
    return {'signed_in': True, 'username': values.username.strip().casefold(),
            'setup_complete': accounts.current(token)['setup_complete']}


@app.post('/api/account/reset')
def reset_account_password(values: AccountRequest, request: Request, response: Response):
    local_account_access(request)
    key = request.headers.get('x-learner-key')
    if not key:
        raise HTTPException(422, 'Enter the recovery key on My progress before resetting a password.')
    try:
        token = accounts.reset_password(values.username, values.password, key, learner)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    account_cookie(response, request, token)
    return {'signed_in': True, 'username': values.username.strip().casefold(),
            'setup_complete': accounts.current(token)['setup_complete']}


@app.get('/api/account')
def current_account(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    session = accounts.current(request.cookies.get(COOKIE))
    return {'signed_in': bool(session), 'username': session['username'] if session else None,
            'profile_id': session['profile_id'] if session else None,
            'setup_complete': session['setup_complete'] if session else False}


@app.post('/api/account/logout')
def logout_account(request: Request, response: Response):
    local_account_access(request)
    accounts.logout(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path='/')
    response.headers['Cache-Control'] = 'no-store'
    return {'signed_in': False}


class LibraryItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(max_length=120)
    text: str = Field(max_length=50000)
    created_at: str = Field(default='', max_length=40)


class LibrarySave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[LibraryItem] = Field(max_length=200)


def library_account(request: Request):
    local_account_access(request)
    session = accounts.current(request.cookies.get(COOKIE))
    if not session or not session['setup_complete']:
        raise HTTPException(401, 'Sign in and finish profile setup to use your library.')
    return session


@app.get('/api/account/library/{kind}')
def get_account_library(kind: Literal['passages', 'notes'], request: Request, response: Response):
    session = library_account(request)
    response.headers['Cache-Control'] = 'no-store'
    return {'items': accounts.library(session['profile_id'], kind)}


@app.put('/api/account/library/{kind}')
def put_account_library(kind: Literal['passages', 'notes'], values: LibrarySave, request: Request, response: Response):
    session = library_account(request)
    items = [item.model_dump() for item in values.items]
    if len({item['id'] for item in items}) != len(items):
        raise HTTPException(422, 'Library item IDs must be unique.')
    accounts.save_library(session['profile_id'], kind, items)
    response.headers['Cache-Control'] = 'no-store'
    return {'saved': len(items)}


@app.get("/api/health")
def health():
    return {"status": "ok", "build": "multilingual-learner-research-v4"}


@app.get("/api/model-status")
def model_status():
    from ML.local_generation import available as generation_available
    from ML.neural_features import available as embeddings_available
    from ML.onnx_verification import available as nli_available
    from ML.readiness import services
    from ML.cloud_help import available as online_available
    return {**pipe.status(),'services':services(),'online_ai':{'available':online_available(),'provider':'Groq','explicit_consent_required':True},'prototype':{'available':adaptive.trainer.model is not None,
        'active':adaptive.trainer.active,'data_status':'AI_WEAK_LABEL_PROTOTYPE',
        'valid_for_scientific_claims':False,'pretrained_embeddings_available':embeddings_available()},
        'human_routing':json.loads((ROOT/'ARTIFACTS/human_routing_active.json').read_text(encoding="utf-8")) if (ROOT/'ARTIFACTS/human_routing_active.json').exists() else {'available':False,'reason':'Human-reviewed routing labels and evaluated comparison required'},
        'learner_model':{'method':'Online Dirichlet evidence model','languages':['en','hi','kn','ta'],'synthetic_routing_model_active':False},
        'local_generation':{'available':generation_available(),'model':'Qwen3-4B Q4_K_M'},
        'pretrained_semantic_verification':{'available':nli_available(),'model':'nli-MiniLM2-L6-H768'}}


@app.post("/api/adapt")
def adapt(req: AdaptRequest, request: Request):
    try:
        return adaptive.adapt(pipe,req,learner_key(request))
    except LookupError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/feedback")
def feedback(req: FeedbackRequest, request: Request):
    try:
        persistent=adaptive.feedback(learner_key(request),req.trace_id,req.decision,req.comfort_rating)
    except ValueError as e:
        raise HTTPException(422,str(e))
    if persistent is False:raise HTTPException(404,'unknown trace_id for this learner')
    if persistent:return {'status':'recorded','logged_to_disk':True,'personalization_updated':True}
    if not pipe.traces.feedback(req.trace_id, req.decision, req.comfort_rating):
        raise HTTPException(404, "unknown trace_id")
    return {"status": "recorded", "logged_to_disk": pipe.traces.log_on}


@app.get('/api/profile')
def learner_profile(request:Request):
    try:return adaptive.profile(learner_key(request))
    except ValueError as e:raise HTTPException(422,str(e))

@app.delete('/api/profile')
def forget_profile(request:Request,response:Response):
    try:
        key=learner_key(request)
        learner.forget(key)
        result=adaptive.forget(key)
        accounts.forget_profile(key)
        response.delete_cookie(COOKIE,path='/')
        return result
    except ValueError as e:raise HTTPException(422,str(e))

class ReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    trace_id:str=Field(min_length=32,max_length=32)
    label:Literal['VOCABULARY','SYNTACTIC','CONCEPTUAL','OTHER_UNCERTAIN']
    reason:str=Field(min_length=8,max_length=1000)
    reviewer:str=Field(min_length=2,max_length=100)

class PromotionRequest(BaseModel):
    run_id:str=Field(min_length=32,max_length=32)

@app.get('/api/admin/learning',dependencies=[Depends(admin)])
def learning_dashboard():return adaptive.analytics()


@app.get('/api/admin/dataset-status', dependencies=[Depends(admin)])
def dataset_status():
    from ML.readiness import public_datasets

    return public_datasets()

@app.post('/api/admin/review',dependencies=[Depends(admin)])
def review_feedback(req:ReviewRequest):
    try:return adaptive.review(req.trace_id,req.label,req.reason,req.reviewer)
    except ValueError as e:raise HTTPException(422,str(e))

@app.post('/api/admin/train',dependencies=[Depends(admin)])
def train_candidate():
    raise HTTPException(409,'Archived GPT pilot training is disabled. Use the human-data experiment runner; support-routing training requires a verified human-reviewed CSV.')
    try:return adaptive.start_training()
    except ValueError as e:raise HTTPException(409,str(e))

@app.get('/api/admin/jobs/{job_id}',dependencies=[Depends(admin)])
def training_job(job_id:str):
    if job_id not in adaptive.jobs:raise HTTPException(404,'job not found; job status is session-local, completed reports persist')
    return adaptive.jobs[job_id]

@app.post('/api/admin/promote',dependencies=[Depends(admin)])
def promote_candidate(req:PromotionRequest):
    try:
        result=adaptive.trainer.promote(req.run_id)
        with adaptive.db() as db:
            import uuid
            from BACKEND.adaptive import now
            db.execute('INSERT INTO audit VALUES (?,?,?,?)',(uuid.uuid4().hex,'model_promotion',json.dumps(result),now()))
        return result
    except FileNotFoundError:raise HTTPException(404,'candidate not found')
    except ValueError as e:raise HTTPException(422,str(e))

@app.post('/api/admin/rollback',dependencies=[Depends(admin)])
def rollback_model():
    try:return adaptive.trainer.rollback()
    except ValueError as e:raise HTTPException(422,str(e))


@app.get("/api/disclaimer")
def disclaimer():
    return {"disclaimer": DISCLAIMER}


@app.get("/api/research/summary", dependencies=[Depends(admin)])
def r_summary():
    summary=research_summary(pipe.status())
    summary['prototype']=adaptive.analytics()
    rows=adaptive.trainer.data()['rows']
    from collections import Counter
    summary['prototype_data']={'archived':True,'total':len(rows),'agreed':sum(r['category'] is not None for r in rows),
        'unresolved':sum(r['category'] is None for r in rows),
        'splits':dict(Counter(r['split'] for r in rows if r['category'] is not None)),
        'categories':dict(Counter(r['category'] for r in rows if r['category'] is not None)),
        'provenance':'ARCHIVED GPT pilot; not active and not used for current research results.'}
    summary['runtime_status']=model_status()
    summary['document_status']=document_status()
    return summary


@app.get("/api/research/artifact", dependencies=[Depends(admin)])
def r_artifact(path: str = Query(min_length=1)):
    try:
        return read_artifact(path)
    except FileNotFoundError:
        raise HTTPException(404, "artifact not found")
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/api/research/traces", dependencies=[Depends(admin)])
def r_traces(limit: int = Query(100, ge=1, le=1000)):
    return list_traces(limit)


# UploadFile may use transient framework temp files, closed before processing. No raw uploads are retained.
from fastapi import UploadFile, File, Form

@app.get('/api/document-status')
def document_status():
    from ML.visual_support import available
    import importlib.util
    return {'ocr_available':importlib.util.find_spec('rapidocr_onnxruntime') is not None or __import__('BACKEND.documents',fromlist=['tesseract_available']).tesseract_available(),
            'pdf_available':importlib.util.find_spec('pypdfium2') is not None,'native_multilingual_ocr_available':__import__('BACKEND.documents',fromlist=['tesseract_available']).tesseract_available(),
            'vision_available':available(), 'max_upload_mb':25, 'storage':'transient_processing_no_retained_uploads'}

@app.post('/api/documents/extract')
async def document_extract(file:UploadFile=File(...), page:int=Form(1), force_ocr:bool=Form(False), language:str=Form('auto')):
    from BACKEND.documents import extract, MAX_UPLOAD
    from starlette.concurrency import run_in_threadpool
    data=await file.read(MAX_UPLOAD+1)
    await file.close()
    try: return await run_in_threadpool(extract,data,file.filename or '',page,force_ocr,language)
    except ValueError as e: raise HTTPException(422,str(e))
    except LookupError as e:raise HTTPException(503,str(e))
    except ImportError: raise HTTPException(503,'Document dependencies missing. Install BACKEND/requirements-documents.txt.')
    except Exception:
        import logging
        logging.exception('Page extraction failed')
        raise HTTPException(503,'Page extraction failed. Try a clearer or smaller file; inspect the helper terminal for setup problems.')

@app.post('/api/documents/explain')
async def document_explain(request:Request, file:UploadFile=File(...), question:str=Form('Explain this picture in simple language.'), style:str=Form('auto'), labels:str=Form(''), language:str=Form('en'), kind:str=Form('general'), session_id:str=Form('')):
    from BACKEND.documents import decode_image,MAX_UPLOAD
    from ML.visual_support import explain
    from starlette.concurrency import run_in_threadpool
    data=await file.read(MAX_UPLOAD+1)
    await file.close()
    if len(data)>MAX_UPLOAD: raise HTTPException(413,'Choose an image smaller than 25 MB.')
    if not 1<=len(question.strip())<=500: raise HTTPException(422,'Use a question between 1 and 500 characters.')
    if language not in {'en','hi','kn','ta'}:raise HTTPException(422,'Unsupported explanation language.')
    if len(labels)>5000 or style not in {'auto','short','steps','example'} or kind not in {'general','biology','graph','geometry'}: raise HTTPException(422,'Invalid visual explanation options.')
    try:
        image=decode_image(data)
        image.thumbnail((1600,1600))
        key=learner_key(request)
        adaptive.identity(key)
        consent_version=adaptive.consent_version(key)
        if style=='auto':style=adaptive.profile(key)['preferences'].get('VISUAL','short') if key else 'short'
        response=await run_in_threadpool(explain,image,question,labels,style,language,kind)
        response['trace_id']=adaptive.record_visual(key,style,question,response,consent_version)
        response['style']=style
        return response
    except ValueError as e: raise HTTPException(422,str(e))
    except LookupError as e: raise HTTPException(503,str(e))
    except ImportError: raise HTTPException(503,'Vision dependencies missing. Install BACKEND/requirements-documents.txt.')
    except Exception:
        import logging
        logging.exception('Visual inference failed')
        raise HTTPException(503,'Visual inference failed. Check the helper terminal and installed vision model.')

class VisualFeedbackRequest(BaseModel):
    trace_id:str=Field(min_length=32,max_length=32)
    decision:Literal['accept','reject']

@app.post('/api/documents/feedback')
def visual_feedback(req:VisualFeedbackRequest,request:Request):
    try:return adaptive.visual_feedback(learner_key(request),req.trace_id,req.decision)
    except ValueError as e:raise HTTPException(422,str(e))
    except LookupError as e:raise HTTPException(404,str(e))

class SurveyRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    consent:bool
    reading_settings:dict=Field(default_factory=dict)
    alias:str=Field(default='',max_length=60)
    preferred_language:Literal['en','hi','kn','ta']='en'
    study_languages:list[Literal['en','hi','kn','ta']]=Field(default_factory=lambda:['en'],min_length=1,max_length=4)
    preferred_style:Literal['short','steps','example']='short'
    difficulties:list[Literal['VOCABULARY','SYNTACTIC','CONCEPTUAL','PRONUNCIATION','VISUAL']]=Field(default_factory=list,max_length=5)

class SessionRequest(BaseModel):
    language:Literal['en','hi','kn','ta']
class EventRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    client_id:str=Field(min_length=16,max_length=64)
    session_id:str=Field(min_length=32,max_length=32)
    language:Literal['en','hi','kn','ta']
    kind:Literal['help_request','style_choice','reread','attention_return','dwell','undo','regenerate','settings_change','optional_feedback','session_end']
    payload:dict=Field(default_factory=dict)

@app.post('/api/learner/survey')
def learner_survey(req:SurveyRequest,request:Request):
    try:return learner.survey(learner_key(request),req.model_dump())
    except ValueError as e:raise HTTPException(422,str(e))
@app.get('/api/learner/state')
def learner_state(request:Request,language:Literal['en','hi','kn','ta']='en',span:str=Query('',max_length=300)):
    key=learner_key(request)
    if not key:return {'enrolled':False,'revision':0}
    try:return learner.state(key,language,span)
    except ValueError as e:raise HTTPException(422,str(e))
@app.get('/api/learner/report')
def learner_report(request:Request,response:Response):
    response.headers['Cache-Control']='no-store'
    try:return learner.report(learner_key(request))
    except ValueError as e:raise HTTPException(422,str(e))
    except LookupError as e:raise HTTPException(404,str(e))
@app.post('/api/learner/session')
def learner_session(req:SessionRequest,request:Request):
    try:return learner.start(learner_key(request),req.language)
    except ValueError as e:raise HTTPException(422,str(e))
@app.post('/api/learner/event')
def learner_event(req:EventRequest,request:Request):
    if len(json.dumps(req.payload))>5000:raise HTTPException(422,'Signal payload is too large.')
    try:return learner.record(learner_key(request),req.model_dump())
    except ValueError as e:raise HTTPException(422,str(e))
@app.get('/api/admin/learner-evidence',dependencies=[Depends(admin)])
def learner_evidence(response:Response,profile_id:str=Query('',max_length=64)):
    response.headers['Cache-Control']='no-store'
    try:return learner.dashboard(profile_id or None)
    except LookupError as e:raise HTTPException(404,str(e))

@app.get('/api/admin/learner-overview',dependencies=[Depends(admin)])
def learner_overview(response:Response):
    response.headers['Cache-Control']='no-store'
    return learner.overview()

class SupportRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    span:str=Field(min_length=1,max_length=300)
    text:str=Field(min_length=1,max_length=5000)
    span_start:Optional[int]=Field(default=None,ge=0)
    span_offset_unit:Literal['codepoint','utf16']='codepoint'
    request_id:Optional[str]=Field(default=None,min_length=16,max_length=64,pattern='^[a-zA-Z0-9_-]+$')
    variant:int=Field(default=0,ge=0,le=1)
    document_text:Optional[str]=Field(default=None,max_length=50000)
    category_override:Optional[Literal['VOCABULARY','SYNTACTIC','CONCEPTUAL','PRONUNCIATION','VISUAL']]=None
    support_style:Literal['auto','short','steps','example']='auto'
    response_mode:Literal['quick','local_ai','online_ai']='quick'
    cloud_consent:bool=False
    document_language:Literal['auto','en','hi','kn','ta']='auto'
    explanation_language:Literal['same','en','hi','kn','ta']='same'
    session_id:Optional[str]=Field(default=None,min_length=32,max_length=32)

class ParagraphSupportRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    paragraph:str=Field(min_length=1,max_length=3000)
    document_language:Literal['en','hi','kn','ta']='en'
    category:Literal['auto','VOCABULARY','SYNTACTIC','CONCEPTUAL']='auto'
    style:Literal['auto','short','steps','example']='auto'

@app.post('/api/paragraph-support')
def paragraph_support(req:ParagraphSupportRequest,request:Request):
    import re
    from ML.interventions import vocabulary,conceptual

    if not req.paragraph.strip():raise HTTPException(422,'Choose a paragraph with text.')
    key=learner_key(request)
    state=learner.state(key,req.document_language) if key else {'enrolled':False}
    category=req.category
    source='learner_choice' if category!='auto' else 'default_layout'
    if category=='auto' and state.get('enrolled'):
        history=learner.paragraph_requests(key,req.document_language,req.paragraph)
        scores=history['scores']
        ranked=sorted(scores,key=scores.get,reverse=True)
        first=ranked[0]
        if first in {'VOCABULARY','SYNTACTIC','CONCEPTUAL'} and history['counts'][first]>=2 and scores[first]-scores[ranked[1]]>=.35:
            category=first;source='learner_history'
        elif len(state['survey'].get('difficulties',[]))==1 and state['survey']['difficulties'][0] in {'VOCABULARY','SYNTACTIC','CONCEPTUAL'}:
            category=state['survey']['difficulties'][0];source='starting_survey'
    if category=='auto':category='SYNTACTIC'
    style=req.style if req.style!='auto' else state.get('preferred_style','short')
    sentences=[part for part in re.split(r'(?<=[.!?])(?=\s|$)',req.paragraph) if part]
    glossary=[]
    if category=='VOCABULARY' and req.document_language=='en':
        glossary=[{'word':operation['from'],'meaning':operation['to'].split(' (',1)[-1].removesuffix(')')}
                  for operation in vocabulary(req.paragraph)['operations'] if operation['rule']=='lexicon_gloss']
    prompts=conceptual(req.paragraph)['scaffold']['questions'] if category=='CONCEPTUAL' else []
    source_example=next((sentence.strip() for sentence in sentences if re.search(r'\b(for example|such as)\b',sentence,re.I)),None)
    return {'original':req.paragraph,'sentences':sentences,'category':category,'source':source,'style':style,
            'glossary':glossary,'prompts':prompts,'source_example':source_example,'text_changed':False,
            'note':'The original words and order are unchanged. Glossary notes are unreviewed; check them against the source.'}

@app.post('/api/paragraph-rewrite')
def paragraph_rewrite(req:ParagraphSupportRequest,request:Request):
    from ML.paragraph_rewrite import rewrite_paragraph

    selected=paragraph_support(req,request)
    rewritten=rewrite_paragraph(req.paragraph,selected['category'],req.document_language)
    return {**rewritten,'category':selected['category'],'source':selected['source']}

@app.post('/api/support')
def research_support(req:SupportRequest,request:Request):
    from ML.multilingual import detect,explanation
    from ML.context import build_context,codepoint_offset,span_offset_in_sentence
    if req.response_mode == 'online_ai':
        local_account_access(request)
        from ML.cloud_help import available as online_available
        if not req.cloud_consent:
            raise HTTPException(422, 'Confirm before sending this selected sentence to online AI.')
        if not online_available():
            raise HTTPException(503, 'Online AI is not configured. Local help is still available.')
    key=learner_key(request)
    try:
        offset=codepoint_offset(req.text,req.span_start,req.span_offset_unit)
        context=build_context(req.text,req.span,offset)
        language=detect(req.text) if req.document_language=='auto' else req.document_language
        target=language if req.explanation_language=='same' else req.explanation_language
        if req.category_override and key and learner.enrolled(key):
            learner.record(key,{'client_id':req.request_id or __import__('uuid').uuid4().hex,'session_id':req.session_id,'language':language,'kind':'help_request','payload':{'span':req.span,'category':req.category_override}})
        prediction=None
        try:
            from ML.public_experiment import predict_word
            prediction=predict_word(req.span,context['sentence']) if language=='en' and not req.category_override else None
        except (ImportError,LookupError,OSError,RuntimeError):pass
        from ML.routing_runtime import predict as routing_predict
        routing_prediction=routing_predict(req.span,req.text,language,offset) if not req.category_override else None
        route=learner.choose(key,req.session_id,language,req.span,req.category_override,req.support_style,prediction,routing_prediction,req.variant)
        local_offset=span_offset_in_sentence(req.text[:context['span_start']],req.span,req.text[context['span_end']:])
        if req.response_mode == 'online_ai':
            from ML.cloud_help import explain as online_explain
            try:
                help = online_explain(req.span, context['sentence'], route['selected'], route['style'], target, local_offset)
            except RuntimeError as error:
                help = explanation(req.span, context['sentence'], route['selected'], route['style'], language, target,
                                   span_start=local_offset, allow_generation=False)
                help['provider_status'] = str(error) + ' Local help is shown instead.'
        else:
            help=explanation(req.span,context['sentence'],route['selected'],route['style'],language,target,span_start=local_offset,allow_generation=req.response_mode=='local_ai')
        learner.record_quality(key,route['route_id'],{'available':help.get('available'), 'source':help.get('source'),'screening':help.get('quality',help.get('generation_checks')),'summary':str(help.get('summary',''))[:1000]})
        from ML.semantic_verifier import verify
        checks=verify(req.span,req.span)
        checks.update(status='review',flags=[{'check':'supplemental_explanation','note':'Original unchanged; additional explanation requires source checking.'}])
        return {'trace_id':route['route_id'],'routing':route,'research_mode':'learner_evidence','valid_for_research':False,
            'input':{'span':req.span,'sentence':context['sentence']},'category':{'category':route['selected'],'source':route['source'],'is_trained_model_output':route['source']=='human_routing_model', 'lexical_prediction_is_separate':bool(prediction),'needs_choice':route['needs_choice']},
            'explanation':help,'personalization':{'enabled':route['learner_state'].get('enrolled',False),'style':route['style'],'source':'survey_and_session_evidence'},
            'intervention':{'status':'no_change','reason':'Supplemental help; original source is retained.','word_diff':[]},'presentable':False,
            'comparison':{'original':req.span,'original_sentence':context['sentence'],'adapted':req.span,'adapted_sentence':context['sentence']},'verification':checks,'document_language':language,'explanation_language':target}
    except HTTPException:raise
    except ValueError as e:raise HTTPException(422,str(e))
    except Exception:
        import logging
        logging.exception('Localized support failed')
        raise HTTPException(503,'Support model unavailable. Check the helper setup; the original is unchanged.')

class SpeechRequest(BaseModel):
    text:str=Field(min_length=1,max_length=400)
    language:Literal['en','hi','kn','ta']
@app.post('/api/speech')
def local_speech(req:SpeechRequest):
    from ML.multilingual import speech
    from fastapi.responses import Response
    try:return Response(speech(req.text,req.language),media_type='audio/wav',headers={'Cache-Control':'no-store'})
    except LookupError as e:raise HTTPException(503,str(e))
    except Exception:
        import logging
        logging.exception('Offline speech failed')
        raise HTTPException(503,'Speech failed. Check the language-model setup.')

PUBLIC_JOBS={}
PUBLIC_JOB_LOCK=__import__('threading').Lock()
class PublicExperimentRequest(BaseModel):
    max_train:int=Field(default=512,ge=128,le=7662)
    epochs:int=Field(default=2,ge=1,le=10)
@app.get('/api/admin/research-evidence',dependencies=[Depends(admin)])
def current_research_evidence():
    from ML.public_experiment import reports
    path=ROOT/'DATA/public_sources.json'
    return {'sources':json.loads(path.read_text(encoding="utf-8")) if path.exists() else {'sources':[]},'lexical_runs':reports(),
            'routing_status':'EVALUATED_HUMAN_ROUTING_ACTIVE' if (ROOT/'ARTIFACTS/human_routing_active.json').exists() else 'HUMAN_REVIEWED_ROUTING_LABELS_REQUIRED','synthetic_active_model':False,
            'approved_languages':['en','hi','kn','ta'],'routing_runs':[json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT/'ARTIFACTS/routing_comparison').glob('*/comparison.json'))],'routing_active':json.loads((ROOT/'ARTIFACTS/human_routing_active.json').read_text(encoding="utf-8")) if (ROOT/'ARTIFACTS/human_routing_active.json').exists() else None}
@app.post('/api/admin/public-experiment',dependencies=[Depends(admin)])
def start_public_experiment(req:PublicExperimentRequest):
    import subprocess,sys,threading,uuid
    with PUBLIC_JOB_LOCK:
        if any(j['status']=='running' for j in PUBLIC_JOBS.values()):raise HTTPException(409,'A comparison is already running.')
        jid=uuid.uuid4().hex;directory=ROOT/'ARTIFACTS/public_jobs';directory.mkdir(parents=True,exist_ok=True);log=directory/(jid+'.log')
        PUBLIC_JOBS[jid]={'job_id':jid,'status':'running','progress':None}
    def work():
        try:
            with log.open('w') as output:
                child=subprocess.Popen([sys.executable,'-m','ML.public_experiment','--max-train',str(req.max_train),'--epochs',str(req.epochs)],cwd=ROOT,stdout=output,stderr=output)
                while child.poll() is None:
                    lines=log.read_text(errors='replace').splitlines()
                    for line in reversed(lines):
                        try:
                            value=json.loads(line)
                            if isinstance(value,dict) and 'stage' in value:PUBLIC_JOBS[jid]['progress']=value;break
                        except ValueError:pass
                    __import__('time').sleep(1)
                PUBLIC_JOBS[jid]['status']='completed' if child.returncode==0 else 'failed'
                PUBLIC_JOBS[jid]['exit_code']=child.returncode
            (directory/(jid+'.json')).write_text(json.dumps(PUBLIC_JOBS[jid]), encoding="utf-8")
        except Exception as e:PUBLIC_JOBS[jid].update(status='failed',error=str(e))
    threading.Thread(target=work,daemon=True).start();return PUBLIC_JOBS[jid]
@app.get('/api/admin/public-jobs/{job_id}',dependencies=[Depends(admin)])
def public_job(job_id:str):
    if job_id not in PUBLIC_JOBS:
        if not __import__('re').fullmatch('[a-f0-9]{32}',job_id):raise HTTPException(404,'Job not found')
        path=ROOT/'ARTIFACTS/public_jobs'/(job_id+'.json')
        if path.exists():return json.loads(path.read_text(encoding="utf-8"))
        raise HTTPException(404,'Job status unavailable after restart; saved experiment reports remain available.')
    return PUBLIC_JOBS[job_id]

@app.post('/api/admin/routing-data',dependencies=[Depends(admin)])
async def import_human_routing(file:UploadFile=File(...)):
    import io,hashlib,pandas as pd
    data=await file.read(3*1024*1024+1);await file.close()
    if len(data)>3*1024*1024:raise HTTPException(413,'Reviewed CSV exceeds 3 MB.')
    try:
        df=pd.read_csv(io.BytesIO(data))
        from ML.data_validation import check
        rep=check(df,'research')
        errors=list(rep.errors)
        if 'annotation_type' not in df or not df.annotation_type.eq('HUMAN_REVIEWED').all():errors.append('Explicit HUMAN_REVIEWED annotation_type is required.')
        if 'language' not in df or not df.language.isin(['en','hi','kn','ta']).all():errors.append('A supported language is required on every row.')
        if 'rationale' in df and df.rationale.fillna('').str.strip().eq('').any():errors.append('Human review reasons must not be empty.')
        if errors:raise ValueError('; '.join(errors))
        digest=hashlib.sha256(data).hexdigest();folder=ROOT/'DATA/human_routing';folder.mkdir(exist_ok=True)
        path=folder/(digest+'.csv');path.write_bytes(data)
        return {'dataset_id':digest,'rows':len(df),'unresolved_rows':int(df.category.eq('OTHER_UNCERTAIN').sum()),'warnings':rep.warnings,'note':'Provenance is reviewer-declared; importing does not independently authenticate who annotated it. Unresolved rows are preserved and excluded from 3-category training.'}
    except Exception as e:raise HTTPException(422,str(e))

class RoutingTrainingRequest(BaseModel):
    dataset_id:str=Field(min_length=64,max_length=64,pattern='^[a-f0-9]+$')
    epochs:int=Field(default=4,ge=1,le=10)
@app.post('/api/admin/routing-comparison',dependencies=[Depends(admin)])
def start_routing_comparison(req:RoutingTrainingRequest):
    import pandas as pd,subprocess,sys,uuid,threading
    path=ROOT/'DATA/human_routing'/(req.dataset_id+'.csv')
    if not path.exists():raise HTTPException(404,'Reviewed dataset not found.')
    df=pd.read_csv(path)
    agreed=df.loc[df.category.ne('OTHER_UNCERTAIN')]
    if set(agreed.category)!= {'VOCABULARY','SYNTACTIC','CONCEPTUAL'}:raise HTTPException(422,'Agreed examples for all three categories are required.')
    training=path.with_name(req.dataset_id+'.agreed.csv')
    if not training.exists():agreed.to_csv(training,index=False)
    with PUBLIC_JOB_LOCK:
        if any(j['status']=='running' for j in PUBLIC_JOBS.values()):raise HTTPException(409,'A comparison is already running.')
        jid=uuid.uuid4().hex;directory=ROOT/'ARTIFACTS/public_jobs';directory.mkdir(exist_ok=True);log=directory/(jid+'.log')
        PUBLIC_JOBS[jid]={'job_id':jid,'status':'running','task':'human_support_routing','progress':None}
    def work():
        try:
            with log.open('w',encoding='utf-8') as output:
                child=subprocess.Popen([sys.executable,'-m','ML.routing_comparison','--csv',str(training),'--epochs',str(req.epochs)],cwd=ROOT,stdout=output,stderr=output)
                code=child.wait()
            PUBLIC_JOBS[jid].update(status='completed' if code==0 else 'failed',exit_code=code)
        except Exception as error:PUBLIC_JOBS[jid].update(status='failed',error=type(error).__name__+': '+str(error))
        finally:(directory/(jid+'.json')).write_text(json.dumps(PUBLIC_JOBS[jid]),encoding='utf-8')
    threading.Thread(target=work,daemon=True).start();return PUBLIC_JOBS[jid]

@app.post('/api/admin/routing-activate/{run_id}',dependencies=[Depends(admin)])
def activate_human_routing(run_id:str):
    from ML.routing_runtime import activate
    try:return activate(run_id)
    except ValueError as e:raise HTTPException(422,str(e))

@app.get('/api/admin/public-materials',dependencies=[Depends(admin)])
def public_materials(language:Literal['hi','kn','ta']='hi',limit:int=Query(5,ge=1,le=20)):
    from ML.public_materials import native_examples
    try:return {'examples':native_examples(language,limit),'use':'Public comprehension material, not student results or routing labels'}
    except LookupError as e:raise HTTPException(503,str(e))


@app.get('/api/review/public-pool')
def review_pool():
    from ML.human_review import pool
    return pool()


@app.post('/api/admin/reviews/merge',dependencies=[Depends(admin)])
async def merge_reviews(files:list[UploadFile]=File(...)):
    from ML.human_review import merge
    try:
        if not 2<=len(files)<=8:raise ValueError('Choose 2–8 independent JSON exports.')
        exports=[];total=0
        for upload in files:
            raw=await upload.read(3*1024*1024+1);total+=len(raw)
            if len(raw)>3*1024*1024 or total>8*1024*1024:raise ValueError('Review uploads exceed the 3 MB per file / 8 MB total limit.')
            exports.append(json.loads(raw.decode('utf-8-sig')))
        return merge(exports)
    except (ValueError,UnicodeError) as e:raise HTTPException(422,str(e))
    finally:
        for upload in files:await upload.close()


@app.get('/api/admin/review-results/{review_id}/{filename}',dependencies=[Depends(admin)])
def review_result(review_id:str,filename:str):
    from fastapi.responses import FileResponse
    import re
    if not re.fullmatch('[a-f0-9]{32}',review_id) or filename not in {'merged.csv','reviewed.csv','report.json','raw-exports.json'}:raise HTTPException(404,'Review artifact not found.')
    path=ROOT/'ARTIFACTS/human_review'/review_id/filename
    if not path.is_file():raise HTTPException(404,'Review artifact not found.')
    return FileResponse(path,filename=filename,headers={'Cache-Control':'no-store'})

app.mount("/", StaticFiles(directory=ROOT / "FRONTEND", html=True), name="frontend")
