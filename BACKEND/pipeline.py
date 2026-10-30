"""Backend pipeline: context -> category -> intervention -> verification -> trace.

Research integrity:
- A trained model is used for the category ONLY if ARTIFACTS/research_model/registry.json points to a
  run whose results.json has data_status == "research" (and valid_for_scientific_claims for
  transformers). Smoke/fixture artifacts are rejected.
- Without that, a clearly labelled demo heuristic may *suggest* a support type. It has no
  probability/confidence and is never described as a prediction of a trained model.
- Visual/presentation preferences are not part of this pipeline's inputs.
"""
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ML.context import build_context, sentence_around, span_offset_in_sentence
from ML.interventions import intervene, load_lexicon
from ML.semantic_verifier import verify, EmbeddingScorer, NLIScorer

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ARTIFACTS"
PIPELINE_VERSION = "0.2.0"
DISCLAIMER = ("DyslexiAdapt is a reading aid. It does not diagnose dyslexia or any condition and does not "
              "identify a medical cause. Suggestions can be wrong; you decide what helps.")
LABELS = ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]


# ------------------------------------------------------------------ predictors
class DemoHeuristic:
    """Rule-of-thumb suggestion of a support type. NOT a trained model: no probabilities, no confidence."""
    source = "demo_heuristic_rules"

    def suggest(self, span, sentence):
        n = len(re.findall(r"\b[\w'-]+\b", span))
        s_n = len(re.findall(r"\b[\w'-]+\b", sentence))
        clause_marks = len(re.findall(r",|;|\b(?:which|although|though|because|while|whereas)\b", sentence))
        if n <= 2:
            cat = "VOCABULARY"
        elif s_n >= 18 and clause_marks >= 2 or n >= 12:
            cat = "SYNTACTIC"
        else:
            cat = "CONCEPTUAL"
        return {"category": cat, "source": self.source, "probabilities": None, "confidence": None,
                "is_trained_model_output": False,
                "note": "Demo rule of thumb, not a trained prediction. You can choose a different support type."}


class ResearchModel:
    def __init__(self, kind, predict_fn, experiment_id, info):
        self.kind, self._predict, self.experiment_id, self.info = kind, predict_fn, experiment_id, info

    def suggest(self, span, sentence, before="", after=""):
        probs = self._predict(span, before, after)
        cat = max(probs, key=probs.get)
        return {"category": cat, "source": f"trained_model:{self.kind}", "probabilities": probs,
                "confidence": None, "is_trained_model_output": True,
                "note": "Probabilities are the model's raw softmax outputs; they are not calibrated."}


def _validate_run(results, require_valid=True):
    if not require_valid:
        return None
    if results.get("data_status") != "research":
        return f"data_status is {results.get('data_status')!r}, not 'research'"
    if results.get("smoke"):
        return "run was a smoke test"
    if "valid_for_scientific_claims" in results and not results["valid_for_scientific_claims"]:
        return "valid_for_scientific_claims is false"
    return None


def load_research_model(art_dir=None, require_valid=True):
    """Return (ResearchModel|None, status dict). Never raises for a missing/invalid model."""
    d = Path(art_dir or ART / "research_model")
    reg = d / "registry.json"
    if not reg.exists():
        return None, {"available": False, "reason": "no ARTIFACTS/research_model/registry.json"}
    try:
        r = json.loads(reg.read_text(encoding="utf-8"))
        run_dir = (d / r["path"]).resolve()
        results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
        why = _validate_run(results, require_valid)
        if why:
            return None, {"available": False, "reason": f"registered run rejected: {why}"}
        kind = r["kind"]
        if kind == "sklearn":
            import joblib
            import pandas as pd
            m = joblib.load(run_dir / r["model_file"])
            classes = list(m.classes_) if hasattr(m, "classes_") else LABELS

            def predict(span, before, after):
                x = pd.Series([f"{before} [SPAN] {span} [/SPAN] {after}"])
                clf = m.named_steps["clf"]
                z = clf.predict_proba(m.named_steps["tfidf"].transform(x))[0] if hasattr(clf, "predict_proba") \
                    else None
                if z is None:
                    raise RuntimeError("model has no probabilities; register a probabilistic model")
                return {c: float(p) for c, p in zip(classes, z)}
        elif kind == "fusion":
            import numpy as np
            import torch
            import pandas as pd
            from ML.fusion import load_fusion, feature_matrix
            m, tok, cfg = load_fusion(run_dir / "model")

            def predict(span, before, after):
                df = pd.DataFrame([{"text": span, "context_before": before, "context_after": after}])
                F = (feature_matrix(df) - np.array(cfg["scaler_mean"])) / np.array(cfg["scaler_std"])
                enc = tok([f"{before} [SPAN] {span} [/SPAN] {after}"], return_tensors="pt", truncation=True,
                          max_length=cfg.get("max_len", 128))  # must match training length
                with torch.no_grad():
                    p = torch.softmax(m(enc["input_ids"], enc["attention_mask"],
                                        features=torch.tensor(F, dtype=torch.float)), -1)[0].tolist()
                return dict(zip(cfg["labels"], p))
        else:
            return None, {"available": False, "reason": f"unsupported kind {kind!r}"}
        meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8")) if (run_dir / "metadata.json").exists() else {}
        exp = r.get("experiment_id") or f"{run_dir.name}@{str(meta.get('dataset_sha256', ''))[:8]}"
        return ResearchModel(kind, predict, exp, {"path": str(run_dir)}), {
            "available": True, "kind": kind, "experiment_id": exp, "data_status": results["data_status"]}
    except Exception as e:
        return None, {"available": False, "reason": f"{type(e).__name__}: {str(e)[:200]}"}


# ------------------------------------------------------------------ trace store (minimal data)
class TraceStore:
    """In-memory summaries (no learner text). Optional JSONL log; text only with explicit opt-in."""

    def __init__(self, max_items=500):
        self.items, self.max = {}, max_items
        self.log_on = os.environ.get("DYSLEXIADAPT_LOG") == "1"
        self.log_text = os.environ.get("DYSLEXIADAPT_LOG_TEXT") == "1"
        self.dir = Path(os.environ.get("DYSLEXIADAPT_TRACE_DIR", ART / "traces"))

    def _write(self, rec):
        if not self.log_on:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "traces.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def add(self, summary, text_payload=None):
        self.items[summary["trace_id"]] = summary
        while len(self.items) > self.max:
            self.items.pop(next(iter(self.items)))
        rec = {"event": "adapt", **summary}
        if self.log_text and text_payload:
            rec["text"] = text_payload
        self._write(rec)

    def feedback(self, trace_id, decision, comfort=None):
        if trace_id not in self.items:
            return False
        self._write({"event": "feedback", "trace_id": trace_id, "decision": decision, "comfort_rating": comfort,
                     "at": datetime.now(timezone.utc).isoformat()})
        self.items[trace_id]["last_decision"] = decision
        return True


# ------------------------------------------------------------------ pipeline
class Pipeline:
    def __init__(self, art_dir=None):
        self.demo = DemoHeuristic()
        self.model, self.model_status = load_research_model(art_dir)
        self.traces = TraceStore()
        self.embedder = self.nli = None
        if os.environ.get("DYSLEXIADAPT_SEMANTIC_MODELS") == "1":
            self.embedder, self.nli = EmbeddingScorer(), NLIScorer()
        _, self.lex_meta = load_lexicon()

    def status(self):
        sem = {"enabled_by_config": os.environ.get("DYSLEXIADAPT_SEMANTIC_MODELS") == "1"}
        for n, s in (("embedding", self.embedder), ("nli", self.nli)):
            sem[n] = ("disabled" if s is None else "available" if s.available else f"unavailable: {s.error}")
        return {"pipeline_version": PIPELINE_VERSION, "mode": "research" if self.model else "demo",
                "research_model_available": self.model is not None, "research_model": self.model_status,
                "warning": None if self.model else
                "No validated research model is loaded. Category suggestions come from a demo heuristic "
                "and nothing produced here is a research result.",
                "semantic_scorers": sem, "lexicon": {"name": self.lex_meta["name"], "status": self.lex_meta["status"]},
                "logging": {"enabled": self.traces.log_on, "text_logged": self.traces.log_text}}

    def adapt(self, span, text=None, span_start=None, context_before="", context_after="",
              category_override=None, variant=0, want_research=False):
        if want_research and not self.model:
            raise LookupError("research mode requested but no validated research model is available: "
                              + str(self.model_status.get("reason")))
        if text:
            ctx = build_context(text, span, span_start)
            before, after, sentence = ctx["context_before"], ctx["context_after"], ctx["sentence"]
            selected_offset = span_offset_in_sentence(text[:ctx["span_start"]], span, text[ctx["span_end"]:])
            original_sentence_start = ctx["span_start"] - selected_offset
        else:
            before, after = context_before, context_after
            sentence = sentence_around(before, span, after)
            selected_offset = span_offset_in_sentence(before, span, after)
            original_sentence_start = None
        if category_override:
            cat = {"category": category_override, "source": "learner_choice", "probabilities": None,
                   "confidence": None, "is_trained_model_output": False,
                   "note": "You chose this support type."}
        elif self.model:
            cat = self.model.suggest(span, sentence, before, after)
        else:
            cat = self.demo.suggest(span, sentence)

        iv = intervene(cat["category"], span, sentence, before, after, variant)
        adapted_sentence = (sentence[:selected_offset] + iv["adapted"] + sentence[selected_offset + len(span):]
                            if iv["unit"] == "span" and span in sentence else
                            iv["adapted"] if iv["unit"] == "sentence" else None)
        # verify at sentence level when possible: a gloss legitimately lengthens a bare word, but
        # negation/number/entity changes must be judged in the sentence the learner reads
        ver = verify(sentence, adapted_sentence, self.embedder, self.nli) if adapted_sentence \
            else verify(iv["original"], iv["adapted"], self.embedder, self.nli)
        ver["verified_unit"] = "sentence" if adapted_sentence else iv["unit"]
        used_model = cat["is_trained_model_output"]
        trace_id = uuid.uuid4().hex
        presentable = ver["status"] != "fail" and iv["status"] in {"applied", "layout_only", "scaffold_only"}
        warnings = []
        if not used_model:
            warnings.append("DEMO: not produced by a trained research model; do not report as a research result.")
        if ver["status"] == "review":
            warnings.append("Some automatic checks raised a caution; please read the adapted text carefully.")
        if ver["status"] == "fail":
            warnings.append("Automatic checks suggest the adapted text may change the meaning, so it is hidden.")
        resp = {
            "trace_id": trace_id, "at": datetime.now(timezone.utc).isoformat(),
            "research_mode": "research" if used_model and self.model else "demo",
            "valid_for_research": False if not used_model else self.model_status.get("data_status") == "research",
            "experiment_id": self.model.experiment_id if used_model else "demo",
            "pipeline_version": PIPELINE_VERSION,
            "input": {"span": span, "sentence": sentence, "context_before": before, "context_after": after},
            "category": cat, "intervention": iv, "verification": ver, "presentable": presentable,
            "comparison": {"unit": iv["unit"], "original": iv["original"], "adapted": iv["adapted"],
                           "original_sentence": sentence, "adapted_sentence": adapted_sentence,
                           "original_sentence_start": original_sentence_start},
            "warnings": warnings, "disclaimer": DISCLAIMER}
        self.traces.add({"trace_id": trace_id, "at": resp["at"], "research_mode": resp["research_mode"],
                         "experiment_id": resp["experiment_id"], "category": cat["category"],
                         "category_source": cat["source"], "variant": variant,
                         "rules": [o["rule"] for o in iv["operations"]], "intervention_status": iv["status"],
                         "verification_status": ver["status"], "flags": [f["check"] for f in ver["flags"]]},
                        {"span": span, "sentence": sentence})
        return resp
