import pytest
from ML.semantic_verifier import (basic_verify, verify, numbers, negation_count, entities, EmbeddingScorer,
                                  NLIScorer)


class FakeEmb:
    available = True
    def __init__(self, v): self.v = v
    def score(self, a, b): return self.v


class FakeNLI:
    available = True
    def __init__(self, e, c): self.e, self.c = e, c
    def probs(self, p, h): return {"entailment": self.e, "neutral": 1 - self.e - self.c, "contradiction": self.c}


def test_number_preservation():
    r = basic_verify("The plant grew 20 cm.", "The plant grew 20 cm.")
    assert r["numbers_preserved"] is True and r["status"] == "pass"


def test_numbers_normalise_commas_and_detect_change():
    assert numbers("It cost 1,200 or 3.5%") == ["1200", "3.5%"]
    assert verify("It grew 20 cm.", "It grew 25 cm.")["status"] == "fail"


def test_negation_flip_is_hard_fail():
    assert negation_count("It doesn't work, never") == 2
    r = verify("The drug is not safe.", "The drug is safe.")
    assert r["status"] == "fail" and any(f["check"] == "negation" for f in r["flags"])


def test_dropped_entity_hard_added_entity_soft():
    assert entities("Then Newton met Einstein at NASA.") == {"Newton", "Einstein", "NASA"}
    assert verify("Then Newton met Einstein.", "Then he met Einstein.")["status"] == "fail"
    r = verify("It is hot there.", "It is hot there in Spain.")
    assert r["status"] == "review" and r["entities_preserved"] is False


def test_modality_change_is_soft_review():
    r = verify("All metals may corrode.", "Metals corrode.")
    assert r["status"] == "review" and any(f["check"] == "modality" for f in r["flags"])


def test_unavailable_scorers_are_reported_not_replaced():
    r = verify("The cat sat.", "The cat sat.")
    names = {u["check"] for u in r["checks_unavailable"]}
    assert names == {"embedding_cosine", "nli"} and r["embedding_cosine"] is None and r["nli"] is None
    assert r["meaning_preservation_guaranteed"] is False and r["thresholds_validated"] is False


def test_scorers_used_when_present():
    ok = verify("The cat sat.", "The cat sat down.", embedder=FakeEmb(0.9), nli=FakeNLI(0.9, 0.01))
    assert ok["status"] == "pass" and {"embedding_cosine", "nli"} <= set(ok["checks_run"])
    low = verify("The cat sat.", "The cat sat down.", embedder=FakeEmb(0.2), nli=FakeNLI(0.9, 0.01))
    assert low["status"] == "review"
    bad = verify("The cat sat.", "The cat sat down.", embedder=FakeEmb(0.9), nli=FakeNLI(0.1, 0.8))
    assert bad["status"] == "fail"


def test_real_scorers_degrade_gracefully_offline():
    e, n = EmbeddingScorer("no/such-model", offline=True), NLIScorer("no/such-model", offline=True)
    assert not e.available and e.error and not n.available and n.error
    r = verify("a b c", "a b c", embedder=e, nli=n)
    assert {u["check"] for u in r["checks_unavailable"]} == {"embedding_cosine", "nli"}
    assert all(u["reason"] for u in r["checks_unavailable"])


def test_large_length_change_flagged():
    assert verify("Cells divide.", "Cells divide " + "and grow " * 20)["status"] == "review"
