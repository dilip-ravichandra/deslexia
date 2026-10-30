import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from ML.distilbert_trainer import run
from ML.group_split import split
from TESTS.test_baselines import synth, SEED_CSV  # SYNTHETIC fixture only

FAST = dict(epochs=2, batch_size=16, max_len=32, patience=2)


def csv_of(tmp_path, df=None, name="d.csv"):
    p = tmp_path / name
    (synth() if df is None else df).to_csv(p, index=False)
    return p


def test_smoke_run_artifacts_and_stamps(tmp_path):
    r = run(csv_of(tmp_path), tmp_path / "o", smoke=True, **FAST)
    assert r["smoke"] and r["weights"] == "random_init_tiny_local"
    assert r["pretrained_weights_used"] is False and r["valid_for_scientific_claims"] is False
    assert r["data_status"] == "fixture_not_research"
    o = tmp_path / "o"
    for f in ["results.json", "metadata.json", "predictions.csv", "training_log.jsonl", "model", "tokenizer"]:
        assert (o / f).exists(), f
    log = [json.loads(l) for l in (o / "training_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert 1 <= len(log) <= 2 and {"epoch", "train_loss", "val_macro_f1"} <= set(log[0])
    pr = pd.read_csv(o / "predictions.csv")
    assert set(pr.split) == {"validation", "test"}
    assert np.allclose(pr[[f"p_{l}" for l in ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]]].sum(axis=1), 1, atol=1e-4)
    cm = np.array(r["test"]["confusion_matrix"]["matrix"])
    assert cm.sum() == r["split_sizes"]["test"]
    meta = json.loads((o / "metadata.json").read_text(encoding="utf-8"))
    assert meta["seed"] == 42 and len(meta["dataset_sha256"]) == 64 and "torch" in meta["versions"]


def test_non_smoke_refused_on_seed_and_fixture_data(tmp_path):
    with pytest.raises(RuntimeError, match="research"):
        run(SEED_CSV, tmp_path / "a")
    with pytest.raises(RuntimeError, match="research"):
        run(csv_of(tmp_path), tmp_path / "b")


def test_download_failure_is_hard_error_not_random_weights(tmp_path):
    d = synth()
    d["annotator_id"] = "h1"; d["guideline_version"] = "v1"; d["confidence"] = 4; d["rationale"] = "r"
    d["source_license"] = "CC-BY-4.0"; d["created_at"] = "2026-01-01T00:00:00Z"
    p = csv_of(tmp_path, d)
    from ML.group_split import freeze
    freeze(p, tmp_path / "m.json")
    with pytest.raises(RuntimeError, match="pretrained weights"):
        run(p, tmp_path / "o", manifest_path=tmp_path / "m.json", offline=True,
            model_name="definitely-not-cached/model-xyz", **FAST)
    info = json.loads((tmp_path / "o" / "DOWNLOAD_FAILED.json").read_text(encoding="utf-8"))
    assert info["status"] == "PRETRAINED_WEIGHTS_UNAVAILABLE" and info["practical_alternatives"]
    assert not (tmp_path / "o" / "model").exists() and not (tmp_path / "o" / "results.json").exists()


def test_same_seed_reproduces_predictions(tmp_path):
    p = csv_of(tmp_path)
    a = run(p, tmp_path / "a", smoke=True, **FAST); b = run(p, tmp_path / "b", smoke=True, **FAST)
    pa, pb = (pd.read_csv(tmp_path / x / "predictions.csv") for x in "ab")
    assert pa.pred.tolist() == pb.pred.tolist()
    assert a["validation"]["macro_f1"] == b["validation"]["macro_f1"]


def test_test_labels_do_not_influence_selection(tmp_path):
    d = synth(noise=0.3, seed=3)
    _, _, te = split(d, seed=42)
    d2 = d.copy()
    rng = np.random.default_rng(0)
    d2.loc[te.index, "category"] = rng.permutation(d2.loc[te.index, "category"].values)
    a = run(csv_of(tmp_path, d, "a.csv"), tmp_path / "a", smoke=True, **FAST)
    b = run(csv_of(tmp_path, d2, "b.csv"), tmp_path / "b", smoke=True, **FAST)
    assert a["best_epoch"] == b["best_epoch"]
    assert a["validation"] == b["validation"]
    pa, pb = (pd.read_csv(tmp_path / x / "predictions.csv") for x in "ab")
    assert pa[pa.split == "test"].pred.tolist() == pb[pb.split == "test"].pred.tolist()


def test_missing_train_class_rejected(tmp_path):
    d = synth(); d = d[d.category != "CONCEPTUAL"]
    with pytest.raises(ValueError):
        run(csv_of(tmp_path, d), tmp_path / "o", smoke=True, **FAST)
