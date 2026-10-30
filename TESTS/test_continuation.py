"""Regression checks and synthetic tooling tests. Never research evidence."""
import json
from pathlib import Path

import pandas as pd
import pytest

from ML.annotation import make_batches, import_annotations, resolve, write_resolution
from ML.context import build_context, sentence_around
from ML.data_validation import check
from ML.evaluation import change_metrics, evaluate, write_evaluation
from ML.experiment_runner import run_experiment
from ML.features import linguistic_features
from ML.group_split import freeze, load_frozen
from ML.paper_tables import export_tables
from TESTS.test_data_validation import row
from TESTS.test_baselines import synth


@pytest.mark.parametrize("kw", [dict(annotator_id=None), dict(annotator_id=" "),
    dict(annotator_id=" AI "), dict(source_license=" unknown "), dict(confidence=2.5)])
def test_research_validation_rejects_missing_and_disguised_metadata(kw):
    assert not check(pd.DataFrame([row(**kw)]), "research").ok


def test_empty_data_is_not_research_valid():
    assert not check(pd.DataFrame([row()]).iloc[:0], "research").ok


def test_context_boundary_and_actual_token_lengths():
    c = build_context("The catalyst speeds the reaction.", "catalyst")
    assert sentence_around(c["context_before"], c["span"], c["context_after"]) == c["sentence"]
    assert linguistic_features("a, bee!")["avg_token_length"] == 2
    c = build_context("The acceleration stopped.", "celer", 6)
    assert sentence_around(c["context_before"], c["span"], c["context_after"]) == c["sentence"]


def test_selected_repeated_word_changes_the_correct_occurrence():
    from BACKEND.pipeline import Pipeline
    text = "A catalyst needs another catalyst."
    offset = text.rfind("catalyst")
    r = Pipeline().adapt("catalyst", text=text, span_start=offset, category_override="VOCABULARY")
    assert r["comparison"]["adapted_sentence"].startswith("A catalyst needs another catalyst (")


def test_duplicate_votes_cannot_create_gold():
    long = pd.DataFrame({"span_id": ["s", "s"], "annotator_id": ["h", "h"], "category": ["VOCABULARY"] * 2})
    with pytest.raises(ValueError, match="duplicate"):
        resolve(long)
    with pytest.raises(ValueError, match="at least 2"):
        resolve(long.iloc[:1], min_annotators=1)


@pytest.mark.parametrize("ids,copies", [(["a", "../b"], 2), (["a", " "], 2), (["a", "b"], 0)])
def test_batch_guards(ids, copies):
    with pytest.raises(ValueError):
        make_batches(synth(), ids, copies=copies)


def test_annotation_resolution_roundtrip_and_unreturned_spans(tmp_path):
    # Artificial content and votes used only to exercise plumbing.
    pool = pd.DataFrame([row(span_id="s1"), row(span_id="s2"), row(span_id="s3")]).drop(columns="category")
    p = tmp_path / "pool.csv"; pool.to_csv(p, index=False)
    paths = []
    for who, labs in [("h1", ["VOCABULARY", "SYNTACTIC"]), ("h2", ["VOCABULARY", "CONCEPTUAL"])]:
        frame = pool.iloc[:2].assign(annotator_id=who, category=labs)
        fp = tmp_path / f"{who}.csv"; frame.to_csv(fp, index=False); paths.append(fp)
    r = write_resolution(p, paths, tmp_path / "round1", "v1")
    assert r["n_resolved"] == 1 and r["n_pending"] == 2 and not r["ready_for_dataset_review"]
    q = pd.read_csv(tmp_path / "round1" / "adjudication_queue.csv")
    assert set(q.reason) == {"disagreement", "no_annotations"}
    gold = pd.read_csv(tmp_path / "round1" / "gold_resolved.csv")
    assert check(gold, "research").ok and gold.annotator_id.iloc[0] == "h1|h2"
    with pytest.raises(FileExistsError):
        write_resolution(p, paths, tmp_path / "round1", "v1")


def test_fractional_confidence_not_silently_truncated(tmp_path):
    p = tmp_path / "a.csv"
    pd.DataFrame([row(confidence=2.5)]).to_csv(p, index=False)
    with pytest.raises(ValueError, match="confidence"):
        import_annotations(p, ["d1_1"], "v1")


def test_artifact_prefix_sibling_is_not_allowed(tmp_path, monkeypatch):
    import BACKEND.research as research
    root = tmp_path / "project"; root.mkdir()
    allowed = root / "DATA"; allowed.mkdir()
    sibling = root / "DATA_private"; sibling.mkdir()
    (sibling / "private.txt").write_text("private", encoding="utf-8")
    monkeypatch.setattr(research, "ROOT", root)
    monkeypatch.setattr(research, "ALLOWED_ROOTS", [allowed])
    with pytest.raises(PermissionError):
        research.read_artifact("DATA_private/private.txt")


def test_tampered_frozen_assignment_is_rejected(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    mp = tmp_path / "split.json"; m = freeze(p, mp)
    m["splits"]["test"]["groups"].append(m["splits"]["train"]["groups"][0])
    mp.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(ValueError, match="overlapping"):
        load_frozen(mp, p)


def comparison():
    return {"sample_id": "fixture1", "document_id": "fixture_doc",
        "original": "The catalyst speeds the reaction.",
        "generic_accessibility": "The catalyst speeds the reaction.",
        "uniform_simplification": "This substance makes the reaction faster.",
        "targeted": "The catalyst (a helpful substance) speeds the reaction."}


def test_changes_count_additions_without_claiming_source_rewrites():
    unchanged = change_metrics("The plant grew.", "The plant grew.")
    assert unchanged["total_edit_budget"] == 0
    appended = change_metrics("The plant grew.", "The plant grew. It got bigger.")
    assert appended["changed_original_tokens"] == 0 and appended["added_tokens"] > 0
    assert appended["unchanged_original_token_ratio"] == 1
    layout = change_metrics("The plant grew.", "The  plant\ngrew.")
    assert layout["layout_only_change"] and layout["total_edit_budget"] == 0
    replacement = change_metrics("red red blue", "red green blue")
    assert replacement["changed_original_tokens"] == 1 and replacement["added_tokens"] == 1


def test_four_condition_evaluation_is_paired_and_never_fabricates_model_scores():
    r = evaluate([comparison()], allow_fixture=True)
    assert not r["valid_for_scientific_claims"] and r["data_status"] == "fixture_not_research"
    assert set(r["summary"]) == {"original", "generic_accessibility", "uniform_simplification", "targeted"}
    assert r["summary"]["targeted"]["mean_total_edit_budget"] > 0
    assert r["summary"]["original"]["mean_total_edit_budget"] == 0
    for v in r["passages"][0]["conditions"].values():
        assert v["readability_score_delta"] is None
        assert v["verification"]["embedding_cosine"] is None and v["verification"]["nli"] is None


def test_missing_conditions_and_invalid_control_fail():
    c = comparison(); del c["targeted"]
    with pytest.raises(ValueError): evaluate([c])
    with pytest.raises(ValueError, match="preserve original"):
        evaluate([{**comparison(), "generic_accessibility": "new text"}])
    with pytest.raises(ValueError, match="duplicate"):
        evaluate([comparison(), comparison()])


def test_evaluation_write_hash_and_no_overwrite(tmp_path):
    p = tmp_path / "in.jsonl"; p.write_text(json.dumps(comparison()) + "\n", encoding="utf-8")
    r = write_evaluation(p, tmp_path / "output", allow_fixture=True)
    assert len(r["source"]["sha256"]) == 64 and "NOT RESEARCH" in (tmp_path / "output" / "evaluation.md").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError): write_evaluation(p, tmp_path / "output", True)


@pytest.fixture
def baseline_experiment(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"seed": 7, "labels": ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"],
        "split": {"strategy": "grouped_by_document", "train": .7, "validation": .15, "test": .15},
        "models": {"baselines": ["tfidf_logreg", "tfidf_svm"], "transformer": None, "fusion": False},
        "analysis": {"bootstrap_resamples": 20, "top_k_examples": 2}}), encoding="utf-8")
    m = run_experiment(cfg, p, tmp_path / "exp", allow_fixture=True)
    return tmp_path / "exp" / m["experiment_id"], p, cfg


def test_paper_tables_reject_fixture_by_default_and_mark_test_exports(baseline_experiment, tmp_path):
    exp, _, _ = baseline_experiment
    with pytest.raises(ValueError, match="research"):
        export_tables(exp, tmp_path / "paper")
    assert not (tmp_path / "paper").exists()
    export_tables(exp, tmp_path / "fixture_paper", allow_fixture=True)
    table = pd.read_csv(tmp_path / "fixture_paper" / "classification.csv")
    assert len(table) == 3 and table.evidence_status.str.startswith("NOT RESEARCH").all()
    assert set(table.split) == {"test"}
    with pytest.raises(FileExistsError): export_tables(exp, tmp_path / "fixture_paper", True)


def test_paper_export_and_runner_refuse_tampered_artifacts(baseline_experiment, tmp_path):
    exp, data, cfg = baseline_experiment
    p = exp / "baselines" / "results.json"; p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        export_tables(exp, tmp_path / "paper", True)
    with pytest.raises(ValueError, match="changed"):
        run_experiment(cfg, data, exp.parent, allow_fixture=True)
    with pytest.raises(FileExistsError, match="overwrite"):
        run_experiment(cfg, data, exp.parent, allow_fixture=True, force=True)


def test_paper_metric_consistency():
    from ML.paper_tables import _row
    from ML.baselines import metrics
    good = metrics(["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"], ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"])
    assert _row("fixture", 1, good, False)["accuracy"] == 1
    good["accuracy"] = .5
    with pytest.raises(ValueError, match="accuracy disagrees"):
        _row("fixture", 1, good, False)
