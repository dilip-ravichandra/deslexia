"""Publisher-provided native QA material, never relabelled as support routing."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def native_examples(language,limit=10):
 if language not in {'hi','kn','ta'}:raise ValueError('IndicQA is available here for Hindi, Kannada and Tamil.')
 path=ROOT/'DATA/public/IndicQA/data'/('indicqa.'+language+'.json')
 if not path.exists():raise LookupError('Verified public material is not installed.')
 source=json.loads(path.read_text(encoding="utf-8"));rows=[]
 for document in source['data']:
  for paragraph in document['paragraphs']:
   for question in paragraph['qas']:
    rows.append({'id':str(question['id']),'context':paragraph['context'],'question':question['question'],'answers':question['answers'],'reference_quality':{'all_answer_texts_found':all(a['text'] in paragraph['context'] for a in question['answers']),'all_offsets_match':all(isinstance(a.get('answer_start'),int) and paragraph['context'][a['answer_start']:a['answer_start']+len(a['text'])]==a['text'] for a in question['answers'])},'language':language,'source':'ai4bharat/IndicQA','license':'CC-BY-4.0','annotation':'Published expert-generated extractive QA; not dyslexia participants or support-routing labels'})
    if len(rows)>=limit:return rows
 return rows
