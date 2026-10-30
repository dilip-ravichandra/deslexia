"""Error analysis (Task 08): everything is computed from real prediction files; nothing is invented.

Inputs : predictions.csv (columns: [model], split, span_id, true, pred, [p_VOCABULARY, p_SYNTACTIC, p_CONCEPTUAL])
         optional dataset CSV (for text, context, document_id, source_id).
Outputs: error_analysis.json + error_analysis.md, stamped with the data_status of the run that produced
         the predictions (read from a sibling results.json). Non-research analyses carry a NOT RESEARCH banner.

Selection rules for examples are deterministic and stated in the output:
  with probabilities -> most confident errors first (ties by span_id); without -> span_id order.
Test-set caveat: examining test errors and then changing the model contaminates the test set.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

LABELS = ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]
PROB_COLS = [f"p_{l}" for l in LABELS]
MIN_SLICE_N = 20
TEST_CAVEAT = ("Looking at test-set errors and then changing the model or preprocessing contaminates the test "
               "set. Use validation errors for development; freeze a new test set before re-evaluating.")


def _idx(y):
    m = {l: i for i, l in enumerate(LABELS)}
    return np.array([m[v] for v in y])


def confusion_counts(t, p):
    return np.bincount(t * 3 + p, minlength=9).reshape(3, 3)


def macro_f1_from_cm(cm):
    tp = np.diag(cm).astype(float)
    den = 2 * tp + (cm.sum(0) - tp) + (cm.sum(1) - tp)
    f1 = np.where(den > 0, 2 * tp / np.where(den > 0, den, 1), 0.0)   # zero_division=0, like sklearn
    return float(f1.mean())


def per_class(cm):
    out = {}
    for i, l in enumerate(LABELS):
        tp, fp, fn = int(cm[i, i]), int(cm[:, i].sum() - cm[i, i]), int(cm[i, :].sum() - cm[i, i])
        pr = tp / (tp + fp) if tp + fp else None
        rc = tp / (tp + fn) if tp + fn else None
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        out[l] = {"precision": pr, "recall": rc, "f1": f1, "support": int(cm[i].sum()), "predicted": int(cm[:, i].sum())}
    return out


def cluster_bootstrap_macro_f1(t, p, groups, n_boot=1000, seed=42):
    """Resample whole documents (clusters) with replacement; percentile 95% CI of macro-F1."""
    rng = np.random.default_rng(seed)
    g = pd.Series(groups).astype(str)
    members = [np.flatnonzero(g.values == k) for k in g.unique()]
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(members), len(members))
        ix = np.concatenate([members[j] for j in pick])
        vals.append(macro_f1_from_cm(confusion_counts(t[ix], p[ix])))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"low": float(lo), "high": float(hi), "n_clusters": len(members), "n_boot": n_boot, "seed": seed}


def confidence_block(df, t, p, bins=10):
    if not all(c in df.columns for c in PROB_COLS):
        return {"available": False, "reason": "no probability columns (e.g. majority/SVM baselines)"}
    P = df[PROB_COLS].to_numpy(float)
    if not np.allclose(P.sum(1), 1, atol=1e-3):
        return {"available": False, "reason": "probabilities do not sum to 1"}
    conf, correct = P.max(1), (t == p)
    edges = np.linspace(0, 1, bins + 1)
    which = np.minimum(np.digitize(conf, edges[1:-1]), bins - 1)
    rel, ece = [], 0.0
    for b in range(bins):
        m = which == b
        if m.any():
            acc, c = float(correct[m].mean()), float(conf[m].mean())
            ece += m.mean() * abs(acc - c)
            rel.append({"bin": f"{edges[b]:.1f}-{edges[b+1]:.1f}", "n": int(m.sum()), "mean_confidence": c, "accuracy": acc})
    hist = lambda v: np.histogram(v, bins=edges)[0].tolist()
    return {"available": True, "ece": float(ece), "reliability": rel, "bin_edges": edges.tolist(),
            "hist_correct": hist(conf[correct]), "hist_incorrect": hist(conf[~correct]),
            "mean_conf_correct": float(conf[correct].mean()) if correct.any() else None,
            "mean_conf_incorrect": float(conf[~correct].mean()) if (~correct).any() else None,
            "warning": "fewer than 50 predictions: calibration estimates are unreliable" if len(df) < 50 else None,
            "note": "softmax outputs are not calibrated probabilities; ECE here is descriptive"}


def _examples(df, t, p, info, k):
    ids = df["span_id"].astype(str).to_numpy()
    probs = df[PROB_COLS].to_numpy(float).max(1) if all(c in df.columns for c in PROB_COLS) else None
    wrong = np.flatnonzero(t != p)
    def order(ix):
        if probs is not None:
            return sorted(ix, key=lambda i: (-probs[i], ids[i]))
        return sorted(ix, key=lambda i: ids[i])
    def row(i):
        r = {"span_id": ids[i], "true": LABELS[t[i]], "pred": LABELS[p[i]],
             "confidence": float(probs[i]) if probs is not None else None}
        if info is not None and ids[i] in info.index:
            for c in ("text", "context_before", "context_after", "document_id", "source_id"):
                if c in info.columns:
                    r[c] = None if pd.isna(info.loc[ids[i], c]) else str(info.loc[ids[i], c])
        return r
    pairs = {}
    for i in wrong:
        pairs.setdefault((LABELS[t[i]], LABELS[p[i]]), []).append(i)
    by_pair = {f"{a}->{b}": [row(i) for i in order(ix)[:k]]
               for (a, b), ix in sorted(pairs.items(), key=lambda kv: -len(kv[1]))[:6]}
    fp = {l: [row(i) for i in order([i for i in wrong if p[i] == j])[:k]] for j, l in enumerate(LABELS)}
    fn = {l: [row(i) for i in order([i for i in wrong if t[i] == j])[:k]] for j, l in enumerate(LABELS)}
    return {"selection_rule": "most confident errors first (ties by span_id)" if probs is not None
            else "span_id order (no probabilities available)",
            "by_confusion_pair": by_pair, "false_positives_by_class": fp, "false_negatives_by_class": fn}


def _slices(df, t, p, info):
    if info is None:
        return {}
    j = df[["span_id"]].astype(str).join(info, on="span_id")
    out = {}
    def add(name, keys):
        for k in sorted(set(keys.dropna())):
            m = (keys == k).to_numpy()
            if not m.any():
                continue
            cm = confusion_counts(t[m], p[m])
            out.setdefault(name, []).append({"slice": str(k), "n": int(m.sum()), "accuracy": float((t[m] == p[m]).mean()),
                                             "macro_f1": macro_f1_from_cm(cm),
                                             "unreliable": bool(m.sum() < MIN_SLICE_N)})
    if "text" in j.columns:
        n = j["text"].fillna("").astype(str).str.split().str.len()
        add("span_length_tokens", pd.cut(n, [0, 1, 3, 8, 10_000], labels=["1", "2-3", "4-8", "9+"]).astype(object))
    if "source_id" in j.columns:
        add("source_id", j["source_id"])
    return out


def analyze(pred_df, dataset_df=None, data_status="unknown", valid_for_scientific_claims=False,
            split="test", n_boot=1000, seed=42, top_k=5):
    need = {"split", "span_id", "true", "pred"}
    if not need <= set(pred_df.columns):
        raise ValueError(f"predictions must have columns {sorted(need)}")
    if "model" not in pred_df.columns:
        pred_df = pred_df.assign(model="model")
    info = None
    if dataset_df is not None and "span_id" in dataset_df.columns:
        info = dataset_df.astype({"span_id": str}).drop_duplicates("span_id").set_index("span_id")
    res = {"data_status": data_status, "valid_for_scientific_claims": bool(valid_for_scientific_claims),
           "split_analysed": split, "seed": seed, "models": {}}
    if split == "test":
        res["caveat"] = TEST_CAVEAT
    for model, g in pred_df[pred_df.split == split].groupby("model", sort=True):
        g = g.reset_index(drop=True)
        bad = set(g.true) | set(g.pred)
        if not bad <= set(LABELS):
            raise ValueError(f"unknown labels in predictions: {sorted(bad - set(LABELS))}")
        t, p = _idx(g.true), _idx(g.pred)
        cm = confusion_counts(t, p)
        rows = cm.sum(1, keepdims=True)
        groups = None
        if info is not None and "document_id" in info.columns:
            groups = g.span_id.astype(str).map(info["document_id"])
            groups = None if groups.isna().any() else groups.values
        boot_kind = "document-clustered" if groups is not None else "span-level (ignores document clustering)"
        ci = cluster_bootstrap_macro_f1(t, p, groups if groups is not None else np.arange(len(g)), n_boot, seed)
        warn = []
        if ci["n_clusters"] < 10:
            warn.append(f"only {ci['n_clusters']} bootstrap clusters; the interval is unreliable")
        if len(g) < MIN_SLICE_N:
            warn.append(f"only {len(g)} examples; every number here is unstable")
        pairs = [{"true": LABELS[i], "pred": LABELS[j], "count": int(cm[i, j]),
                  "rate_of_true_class": float(cm[i, j] / rows[i, 0]) if rows[i, 0] else None}
                 for i in range(3) for j in range(3) if i != j and cm[i, j]]
        res["models"][model] = {
            "n": int(len(g)), "accuracy": float((t == p).mean()), "macro_f1": macro_f1_from_cm(cm),
            "macro_f1_ci95": {**ci, "kind": boot_kind}, "per_class": per_class(cm),
            "confusion": {"labels": LABELS, "counts": cm.tolist(),
                          "row_normalised": [[(float(v / rows[i, 0]) if rows[i, 0] else None) for v in cm[i]] for i in range(3)]},
            "top_confusions": sorted(pairs, key=lambda r: -r["count"]),
            "true_distribution": {l: int(cm[i].sum()) for i, l in enumerate(LABELS)},
            "predicted_distribution": {l: int(cm[:, i].sum()) for i, l in enumerate(LABELS)},
            "confidence": confidence_block(g, t, p), "examples": _examples(g, t, p, info, top_k),
            "slices": _slices(g, t, p, info), "warnings": warn}
    if not res["models"]:
        res["warnings"] = [f"no predictions for split {split!r}"]
    return res


def to_markdown(res):
    L = []
    if not res["valid_for_scientific_claims"]:
        L += ["> **NOT RESEARCH** — data_status: " + str(res["data_status"]) + ". Smoke/fixture or unvalidated output; "
              "do not cite any number below as a result.", ""]
    L += [f"# Error analysis ({res['split_analysed']} split)", ""]
    if res.get("caveat"):
        L += [f"*{res['caveat']}*", ""]
    for m, r in res["models"].items():
        ci = r["macro_f1_ci95"]
        L += [f"## {m}", f"n={r['n']} · accuracy {r['accuracy']:.3f} · macro-F1 {r['macro_f1']:.3f} "
              f"(95% CI {ci['low']:.3f}–{ci['high']:.3f}, {ci['kind']}, {ci['n_clusters']} clusters, {ci['n_boot']} resamples)", ""]
        for w in r["warnings"]:
            L.append(f"- WARNING: {w}")
        L += ["", "| class | precision | recall | F1 | support | predicted |", "|---|---:|---:|---:|---:|---:|"]
        f = lambda v: "n/a" if v is None else f"{v:.3f}"
        for l, v in r["per_class"].items():
            L.append(f"| {l} | {f(v['precision'])} | {f(v['recall'])} | {f(v['f1'])} | {v['support']} | {v['predicted']} |")
        L += ["", "Top confusions: " + (", ".join(f"{c['true']}→{c['pred']} ×{c['count']}" for c in r["top_confusions"][:5]) or "none"), ""]
        c = r["confidence"]
        L.append(f"Confidence: ECE {c['ece']:.3f}; mean confidence correct {f(c['mean_conf_correct'])} vs incorrect {f(c['mean_conf_incorrect'])}"
                 if c["available"] else f"Confidence: not available ({c['reason']})")
        L += ["", f"Example selection: {r['examples']['selection_rule']}", ""]
    return "\n".join(L)


def write_error_analysis(pred_csv, out_dir, dataset_csv=None, split="test", n_boot=1000, seed=42, top_k=5):
    pred_csv, out = Path(pred_csv), Path(out_dir)
    status, valid = "unknown", False
    rj = pred_csv.parent / "results.json"
    if rj.exists():
        r = json.loads(rj.read_text(encoding="utf-8"))
        status = r.get("data_status", "unknown")
        valid = bool(r.get("valid_for_scientific_claims", status == "research" and "models" in r))
    res = analyze(pd.read_csv(pred_csv), pd.read_csv(dataset_csv) if dataset_csv else None,
                  status, valid, split, n_boot, seed, top_k)
    res["source_predictions"] = pred_csv.name
    out.mkdir(parents=True, exist_ok=True)
    (out / f"error_analysis_{split}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    (out / f"error_analysis_{split}.md").write_text(to_markdown(res), encoding="utf-8")
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--dataset")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="validation", choices=["validation", "test"])
    a = ap.parse_args()
    r = write_error_analysis(a.predictions, a.out, a.dataset, a.split)
    print(f"wrote {a.out}  (valid_for_scientific_claims={r['valid_for_scientific_claims']})")
