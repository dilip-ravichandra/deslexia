"""Task 00 audit guards: repository integrity and research-integrity invariants.

These tests do not measure model performance. They protect against fabricated
results, demo/research mixing, and malformed seed data.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_project_state_makes_no_unsupported_claims():
    s = json.loads((ROOT / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    assert s["research_model_available"] is False
    assert s["gold_dataset_available"] is False


def test_manifest_declares_no_fabricated_results():
    m = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    assert m["fabricated_results"] is False
    assert m["research_model_bundled"] is False


def test_seed_csv_parses_with_consistent_columns():
    df = pd.read_csv(ROOT / "DATA" / "seed_examples.csv")
    assert len(df) == 3
    assert df["span_id"].notna().all()
    assert (df["annotator_id"] == "seed").all()  # seed rows are smoke data, not gold


def test_results_template_contains_no_numeric_results():
    text = (ROOT / "PAPER" / "results_template.md").read_text(encoding="utf-8")
    rows = [r for r in text.splitlines() if r.startswith("| ") and "---" not in r][1:]
    assert rows and all("NOT_AVAILABLE" in r for r in rows)


def test_shipped_lexical_results_do_not_impersonate_routing_or_student_results():
    art = ROOT / "ARTIFACTS"
    for path in (art/'human_lexical').glob('*/results.json'):
        result=json.loads(path.read_text(encoding='utf-8'))
        assert result['routing_claims_allowed'] is False
        assert result['data_status']=='PUBLIC_HUMAN_LEXICAL_ONLY'
        assert result['status'] in {'completed','interrupted','failed','running'}
    assert not (art/'human_routing_active.json').exists()


def test_backend_is_labelled_demo_without_a_validated_model():
    from fastapi.testclient import TestClient
    from BACKEND.app import app

    c = TestClient(app)
    assert c.get("/api/model-status").json()["research_model_available"] is False
    r = c.post("/api/adapt", json={"text": "The catalyst helped.", "span": "catalyst"}).json()
    assert r["research_mode"] == "demo" and r["valid_for_research"] is False
    assert r["category"]["is_trained_model_output"] is False and r["category"]["probabilities"] is None
