"""Conservative, inspectable paragraph rewrites for the reader."""
import re
from collections import Counter
from difflib import SequenceMatcher

from ML.interventions import syntactic, vocabulary
from ML.semantic_verifier import verify


PROTECTED = {
    'if', 'unless', 'because', 'although', 'though', 'despite', 'therefore',
    'however', 'before', 'after', 'when', 'while', 'which', 'who', 'whose',
    'and', 'or', 'but', 'not', 'no', 'never', 'only', 'all', 'some',
    'every', 'each', 'may', 'might', 'must', 'can', 'cannot', 'could', 'should',
}


def protected_words(text):
    return Counter(word.casefold() for word in re.findall(r"[A-Za-z]+", text)
                   if word.casefold() in PROTECTED)


def diff_parts(original, adapted):
    original_tokens = re.findall(r'\w+|[^\w\s]+|\s+', original)
    adapted_tokens = re.findall(r'\w+|[^\w\s]+|\s+', adapted)
    original_parts = []
    adapted_parts = []
    for operation, original_start, original_end, adapted_start, adapted_end in SequenceMatcher(
            None, original_tokens, adapted_tokens, autojunk=False).get_opcodes():
        if original_start != original_end:
            original_parts.append({'text': ''.join(original_tokens[original_start:original_end]),
                                   'changed': operation != 'equal'})
        if adapted_start != adapted_end:
            adapted_parts.append({'text': ''.join(adapted_tokens[adapted_start:adapted_end]),
                                  'changed': operation != 'equal'})
    return original_parts, adapted_parts


def rewrite_paragraph(paragraph, category, language='en'):
    sentences = []
    for part in re.split(r'(?<=[.!?])(?=\s|$)', paragraph):
        if not part:
            continue
        leading = part[:len(part) - len(part.lstrip())]
        trailing = part[len(part.rstrip()):]
        original = part.strip()
        candidate = original
        reason = 'No safe wording change was available.'
        checks = None
        if original and language == 'en':
            if category == 'SYNTACTIC':
                intervention = syntactic(original)
                if intervention['status'] == 'applied':
                    candidate = intervention['adapted']
            elif category == 'VOCABULARY':
                intervention = vocabulary(original, variant=1)
                if intervention['operations'] and all(operation['rule'] == 'lexicon_replace'
                                                       for operation in intervention['operations']):
                    candidate = intervention['adapted']
            elif category == 'CONCEPTUAL':
                reason = 'Idea support uses questions; no reliable wording change was available.'
        elif language != 'en':
            reason = 'Automatic wording changes are currently limited to English.'
        if candidate != original:
            checks = verify(original, candidate)
            if protected_words(original) != protected_words(candidate):
                reason = 'A condition, qualifier, or relationship word would change.'
            elif checks['status'] != 'pass':
                reason = 'An automatic meaning check raised a flag.'
            else:
                reason = 'Passed limited automatic checks; compare it with the original.'
                rewritten = leading + candidate + trailing
                original_parts, adapted_parts = diff_parts(part, rewritten)
                sentences.append({'original': part, 'adapted': rewritten, 'changed': True,
                                  'reason': reason, 'checks': checks,
                                  'original_parts': original_parts, 'adapted_parts': adapted_parts})
                continue
        original_parts, adapted_parts = diff_parts(part, part)
        sentences.append({'original': part, 'adapted': part, 'changed': False,
                          'reason': reason, 'checks': checks,
                          'original_parts': original_parts, 'adapted_parts': adapted_parts})
    return {'original': paragraph, 'adapted': ''.join(sentence['adapted'] for sentence in sentences),
            'sentences': sentences, 'changed_count': sum(sentence['changed'] for sentence in sentences),
            'meaning_preservation_guaranteed': False,
            'note': 'Only deterministic changes that pass limited automatic checks appear. Checks can miss meaning errors; compare every change with the original.'}
