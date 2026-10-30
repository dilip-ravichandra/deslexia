"""Dataset schema validation (Task 01).

Two modes:
  smoke    - base columns only; for seed/test fixtures. Never valid as research data.
  research - provenance + annotation metadata required; seed/synthetic rows rejected.
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REQUIRED = ["source_id", "document_id", "span_id", "text",
            "context_before", "context_after", "category"]
PROVENANCE = ["annotator_id", "guideline_version", "confidence",
              "rationale", "source_license", "created_at"]
PRIMARY_LABELS = ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]
LABELS = set(PRIMARY_LABELS) | {"OTHER_UNCERTAIN"}
NON_GOLD_ANNOTATORS = {"seed", "synthetic", "ai", "model", "llm", "heuristic"}
NON_GOLD_LICENSES = {"", "unknown", "synthetic-smoke-test"}


@dataclass
class Report:
    mode: str
    rows: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors

    def to_dict(self):
        return {"mode": self.mode, "rows": self.rows, "ok": self.ok,
                "errors": self.errors, "warnings": self.warnings}


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def check(df, mode="smoke"):
    if mode not in {"smoke", "research"}:
        raise ValueError("mode must be 'smoke' or 'research'")
    rep = Report(mode=mode, rows=len(df))
    err, warn = rep.errors.append, rep.warnings.append
    if df.empty:
        err("dataset is empty")

    need = REQUIRED + (PROVENANCE if mode == "research" else [])
    missing = [c for c in need if c not in df.columns]
    if missing:
        err(f"missing columns: {missing}")
        return rep

    for c in ["source_id", "document_id", "span_id", "text", "category"]:
        bad = df[c].isna() | (df[c].astype(str).str.strip() == "")
        if bad.any():
            err(f"empty values in required column '{c}' (rows {df.index[bad].tolist()[:5]})")
    if df["span_id"].duplicated().any():
        err("duplicate span_id: " + str(df.loc[df.span_id.duplicated(), "span_id"].tolist()[:5]))

    cats = df["category"].dropna().astype(str)
    unknown = set(cats) - LABELS
    if unknown:
        err(f"unknown labels (exact uppercase match required): {sorted(unknown)}")

    key = ["document_id", "text", "context_before", "context_after"]
    if df.duplicated(subset=key).any():
        warn("duplicate (document, span, context) rows - expected only for multi-annotator files")

    if mode == "research":
        ann = df["annotator_id"].fillna("").astype(str).str.strip().str.lower()
        if ann.eq("").any() or ann.isin(NON_GOLD_ANNOTATORS).any():
            err("non-human or seed annotator_id present; not valid gold data")
        if df["source_license"].fillna("").astype(str).str.strip().str.lower().isin(NON_GOLD_LICENSES).any():
            err("missing/unknown/synthetic source_license (HG-03)")
        conf = pd.to_numeric(df["confidence"], errors="coerce")
        if conf.isna().any() or not conf.between(1, 5).all() or not conf.mod(1).eq(0).all():
            err("confidence must be an integer-like value in 1..5")
        ts = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        if ts.isna().any():
            err("created_at must be ISO-8601")
        if df["guideline_version"].fillna("").astype(str).str.strip().eq("").any():
            err("guideline_version required")
        counts = df["category"].value_counts()
        for lab in PRIMARY_LABELS:
            if counts.get(lab, 0) == 0:
                warn(f"no examples for label {lab}")
        if df["document_id"].nunique() < 10:
            warn("fewer than 10 documents: grouped splitting will be unreliable")
    return rep


def validate(path, mode="smoke"):
    """Backward-compatible: returns DataFrame or raises ValueError."""
    df = pd.read_csv(path)
    rep = check(df, mode)
    if not rep.ok:
        raise ValueError("; ".join(rep.errors))
    return df


def dataset_manifest(path, mode="research"):
    df = pd.read_csv(path)
    rep = check(df, mode)
    return {
        "file": Path(path).name, "sha256": file_sha256(path),
        "validation": rep.to_dict(),
        "label_distribution": df["category"].value_counts().to_dict(),
        "n_documents": int(df["document_id"].nunique()),
        "n_sources": int(df["source_id"].nunique()),
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--mode", default="smoke", choices=["smoke", "research"])
    ap.add_argument("--manifest-out")
    a = ap.parse_args()
    m = dataset_manifest(a.csv, a.mode)
    print(json.dumps(m, indent=2))
    if a.manifest_out:
        Path(a.manifest_out).write_text(json.dumps(m, indent=2), encoding="utf-8")
    raise SystemExit(0 if m["validation"]["ok"] else 1)
