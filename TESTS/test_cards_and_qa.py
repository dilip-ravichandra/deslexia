import json
import re
from pathlib import Path
import pytest
from ML.cards import model_card, dataset_card, facts, write_cards
from QA import audit as qa

ROOT = Path(__file__).resolve().parents[1]


def mini_root(tmp, pending=True):
    (tmp / "ARTIFACTS").mkdir(); (tmp / "DATA").mkdir()
    (tmp / "DECISIONS.md").write_text("## ADR-009\nstatus: " + ("PENDING" if pending else "ACCEPTED") + "\n", encoding="utf-8")
    (tmp / "PROJECT_STATE.json").write_text("{}", encoding="utf-8")
    return tmp


def run_dir(tmp, name, status, valid, acc, f1):
    d = tmp / "ARTIFACTS" / name; d.mkdir(parents=True)
    m = {"test": {"accuracy": acc, "macro_f1": f1, "n": 40}, "validation": {"accuracy": 0, "macro_f1": 0, "n": 1},
         "data_status": status, "valid_for_scientific_claims": valid, "weights": "pretrained:x", "split_sizes": {"test": 40}}
    (d / "results.json").write_text(json.dumps(m), encoding="utf-8"); (d / "metadata.json").write_text(json.dumps({"dataset_sha256": "ab" * 32}), encoding="utf-8")


def test_cards_with_no_artifacts_state_no_model_no_dataset_and_no_numbers(tmp_path):
    r = mini_root(tmp_path)
    mc, dc = model_card(r), dataset_card(r)
    assert "NO VALIDATED MODEL" in mc and "NOT AVAILABLE" in mc
    assert "NO GOLD DATASET EXISTS" in dc and "DO NOT REDISTRIBUTE" in dc and "PENDING" in dc
    assert not re.search(r"\| *0\.\d{3}", mc)                       # no metric cells


def test_smoke_runs_are_counted_but_never_quoted(tmp_path):
    r = mini_root(tmp_path); run_dir(r, "smoke", "fixture_not_research", False, 0.987, 0.654)
    mc = model_card(r)
    assert "NO VALIDATED MODEL" in mc and "0.987" not in mc and "0.654" not in mc
    assert "present in this checkout (not quoted): 1" in mc


def test_research_run_metrics_are_quoted_from_the_artifact(tmp_path):
    # PLUMBING TEST: forged artifact, only to prove the card copies values from artifacts and nothing else
    r = mini_root(tmp_path); run_dir(r, "real", "research", True, 0.8123, 0.7777)
    mc = model_card(r)
    assert "NO VALIDATED MODEL" not in mc and "0.812" in mc and "0.778" in mc and "abababababab" in mc


def test_dataset_card_release_status_follows_adr009(tmp_path):
    assert "DO NOT REDISTRIBUTE" in dataset_card(mini_root(tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path))
    b = tmp_path / "b"; b.mkdir()
    assert "DO NOT REDISTRIBUTE" not in dataset_card(mini_root(b, pending=False))


def test_repo_cards_are_up_to_date_with_generator(tmp_path):
    assert (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8") == model_card(ROOT)
    assert (ROOT / "DATASET_CARD.md").read_text(encoding="utf-8") == dataset_card(ROOT)


# ------------------------------------------------------------------ QA audit
def test_claim_regex_flags_unqualified_metrics_only():
    bad = "The model reached macro-F1 0.83 on the test set."
    ok = ["Smoke fixture macro-F1 0.5 means nothing.", "| Majority | NOT_AVAILABLE |", "alpha = 0.743 published reference"]
    assert qa.CLAIM.search(bad) and not qa.SAFE_WORDS.search(bad)
    assert all(qa.SAFE_WORDS.search(l) for l in ok)


def test_secret_patterns_catch_tokens():
    samples = ["hf_" + "a" * 34, "sk-" + "b" * 24, "ghp_" + "c" * 36, 'api_key = "' + "d" * 20 + '"']
    assert all(any(re.search(p, s) for p in qa.SECRETS) for s in samples)
    assert not any(re.search(p, "def token_count(): return 3") for p in qa.SECRETS)


def test_ui_collector_detects_unlabelled_controls():
    c = qa.Collect(); c.feed('<html><input id="a"><label for="b">B</label><input id="b"><input id="c" aria-label="C"><button></button></html>')
    unl = [x["id"] for x in c.controls if not (x["in_label"] or x["aria"] or (x["id"] in c.labels_for))]
    assert unl == ["a"] and c.buttons[0]["text"].strip() == ""


def test_research_integrity_check_flags_false_state_claims(tmp_path):
    (tmp_path / "PROJECT_STATE.json").write_text(json.dumps({"research_model_available": True}), encoding="utf-8")
    r = qa.R(); qa.research_integrity(tmp_path, r)
    ri01 = next(i for i in r.items if i["id"] == "RI-01")
    assert ri01["status"] == "fail"


def test_repo_passes_qa_audit_without_high_severity_failures():
    res = qa.audit(ROOT, run_tests=False, final_docs=True)
    assert res["high_severity_failures"] == [], [i for i in res["items"] if i["status"] == "fail"]
    assert res["counts"]["fail"] == 0, [i for i in res["items"] if i["status"] == "fail"]
