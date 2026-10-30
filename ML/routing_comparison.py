"""The agreed 3-way support-routing experiment. Requires genuine reviewed data."""
import json,uuid
from pathlib import Path
import pandas as pd
from ML.data_validation import check,file_sha256
from ML.group_split import freeze,load_frozen
ROOT=Path(__file__).resolve().parents[1]

def run(csv_path,manifest_path=None,epochs=4):
    csv_path=Path(csv_path);df=pd.read_csv(csv_path)
    report=check(df,'research')
    if not report.ok:raise ValueError('; '.join(report.errors))
    if 'annotation_type' not in df or not df.annotation_type.eq('HUMAN_REVIEWED').all():raise ValueError('Explicit HUMAN_REVIEWED provenance is required; learner requests alone are not gold labels.')
    if 'language' not in df or not df.language.isin(['en','hi','kn','ta']).all():raise ValueError('Each reviewed row requires its language.')
    if df['category'].eq('OTHER_UNCERTAIN').any():raise ValueError('Preserve unresolved rows in the review archive, not in the 3-category training CSV.')
    if manifest_path is None:
        manifest_path=csv_path.with_suffix('.split.json')
        if not manifest_path.exists():freeze(csv_path,manifest_path)
    load_frozen(manifest_path,csv_path)
    run_id=uuid.uuid4().hex;directory=ROOT/'ARTIFACTS/routing_comparison'/run_id;directory.mkdir(parents=True)
    print(json.dumps({'run_id':run_id,'stage':'started','dataset_sha256':file_sha256(csv_path)}),flush=True)
    from ML.multilingual import models
    backbone=models()/'distilmbert'
    if not (backbone/'model.safetensors').exists():raise LookupError('Pinned multilingual DistilBERT is missing.')
    from ML.baselines import run as baselines
    from ML.distilbert_trainer import run as transformer
    baseline=baselines(csv_path,directory/'tfidf',manifest_path=manifest_path)
    print(json.dumps({'run_id':run_id,'stage':'tfidf_completed'}),flush=True)
    plain=transformer(csv_path,directory/'distilbert',manifest_path=manifest_path,model_name=str(backbone),offline=True,epochs=epochs,arch='fusion_off',batch_size=8)
    print(json.dumps({'run_id':run_id,'stage':'distilbert_completed'}),flush=True)
    fused=transformer(csv_path,directory/'distilbert_features',manifest_path=manifest_path,model_name=str(backbone),offline=True,epochs=epochs,arch='fusion_on',batch_size=8)
    summary={'run_id':run_id,'task':'Human-reviewed 3-category support routing','dataset_sha256':file_sha256(csv_path),'split_manifest':str(manifest_path),'matched_transformer_heads':True,'checkpoint':'distilbert/distilbert-base-multilingual-cased','synthetic_rows':0,'baseline':baseline,'distilbert':plain,'distilbert_features':fused,'test_used_for_selection':False}
    (directory/'comparison.json').write_text(json.dumps(summary,indent=2), encoding="utf-8");return summary

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--manifest');p.add_argument('--epochs',type=int,default=4);a=p.parse_args();print(json.dumps(run(a.csv,a.manifest,a.epochs),indent=2))
