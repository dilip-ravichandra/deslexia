"""Finite source checks. Passing a screen is not proof of semantic entailment."""
import hashlib
import json
import re
import unicodedata

PROTOCOL = 'source-claims-v1'
SCHEMA = {'type':'object','properties':{'claims':{'type':'array','minItems':0,'maxItems':2,'items':{
    'type':'object','properties':{'text':{'type':'string'},'evidence':{'type':'string'},'source':{'type':'string','enum':['passage','notes']}},
    'required':['text','evidence','source'],'additionalProperties':False}}},'required':['claims'],'additionalProperties':False}
PATTERNS = {
    'negation': {
        'en':r'\b(?:not|never|no|cannot|without|unless)\b|n.t\b',
        'hi':r'नहीं|नही|मत|बिना', 'kn':r'ಇಲ್ಲ|ಅಲ್ಲ|ಬೇಡ|ವಿನಾ', 'ta':r'இல்லை|அல்ல|கூடாது|இன்றி'},
    'temperature': {
        'en':r'\b(?:temperature|heated|heating|boiling|hotter)\b', 'hi':r'तापमान|उच्च ताप|गरम|गर्म',
        'kn':r'ತಾಪಮಾನ|ಬಿಸಿ', 'ta':r'வெப்பநிலை|சூடா'},
    'condition': {
        'en':r'\b(?:only if|must|requires?|always|guaranteed|necessarily)\b', 'hi':r'केवल|जरूर|ज़रूर|अनिवार्य|हमेशा',
        'kn':r'ಮಾತ್ರ|ಕಡ್ಡಾಯ|ಯಾವಾಗಲೂ', 'ta':r'மட்டும்|கட்டாய|எப்போதும்'}
}

def quantities(text):
    normalized=''.join(str(unicodedata.digit(c)) if c.isdecimal() else c for c in text)
    return set(re.findall(r'\d+(?:[.,]\d+)*',normalized))

def screen(raw, passage, notes, language):
    from ML.multilingual import script_ok
    flags=[];claims=[]
    try:
        value=json.loads(raw)
        if not isinstance(value,dict) or set(value)!={'claims'}:raise ValueError()
        claims=value['claims']
        if not isinstance(claims,list) or not 1<=len(claims)<=2:raise ValueError()
        for claim in claims:
            if not isinstance(claim,dict) or set(claim)!={'text','evidence','source'}:raise ValueError()
            if not all(isinstance(claim[k],str) for k in claim):raise ValueError()
            if not 4<=len(claim['text'].strip())<=1200 or not 4<=len(claim['evidence'].strip())<=2200:raise ValueError()
            if claim['source'] not in {'passage','notes'}:raise ValueError()
    except (ValueError,TypeError):
        flags.append('invalid_claim_structure');claims=[]
    for claim in claims:
        text=claim['text'];evidence=claim['evidence'];source=passage if claim['source']=='passage' else notes
        if evidence not in source:flags.append('evidence_not_in_source')
        if not script_ok(text,language):flags.append('wrong_language_script')
        if quantities(text)-quantities(evidence):flags.append('introduced_quantity')
        # Quotes must retain qualifiers when the claim paraphrases their meaning.
        for kind,patterns in PATTERNS.items():
            pattern=patterns[language]
            in_claim=bool(re.search(pattern,text,re.I));in_evidence=any(re.search(p,evidence,re.I) for p in patterns.values())
            if kind=='negation' and in_evidence and not in_claim:flags.append('lost_negation')
            if kind!='negation' and in_claim and not in_evidence:flags.append('introduced_'+kind)
    return {'protocol':PROTOCOL,'status':'rejected' if flags else 'screened','flags':sorted(set(flags)),
            'meaning_guaranteed':False,'claims':claims if not flags else [],
            'draft_sha256':hashlib.sha256(raw.encode()).hexdigest(),
            'note':'Exact quotations and finite pattern checks do not prove entailment, naturalness or educational quality.'}
