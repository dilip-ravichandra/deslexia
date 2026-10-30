import json
from pathlib import Path
import pytest
from ML.multilingual import detect,script_ok
from ML.public_experiment import prepare
from ML.public_materials import native_examples
from ML.routing_runtime import activate
ROOT=Path(__file__).resolve().parents[1]
def test_language_detection_ignores_small_ocr_script_noise():
 assert detect('Kleene Closure special notes. An infinite set of all words. ನನ್ನ')=='en'
 assert detect('विद्यालय में बच्चे पढ़ते हैं।')=='hi'
 assert detect('हाँ')=='hi'
 assert detect('ಕನ್ನಡದಲ್ಲಿ ಓದಲು ಸುಲಭವಾಗಿದೆ.')=='kn'
 assert detect('தமிழில் படிக்க எளிது.')=='ta'

def test_script_guard_does_not_accept_an_english_answer_with_native_prefix():
 assert script_ok('पौधों को पानी चाहिए।','hi')
 assert not script_ok('ನೀರು This is a long answer in English with an unrelated native word.','kn')
 assert not script_ok('Tamil means this English response is valid.','ta')
 assert not script_ok('','en')
def test_frozen_public_data_has_no_context_overlap_or_synthetic_rows():
 data,manifest=prepare(512);groups=[{r['sentence'].strip().casefold() for r in data[k]} for k in ['train','validation','test']]
 assert not groups[0]&groups[1];assert not groups[0]&groups[2];assert not groups[1]&groups[2];assert manifest['synthetic_rows']==0
 assert manifest['partitions']['train']==json.loads((ROOT/'DATA/human_lexical_split_512.json').read_text(encoding="utf-8"))['partitions']['train']
@pytest.mark.parametrize('language',['hi','kn','ta'])
def test_native_public_qa_answers_remain_source_spans(language):
 rows=native_examples(language,10);assert len(rows)==10
 for row in rows:
  assert row['license']=='CC-BY-4.0'
  assert row['reference_quality']['all_answer_texts_found']==all(a['text'] in row['context'] for a in row['answers'])
def test_missing_human_run_cannot_be_activated():
 with pytest.raises(ValueError):activate('0'*32)
