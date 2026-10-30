import pandas as pd
import pytest
from sklearn.metrics import cohen_kappa_score
from ML.agreement import (cohen_kappa, krippendorff_alpha_nominal,
                          agreement_report, conflict_report)


def test_cohen_matches_sklearn():
    a = list("VVVSSCCVSC" * 3)
    b = list("VVSSSCVVSC" * 3)
    assert cohen_kappa(a, b) == pytest.approx(cohen_kappa_score(a, b))


def test_cohen_undefined_when_single_label_not_faked():
    assert cohen_kappa(["V"] * 5, ["V"] * 5) is None


def test_cohen_chance_level_is_zero_and_perfect_is_one():
    assert cohen_kappa(list("VVSS"), list("VSVS")) == pytest.approx(0.0)
    assert cohen_kappa(list("VSCV"), list("VSCV")) == pytest.approx(1.0)


def test_krippendorff_reference_example():
    # Krippendorff's published nominal example (4 observers, 12 units, missing data): alpha = 0.743
    A = [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None]
    B = [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3]
    C = [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None]
    D = [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]
    units = [[v for v in col if v is not None] for col in zip(A, B, C, D)]
    assert krippendorff_alpha_nominal(units) == pytest.approx(0.743, abs=1e-3)


def test_krippendorff_perfect_and_undefined():
    assert krippendorff_alpha_nominal([["a", "a"], ["b", "b"], ["c", "c"]]) == pytest.approx(1.0)
    assert krippendorff_alpha_nominal([["a", "a"], ["a", "a"]]) is None
    assert krippendorff_alpha_nominal([["a"], ["b"]]) is None


def long_df(la, lb):
    ids = [f"s{i}" for i in range(len(la))]
    return pd.concat([pd.DataFrame(dict(span_id=ids, annotator_id="a1", category=la)),
                      pd.DataFrame(dict(span_id=ids, annotator_id="a2", category=lb))])


def test_report_structure_and_small_sample_warning():
    la = ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL", "VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]
    lb = ["VOCABULARY", "SYNTACTIC", "VOCABULARY", "VOCABULARY", "CONCEPTUAL", "CONCEPTUAL"]
    long = long_df(la, lb)
    r = agreement_report(long)
    assert r["n_spans_multi_annotated"] == 6
    assert r["warnings"] and "unstable" in r["warnings"][0]
    assert r["pairwise"]["a1__a2"]["cohen_kappa"] == pytest.approx(cohen_kappa_score(la, lb))
    assert r["pairwise"]["a1__a2"]["n"] == 6
    assert r["raw_percent_agreement"] == pytest.approx(4 / 6)
    assert set(r["per_class_alpha_one_vs_rest"]) == {"VOCABULARY", "SYNTACTIC", "CONCEPTUAL"}
    assert r["conflict_pair_counts"] == {"CONCEPTUAL|VOCABULARY": 1, "CONCEPTUAL|SYNTACTIC": 1}


def test_single_annotated_spans_excluded_and_conflicts_listed():
    long = pd.concat([long_df(["VOCABULARY", "SYNTACTIC"], ["VOCABULARY", "CONCEPTUAL"]),
                      pd.DataFrame(dict(span_id=["solo"], annotator_id=["a1"], category=["VOCABULARY"]))])
    r = agreement_report(long)
    assert r["n_spans"] == 3 and r["n_spans_multi_annotated"] == 2
    c = conflict_report(long)
    assert list(c.span_id) == ["s1"]


def test_adjudication_tracking():
    long = long_df(["VOCABULARY", "SYNTACTIC"], ["VOCABULARY", "CONCEPTUAL"])
    queue = pd.DataFrame(dict(span_id=["s1"]))
    adj = pd.DataFrame(dict(span_id=["x"]))
    r = agreement_report(long, adjudications=adj, queue=queue)
    assert r["adjudication"] == {"queued": 2, "adjudicated": 1, "pending": 1}
