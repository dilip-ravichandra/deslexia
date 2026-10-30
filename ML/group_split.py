"""Group-aware train/validation/test splitting with leakage report and frozen manifest (Task 04).

Whole groups (default: document_id) are assigned to exactly one split. Assignment is
deterministic for a given seed: groups are shuffled, then each goes to the split with
the largest remaining row deficit against its target share.
"""
import json
import random
from pathlib import Path

import pandas as pd

from ML.data_validation import file_sha256

MIN_GROUPS = 3


def split(df, group="document_id", seed=42, train=0.70, validation=0.15):
    if not 0 < train < 1 or not 0 < validation < 1 or train + validation >= 1:
        raise ValueError("need train>0, validation>0 and train+validation<1")
    if group not in df.columns:
        raise ValueError(f"missing group column {group!r}")
    if df[group].isna().any():
        raise ValueError(f"null values in group column {group!r}")
    sizes = df.groupby(group).size()
    if len(sizes) < MIN_GROUPS:
        raise ValueError(f"need at least {MIN_GROUPS} distinct {group} values, got {len(sizes)}")
    targets = {"train": train * len(df), "validation": validation * len(df),
               "test": (1 - train - validation) * len(df)}
    names = ["train", "validation", "test"]
    rng = random.Random(seed)
    groups = sorted(sizes.index.tolist(), key=str)
    rng.shuffle(groups)
    filled = {n: 0 for n in names}
    assigned = {n: [] for n in names}
    # guarantee every split gets a group first (largest-remaining-deficit order)
    for g in groups:
        empty = [n for n in names if not assigned[n]]
        if empty and len(groups) - sum(len(v) for v in assigned.values()) <= len(empty):
            pick = max(empty, key=lambda n: targets[n] - filled[n])
        else:
            pick = max(names, key=lambda n: (targets[n] - filled[n]) / targets[n])
        assigned[pick].append(g)
        filled[pick] += int(sizes[g])
    out = [df[df[group].isin(assigned[n])].copy() for n in names]
    tr, va, te = out
    assert not set(tr[group]) & set(va[group])
    assert not set(tr[group]) & set(te[group])
    assert not set(va[group]) & set(te[group])
    return tr, va, te


def _key(df):
    cols = [c for c in ["text", "context_before", "context_after"] if c in df.columns]
    norm = df[cols].fillna("").astype(str).apply(lambda s: s.str.strip().str.lower())
    return set(map(tuple, norm.values.tolist()))


def leakage_report(tr, va, te, group="document_id", label="category", extra_groups=("source_id",)):
    parts = {"train": tr, "validation": va, "test": te}
    rep = {"sizes": {k: int(len(v)) for k, v in parts.items()},
           "n_groups": {k: int(v[group].nunique()) for k, v in parts.items()},
           "leaks": {}, "warnings": []}
    pairs = [("train", "validation"), ("train", "test"), ("validation", "test")]
    for a, b in pairs:
        rep["leaks"][f"{a}|{b}|{group}"] = sorted(map(str, set(parts[a][group]) & set(parts[b][group])))
        rep["leaks"][f"{a}|{b}|duplicate_span_context"] = len(_key(parts[a]) & _key(parts[b]))
    for g in extra_groups:  # source overlap is informational (domain shift vs leakage)
        if all(g in v.columns for v in parts.values()):
            for a, b in pairs:
                ov = sorted(map(str, set(parts[a][g]) & set(parts[b][g])))
                rep["leaks"][f"{a}|{b}|{g}"] = ov
    rep["leaks_found"] = any(bool(v) for k, v in rep["leaks"].items()
                             if k.endswith(group) or k.endswith("duplicate_span_context"))
    if label in tr.columns:
        rep["label_distribution"] = {k: v[label].value_counts().to_dict() for k, v in parts.items()}
        all_labels = set(pd.concat(parts.values())[label])
        for k, v in parts.items():
            miss = all_labels - set(v[label])
            if miss:
                rep["warnings"].append(f"{k} split has no examples of {sorted(miss)}")
    for k, v in parts.items():
        if len(v) < 30:
            rep["warnings"].append(f"{k} has only {len(v)} rows; metrics will be unstable")
    return rep


def build_manifest(df, tr, va, te, dataset_path, group="document_id", seed=42,
                   train=0.70, validation=0.15):
    return {
        "frozen": True, "group": group, "seed": seed,
        "ratios": {"train": train, "validation": validation, "test": round(1 - train - validation, 6)},
        "dataset_file": Path(dataset_path).name, "dataset_sha256": file_sha256(dataset_path),
        "splits": {n: {"groups": sorted(map(str, p[group].unique())),
                       "span_ids": sorted(p["span_id"].astype(str)) if "span_id" in p else None}
                   for n, p in zip(["train", "validation", "test"], [tr, va, te])},
        "leakage": leakage_report(tr, va, te, group=group),
    }


def freeze(dataset_path, out_path, group="document_id", seed=42, train=0.70, validation=0.15,
           force=False):
    out = Path(out_path)
    if out.exists() and not force:
        raise FileExistsError(f"{out} is frozen; refusing to overwrite (use force only with a DECISIONS.md entry)")
    df = pd.read_csv(dataset_path)
    tr, va, te = split(df, group, seed, train, validation)
    m = build_manifest(df, tr, va, te, dataset_path, group, seed, train, validation)
    if m["leakage"]["leaks_found"]:
        raise RuntimeError("leakage detected; manifest not written")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2), encoding="utf-8")
    return m


def load_frozen(manifest_path, dataset_path):
    """Return (train, val, test) exactly as frozen; fails if the dataset changed."""
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if file_sha256(dataset_path) != m["dataset_sha256"]:
        raise ValueError("dataset changed since split was frozen; create a new versioned split")
    df = pd.read_csv(dataset_path)
    g = m["group"]
    if m.get("frozen") is not True or g not in df or df[g].isna().any():
        raise ValueError("invalid frozen split manifest")
    names = ["train", "validation", "test"]
    groups = [set(m["splits"][n]["groups"]) for n in names]
    if any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError("frozen split has overlapping groups")
    if set.union(*groups) != set(df[g].astype(str)):
        raise ValueError("frozen split does not cover the dataset exactly")
    parts = tuple(df[df[g].astype(str).isin(groups[i])].copy() for i in range(3))
    if any(p.empty for p in parts):
        raise ValueError("frozen split contains an empty partition")
    for n, p in zip(names, parts):
        expected = m["splits"][n].get("span_ids")
        if expected is not None and ("span_id" not in p or sorted(p.span_id.astype(str)) != expected):
            raise ValueError("frozen span assignments do not match group assignments")
    if leakage_report(*parts, group=g)["leaks_found"]:
        raise ValueError("leakage in frozen split")
    return parts


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="DATA/split_manifest.json")
    ap.add_argument("--group", default="document_id")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    print(json.dumps(freeze(a.csv, a.out, a.group, a.seed)["leakage"], indent=2))
