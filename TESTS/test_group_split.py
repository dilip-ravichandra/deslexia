import pandas as pd
from ML.group_split import split

def test_document_groups_do_not_leak():
    d = pd.DataFrame({
        "document_id": ["a","a","b","b","c","c","d","d","e","e"],
        "category": ["VOCABULARY"] * 10
    })
    tr, va, te = split(d)
    assert not set(tr.document_id) & set(va.document_id)
    assert not set(tr.document_id) & set(te.document_id)
    assert not set(va.document_id) & set(te.document_id)


import pytest
from ML.group_split import leakage_report, freeze, load_frozen, MIN_GROUPS


def synth(n_docs=20, per=5):
    # SYNTHETIC TEST FIXTURE ONLY
    rows = [dict(source_id=f"src{d%4}", document_id=f"d{d}", span_id=f"d{d}_{i}",
                 text=f"w{d}_{i}", context_before="", context_after="",
                 category=["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"][(d + i) % 3])
            for d in range(n_docs) for i in range(per)]
    return pd.DataFrame(rows)


def test_every_split_nonempty_and_proportions_reasonable():
    d = synth()
    tr, va, te = split(d)
    assert min(len(tr), len(va), len(te)) > 0
    assert len(tr) + len(va) + len(te) == len(d)
    assert abs(len(tr) / len(d) - 0.70) <= 0.10


def test_deterministic_and_seed_sensitive():
    d = synth()
    a = split(d, seed=1)[0].span_id.tolist()
    assert a == split(d, seed=1)[0].span_id.tolist()
    assert a != split(d, seed=2)[0].span_id.tolist()


def test_too_few_groups_fails_clearly():
    with pytest.raises(ValueError, match="at least"):
        split(synth(n_docs=MIN_GROUPS - 1))
    with pytest.raises(ValueError):
        split(synth(), train=0.9, validation=0.2)


def test_leakage_report_detects_planted_leak_and_duplicates():
    d = synth()
    tr, va, te = split(d)
    assert not leakage_report(tr, va, te)["leaks_found"]
    leaked = pd.concat([va, tr.iloc[:1]])
    assert leakage_report(tr, leaked, te)["leaks_found"]
    dup = va.copy(); dup.iloc[0, dup.columns.get_loc("text")] = tr.iloc[0]["text"]
    assert leakage_report(tr, dup, te)["leaks"]["train|validation|duplicate_span_context"] == 1


def test_freeze_roundtrip_refuses_overwrite_and_detects_data_change(tmp_path):
    p = tmp_path / "d.csv"
    synth().to_csv(p, index=False)
    m = freeze(p, tmp_path / "m.json")
    assert m["frozen"] and not m["leakage"]["leaks_found"]
    tr, va, te = load_frozen(tmp_path / "m.json", p)
    assert len(tr) + len(va) + len(te) == 100
    with pytest.raises(FileExistsError):
        freeze(p, tmp_path / "m.json")
    synth(21).to_csv(p, index=False)
    with pytest.raises(ValueError, match="changed"):
        load_frozen(tmp_path / "m.json", p)
