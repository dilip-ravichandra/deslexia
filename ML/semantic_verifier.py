"""Meaning-preservation checks for adapted text (Task 10).

Layered signals, each reported separately:
  hard (fail)  numbers changed, negation count changed, named entities/acronyms dropped,
               NLI contradiction (only if an NLI scorer is available)
  soft (review) entities added, modality/quantifier words changed, low token retention,
               large length change, low embedding similarity / low entailment (only if scorers available)

HONEST LIMITS
- `pass` means "no automated flag was raised", NOT "meaning is preserved". The result always carries
  meaning_preservation_guaranteed=False.
- Thresholds are engineering defaults and are NOT calibrated against human judgements
  (thresholds_validated=False). Do not report them as validated performance.
- Embedding/NLI scorers need model weights. When unavailable they are listed in
  `checks_unavailable`; they are never silently replaced by the lexical ratio.
- `lexical_char_ratio` is character overlap, not semantic similarity.
"""
import re
from collections import Counter
from difflib import SequenceMatcher

DEFAULT_THRESHOLDS = {"min_token_retention": 0.5, "max_length_ratio": 2.5, "min_length_ratio": 0.4,
                      "min_embedding_cosine": 0.75, "min_entailment": 0.5, "max_contradiction": 0.5}
NEGATIONS = {"not", "no", "never", "none", "neither", "nor", "cannot", "without", "nothing", "nobody", "nowhere"}
MODALS = {"all", "some", "none", "every", "always", "never", "must", "may", "might", "can", "could",
          "should", "only", "most", "few", "many", "often", "sometimes", "rarely", "usually"}
_STOP = {"the", "a", "an", "of", "to", "in", "and", "or", "is", "are", "was", "were", "it", "that", "this",
         "as", "at", "by", "for", "on", "with", "be", "been", "has", "have", "had"}


def numbers(text):
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?%?", text)]


def _tokens(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def negation_count(text):
    toks = [t.lower() for t in _tokens(text)]
    return sum(t in NEGATIONS or t.endswith(("n't", "n’t")) for t in toks)


def entities(text):
    """Heuristic named entities: capitalised tokens not at a sentence start, plus ALL-CAPS acronyms."""
    found = set()
    for sent in re.split(r"(?<=[.!?])\s+", text):
        toks = _tokens(sent)
        for i, t in enumerate(toks):
            if (i > 0 and t[0].isupper() and not t.isupper()) or (len(t) >= 2 and t.isupper() and t.isalpha()):
                found.add(t)
    return found


def modals(text):
    return Counter(t.lower() for t in _tokens(text) if t.lower() in MODALS)


class EmbeddingScorer:
    """Cosine similarity with a sentence-transformers model (e.g. sentence-transformers/all-MiniLM-L6-v2)."""
    name = "embedding_cosine"

    def __init__(self, model="sentence-transformers/all-MiniLM-L6-v2", offline=False):
        self.model_name, self.error, self._m = model, None, None
        try:
            from sentence_transformers import SentenceTransformer
            self._m = SentenceTransformer(model, local_files_only=offline)
        except Exception as e:  # missing package, no network, no cache
            self.error = f"{type(e).__name__}: {str(e)[:200]}"

    @property
    def available(self):
        return self._m is not None

    def score(self, a, b):
        import numpy as np
        va, vb = self._m.encode([a, b], normalize_embeddings=True)
        return float(np.dot(va, vb))


class NLIScorer:
    """Entailment/neutral/contradiction probabilities (e.g. cross-encoder/nli-deberta-v3-small)."""
    name = "nli"

    def __init__(self, model="cross-encoder/nli-deberta-v3-small", offline=False):
        self.model_name, self.error, self._m = model, None, None
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(model, local_files_only=offline)
            self._m = AutoModelForSequenceClassification.from_pretrained(model, local_files_only=offline).eval()
        except Exception as e:
            self.error = f"{type(e).__name__}: {str(e)[:200]}"

    @property
    def available(self):
        return self._m is not None

    def probs(self, premise, hypothesis):
        import torch
        enc = self._tok(premise, hypothesis, return_tensors="pt", truncation=True)
        with torch.no_grad():
            p = torch.softmax(self._m(**enc).logits, -1)[0].tolist()
        names = {int(i): n.lower() for i, n in self._m.config.id2label.items()}
        return {names[i]: p[i] for i in range(len(p))}


def verify(original, adapted, embedder=None, nli=None, thresholds=None):
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    flags, run, unavailable = [], ["numbers", "negation", "entities", "modality", "token_retention",
                                   "length_ratio", "lexical_char_ratio"], []

    def flag(check, severity, detail):
        flags.append({"check": check, "severity": severity, "detail": detail})

    n_o, n_a = Counter(numbers(original)), Counter(numbers(adapted))
    numbers_ok = n_o == n_a
    if not numbers_ok:
        flag("numbers", "hard", f"numbers changed: original={dict(n_o)} adapted={dict(n_a)}")
    neg_o, neg_a = negation_count(original), negation_count(adapted)
    if neg_o != neg_a:
        flag("negation", "hard", f"negation words {neg_o} -> {neg_a}")
    e_o, e_a = entities(original), entities(adapted)
    dropped, added = sorted(e_o - e_a), sorted(e_a - e_o)
    if dropped:
        flag("entities", "hard", f"entities dropped: {dropped}")
    if added:
        flag("entities", "soft", f"entities added: {added}")
    m_o, m_a = modals(original), modals(adapted)
    if m_o != m_a:
        flag("modality", "soft", f"quantifier/modal words changed: {dict(m_o)} -> {dict(m_a)}")

    content = lambda s: {t.lower() for t in _tokens(s)} - _STOP
    c_o, c_a = content(original), content(adapted)
    retention = (len(c_o & c_a) / len(c_o)) if c_o else 1.0
    if retention < th["min_token_retention"]:
        flag("token_retention", "soft", f"only {retention:.2f} of content words kept")
    w_o, w_a = max(1, len(_tokens(original))), len(_tokens(adapted))
    ratio = w_a / w_o
    if ratio > th["max_length_ratio"] or ratio < th["min_length_ratio"]:
        flag("length_ratio", "soft", f"length changed by x{ratio:.2f}")
    lexical = SequenceMatcher(None, original.lower(), adapted.lower()).ratio()

    emb = None
    if embedder is not None and getattr(embedder, "available", True):
        emb = embedder.score(original, adapted)
        run.append("embedding_cosine")
        if emb < th["min_embedding_cosine"]:
            flag("embedding_cosine", "soft", f"cosine {emb:.2f} below {th['min_embedding_cosine']}")
    else:
        unavailable.append({"check": "embedding_cosine",
                            "reason": getattr(embedder, "error", None) or "no embedding scorer configured"})
    nli_res = None
    if nli is not None and getattr(nli, "available", True):
        fwd, bwd = nli.probs(original, adapted), nli.probs(adapted, original)
        nli_res = {"original_entails_adapted": fwd.get("entailment"), "adapted_entails_original": bwd.get("entailment"),
                   "contradiction": max(fwd.get("contradiction", 0.0), bwd.get("contradiction", 0.0))}
        run.append("nli")
        if nli_res["contradiction"] >= th["max_contradiction"]:
            flag("nli", "hard", f"contradiction probability {nli_res['contradiction']:.2f}")
        elif min(nli_res["original_entails_adapted"] or 0, nli_res["adapted_entails_original"] or 0) < th["min_entailment"]:
            flag("nli", "soft", "bidirectional entailment below threshold")
    else:
        unavailable.append({"check": "nli",
                            "reason": getattr(nli, "error", None) or "no NLI scorer configured"})

    status = "fail" if any(f["severity"] == "hard" for f in flags) else ("review" if flags else "pass")
    return {"status": status,
            "status_meaning": {"pass": "no automated flag raised (NOT a guarantee of meaning)",
                               "review": "soft flag(s): show to the learner with a caution",
                               "fail": "hard flag(s): do not present as a faithful adaptation"}[status],
            "flags": flags, "checks_run": run, "checks_unavailable": unavailable,
            "numbers_preserved": numbers_ok, "entities_preserved": not dropped and not added,
            "token_retention": retention, "length_ratio": ratio, "lexical_char_ratio": lexical,
            "embedding_cosine": emb, "nli": nli_res,
            "thresholds": th, "thresholds_validated": False, "meaning_preservation_guaranteed": False}


def basic_verify(original, adapted):
    """Backward-compatible wrapper (no model-based checks)."""
    r = verify(original, adapted)
    r["lexical_similarity"] = r["lexical_char_ratio"]
    r["nli_entailment"] = None
    return r
