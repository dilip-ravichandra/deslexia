import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from ML.baselines import run, metrics, select_and_fit, add_model_input, LABELS
from ML.group_split import freeze

SEED_CSV = Path(__file__).resolve().parents[1] / "DATA" / "seed_examples.csv"


def synth(n_docs=30, per=4, noise=0.0, seed=0):
    # SYNTHETIC TEST FIXTURE ONLY: labels are tied to marker words so the pipeline
    # mechanics can be exercised. Scores on this are NOT evidence about the task.
    rng = np.random.default_rng(seed)
    marks = {"VOCABULARY": "lexeme", "SYNTACTIC": "clause", "CONCEPTUAL": "theory"}
    rows = []
    for d in range(n_docs):
        for i in range(per):
            lab = LABELS[(d + i) % 3]
            if rng.random() < noise:
                lab = LABELS[rng.integers(3)]
            rows.append(dict(source_id=f"s{d%3}", document_id=f"d{d}", span_id=f"d{d}_{i}",
                             text=f"{marks[LABELS[(d+i)%3]]}{i}", context_before=f"before {d}",
                             context_after="after", category=lab))
    return pd.DataFrame(rows)


def test_research_run_refused_on_seed_and_on_missing_manifest(tmp_path):
    with pytest.raises(RuntimeError, match="research"):
        run(SEED_CSV, tmp_path)
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    with pytest.raises(RuntimeError):
        run(p, tmp_path / "o")  # fixture data lacks provenance columns


def test_fixture_run_outputs_and_is_stamped(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    r = run(p, tmp_path / "o", allow_fixture=True)
    assert r["data_status"] == "fixture_not_research"
    assert set(r["models"]) == {"majority", "tfidf_logreg", "tfidf_svm"}
    meta = json.loads((tmp_path / "o" / "metadata.json").read_text(encoding="utf-8"))
    assert meta["data_status"] == "fixture_not_research" and len(meta["dataset_sha256"]) == 64
    pr = pd.read_csv(tmp_path / "o" / "predictions.csv")
    assert set(pr.split) == {"validation", "test"} and set(pr.model) == set(r["models"])
    n_test = r["split_sizes"]["test"]
    assert (pr[(pr.model == "majority") & (pr.split == "test")].shape[0]) == n_test
    cm = np.array(r["models"]["tfidf_svm"]["test"]["confusion_matrix"]["matrix"])
    assert cm.sum() == n_test and cm.shape == (3, 3)
    for n in r["models"]:
        assert (tmp_path / "o" / f"{n}.joblib").exists()


def test_metrics_known_values():
    m = metrics(["VOCABULARY", "VOCABULARY", "SYNTACTIC", "CONCEPTUAL"],
                ["VOCABULARY", "SYNTACTIC", "SYNTACTIC", "SYNTACTIC"])
    assert m["accuracy"] == 0.5
    assert m["confusion_matrix"]["matrix"] == [[1, 1, 0], [0, 1, 0], [0, 1, 0]]
    assert m["macro_f1"] == pytest.approx((2/3 + 0.5 + 0.0) / 3)


def test_majority_baseline_predicts_most_frequent_train_class(tmp_path):
    d = synth(); d.loc[d.index % 5 != 0, "category"] = "VOCABULARY"
    p = tmp_path / "d.csv"; d.to_csv(p, index=False)
    run(p, tmp_path / "o", allow_fixture=True)
    pr = pd.read_csv(tmp_path / "o" / "predictions.csv")
    assert set(pr[pr.model == "majority"].pred) == {"VOCABULARY"}


def test_model_selection_never_uses_test_labels():
    d = add_model_input(synth(noise=0.2, seed=1))
    tr, va = d[d.document_id.isin([f"d{i}" for i in range(20)])], d[d.document_id.isin([f"d{i}" for i in range(20, 30)])]
    a = select_and_fit("tfidf_logreg", tr, va)[1:]
    b = select_and_fit("tfidf_logreg", tr, va)[1:]
    assert a == b  # deterministic given train/val only; function has no test argument


def test_full_research_path_with_frozen_manifest(tmp_path):
    d = synth(); d["annotator_id"] = "human1"; d["guideline_version"] = "v1"; d["confidence"] = 4
    d["rationale"] = "r"; d["source_license"] = "CC-BY-4.0"; d["created_at"] = "2026-01-01T00:00:00Z"
    p = tmp_path / "gold_like.csv"; d.to_csv(p, index=False)
    freeze(p, tmp_path / "m.json")
    r = run(p, tmp_path / "o", manifest_path=tmp_path / "m.json")
    # mechanics only: this temp file is synthetic, but passes the structural gate
    assert r["data_status"] == "research"
