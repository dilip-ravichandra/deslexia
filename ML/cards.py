"""Model card and dataset card generator (Task 18).

Cards are produced from real artifacts and the project state. Any metric that appears in a card comes from a
research-grade run's results.json; if none exists the card says so explicitly. Smoke/fixture runs are counted
but never quoted. The dataset card's release status is driven by the ADR-009 licence decision in DECISIONS.md.
"""
import json
import re
from pathlib import Path

from ML.data_validation import PRIMARY_LABELS, REQUIRED, PROVENANCE

ROOT = Path(__file__).resolve().parents[1]


def _j(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def facts(root=ROOT):
    root = Path(root)
    art = root / "ARTIFACTS"
    research, nonresearch, lexical = [], 0, []
    for p in sorted(art.rglob("results.json")) if art.exists() else []:
        r = _j(p, {})
        is_baselines = "models" in r and "tfidf_logreg" in r.get("models", {})
        ok = r.get("data_status") == "research" and (True if is_baselines else bool(r.get("valid_for_scientific_claims")))
        if r.get('data_status')=='PUBLIC_HUMAN_LEXICAL_ONLY':
            lexical.append(r)
        elif ok:
            research.append({"path": str(p.parent.relative_to(root)), "res": r, "meta": _j(p.parent / "metadata.json", {})})
        else:
            nonresearch += 1
    dec = (root / "DECISIONS.md").read_text(encoding="utf-8") if (root / "DECISIONS.md").exists() else ""
    i = dec.find("ADR-009")
    pending = i >= 0 and "PENDING" in dec[i:].upper()
    split = _j(root / "DATA" / "split_manifest.json")
    agreement = [_j(p, {}) | {"_path": str(p.relative_to(root))} for p in sorted(art.rglob("agreement.json"))] if art.exists() else []
    return {"research_runs": research, "lexical_runs":lexical, "non_research_count": nonresearch, "adr009_pending": pending,
            "split": split, "agreement": agreement, "state": _j(root / "PROJECT_STATE.json", {})}


def _f(v):
    return "n/a" if v is None else f"{v:.3f}"


def model_card(root=ROOT):
    F = facts(root)
    L = ["# Model Card — DyslexiAdapt", "",
         "> Status legend used across this project: **IMPLEMENTED** (code exists and is tested), **DEMO** (rule of thumb or "
         "placeholder resource), **SMOKE-TESTED** (pipeline runs on synthetic/tiny data), **VALIDATED** (supported by "
         "research-grade artifacts). Nothing below is VALIDATED unless a research-grade result is listed in the Evaluation section.", "",
         "## Components",
         "| Component | Status | Notes |", "|---|---|---|",
         "| TF-IDF + Logistic Regression / Linear SVM, majority baseline | IMPLEMENTED, SMOKE-TESTED | `ML/baselines.py` |",
         "| DistilBERT span-support classifier | IMPLEMENTED, SMOKE-TESTED (tiny random-init model) | `ML/distilbert_trainer.py`; needs real pretrained weights |",
         "| DistilBERT + linguistic-feature fusion and matched ablation | IMPLEMENTED, SMOKE-TESTED | `ML/fusion.py`, `ML/ablation.py` |",
         "| Current reader support routing | IMPLEMENTED, uncalibrated | manual choice, consented survey/session evidence, eligible activated routing model or separate English lexical model; asks when uncertain |",
         "| Targeted interventions (word gloss/replace, sentence split/chunk, steps/scaffold) | IMPLEMENTED, DEMO lexicon | rule-based; lexicon (39 entries) unreviewed; conceptual support is scaffolding only |",
         "| Source-claim screening and optional semantic checks | IMPLEMENTED | exact source quotes, finite multilingual checks, retry/withholding; no correctness guarantee or completed native-language quality study |", "",
         "## Intended use",
         "Research prototype for studying whether localized, learner-guided support (vs uniform simplification) helps readers while "
         "changing less text. A reading aid under the learner's control.", "",
         "## Out of scope / must not be used for",
         "Diagnosing dyslexia or any condition; inferring health or ability; clinical or educational placement decisions; claims of "
         "clinical effectiveness; automatic rewriting without the learner's choice.", "",
         "## Training data",]
    if F["research_runs"]:
        sizes = {r["path"]: r["res"].get("split_sizes") for r in F["research_runs"]}
        L += ["Research-grade runs exist (see Evaluation). Split sizes: " + json.dumps(sizes)]
    else:
        L += ["**NOT AVAILABLE.** No human-annotated gold dataset exists yet (HG-01). Seed examples in `DATA/seed_examples.csv` are "
              "three smoke-test rows, not gold data."]
    L += ["", "## Evaluation"]
    if not F["research_runs"]:
        L += ["**NO VALIDATED MODEL.** No research-grade result exists. Any score produced by `--smoke` or fixture runs only shows "
              "that the pipeline executes and must not be cited.", ""]
    else:
        L += ["Metrics below come only from research-grade runs (research-valid human data, frozen split, "
              "real pretrained weights for transformers). See the run folders for confusion matrices, seeds and hashes.", ""]
        L += ["| Run | Model | Test accuracy | Test macro-F1 | Test n | Dataset sha256 |", "|---|---|---:|---:|---:|---|"]
        for r in F["research_runs"]:
            res, sha = r["res"], str(r["meta"].get("dataset_sha256", ""))[:12]
            if "models" in res:
                for name, m in res["models"].items():
                    L.append(f"| {r['path']} | {name} | {_f(m['test']['accuracy'])} | {_f(m['test']['macro_f1'])} | {m['test']['n']} | {sha} |")
            else:
                L.append(f"| {r['path']} | {res.get('weights')} | {_f(res['test']['accuracy'])} | {_f(res['test']['macro_f1'])} | {res['test']['n']} | {sha} |")
    if F['lexical_runs']:
        L += ['', '## Supplementary public lexical regression', 'English CompLex human complexity ratings; separate from support routing and student effectiveness.',
              '| Run | Arm | Validation MAE | Test MAE | Status |','|---|---|---:|---:|---|']
        for run in F['lexical_runs']:
            for arm,value in run.get('arms',{}).items():
                L.append(f"| {run['run_id']} | {arm} | {_f(value['validation']['mae'])} | {_f(value['test']['mae'])} | {run['status']} |")
    L += [f"", f"Smoke/fixture result files present in this checkout (not quoted): {F['non_research_count']}.", "",
          "## Ethical considerations",
          "No diagnosis or medical inference. The learner can reject any adaptation. Uncertainty is shown (demo mode is announced; "
          "automatic checks never claim to guarantee meaning). Minimal data: logging is off by default and stores no learner text unless "
          "explicitly enabled with consent (HG-02). Content licences must be verified before any data release (HG-03).", "",
          "## Known limitations",
          "See `LIMITATIONS.md`. Key points: no validated model; unreviewed lexicon; uncalibrated verifier; interface tested only "
          "with engineering fixtures (see current reports for exact browser scope); no user study.", "",
          "## How to reproduce",
          "`python -m ML.experiment_runner --config EXPERIMENTS/config.yaml --csv <gold.csv>` (research data) — see `RUN_COLAB.md`. "
          "Every run writes a manifest with dataset, code and output hashes.", ""]
    return "\n".join(L)


def dataset_card(root=ROOT):
    F = facts(root)
    L = ["# Dataset Card — DyslexiAdapt span-support annotations", ""]
    if F["adr009_pending"]:
        L += ["> **RELEASE STATUS: PENDING — DO NOT REDISTRIBUTE.** The source-text licence decision (ADR-009) is unconfirmed. "
              "Do not publish or share any passage pool, annotated file or derived text until the source licence and release "
              "conditions are verified (see `DATA/LICENSE_ANALYSIS.md`).", ""]
    else:
        L += ["> Release status: ADR-009 is no longer marked PENDING in DECISIONS.md. Re-verify the recorded decision and source "
              "licence before any release.", ""]
    L += ["## Dataset status",]
    if F["split"]:
        sp = F["split"]
        L += [f"A frozen split manifest exists (`DATA/split_manifest.json`, dataset sha256 `{sp.get('dataset_sha256')}`, seed {sp.get('seed')}, "
              f"group {sp.get('group')}). Documents per split: {json.dumps({k: len(v['groups']) for k, v in sp['splits'].items()})}."]
    else:
        L += ["**NO GOLD DATASET EXISTS.** No human annotations have been collected (HG-01). `DATA/seed_examples.csv` holds three "
              "smoke-test rows (annotator `seed`) that are rejected by research-mode validation."]
    L += ["", "## Intended use",
          "Research on computational support-category routing for selected educational text spans.", "",
          "## Not intended for", "- dyslexia diagnosis\n- medical decision making\n- inferring learner health status\n- clinical efficacy claims", "",
          "## Labels", "| Label | Meaning (guidelines v1) |", "|---|---|"]
    meaning = {"VOCABULARY": "a word or short phrase is the barrier",
               "SYNTACTIC": "sentence structure is the barrier",
               "CONCEPTUAL": "the idea itself needs support"}
    for l in PRIMARY_LABELS:
        L.append(f"| {l} | {meaning[l]} |")
    L += ["| OTHER_UNCERTAIN | not trainable; routed to adjudication, excluded from training |", "",
          "Full definitions: `DATA/annotation_guidelines_v1.md`.", "",
          "## Schema", f"Required columns: {', '.join(REQUIRED)}. Research mode also requires: {', '.join(PROVENANCE)}. "
          "Validation: `python -m ML.data_validation --csv <file> --mode research`.", "",
          "## Annotation process",
          "Double annotation by distinct human annotators (AI/seed ids are rejected). Gold = unanimous human label or a named human "
          "adjudicator's decision; disagreements are never auto-resolved. Use `human-review.html` and `HUMAN_REVIEW_GUIDE.md`; the lab preserves raw exports and unresolved decisions.", "",
          "## Required reporting — current status", "| Item | Status |", "|---|---|"]
    ag = F["agreement"]
    L += [f"| Source provenance and licences | {'PENDING (ADR-009)' if F['adr009_pending'] else 'see DECISIONS.md'} |",
          f"| Annotator count | {'NOT AVAILABLE' if not ag else len(ag[0].get('annotators', []))} |",
          "| Guideline version | v1 (`DATA/annotation_guidelines_v1.md`) |",
          f"| Agreement | {'NOT AVAILABLE (no annotations)' if not ag else 'see ' + ag[0]['_path']} |"
          if not ag else f"| Agreement | Krippendorff alpha (nominal) {_f(ag[0].get('krippendorff_alpha_nominal'))}; see {ag[0]['_path']} |",
          "| Adjudication | " + ("NOT AVAILABLE" if not ag else json.dumps(ag[0].get("adjudication", "not recorded"))) + " |",
          "| Class distribution | " + ("NOT AVAILABLE" if not F["split"] else json.dumps(F["split"].get("leakage", {}).get("label_distribution", "not recorded"))) + " |",
          f"| Document-level split | {'frozen manifest present' if F['split'] else 'NOT AVAILABLE'} |", "",
          "## Candidate source and its consequences",
          "Candidate: Simple English Wikipedia text (CC BY-SA, version unconfirmed) — attribution and ShareAlike apply to text and "
          "likely to files that combine text with labels. Source text, excerpts, annotations, metadata and model artefacts carry "
          "different obligations; see `DATA/LICENSE_ANALYSIS.md`. This is an engineering summary, not legal advice.", "",
          "## Known biases and limits",
          "Simple Wikipedia is already simplified, so hard spans may be under-represented. Annotator count and background will bound "
          "label validity. Label categories are an operational scheme, not a theory of reading difficulty.", ""]
    return "\n".join(L)


def write_cards(root=ROOT):
    root = Path(root)
    (root / "MODEL_CARD.md").write_text(model_card(root), encoding="utf-8")
    (root / "DATASET_CARD.md").write_text(dataset_card(root), encoding="utf-8")


if __name__ == "__main__":
    write_cards()
    print("wrote MODEL_CARD.md and DATASET_CARD.md")
