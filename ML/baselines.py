"""Baseline classifiers (Task 05): majority, TF-IDF + LogisticRegression, TF-IDF + LinearSVC.

Protocol:
- hyperparameters (C) are chosen on the validation split only; the test split is
  scored once, after selection.
- research runs require a research-valid dataset and a frozen split manifest.
  Anything else must be run with allow_fixture=True and is stamped
  data_status="fixture_not_research" so it cannot be mistaken for a result.
"""
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ML.data_validation import PRIMARY_LABELS as LABELS, check, file_sha256
from ML.group_split import split, load_frozen

C_GRID = [0.1, 1.0, 10.0]


def add_model_input(d):
    d = d.copy()
    d["model_input"] = (d.get("context_before", "").fillna("") + " [SPAN] " + d["text"].astype(str)
                        + " [/SPAN] " + d.get("context_after", "").fillna(""))
    return d


def _make(name, C, seed):
    tfidf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    if name == "tfidf_logreg":
        return Pipeline([("tfidf", tfidf), ("clf", LogisticRegression(
            C=C, max_iter=3000, class_weight="balanced", random_state=seed))])
    if name == "tfidf_svm":
        return Pipeline([("tfidf", tfidf), ("clf", LinearSVC(
            C=C, class_weight="balanced", random_state=seed))])
    raise ValueError(name)


def metrics(y_true, y_pred):
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "per_class": classification_report(y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0),
        "confusion_matrix": {"labels": LABELS,
                             "matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist()},
    }


def select_and_fit(name, train, val, seed=42):
    """Choose C on validation macro-F1 (never sees test). Returns (model, chosen C, grid scores)."""
    scores = {}
    for C in C_GRID:
        m = _make(name, C, seed).fit(train.model_input, train.category)
        scores[C] = float(f1_score(val.category, m.predict(val.model_input),
                                   labels=LABELS, average="macro", zero_division=0))
    best = max(C_GRID, key=lambda c: (scores[c], -c))  # ties -> smaller C (stronger regularisation)
    return _make(name, best, seed).fit(train.model_input, train.category), best, scores


def run(csv_path, out_dir, manifest_path=None, seed=42, allow_fixture=False):
    raw = pd.read_csv(csv_path)
    rep = check(raw, "research")
    research_ok = rep.ok and manifest_path is not None
    if not research_ok and not allow_fixture:
        raise RuntimeError(
            "Not research-valid (need research-mode validation and a frozen split manifest). "
            f"Problems: {rep.errors or 'no manifest'}. Use allow_fixture=True for pipeline tests only.")
    data_status = "research" if research_ok else "fixture_not_research"

    excluded = int((~raw.category.isin(LABELS)).sum())
    d = add_model_input(raw[raw.category.isin(LABELS)])
    if manifest_path:
        tr, va, te = (x for x in load_frozen(manifest_path, csv_path))
        tr, va, te = (add_model_input(x[x.category.isin(LABELS)]) for x in (tr, va, te))
        split_source = {"manifest": str(manifest_path), "manifest_sha256": file_sha256(manifest_path)}
    else:
        tr, va, te = split(d, seed=seed)
        split_source = {"manifest": None, "note": "ad-hoc split; not frozen"}

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = {"data_status": data_status, "labels": LABELS, "excluded_non_primary_rows": excluded,
               "split_sizes": {"train": len(tr), "validation": len(va), "test": len(te)},
               "models": {}}
    preds_all = []

    models = {"majority": (DummyClassifier(strategy="most_frequent").fit(tr.model_input, tr.category), None, None)}
    for name in ["tfidf_logreg", "tfidf_svm"]:
        models[name] = select_and_fit(name, tr, va, seed)

    for name, (m, C, grid) in models.items():
        entry = {"selected_C": C, "validation_macro_f1_by_C": grid}
        for sp, df in [("validation", va), ("test", te)]:
            p = m.predict(df.model_input)
            entry[sp] = metrics(df.category.tolist(), p.tolist())
            if 'language' in df:
                entry.setdefault('per_language',{})[sp]={lang:metrics(df.loc[df.language.eq(lang),'category'].tolist(),p[df.language.eq(lang)].tolist()) for lang in sorted(set(df.language))}
            preds_all.append(pd.DataFrame({"model": name, "split": sp,
                                           "span_id": df.get("span_id", pd.Series(range(len(df)))).values,
                                           "true": df.category.values, "pred": p}))
        results["models"][name] = entry
        joblib.dump(m, out / f"{name}.joblib")

    pd.concat(preds_all).to_csv(out / "predictions.csv", index=False)
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(), "seed": seed,
        "data_status": data_status, "dataset_file": Path(csv_path).name,
        "dataset_sha256": file_sha256(csv_path), "split": split_source, "c_grid": C_GRID,
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__},
        "command": " ".join(sys.argv),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
