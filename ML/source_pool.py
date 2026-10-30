"""Build an UNLABELLED source-passage pool from a free, licensed text corpus (HG-03 support).

This produces text only. It never produces labels: support categories must come from
human annotators (HG-01). Run the CLI on your own machine (needs `pip install datasets`);
the Claude sandbox cannot reach huggingface.co.
"""
import re
import argparse
import random
from pathlib import Path

import pandas as pd

LICENSE = "CC-BY-SA-3.0"
DEFAULT_REPO = "juno-labs/simple_wikipedia"


def passages(text, min_words=25, max_words=120):
    """Split an article into paragraph-sized passages within a word range."""
    out = []
    for p in re.split(r"\n\s*\n", text or ""):
        p = re.sub(r"\s+", " ", p).strip()
        if p.startswith(("#", "|", "*", "-")):  # headings, tables, lists
            continue
        if min_words <= len(p.split()) <= max_words:
            out.append(p)
    return out


def build_pool(rows, n_articles=200, per_article=3, seed=42, repo=DEFAULT_REPO, license_=LICENSE):
    """rows: iterable of dicts with page_id, title, content. Deterministic for a seed."""
    rows = [r for r in rows if r.get("content") and not r.get("error")]
    rng = random.Random(seed)
    rng.shuffle(rows)
    recs = []
    for r in rows:
        ps = passages(r["content"])
        if not ps:
            continue
        for i, p in enumerate(ps[:per_article]):
            recs.append(dict(
                source_id=f"{repo}", document_id=f"wp_{r['page_id']}",
                passage_id=f"wp_{r['page_id']}_p{i}", text=p, title=r.get("title", ""),
                source_license=license_,
                source_url=f"https://simple.wikipedia.org/?curid={r['page_id']}",
                attribution="Wikipedia contributors (see page history), CC BY-SA 3.0"))
        if len({x["document_id"] for x in recs}) >= n_articles:
            break
    return pd.DataFrame(recs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--n-articles", type=int, default=200)
    ap.add_argument("--scan", type=int, default=5000, help="rows to stream before sampling")
    ap.add_argument("--out", default="DATA/source_pool.csv")
    a = ap.parse_args()
    from datasets import load_dataset  # user-side dependency
    ds = load_dataset(a.repo, split="train", streaming=True)
    rows = [r for _, r in zip(range(a.scan), ds)]
    pool = build_pool(rows, a.n_articles)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(a.out, index=False)
    print(f"wrote {len(pool)} passages from {pool.document_id.nunique()} articles -> {a.out}")
