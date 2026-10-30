import pandas as pd
import pytest
from pathlib import Path
from ML.data_validation import check, validate, dataset_manifest, file_sha256

SEED = Path(__file__).resolve().parents[1] / "DATA" / "seed_examples.csv"


def row(**kw):
    base = dict(source_id="s", document_id="d1", span_id="d1_1", text="word",
                context_before="a", context_after="b", category="VOCABULARY",
                annotator_id="ann1", guideline_version="v1", confidence=4,
                rationale="r", source_license="CC-BY-4.0",
                created_at="2026-01-01T00:00:00Z")
    base.update(kw)
    return base


def df(*rows):
    return pd.DataFrame(list(rows))


def test_seed_passes_smoke_but_fails_research():
    assert len(validate(SEED, "smoke")) == 3
    rep = check(pd.read_csv(SEED), "research")
    assert not rep.ok  # seed data can never be research data


def test_valid_research_rows_pass():
    assert check(df(row(), row(span_id="d1_2", category="SYNTACTIC")), "research").ok


@pytest.mark.parametrize("bad", [
    dict(category="vocabulary"), dict(category="NOPE"), dict(text=" "),
    dict(annotator_id="llm"), dict(source_license="unknown"),
    dict(confidence=9), dict(created_at="yesterday"), dict(guideline_version=""),
])
def test_research_mode_rejects_bad_rows(bad):
    assert not check(df(row(**bad)), "research").ok


def test_duplicate_span_id_rejected():
    assert not check(df(row(), row()), "smoke").ok


def test_missing_provenance_column_rejected_in_research():
    d = df(row()).drop(columns=["source_license"])
    assert not check(d, "research").ok
    assert check(d, "smoke").ok


def test_manifest_hash_is_stable_and_reports_distribution():
    m = dataset_manifest(SEED, "smoke")
    assert m["sha256"] == file_sha256(SEED)
    assert m["label_distribution"] == {"VOCABULARY": 1, "SYNTACTIC": 1, "CONCEPTUAL": 1}
