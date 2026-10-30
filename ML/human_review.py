"""Independent manual review import and immutable merge. No generated judgments."""
import csv
import hashlib
import io
import itertools
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POOL=ROOT/'DATA/human_routing/public_100_REVIEW_REQUIRED.csv'
LABELS={'VOCABULARY','SYNTACTIC','CONCEPTUAL','OTHER_UNCERTAIN'}
MUTABLE={'category','annotator_id','confidence','rationale','created_at','annotation_type','guideline_version'}

def pool(path=None):
    raw=(path or POOL).read_bytes()
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    columns=[c for c in rows[0] if c not in MUTABLE]
    return {'protocol':'independent-routing-v1','sha256':hashlib.sha256(raw).hexdigest(),
            'source_columns':columns,'rows':[{k:r[k] for k in columns} for r in rows]}

def timestamp(value):
    if not isinstance(value,str):raise ValueError('A timezone-aware review timestamp is required.')
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('Invalid review timestamp.') from None
    if parsed.tzinfo is None:raise ValueError('Review timestamps must include a timezone.')
    return parsed

def validate(export, source):
    if not isinstance(export,dict):raise ValueError('Each export must be a JSON object.')
    if export.get('protocol')!=source['protocol'] or export.get('source_pool_sha256')!=source['sha256']:raise ValueError('Export belongs to a different source pool or protocol.')
    reviewer=export.get('reviewer_id','')
    if not isinstance(reviewer,str) or not re.fullmatch(r'[A-Za-z0-9_-]{2,60}',reviewer):raise ValueError('Use a reviewer code of 2–60 letters, digits, underscores or hyphens.')
    if reviewer.casefold() in {'ai','gpt','claude','llm','model','synthetic','seed'}:raise ValueError('Model/fixture identifiers cannot be human reviewers.')
    if export.get('independent_review') is not True or export.get('language_competent') is not True:raise ValueError('Independent review and language competence declarations are required.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,64}',str(export.get('session_id',''))):raise ValueError('Invalid review session identifier.')
    language=export.get('language')
    if not isinstance(language,str) or language not in {'en','hi','kn','ta'}:raise ValueError('Unsupported review language.')
    started=timestamp(export.get('started_at'));submitted=timestamp(export.get('submitted_at'))
    if started>submitted or submitted>datetime.now(timezone.utc):raise ValueError('Review times must be ordered and cannot be in the future.')
    judgments=export.get('judgments')
    if not isinstance(judgments,list) or not 1<=len(judgments)<=len(source['rows']):raise ValueError('Export must contain completed judgments.')
    originals={r['span_id']:r for r in source['rows']};seen=set();clean=[]
    for judgment in judgments:
        if not isinstance(judgment,dict):raise ValueError('Invalid judgment structure.')
        sid=judgment.get('span_id')
        if not isinstance(sid,str) or sid not in originals or sid in seen:raise ValueError('Unknown or duplicate span decision.')
        seen.add(sid);row=originals[sid]
        if row['language']!=language or judgment.get('source')!=row:raise ValueError('Source columns or language changed during review.')
        if not isinstance(judgment.get('category'),str) or judgment['category'] not in LABELS:raise ValueError('Unknown routing category.')
        confidence=judgment.get('confidence')
        if isinstance(confidence,bool) or not isinstance(confidence,int) or not 1<=confidence<=5:raise ValueError('Confidence must be an integer from 1 to 5.')
        reason=judgment.get('rationale')
        if not isinstance(reason,str) or not 3<=len(reason.strip())<=2000:raise ValueError('A short human reason is required (3–2000 characters).')
        reviewed=timestamp(judgment.get('reviewed_at'))
        if not started<=reviewed<=submitted:raise ValueError('Decision time must fall within its review session.')
        clean.append({**judgment,'reviewer_id':reviewer,'language':language,'session_id':export['session_id']})
    return clean

def merge(exports, directory=None, pool_path=None):
    if not 2<=len(exports)<=8:raise ValueError('Provide 2–8 independent reviewer exports.')
    source=pool(pool_path);decisions=[];reviewers=set()
    for export in exports:
        reviewed=validate(export,source)
        # One export per reviewer/language, even if the same reviewer covers several languages.
        key=(export['reviewer_id'].casefold(),export['language'])
        if key in reviewers:raise ValueError('Duplicate reviewer/language export; export the latest complete file once.')
        reviewers.add(key);decisions.extend(reviewed)
    by_span={}
    for d in decisions:by_span.setdefault(d['span_id'],[]).append(d)
    original=list(csv.DictReader(io.StringIO((pool_path or POOL).read_text(encoding='utf-8-sig'))))
    merged=[];counts={};paired={l:[] for l in ['en','hi','kn','ta']}
    for row in original:
        opinions=by_span.get(row['span_id'],[]);labels={d['category'] for d in opinions}
        status='agreed' if len(opinions)>=2 and len(labels)==1 else 'disagreement' if len(labels)>1 else 'missing_second_review' if opinions else 'unreviewed'
        category=next(iter(labels)) if status=='agreed' else 'OTHER_UNCERTAIN'
        counts[status]=counts.get(status,0)+1
        row.update(category=category,annotator_id='|'.join(sorted(d['reviewer_id'] for d in opinions)),
            confidence=min((d['confidence'] for d in opinions),default=''),
            rationale=' | '.join(d['reviewer_id']+': '+d['rationale'] for d in opinions),
            created_at=max((d['reviewed_at'] for d in opinions),default=''),guideline_version=source['protocol'],
            annotation_type='HUMAN_REVIEWED' if len(opinions)>=2 else 'REVIEW_INCOMPLETE',review_status=status)
        merged.append(row)
        if len(opinions)>=2:paired[row['language']].append(opinions)
    from ML.agreement import cohen_kappa
    agreement={}
    for language,groups in paired.items():
        pairwise=[];ids=sorted({d['reviewer_id'] for group in groups for d in group})
        for a,b in itertools.combinations(ids,2):
            pairs=[]
            for group in groups:
                labels={d['reviewer_id']:d['category'] for d in group}
                if a in labels and b in labels:pairs.append((labels[a],labels[b]))
            pairwise.append({'reviewers':[a,b],'n':len(pairs),'cohen_kappa':cohen_kappa([p[0] for p in pairs],[p[1] for p in pairs]) if pairs else None})
        agreement[language]={'multi_reviewed_rows':len(groups),'unanimous_fraction':sum(len({d['category'] for d in g})==1 for g in groups)/len(groups) if groups else None,'pairwise':pairwise}
    review_id=uuid.uuid4().hex
    target=(directory or ROOT/'ARTIFACTS/human_review')/review_id;target.mkdir(parents=True,exist_ok=False)
    def write_csv(name,rows):
        with (target/name).open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(merged[0]));writer.writeheader();writer.writerows(rows)
    write_csv('merged.csv',merged)
    # Incomplete rows stay in the archive, never receive invented reviewer provenance.
    write_csv('reviewed.csv',[r for r in merged if r['review_status'] in {'agreed','disagreement'}])
    report={'review_id':review_id,'source_pool_sha256':source['sha256'],'counts':counts,'agreement':agreement,
            'note':'Declarations do not authenticate people. Undefined agreement remains null. No training or activation was performed.'}
    (target/'raw-exports.json').write_text(json.dumps(exports,ensure_ascii=True,indent=2),encoding='utf-8')
    (target/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
