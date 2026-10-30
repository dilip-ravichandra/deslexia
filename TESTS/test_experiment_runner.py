import json
import shutil
import pandas as pd
import pytest
import yaml
from pathlib import Path
from ML.experiment_runner import (load_config, run_experiment, verify_experiment, experiment_id, code_sha256)
from TESTS.test_baselines import synth  # SYNTHETIC fixture only

CFG = {"seed": 7, "seeds": [1], "labels": ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"],
       "split": {"strategy": "grouped_by_document", "train": 0.7, "validation": 0.15, "test": 0.15},
       "models": {"baselines": ["tfidf_logreg", "tfidf_svm"], "transformer": "distilbert-base-uncased", "fusion": True},
       "hyperparameters": {"epochs": 1, "batch_size": 32, "max_len": 24, "patience": 1},
       "analysis": {"bootstrap_resamples": 30, "top_k_examples": 2}}


def write_cfg(tmp, **over):
    c = json.loads(json.dumps(CFG)); c.update(over)
    p = tmp / "cfg.yaml"; p.write_text(yaml.safe_dump(c), encoding="utf-8"); return p


def research_like(df):
    d = df.copy(); d["annotator_id"] = "h1"; d["guideline_version"] = "v1"; d["confidence"] = 4; d["rationale"] = "r"
    d["source_license"] = "CC-BY-4.0"; d["created_at"] = "2026-01-01T00:00:00Z"; return d


@pytest.fixture(scope="module")
def smoke_exp(tmp_path_factory):
    t = tmp_path_factory.mktemp("exp")
    csv = t / "d.csv"; synth().to_csv(csv, index=False)
    m = run_experiment(write_cfg(t), csv, t / "out", smoke=True, allow_fixture=True)
    return t, csv, m


def test_repo_config_is_valid_and_bad_configs_rejected(tmp_path):
    root = Path(__file__).resolve().parents[1]
    assert load_config(root / "EXPERIMENTS" / "config.yaml")["seeds"]
    for over in ({"labels": ["A"]}, {"seed": "x"}, {"seeds": [1, 1]}, {"split": {"strategy": "random", "train": .7, "validation": .15, "test": .15}},
                 {"split": {"strategy": "grouped_by_document", "train": .8, "validation": .15, "test": .15}},
                 {"models": {"baselines": ["magic"]}}, {"hyperparameters": {"bogus": 1}}):
        with pytest.raises(ValueError, match="invalid config"):
            load_config(write_cfg(tmp_path, **over))


def test_plan_writes_nothing_and_non_research_data_is_refused(tmp_path):
    csv = tmp_path / "d.csv"; synth().to_csv(csv, index=False)
    plan = run_experiment(write_cfg(tmp_path), csv, tmp_path / "out", allow_fixture=True, dry_run=True)
    assert plan["would_run"][:3] == ["validate", "split", "baselines"] and not (tmp_path / "out").exists()
    assert "distilbert" not in plan["would_run"]          # fixture data without --smoke: no transformer
    with pytest.raises(RuntimeError, match="not research-valid"):
        run_experiment(write_cfg(tmp_path), csv, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_smoke_experiment_end_to_end_is_stamped_non_research(smoke_exp):
    t, csv, m = smoke_exp
    assert m["status"] == "complete" and m["data_status"] == "fixture_not_research" and m["smoke"] is True
    assert m["valid_for_scientific_claims"] is False
    assert all(s["status"] == "ok" for s in m["steps"].values()), m["steps"]
    exp = t / "out" / m["experiment_id"]
    for f in ["config.json", "split_manifest.json", "baselines/results.json", "distilbert/seed1/results.json",
              "distilbert/seed1/training_log.jsonl", "ablation/ablation.json", "run_manifest.json"]:
        assert (exp / f).exists(), f
    assert list((exp / "error_analysis").rglob("error_analysis_test.json")) and list((exp / "figures").glob("confusion_*.png"))
    assert any(p.name.startswith("training_curve") for p in (exp / "figures").iterdir())
    ea = json.loads(next((exp / "error_analysis").rglob("error_analysis_test.json")).read_text(encoding="utf-8"))
    assert ea["valid_for_scientific_claims"] is False and ea["data_status"] == "fixture_not_research"
    base = json.loads((exp / "baselines" / "results.json").read_text(encoding="utf-8"))
    assert base["data_status"] == "fixture_not_research"
    assert len(m["dataset"]["sha256"]) == 64 and len(m["code_sha256"]) == 64 and m["artifacts"]["config.json"]
    assert verify_experiment(exp)["ok"]


def test_rerun_is_idempotent_and_tampering_is_detected(smoke_exp):
    t, csv, m = smoke_exp
    again = run_experiment(write_cfg(t), csv, t / "out", smoke=True, allow_fixture=True)
    assert again["reused"] is True and again["experiment_id"] == m["experiment_id"]
    exp = t / "out" / m["experiment_id"]
    target = exp / "baselines" / "predictions.csv"; original = target.read_text(encoding="utf-8")
    target.write_text(original + "tamper\n", encoding="utf-8")
    v = verify_experiment(exp)
    assert not v["ok"] and "baselines/predictions.csv" in v["changed"]
    target.write_text(original, encoding="utf-8")
    assert verify_experiment(exp)["ok"]


def test_experiment_id_depends_on_config_data_code_and_mode(tmp_path):
    cfg = load_config(write_cfg(tmp_path)); cs = code_sha256()
    base = experiment_id(cfg, "d1", cs, {"smoke": True})
    assert base == experiment_id(cfg, "d1", cs, {"smoke": True})
    assert len({base, experiment_id({**cfg, "seed": 8}, "d1", cs, {"smoke": True}), experiment_id(cfg, "d2", cs, {"smoke": True}),
                experiment_id(cfg, "d1", "other", {"smoke": True}), experiment_id(cfg, "d1", cs, {"smoke": False})}) == 5


def test_unavailable_weights_make_experiment_partial_never_valid(tmp_path):
    # PLUMBING TEST: structurally research-valid synthetic data, offline, no cached weights.
    csv = tmp_path / "d.csv"; research_like(synth()).to_csv(csv, index=False)
    m = run_experiment(write_cfg(tmp_path, models={**CFG["models"], "transformer": "not-cached/xyz"}), csv, tmp_path / "out", offline=True)
    assert m["status"] == "partial" and m["valid_for_scientific_claims"] is False
    assert m["steps"]["baselines"]["status"] == "ok" and m["data_status"] == "research"
    assert m["steps"]["distilbert"]["status"] == "unavailable" and "pretrained weights" in m["steps"]["distilbert"]["reason"]
    assert set(m["unavailable_steps"]) >= {"distilbert", "ablation"}
    exp = tmp_path / "out" / m["experiment_id"]
    assert (exp / "distilbert" / "seed1" / "DOWNLOAD_FAILED.json").exists() and not (exp / "distilbert" / "seed1" / "model").exists()


def test_failed_step_is_recorded_and_stops_dependents(tmp_path):
    d = synth(n_docs=2); csv = tmp_path / "d.csv"; d.to_csv(csv, index=False)       # < 3 documents: split must fail
    m = run_experiment(write_cfg(tmp_path), csv, tmp_path / "out", allow_fixture=True)
    assert m["status"] == "failed" and m["failed_steps"] == ["split"] and "baselines" not in m["steps"]
    assert m["valid_for_scientific_claims"] is False and "at least" in m["steps"]["split"]["reason"]
