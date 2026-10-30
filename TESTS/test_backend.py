import json
import numpy as np
import pytest
from fastapi.testclient import TestClient

import BACKEND.app as appmod
import BACKEND.research as research
from BACKEND.pipeline import Pipeline, load_research_model
from ML.interventions import register_generator, clear_generators
from TESTS.test_baselines import synth  # SYNTHETIC fixture only

c = TestClient(appmod.app)
TEXT = "Although the reaction was slow, the catalyst eventually accelerated it. Then it ended."


def adapt(**kw):
    return c.post("/api/adapt", json={"span": "catalyst", "text": TEXT, **kw})


def test_status_and_disclaimer():
    s = c.get("/api/model-status").json()
    assert s["mode"] == "demo" and s["research_model_available"] is False and s["warning"]
    d = c.get("/api/disclaimer").json()["disclaimer"].lower()
    assert "does not diagnose" in d


def test_demo_adapt_trace_is_honest(monkeypatch):
    # Explicitly test the original no-model fallback; the shipped prototype is tested separately.
    monkeypatch.setattr(appmod.adaptive.trainer,'model',None)
    r = adapt().json()
    assert r["research_mode"] == "demo" and r["valid_for_research"] is False and r["experiment_id"] == "demo"
    cat = r["category"]
    assert cat["source"] == "demo_heuristic_rules" and cat["probabilities"] is None
    assert cat["confidence"] is None and cat["is_trained_model_output"] is False
    assert any("DEMO" in w for w in r["warnings"])
    assert r["intervention"]["is_trained_model_output"] is False
    assert r["verification"]["verified_unit"] == "sentence"
    assert r["verification"]["meaning_preservation_guaranteed"] is False
    assert "(a substance that makes a reaction go faster)" in r["comparison"]["adapted_sentence"]
    assert r["presentable"] is True


def test_visual_settings_cannot_enter_classification():
    for extra in ({"background": "cream"}, {"text_size": 22}, {"font": "serif"}, {"letter_spacing": 2}):
        assert adapt(**extra).status_code == 422


def test_input_validation():
    assert c.post("/api/adapt", json={"span": "zzz", "text": TEXT}).status_code == 422
    assert c.post("/api/adapt", json={"span": ""}).status_code == 422
    assert c.post("/api/adapt", json={"span": "x" * 301}).status_code == 422
    assert adapt(category_override="NOPE").status_code == 422


def test_research_mode_without_validated_model_is_refused():
    r = adapt(mode="research")
    assert r.status_code == 503 and "no validated research model" in r.json()["detail"]


def test_learner_override_is_not_labelled_as_a_prediction():
    r = adapt(category_override="CONCEPTUAL").json()
    assert r["category"]["source"] == "learner_choice" and r["category"]["is_trained_model_output"] is False
    assert r["intervention"]["category"] == "CONCEPTUAL" and r["intervention"]["status"] == "scaffold_only"


def test_regenerate_variant_changes_vocab_output():
    a, b = adapt().json(), adapt(variant=1).json()
    assert a["intervention"]["variant"] == 0 and b["intervention"]["variant"] == 1


def test_context_without_text_uses_supplied_context():
    r = c.post("/api/adapt", json={"span": "accelerated", "context_before": "The catalyst eventually ",
                                   "context_after": " it."}).json()
    assert r["input"]["sentence"] == "The catalyst eventually accelerated it."


def test_unsafe_adaptation_is_hidden_and_flagged():
    register_generator("SYNTACTIC", "bad", lambda sp, se, b, a: "It is safe.")
    try:
        r = c.post("/api/adapt", json={"span": "not", "text": "It is not safe.", "category_override": "SYNTACTIC"}).json()
    finally:
        clear_generators()
    assert r["verification"]["status"] == "fail" and r["presentable"] is False
    assert any("hidden" in w for w in r["warnings"])


def test_feedback_roundtrip_and_validation():
    tid = adapt().json()["trace_id"]
    assert c.post("/api/feedback", json={"trace_id": tid, "decision": "accept", "comfort_rating": 4}).status_code == 200
    assert c.post("/api/feedback", json={"trace_id": "0" * 32, "decision": "accept"}).status_code == 404
    assert c.post("/api/feedback", json={"trace_id": tid, "decision": "maybe"}).status_code == 422
    assert c.post("/api/feedback", json={"trace_id": tid, "decision": "accept", "comfort_rating": 9}).status_code == 422


def test_logging_is_off_by_default_and_text_free_when_on(tmp_path, monkeypatch):
    st = appmod.pipe.traces
    assert st.log_on is False
    monkeypatch.setattr(st, "log_on", True); monkeypatch.setattr(st, "dir", tmp_path)
    monkeypatch.setattr(st, "log_text", False)
    tid = adapt().json()["trace_id"]
    c.post("/api/feedback", json={"trace_id": tid, "decision": "reject"})
    recs = [json.loads(l) for l in (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["event"] for r in recs} == {"adapt", "feedback"}
    blob = json.dumps(recs)
    assert "catalyst" not in blob and "reaction" not in blob and "text" not in recs[0]
    monkeypatch.setattr(st, "log_text", True)
    adapt()
    assert "text" in json.loads((tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()[-1])


def test_frontend_is_served():
    assert "DyslexiAdapt" in c.get("/").text
    assert c.get("/research.html").status_code == 200


# ------------------------------------------------------------- research endpoints
def test_research_summary_is_empty_without_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "ART", tmp_path / "A"); monkeypatch.setattr(research, "ROOT", tmp_path)
    s = c.get("/api/research/summary").json()
    assert s["runs"] == [] and s["non_research_runs"] == [] and s["ablations"] == [] and s["agreement"] == []
    assert s["dataset_split"] is None


def test_admin_guard(monkeypatch):
    monkeypatch.setenv("DYSLEXIADAPT_ADMIN_TOKEN", "s3cret")
    assert c.get("/api/research/summary").status_code == 401
    assert c.get("/api/research/summary", headers={"x-admin-token": "wrong"}).status_code == 401
    assert c.get("/api/research/summary", headers={"x-admin-token": "s3cret"}).status_code == 200
    monkeypatch.delenv("DYSLEXIADAPT_ADMIN_TOKEN")
    remote = TestClient(appmod.app, client=("203.0.113.9", 5000))
    assert remote.get("/api/research/summary").status_code == 403
    assert remote.post("/api/adapt", json={"span": "catalyst", "text": TEXT}).status_code == 200  # learner API open


def test_artifact_reader_blocks_traversal():
    assert c.get("/api/research/artifact", params={"path": "../../etc/passwd"}).status_code in (403, 404)
    assert c.get("/api/research/artifact", params={"path": "CLAUDE.md"}).status_code == 403
    assert c.get("/api/research/artifact", params={"path": "DATA/schema.json"}).status_code == 200


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    from ML.distilbert_trainer import run
    d = tmp_path_factory.mktemp("art")
    p = d / "d.csv"; synth().to_csv(p, index=False)
    out = d / "ARTIFACTS" / "fusion_smoke"
    run(p, out, smoke=True, arch="fusion_on", epochs=1, batch_size=32, max_len=24, patience=1)
    return d


def test_smoke_runs_are_listed_as_non_research(smoke_run, monkeypatch):
    monkeypatch.setattr(research, "ART", smoke_run / "ARTIFACTS"); monkeypatch.setattr(research, "ROOT", smoke_run)
    s = c.get("/api/research/summary").json()
    assert s["runs"] == [] and len(s["non_research_runs"]) == 1
    v = s["non_research_runs"][0]
    assert v["kind"] == "fusion" and v["is_research_result"] is False and v["valid_for_scientific_claims"] is False
    assert v["test"]["confusion_matrix"]["labels"] and v["experiment_id"].startswith("fusion_smoke@")


def test_registry_rejects_smoke_but_plumbing_works_when_forced(smoke_run):
    reg = smoke_run / "ARTIFACTS" / "research_model"; reg.mkdir(parents=True, exist_ok=True)
    (reg / "registry.json").write_text(json.dumps({"kind": "fusion", "path": "../fusion_smoke"}), encoding="utf-8")
    m, st = load_research_model(reg)
    assert m is None and st["available"] is False and "not 'research'" in st["reason"]
    m, st = load_research_model(reg, require_valid=False)   # test-only bypass to exercise predict()
    assert st["available"] and m.kind == "fusion"
    probs = m.suggest("catalyst", "The catalyst helped.")["probabilities"]
    assert set(probs) == {"VOCABULARY", "SYNTACTIC", "CONCEPTUAL"} and abs(sum(probs.values()) - 1) < 1e-4
    assert m.suggest("catalyst", "The catalyst helped.")["is_trained_model_output"] is True


def test_pipeline_with_validated_model_reports_research_mode(smoke_run, tmp_path):
    # PLUMBING TEST ONLY: forge a 'research' results.json next to a smoke model to exercise the code path.
    run_dir = smoke_run / "ARTIFACTS" / "fusion_smoke"
    res = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    forged = tmp_path / "A" / "fusion_forged"; forged.mkdir(parents=True)
    import shutil
    shutil.copytree(run_dir / "model", forged / "model")
    res.update(data_status="research", valid_for_scientific_claims=True, smoke=False)
    (forged / "results.json").write_text(json.dumps(res), encoding="utf-8")
    (tmp_path / "A" / "research_model").mkdir()
    (tmp_path / "A" / "research_model" / "registry.json").write_text(json.dumps({"kind": "fusion", "path": "../fusion_forged"}), encoding="utf-8")
    p = Pipeline(tmp_path / "A" / "research_model")
    r = p.adapt("catalyst", text=TEXT, want_research=True)
    assert r["research_mode"] == "research" and r["category"]["is_trained_model_output"] is True
    assert r["category"]["probabilities"] and r["experiment_id"].startswith("fusion_forged")


def test_sklearn_registry_loader_plumbing(tmp_path):
    from ML.baselines import run as run_baselines
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    run_baselines(p, tmp_path / "A" / "baselines", allow_fixture=True)       # fixture run -> rejected as research
    reg = tmp_path / "A" / "research_model"; reg.mkdir()
    (reg / "registry.json").write_text(json.dumps({"kind": "sklearn", "path": "../baselines", "model_file": "tfidf_logreg.joblib"}), encoding="utf-8")
    m, st = load_research_model(reg)
    assert m is None and "not 'research'" in st["reason"]
    m, st = load_research_model(reg, require_valid=False)                    # test-only bypass of the gate
    probs = m.suggest("lexeme0", "before 1 [x]")["probabilities"]
    assert set(probs) == {"VOCABULARY", "SYNTACTIC", "CONCEPTUAL"} and abs(sum(probs.values()) - 1) < 1e-6


def test_experiments_and_error_analyses_are_partitioned_by_validity(tmp_path, monkeypatch):
    from ML.experiment_runner import run_experiment
    import yaml
    csv = tmp_path / "d.csv"; synth().to_csv(csv, index=False)
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"seed": 3, "seeds": [1], "labels": ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"],
        "split": {"strategy": "grouped_by_document", "train": .7, "validation": .15, "test": .15},
        "models": {"baselines": ["tfidf_logreg"], "transformer": None, "fusion": False},
        "hyperparameters": {"epochs": 1}, "analysis": {"bootstrap_resamples": 20, "top_k_examples": 2}}), encoding="utf-8")
    m = run_experiment(cfg, csv, tmp_path / "ARTIFACTS" / "experiments", allow_fixture=True)
    assert m["valid_for_scientific_claims"] is False
    monkeypatch.setattr(research, "ART", tmp_path / "ARTIFACTS"); monkeypatch.setattr(research, "ROOT", tmp_path)
    s = c.get("/api/research/summary").json()
    assert s["experiments"] == [] and s["error_analyses"] == []
    assert len(s["non_research_experiments"]) == 1 and s["non_research_experiments"][0]["experiment_id"] == m["experiment_id"]
    assert s["non_research_error_analyses"] and all(not a["valid_for_scientific_claims"] for a in s["non_research_error_analyses"])
