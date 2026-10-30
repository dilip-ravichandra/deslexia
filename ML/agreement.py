"""Inter-annotator agreement (Task 03).

Computes only from real annotation tables. Undefined values are returned as None
(never coerced to 1.0 or 0.0). Small samples are flagged, not hidden.
"""
import itertools
import json
from collections import Counter, defaultdict

import pandas as pd

MIN_SPANS_INTERPRETABLE = 30


def cohen_kappa(a, b):
    """Unweighted Cohen's kappa for two aligned label sequences. None if undefined."""
    if len(a) != len(b):
        raise ValueError("sequences must be aligned")
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe == 1.0:
        return None  # both annotators used one identical label: kappa undefined
    return (po - pe) / (1 - pe)


def krippendorff_alpha_nominal(units):
    """units: iterable of lists of labels (one list per unit, missing values omitted).
    Units with <2 labels are ignored. Returns None if undefined."""
    o = defaultdict(float)  # coincidence matrix
    for labels in units:
        m = len(labels)
        if m < 2:
            continue
        for i, j in itertools.permutations(range(m), 2):
            o[(labels[i], labels[j])] += 1.0 / (m - 1)
    n = sum(o.values())
    if n <= 1:
        return None
    nc = defaultdict(float)
    for (c, _), v in o.items():
        nc[c] += v
    do = sum(v for (c, k), v in o.items() if c != k)
    de = sum(nc[c] * nc[k] for c in nc for k in nc if c != k)
    if de == 0:
        return None  # only one category observed
    return 1.0 - (n - 1) * do / de


def _units(long, span_ids=None, relabel=None):
    out = []
    for sid, g in long.groupby("span_id"):
        if span_ids is not None and sid not in span_ids:
            continue
        labels = list(g["category"])
        if relabel:
            labels = [relabel(x) for x in labels]
        out.append(labels)
    return out


def agreement_report(long, adjudications=None, queue=None):
    """long: columns span_id, annotator_id, category."""
    multi = long.groupby("span_id")["annotator_id"].nunique()
    multi_ids = set(multi[multi >= 2].index)
    rep = {
        "n_annotations": int(len(long)),
        "n_spans": int(long["span_id"].nunique()),
        "n_spans_multi_annotated": len(multi_ids),
        "annotators": sorted(long["annotator_id"].unique().tolist()),
    }
    rep["warnings"] = []
    if len(multi_ids) < MIN_SPANS_INTERPRETABLE:
        rep["warnings"].append(
            f"only {len(multi_ids)} multi-annotated spans (<{MIN_SPANS_INTERPRETABLE}); "
            "agreement estimates are unstable and must not be reported as final")
    sub = long[long["span_id"].isin(multi_ids)]
    rep["krippendorff_alpha_nominal"] = krippendorff_alpha_nominal(_units(sub))
    raw = [len(set(l)) == 1 for l in _units(sub)]
    rep["raw_percent_agreement"] = (sum(raw) / len(raw)) if raw else None

    pairs = {}
    wide = sub.pivot(index="span_id", columns="annotator_id", values="category")
    for a, b in itertools.combinations(sorted(wide.columns), 2):
        both = wide[[a, b]].dropna()
        pairs[f"{a}__{b}"] = {"n": int(len(both)),
                              "cohen_kappa": cohen_kappa(both[a].tolist(), both[b].tolist()),
                              "percent_agreement": float((both[a] == both[b]).mean()) if len(both) else None}
    rep["pairwise"] = pairs

    cats = sorted(long["category"].unique())
    rep["per_class_alpha_one_vs_rest"] = {
        c: krippendorff_alpha_nominal(_units(sub, relabel=lambda x, c=c: x == c)) for c in cats}
    rep["label_distribution_all_annotations"] = long["category"].value_counts().to_dict()

    conf = Counter()
    for labels in _units(sub):
        for x, y in itertools.combinations(sorted(labels), 2):
            if x != y:
                conf[f"{x}|{y}"] += 1
    rep["conflict_pair_counts"] = dict(conf.most_common())

    if queue is not None:
        done = 0 if adjudications is None else len(adjudications)
        rep["adjudication"] = {"queued": int(len(queue)) + done,
                               "adjudicated": int(done), "pending": int(len(queue))}
    return rep


def conflict_report(long, pool=None):
    """One row per multi-annotated span with disagreement."""
    rows = []
    for sid, g in long.groupby("span_id"):
        if g["annotator_id"].nunique() >= 2 and g["category"].nunique() > 1:
            rows.append(dict(span_id=sid,
                             labels="|".join(f"{a}:{c}" for a, c in zip(g["annotator_id"], g["category"]))))
    df = pd.DataFrame(rows, columns=["span_id", "labels"])
    if pool is not None and len(df):
        df = df.merge(pool[["span_id", "document_id", "text"]], on="span_id", how="left")
    return df


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", required=True, help="long-format CSV (span_id, annotator_id, category)")
    ap.add_argument("--out", default="ARTIFACTS/agreement.json")
    a = ap.parse_args()
    from pathlib import Path
    r = agreement_report(pd.read_csv(a.annotations))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=2), encoding="utf-8")
    print(json.dumps(r, indent=2))
