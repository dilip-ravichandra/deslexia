"""Annotation workflow (Task 02): batches, import/export, double annotation, adjudication.

Rules enforced here (CLAUDE.md, ADR-008):
- Batch files sent to annotators never contain labels or AI suggestions.
- Only human annotator ids are accepted on import.
- Gold labels come only from unanimous human annotation or a named human adjudicator.
  Disagreements are never auto-resolved (no silent majority vote, no model label).
"""
import random
from pathlib import Path

import pandas as pd

from ML.data_validation import LABELS, NON_GOLD_ANNOTATORS

BATCH_COLS = ["source_id", "document_id", "span_id", "text",
              "context_before", "context_after"]
ANNOT_COLS = ["span_id", "annotator_id", "category", "confidence",
              "rationale", "guideline_version", "created_at"]
ADJ_COLS = ["span_id", "adjudicator_id", "final_category", "note", "created_at"]


def make_batches(pool, annotators, copies=2, seed=42):
    """Assign each span to `copies` distinct annotators, balanced by load.
    Returns {annotator_id: DataFrame without any label column}."""
    if copies < 2:
        raise ValueError("copies must be at least 2 distinct human annotators")
    if copies > len(annotators):
        raise ValueError("copies cannot exceed number of annotators")
    if len(set(annotators)) != len(annotators):
        raise ValueError("annotator ids must be unique")
    bad = [a for a in annotators if not a.strip() or a != a.strip() or a.lower() in NON_GOLD_ANNOTATORS
           or any(c in a for c in '/\\') or a in {'.', '..'}]
    if bad:
        raise ValueError(f"non-human annotator ids not allowed: {bad}")
    missing = [c for c in BATCH_COLS if c not in pool.columns]
    if missing:
        raise ValueError(f"pool missing columns: {missing}")
    if pool.empty or pool.span_id.isna().any() or pool.span_id.astype(str).str.strip().eq("").any() or pool.span_id.duplicated().any():
        raise ValueError("pool must contain unique nonblank span_id values")
    rng = random.Random(seed)
    load = {a: 0 for a in annotators}
    assign = {a: [] for a in annotators}
    for i in rng.sample(range(len(pool)), len(pool)):
        chosen = sorted(annotators, key=lambda a: (load[a], rng.random()))[:copies]
        for a in chosen:
            load[a] += 1
            assign[a].append(i)
    return {a: pool.iloc[sorted(ix)][BATCH_COLS].assign(
        annotator_id=a, category="", confidence="", rationale="") .reset_index(drop=True)
        for a, ix in assign.items()}


def export_batches(batches, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for a, df in batches.items():
        p = out / f"batch_{a}.csv"
        df.to_csv(p, index=False)
        paths.append(p)
    return paths


def import_annotations(path, pool_span_ids, guideline_version, expected_annotator=None):
    """Validate and normalise one annotator's returned file."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for c in ["span_id", "annotator_id", "category", "confidence"]:
        if c not in df.columns:
            raise ValueError(f"missing column {c}")
    ids = set(df["annotator_id"])
    if len(ids) != 1:
        raise ValueError(f"file must contain exactly one annotator_id, found {sorted(ids)}")
    ann = ids.pop()
    if ann.strip().lower() in NON_GOLD_ANNOTATORS or not ann.strip() or ann != ann.strip():
        raise ValueError(f"non-human annotator id: {ann!r}")
    if expected_annotator and ann != expected_annotator:
        raise ValueError(f"annotator_id {ann!r} != expected {expected_annotator!r}")
    if df["span_id"].duplicated().any():
        raise ValueError("duplicate span_id in annotation file")
    unknown = set(df["span_id"]) - set(pool_span_ids)
    if unknown:
        raise ValueError(f"span_ids not in pool: {sorted(unknown)[:5]}")
    blank = df["category"].str.strip() == ""
    if blank.any():
        raise ValueError(f"{int(blank.sum())} unlabeled rows; return only completed work or finish the batch")
    badlab = set(df["category"]) - LABELS
    if badlab:
        raise ValueError(f"invalid labels: {sorted(badlab)}")
    conf = pd.to_numeric(df["confidence"], errors="coerce")
    if conf.isna().any() or not conf.between(1, 5).all() or not conf.mod(1).eq(0).all():
        raise ValueError("confidence must be 1..5")
    df = df.copy()
    df["confidence"] = conf.astype(int)
    df["guideline_version"] = guideline_version
    if "created_at" not in df.columns or (df["created_at"] == "").any():
        df["created_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    if "rationale" not in df.columns:
        df["rationale"] = ""
    return df[ANNOT_COLS]


def merge_annotations(frames):
    long = pd.concat(frames, ignore_index=True)
    if long.duplicated(["span_id", "annotator_id"]).any():
        raise ValueError("same annotator labelled the same span twice across files")
    return long


def resolve(long, adjudications=None, min_annotators=2):
    """Return (gold, queue). gold only from unanimity or human adjudication."""
    if min_annotators < 2:
        raise ValueError("min_annotators must be at least 2")
    if long.duplicated(["span_id", "annotator_id"]).any():
        raise ValueError("duplicate annotation by the same annotator")
    ids = long.annotator_id.fillna("").astype(str).str.strip().str.lower()
    if ids.eq("").any() or ids.isin(NON_GOLD_ANNOTATORS).any() or not long.category.isin(LABELS).all():
        raise ValueError("annotations require valid human ids and labels")
    adj = {}
    if adjudications is not None and len(adjudications):
        a = adjudications
        if a["span_id"].duplicated().any():
            raise ValueError("duplicate adjudication for a span")
        if a["adjudicator_id"].str.lower().isin(NON_GOLD_ANNOTATORS).any() or \
           (a["adjudicator_id"].str.strip() == "").any():
            raise ValueError("adjudicator must be a named human")
        if (~a["final_category"].isin(LABELS)).any():
            raise ValueError("invalid adjudicated label")
        adj = a.set_index("span_id").to_dict("index")
    gold, queue = [], []
    for sid, g in long.groupby("span_id", sort=True):
        labels = list(g["category"])
        if len(labels) < min_annotators:
            queue.append(dict(span_id=sid, reason="insufficient_annotations",
                              labels="|".join(labels), annotators="|".join(g["annotator_id"])))
            continue
        unanimous = len(set(labels)) == 1
        uncertain = "OTHER_UNCERTAIN" in labels
        if sid in adj:
            gold.append(dict(span_id=sid, category=adj[sid]["final_category"],
                             resolution="adjudicated", resolved_by=adj[sid]["adjudicator_id"]))
        elif unanimous and not uncertain:
            gold.append(dict(span_id=sid, category=labels[0], resolution="unanimous",
                             resolved_by="|".join(sorted(g["annotator_id"]))))
        else:
            queue.append(dict(span_id=sid,
                              reason="uncertain" if unanimous else "disagreement",
                              labels="|".join(labels), annotators="|".join(g["annotator_id"])))
    cols_g = ["span_id", "category", "resolution", "resolved_by"]
    cols_q = ["span_id", "reason", "labels", "annotators"]
    return pd.DataFrame(gold, columns=cols_g), pd.DataFrame(queue, columns=cols_q)


def adjudication_sheet(queue, pool):
    """Queue joined with context and annotator labels for the adjudicator UI/CSV."""
    j = queue.merge(pool[BATCH_COLS], on="span_id", how="left")
    j["adjudicator_id"] = ""
    j["final_category"] = ""
    j["note"] = ""
    return j


def write_resolution(pool_path, annotation_paths, out_dir, guideline_version, adjudication_path=None):
    """Turn returned human files into a complete, versioned training-data package.

    Keeps agreement before adjudication, raw labels and source provenance. Does
    not produce labels or declare a dataset final while a queue remains.
    """
    import json
    from ML.agreement import agreement_report
    from ML.data_validation import check, file_sha256
    pool = pd.read_csv(pool_path, dtype=str, keep_default_na=False)
    for c in [*BATCH_COLS, "source_license"]:
        if c not in pool:
            raise ValueError(f"pool missing column {c}")
    if pool.span_id.duplicated().any() or pool.span_id.str.strip().eq("").any() or pool.empty:
        raise ValueError("pool requires unique nonblank span ids")
    out = Path(out_dir)
    if out.exists():
        raise FileExistsError("annotation output exists; choose a new versioned directory")
    frames = [import_annotations(p, pool.span_id, guideline_version) for p in annotation_paths]
    long = merge_annotations(frames)
    adj = pd.read_csv(adjudication_path, dtype=str, keep_default_na=False) if adjudication_path else None
    if adj is not None and not set(adj.span_id) <= set(long.span_id):
        raise ValueError("adjudication span ids not in returned annotations")
    gold, queue = resolve(long, adj)
    unreturned = pool[~pool.span_id.isin(long.span_id)]
    if len(unreturned):
        queue = pd.concat([queue, pd.DataFrame({"span_id": unreturned.span_id,
            "reason": "no_annotations", "labels": "", "annotators": ""})], ignore_index=True)
    dataset = pool.merge(gold, on="span_id", how="inner", validate="one_to_one")
    # Discard any pre-existing suggested labels before joining human decisions.
    if "category_x" in dataset:
        dataset = dataset.drop(columns="category_x").rename(columns={"category_y": "category"})
    latest = long.groupby("span_id").created_at.max()
    conf = long.groupby("span_id").confidence.min()
    rationales = long.groupby("span_id")[["annotator_id", "rationale"]].apply(
        lambda g: " | ".join(f"{r.annotator_id}: {r.rationale}" for r in g.itertuples()))
    dataset["annotator_id"] = dataset.resolved_by
    dataset["guideline_version"] = guideline_version
    dataset["confidence"] = dataset.span_id.map(conf)
    dataset["rationale"] = dataset.span_id.map(rationales)
    dataset["created_at"] = dataset.span_id.map(latest)
    rep = check(dataset, "research")
    agreement = agreement_report(long, adj, queue)
    inputs = [pool_path, *annotation_paths] + ([adjudication_path] if adjudication_path else [])
    manifest = {"schema_version": "1.0", "guideline_version": guideline_version,
                "input_hashes": [{"file": Path(p).name, "sha256": file_sha256(p)} for p in inputs],
                "n_pool": len(pool), "n_resolved": len(dataset), "n_pending": len(queue),
                "ready_for_dataset_review": bool(rep.ok and queue.empty),
                "validation": rep.to_dict(),
                "note": "Structural checks do not prove annotators were human or confirm content licensing. Review before freezing."}
    out.mkdir(parents=True)
    long.to_csv(out / "annotations_long.csv", index=False)
    dataset.to_csv(out / "gold_resolved.csv", index=False)
    adjudication_sheet(queue, pool).to_csv(out / "adjudication_queue.csv", index=False)
    (out / "agreement.json").write_text(json.dumps(agreement, indent=2), encoding="utf-8")
    (out / "annotation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    batch = sub.add_parser("batches", help="prepare blank files; never label text")
    batch.add_argument("--pool", required=True)
    batch.add_argument("--annotators", nargs="+", required=True)
    batch.add_argument("--copies", type=int, default=2)
    batch.add_argument("--seed", type=int, default=42)
    batch.add_argument("--out", required=True)
    res = sub.add_parser("resolve", help="import completed human files, agreement and adjudication queue")
    res.add_argument("--pool", required=True)
    res.add_argument("--annotations", nargs="+", required=True)
    res.add_argument("--guideline", required=True)
    res.add_argument("--adjudications")
    res.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.command == "batches":
        if Path(args.out).exists():
            raise FileExistsError("batch output exists; choose a new versioned directory")
        pool = pd.read_csv(args.pool, dtype=str, keep_default_na=False)
        paths = export_batches(make_batches(pool, args.annotators, args.copies, args.seed), args.out)
        print(json.dumps({"blank_batch_files": [str(p) for p in paths], "gold_labels_generated": False}, indent=2))
    else:
        print(json.dumps(write_resolution(args.pool, args.annotations, args.out, args.guideline, args.adjudications), indent=2))
