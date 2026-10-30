"""Targeted, rule-based interventions with full change tracking (Task 09).

VOCABULARY  -> gloss (keep word + plain-language meaning) or in-place replacement, from a lexicon
SYNTACTIC   -> conservative sentence splitting (concessive, semicolon, comma+conjunction, trailing
               'which' clause) or layout-only chunking
CONCEPTUAL  -> bulleted steps when sequence cues exist, plus a reading scaffold (questions + key
               terms extracted from the text). No explanation text is invented.

HONEST LIMITS
- Everything here is deterministic, rule-based ("rule_based_v1"). It is NOT a trained model and not
  an LLM. Conceptual support is scaffolding, not an explanation of the idea.
- The shipped lexicon is a small DEMO resource (DATA/lexicon_demo.json), unreviewed by a linguist.
- When no safe rule applies the result says `no_change` and why; it never pretends to adapt.
- A generator plugin can be registered per category (e.g. an LLM later); its output is tagged
  `plugin:<name>` and must still pass semantic verification.
"""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

LABELS = ("VOCABULARY", "SYNTACTIC", "CONCEPTUAL")
METHOD = "rule_based_v1"
_LEX_PATH = Path(__file__).resolve().parents[1] / "DATA" / "lexicon_demo.json"
_GENERATORS = {}
SEQUENCE_CUES = r"(first(?:ly)?|second(?:ly)?|third(?:ly)?|then|next|after that|afterwards|finally|before that)"


def register_generator(category, name, fn):
    """fn(span, sentence, before, after) -> adapted text. Output is tagged plugin:<name>."""
    _GENERATORS[category] = (name, fn)


def clear_generators():
    _GENERATORS.clear()


def load_lexicon(path=None):
    d = json.loads(Path(path or _LEX_PATH).read_text(encoding="utf-8"))
    return d["entries"], d["_meta"]


def word_diff(a, b):
    wa, wb = a.split(), b.split()
    ops = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb).get_opcodes():
        if tag != "equal":
            ops.append({"type": tag, "from": " ".join(wa[i1:i2]), "to": " ".join(wb[j1:j2])})
    return ops


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _result(category, unit, original, adapted, operations, status, variant, n_variants, **extra):
    return {"category": category, "unit": unit, "original": original, "adapted": adapted,
            "changed": adapted != original, "status": status, "method": METHOD,
            "operations": operations, "word_diff": word_diff(original, adapted),
            "variant": variant, "n_variants": n_variants, "is_heuristic": True,
            "is_trained_model_output": False, **extra}


# ---------------------------------------------------------------- vocabulary
def _lookup(entries, tok):
    t = tok.lower()
    if t in entries:
        return t, entries[t]
    for key, e in entries.items():           # explicit inflected forms
        if t in e.get("replace", {}):
            return key, e
    for suf in ("s", "es"):                   # simple plural
        if t.endswith(suf) and t[:-len(suf)] in entries:
            return t[:-len(suf)], entries[t[:-len(suf)]]
    return None, None


def vocabulary(span, variant=0, lexicon=None):
    entries, meta = lexicon or load_lexicon()
    use_replace = variant == 1
    out, ops, pos, seen = [], [], 0, set()
    for m in re.finditer(r"[A-Za-z][A-Za-z'-]*", span):
        key, e = _lookup(entries, m.group())
        out.append(span[pos:m.start()])
        word = m.group()
        if e is None or key in seen:
            out.append(word)
        else:
            seen.add(key)
            rep = e.get("replace", {}).get(word.lower())
            if use_replace and rep:
                new = _cap(rep) if word[0].isupper() else rep
                out.append(new)
                ops.append({"rule": "lexicon_replace", "from": word, "to": new, "entry": key})
            else:
                out.append(f"{word} ({e['gloss']})")
                ops.append({"rule": "lexicon_gloss" if not use_replace else "lexicon_gloss_fallback",
                            "from": word, "to": f"{word} ({e['gloss']})", "entry": key})
        pos = m.end()
    out.append(span[pos:])
    adapted = "".join(out)
    status = "applied" if ops else "no_change"
    extra = {"resources": {"lexicon": meta["name"], "lexicon_status": meta["status"]}}
    if not ops:
        extra["reason"] = "no lexicon entry for the words in the selection"
    return _result("VOCABULARY", "span", span, adapted, ops, status, variant, 2, **extra)


# ---------------------------------------------------------------- syntactic
def _wc(s):
    return len(s.split())


def _split_once(s):
    """Return (pieces, rule) or (None, None). Conservative: both parts need enough words."""
    end = s[-1] if s and s[-1] in ".!?" else "."
    core = s.rstrip(".!? ")
    m = re.match(r"^(Although|Though|Even though)\s+(.+?),\s+(.+)$", core)
    if m and _wc(m.group(2)) >= 3 and _wc(m.group(3)) >= 3:
        return [_cap(m.group(2)) + ".", "But " + m.group(3) + end], "concessive_split"
    if ";" in core:
        parts = [p.strip() for p in core.split(";") if p.strip()]
        if len(parts) == 2 and all(_wc(p) >= 3 for p in parts):
            return [_cap(parts[0]) + ".", _cap(parts[1]) + end], "semicolon_split"
    m = re.match(r"^(.+?),\s+(and|but|so)\s+(.+)$", core)
    if m and m.group(1).count(",") == 0 and _wc(m.group(1)) >= 5 and _wc(m.group(3)) >= 5:
        conj = m.group(2)
        second = _cap(m.group(3)) if conj == "and" else f"{_cap(conj)} {m.group(3)}"
        return [m.group(1) + ".", second + end], f"comma_{conj}_split"
    m = re.match(r"^(.+?),\s+which\s+([^,]+)$", core)
    if m and _wc(m.group(1)) >= 4 and _wc(m.group(2)) >= 3:
        return [m.group(1) + ".", "This " + m.group(2) + end], "which_clause_split"
    return None, None


def chunks(sentence):
    parts = re.split(r"(?<=[,;:])\s+|\s+(?=(?:because|although|though|which|while|if|when|unless)\b)", sentence)
    return [p.strip() for p in parts if p and p.strip()]


def syntactic(sentence, variant=0):
    ch = chunks(sentence)
    if variant == 0:
        pieces, rule = _split_once(sentence)
        if pieces:
            ops, final = [{"rule": rule, "from": sentence, "to": " ".join(pieces)}], list(pieces)
            again, rule2 = _split_once(final[-1])          # one extra pass on the last piece
            if again:
                final = final[:-1] + again
                ops.append({"rule": rule2, "from": pieces[-1], "to": " ".join(again)})
            return _result("SYNTACTIC", "sentence", sentence, " ".join(final), ops, "applied", 0, 2, chunks=ch)
    adapted_status = "no_change"
    extra = {"chunks": ch}
    if variant == 0:
        extra["reason"] = "no safe sentence-splitting rule matched; chunked view offered instead"
    return _result("SYNTACTIC", "sentence", sentence, sentence,
                   [{"rule": "layout_chunks", "from": sentence, "to": " | ".join(ch)}] if len(ch) > 1 else [],
                   adapted_status if variant == 0 else ("layout_only" if len(ch) > 1 else "no_change"),
                   variant, 2, **extra)


# ---------------------------------------------------------------- conceptual
def _key_terms(text):
    words = re.findall(r"[A-Za-z][A-Za-z'-]{7,}", text)
    seen, out = set(), []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower()); out.append(w)
    return out[:5]


def conceptual(sentence, variant=0):
    scaffold = {"questions": ["What is the main thing being described?",
                              "What happens to it, or what does it do?",
                              "Can you say it in your own words in one sentence?"],
                "key_terms_in_text": _key_terms(sentence),
                "tip": "Try sketching it as a few boxes and arrows.",
                "note": "This is a reading scaffold. It does not explain the idea."}
    cues = re.split(rf"(?:,\s*|\s+)(?={SEQUENCE_CUES}\b)", sentence, flags=re.I)
    cues = [c.strip(" ,.") for c in cues if c.strip(" ,.")]
    if variant == 0 and len(cues) >= 3:
        # Numeric list labels would be mistaken for changed educational quantities
        # by the number-preservation check. Bullets are presentation only.
        steps = [f"• {_cap(c)}" for c in cues]
        return _result("CONCEPTUAL", "sentence", sentence, "\n".join(steps),
                       [{"rule": "sequence_steps", "from": sentence, "to": "\n".join(steps)}],
                       "applied", 0, 2, scaffold=scaffold)
    return _result("CONCEPTUAL", "sentence", sentence, sentence, [], "scaffold_only", variant, 2,
                   scaffold=scaffold, reason="no explanation is generated; scaffold shown")


# ---------------------------------------------------------------- routing
def intervene(category, span, sentence=None, context_before="", context_after="", variant=0, lexicon=None):
    if category not in LABELS:
        raise ValueError("Unsupported category")
    sentence = sentence or span
    if category in _GENERATORS:
        name, fn = _GENERATORS[category]
        adapted = fn(span, sentence, context_before, context_after)
        unit = "span" if category == "VOCABULARY" else "sentence"
        orig = span if unit == "span" else sentence
        r = _result(category, unit, orig, adapted, [{"rule": f"plugin:{name}", "from": orig, "to": adapted}],
                    "applied" if adapted != orig else "no_change", variant, 1)
        r["method"] = f"plugin:{name}"
        r["is_heuristic"] = False
        return r
    if category == "VOCABULARY":
        return vocabulary(span, variant, lexicon)
    if category == "SYNTACTIC":
        return syntactic(sentence, variant)
    return conceptual(sentence, variant)


def route(category, text, context=""):
    """Backward-compatible entry point."""
    r = intervene(category, text, sentence=text)
    return {**r, "original": text}
