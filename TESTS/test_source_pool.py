from ML.source_pool import build_pool, passages

# SYNTHETIC rows, only to test the transform; not real corpus content.
LONG = " ".join(["word"] * 40)
ROWS = [dict(page_id=i, title=f"T{i}", content=f"# Head\n\n{LONG}\n\nshort\n\n{LONG} more", error=False)
        for i in range(10)] + [dict(page_id=99, title="bad", content=LONG, error=True)]


def test_passages_filters_headings_and_short_text():
    ps = passages(f"# Head\n\n{LONG}\n\nshort\n\n| a | b |")
    assert ps == [LONG]


def test_pool_has_license_attribution_no_labels_and_is_deterministic():
    a = build_pool(list(ROWS), n_articles=5, per_article=2)
    b = build_pool(list(ROWS), n_articles=5, per_article=2)
    assert a.equals(b)
    assert a.document_id.nunique() == 5 and 99 not in set(a.document_id.str[3:].astype(int))
    assert (a.source_license == "CC-BY-SA-3.0").all() and a.attribution.str.len().gt(0).all()
    assert "category" not in a.columns
