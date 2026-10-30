import pandas as pd
import pytest
from ML.annotation import (make_batches, export_batches, import_annotations,
                           merge_annotations, resolve, adjudication_sheet)

# SYNTHETIC TEST FIXTURE ONLY - not data, not labels from any real annotator.
POOL = pd.DataFrame({
    "source_id": "fixture", "document_id": [f"d{i//2}" for i in range(8)],
    "span_id": [f"sp{i}" for i in range(8)], "text": [f"t{i}" for i in range(8)],
    "context_before": "", "context_after": ""})


def labelled(batch, labels, who):
    b = batch.copy()
    b["category"] = [labels.get(s, "VOCABULARY") for s in b["span_id"]]
    b["confidence"] = 4
    b["annotator_id"] = who
    return b


def test_batches_double_annotated_balanced_and_label_free():
    b = make_batches(POOL, ["a1", "a2", "a3"], copies=2)
    counts = pd.concat(b.values())["span_id"].value_counts()
    assert (counts == 2).all() and len(counts) == 8
    sizes = [len(v) for v in b.values()]
    assert max(sizes) - min(sizes) <= 1
    assert all((v["category"] == "").all() for v in b.values())


def test_batches_deterministic_and_reject_ai_annotators():
    assert make_batches(POOL, ["a", "b"], seed=1)["a"].equals(make_batches(POOL, ["a", "b"], seed=1)["a"])
    with pytest.raises(ValueError):
        make_batches(POOL, ["a", "llm"])
    with pytest.raises(ValueError):
        make_batches(POOL, ["a"], copies=2)


def roundtrip(tmp_path, who, labels):
    batches = make_batches(POOL, ["a1", "a2"], copies=2)
    p = export_batches({who: labelled(batches[who], labels, who)}, tmp_path)[0]
    return import_annotations(p, POOL.span_id, "guideline_v1", expected_annotator=who)


def test_import_roundtrip_and_validation(tmp_path):
    df = roundtrip(tmp_path, "a1", {})
    assert set(df.guideline_version) == {"guideline_v1"} and len(df) == 8
    bad = labelled(make_batches(POOL, ["a1", "a2"])["a1"], {"sp0": "NOPE"}, "a1")
    bad.to_csv(tmp_path / "bad.csv", index=False)
    with pytest.raises(ValueError):
        import_annotations(tmp_path / "bad.csv", POOL.span_id, "g")
    blank = make_batches(POOL, ["a1", "a2"])["a1"]
    blank.to_csv(tmp_path / "blank.csv", index=False)
    with pytest.raises(ValueError):
        import_annotations(tmp_path / "blank.csv", POOL.span_id, "g")
    with pytest.raises(ValueError):
        import_annotations(tmp_path / "bad.csv", POOL.span_id, "g", expected_annotator="a2")


def test_resolve_never_auto_resolves_disagreement(tmp_path):
    b = make_batches(POOL, ["a1", "a2"], copies=2)
    f1 = import_annotations(export_batches({"a1": labelled(b["a1"], {"sp0": "SYNTACTIC"}, "a1")}, tmp_path / "1")[0], POOL.span_id, "g")
    f2 = import_annotations(export_batches({"a2": labelled(b["a2"], {"sp0": "CONCEPTUAL", "sp1": "OTHER_UNCERTAIN"}, "a2")}, tmp_path / "2")[0], POOL.span_id, "g")
    long = merge_annotations([f1, f2])
    gold, queue = resolve(long)
    assert set(queue.span_id) == {"sp0", "sp1"}
    assert dict(zip(queue.span_id, queue.reason)) == {"sp0": "disagreement", "sp1": "disagreement"}
    assert len(gold) == 6 and set(gold.resolution) == {"unanimous"}
    adj = pd.DataFrame([dict(span_id="sp0", adjudicator_id="prof_x", final_category="CONCEPTUAL", note="", created_at="t")])
    gold2, queue2 = resolve(long, adj)
    assert "sp0" in set(gold2.span_id) and set(queue2.span_id) == {"sp1"}
    assert gold2.set_index("span_id").loc["sp0", "resolution"] == "adjudicated"
    sheet = adjudication_sheet(queue2, POOL)
    assert {"text", "context_before", "final_category"} <= set(sheet.columns)


def test_adjudicator_must_be_human_and_unique():
    long = pd.DataFrame(dict(span_id=["x", "x"], annotator_id=["a", "b"], category=["VOCABULARY", "SYNTACTIC"]))
    bad = pd.DataFrame([dict(span_id="x", adjudicator_id="model", final_category="VOCABULARY", note="", created_at="")])
    with pytest.raises(ValueError):
        resolve(long, bad)
    dup = pd.concat([bad.assign(adjudicator_id="h")] * 2)
    with pytest.raises(ValueError):
        resolve(long, dup)


def test_single_annotation_goes_to_queue():
    long = pd.DataFrame(dict(span_id=["x"], annotator_id=["a"], category=["VOCABULARY"]))
    gold, q = resolve(long)
    assert gold.empty and q.reason.iloc[0] == "insufficient_annotations"
