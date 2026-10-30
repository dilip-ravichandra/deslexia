"""Import two GPT passes per pilot, freeze document partitions, train local baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from ML.prototype import PrototypeTrainer

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def read_xlsx(path):
    with zipfile.ZipFile(path) as archive:
        shared=[''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in archive.namelist() else []
        rows=[]
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//m:row',NS):
            record={}
            for cell in row.findall('m:c',NS):
                value=cell.find('m:v',NS);text=value.text if value is not None else ''
                if cell.get('t')=='s':text=shared[int(text)]
                elif cell.get('t')=='inlineStr':text=''.join(cell.find('m:is',NS).itertext())
                record[''.join(filter(str.isalpha,cell.get('r')))]=text
            rows.append(record)
        return rows[1:]

def create_data(pairs,root):
    rows=[];sources=[]
    for pilot,a_path,b_path in pairs:
        a,b=read_xlsx(a_path),read_xlsx(b_path);lookup={r['K']:r for r in b}
        docs=sorted({r['J'] for r in a},key=lambda d:hashlib.sha256(f'DyslexiAdapt-pilot{pilot}-split-v1|{d}'.encode()).hexdigest())
        n_train=int(len(docs)*0.6);n_val=int(len(docs)*0.2)
        assignment={d:'TRAIN' if i<n_train else 'VALIDATION' if i<n_train+n_val else 'TEST' for i,d in enumerate(docs)}
        sources += [{'file':Path(p).name,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in [a_path,b_path]]
        for arow in a:
            brow=lookup[arow['K']]
            if any(arow.get(c)!=brow.get(c) for c in ['A','B','C','J','Q','R']):raise ValueError('Examples differ')
            agreed=arow['D']==brow['D']
            rows.append({'text':arow['A'],'context_before':arow['B'],'context_after':arow['C'],
                'document_text':arow['B']+arow['A']+arow['C'],'document_id':arow['J'],'span_id':arow['K'],
                'category':arow['D'] if agreed else None,'pass_a_label':arow['D'],'pass_b_label':brow['D'],
                'pass_a_rationale':arow['F'],'pass_b_rationale':brow['F'],'agreement_status':'AGREED' if agreed else 'UNRESOLVED',
                'split':assignment[arow['J']],'pilot':pilot,'source_type':'AI_GENERATED_PRACTICE',
                'annotation_provenance':'TWO_GPT_PASSES','data_status':'AI_WEAK_LABEL_PROTOTYPE'})
    path=Path(root)/'DATA'/'prototype_pilots.json'
    if path.exists():raise ValueError('Frozen data already exists; do not overwrite splits')
    path.write_text(json.dumps({'rows':rows,'sources':sources,'valid_for_scientific_claims':False,
        'split_rule':'Per-pilot SHA256 document ordering, 60/20/20; Pilot 2 matches previously prepared split.',
        'note':'Both annotator passes are GPT-generated, per the user correction. No human agreement claimed.'},indent=2), encoding="utf-8")
    return path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot2-a',required=True);parser.add_argument('--pilot2-b',required=True);parser.add_argument('--pilot3-a',required=True);parser.add_argument('--pilot3-b',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    create_data([(2,args.pilot2_a,args.pilot2_b),(3,args.pilot3_a,args.pilot3_b)],root)
    trainer=PrototypeTrainer(root);report=trainer.train();trainer.promote(report['run_id']);test=trainer.initial_test()
    print(json.dumps({'run':report,'initial_test':test},indent=2))

if __name__=='__main__':main()
