import json
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score, precision_recall_fscore_support
from ML.error_analysis import (LABELS, analyze, confusion_counts, macro_f1_from_cm, per_class,
                               cluster_bootstrap_macro_f1, confidence_block, write_error_analysis, to_markdown, _idx)

rng = np.random.default_rng(0)


def fixture(n=60, with_probs=True):
    # SYNTHETIC FIXTURE: random labels/predictions to test the arithmetic only
    t = rng.integers(0, 3, n); p = np.where(rng.random(n) < 0.6, t, rng.integers(0, 3, n))
    df = pd.DataFrame({"model": "m", "split": "test", "span_id": [f"s{i}" for i in range(n)],
                       "true": [LABELS[i] for i in t], "pred": [LABELS[i] for i in p]})
    ds = pd.DataFrame({"span_id": df.span_id, "document_id": [f"d{i // 4}" for i in range(n)],
                       "source_id": [f"src{i % 3}" for i in range(n)], "text": [f"word{i} x" * (1 + i % 5) for i in range(n)],
                       "context_before": "b", "context_after": "a"})
    if with_probs:
        P = rng.dirichlet(np.ones(3), n); P[np.arange(n), p] += 0.5; P /= P.sum(1, keepdims=True)
        for j, l in enumerate(LABELS):
            df[f"p_{l}"] = P[:, j]
    return df, ds, t, p


def test_metrics_match_sklearn():
    df, ds, t, p = fixture()
    cm = confusion_counts(t, p)
    assert macro_f1_from_cm(cm) == pytest.approx(f1_score(t, p, labels=[0, 1, 2], average="macro", zero_division=0))
    pr, rc, f1, sup = precision_recall_fscore_support(t, p, labels=[0, 1, 2], zero_division=0)
    pc = per_class(cm)
    for i, l in enumerate(LABELS):
        assert pc[l]["f1"] == pytest.approx(f1[i]) and pc[l]["support"] == sup[i]
        assert pc[l]["recall"] == pytest.approx(rc[i])


def test_absent_class_is_none_not_zero_or_one():
    cm = confusion_counts(np.array([0, 0, 1]), np.array([0, 1, 1]))   # class 2 absent everywhere
    pc = per_class(cm)
    assert pc["CONCEPTUAL"]["precision"] is None and pc["CONCEPTUAL"]["recall"] is None and pc["CONCEPTUAL"]["f1"] == 0.0


def test_bootstrap_is_seeded_clustered_and_brackets_point_estimate():
    df, ds, t, p = fixture(120)
    groups = [f"d{i // 4}" for i in range(120)]
    a = cluster_bootstrap_macro_f1(t, p, groups, 300, 1); b = cluster_bootstrap_macro_f1(t, p, groups, 300, 1)
    assert a == b and a["n_clusters"] == 30 and a["low"] <= macro_f1_from_cm(confusion_counts(t, p)) <= a["high"]
    assert cluster_bootstrap_macro_f1(t, p, groups, 300, 2) != a


def test_clustered_ci_is_wider_when_errors_are_correlated_within_documents():
    # SYNTHETIC: each document is either entirely right or entirely wrong (strong intra-document correlation)
    n_docs, per = 24, 5
    t = np.tile(np.array([0, 1, 2, 0, 1]), n_docs)
    bad_doc = np.arange(n_docs) % 3 == 0
    p = t.copy()
    for d in np.flatnonzero(bad_doc):
        p[d * per:(d + 1) * per] = (t[d * per:(d + 1) * per] + 1) % 3
    docs = [f"d{i // per}" for i in range(n_docs * per)]
    clustered = cluster_bootstrap_macro_f1(t, p, docs, 500, 3)
    naive = cluster_bootstrap_macro_f1(t, p, [f"s{i}" for i in range(len(t))], 500, 3)
    assert (clustered["high"] - clustered["low"]) > 1.5 * (naive["high"] - naive["low"])


def test_confidence_block_ece_and_unavailable_reason():
    df, ds, t, p = fixture(80)
    c = confidence_block(df, t, p)
    assert c["available"] and 0 <= c["ece"] <= 1 and sum(c["hist_correct"]) + sum(c["hist_incorrect"]) == 80
    perfect = pd.DataFrame({f"p_{l}": [1.0 if l == "VOCABULARY" else 0.0] * 5 for l in LABELS})
    assert confidence_block(perfect, np.zeros(5, int), np.zeros(5, int))["ece"] == pytest.approx(0.0)
    nop = confidence_block(df.drop(columns=[f"p_{l}" for l in LABELS]), t, p)
    assert nop["available"] is False and "no probability" in nop["reason"]


def test_analyze_structure_examples_rule_and_slices():
    df, ds, t, p = fixture(80)
    r = analyze(df, ds, data_status="fixture_not_research")
    m = r["models"]["m"]
    assert r["valid_for_scientific_claims"] is False and "caveat" in r
    assert m["n"] == 80 and m["macro_f1_ci95"]["kind"] == "document-clustered"
    ex = m["examples"]
    assert "most confident" in ex["selection_rule"]
    for lst in ex["false_negatives_by_class"].values():
        confs = [e["confidence"] for e in lst]
        assert confs == sorted(confs, reverse=True) and all(e["true"] != e["pred"] for e in lst)
    first = next(iter(ex["by_confusion_pair"].values()))[0]
    assert "text" in first and "context_before" in first
    assert {s["slice"] for s in m["slices"]["span_length_tokens"]} <= {"1", "2-3", "4-8", "9+"}
    assert all(s["unreliable"] == (s["n"] < 20) for s in m["slices"]["source_id"])
    assert sum(m["predicted_distribution"].values()) == 80


def test_no_probabilities_falls_back_to_span_id_order():
    df, ds, t, p = fixture(40, with_probs=False)
    m = analyze(df, ds)["models"]["m"]
    assert "span_id order" in m["examples"]["selection_rule"] and m["confidence"]["available"] is False


def test_unknown_labels_and_missing_columns_rejected():
    df, ds, *_ = fixture(10)
    with pytest.raises(ValueError):
        analyze(df.drop(columns=["pred"]))
    bad = df.copy(); bad.loc[0, "pred"] = "OTHER_UNCERTAIN"
    with pytest.raises(ValueError):
        analyze(bad)


def test_write_stamps_status_and_markdown_banner(tmp_path):
    df, ds, *_ = fixture(40)
    d = tmp_path / "run"; d.mkdir()
    df.to_csv(d / "predictions.csv", index=False); ds.to_csv(tmp_path / "ds.csv", index=False)
    (d / "results.json").write_text(json.dumps({"data_status": "fixture_not_research", "valid_for_scientific_claims": False}), encoding="utf-8")
    r = write_error_analysis(d / "predictions.csv", tmp_path / "ea", tmp_path / "ds.csv", split="test", n_boot=50)
    md = (tmp_path / "ea" / "error_analysis_test.md").read_text(encoding="utf-8")
    assert md.startswith("> **NOT RESEARCH**") and "contaminates the test set" in md
    assert r["valid_for_scientific_claims"] is False and (tmp_path / "ea" / "error_analysis_test.json").exists()


def test_missing_results_json_is_treated_as_non_research(tmp_path):
    df, ds, *_ = fixture(30)
    df.to_csv(tmp_path / "predictions.csv", index=False)
    assert write_error_analysis(tmp_path / "predictions.csv", tmp_path / "o", split="test", n_boot=20)["valid_for_scientific_claims"] is False
