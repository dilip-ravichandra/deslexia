import pytest
from ML.interventions import (intervene, vocabulary, syntactic, conceptual, register_generator,
                              clear_generators, word_diff, route, chunks)
from ML.semantic_verifier import verify


def test_vocab_gloss_keeps_word_and_tracks_ops():
    r = vocabulary("the catalyst")
    assert r["adapted"] == "the catalyst (a substance that makes a reaction go faster)"
    assert r["status"] == "applied" and r["operations"][0]["entry"] == "catalyst"
    assert r["is_heuristic"] and r["is_trained_model_output"] is False
    assert "DEMO" in r["resources"]["lexicon_status"]


def test_vocab_replace_variant_inflection_and_capitalisation():
    assert vocabulary("accelerated", variant=1)["adapted"] == "sped up"
    assert vocabulary("Eventually", variant=1)["adapted"] == "In the end"
    r = vocabulary("catalyst", variant=1)       # no replacement form -> falls back to gloss
    assert r["operations"][0]["rule"] == "lexicon_gloss_fallback"


def test_vocab_unknown_word_is_honest_no_change():
    r = vocabulary("zorblax")
    assert r["status"] == "no_change" and r["changed"] is False and "no lexicon entry" in r["reason"]


def test_vocab_each_entry_glossed_once_and_plural():
    r = vocabulary("catalyst and catalysts")
    assert r["adapted"].count("(") == 1
    assert "(" in vocabulary("enzymes")["adapted"]


def test_syntactic_concessive_and_which_and_semicolon():
    r = syntactic("Although the reaction was slow, the catalyst eventually accelerated it.")
    assert r["adapted"] == "The reaction was slow. But the catalyst eventually accelerated it."
    assert r["operations"][0]["rule"] == "concessive_split"
    r = syntactic("The enzyme binds the substrate, which lowers the energy needed.")
    assert r["adapted"] == "The enzyme binds the substrate. This lowers the energy needed."
    r = syntactic("The water heated up quickly; the ice melted soon after.")
    assert r["adapted"] == "The water heated up quickly. The ice melted soon after."


def test_syntactic_list_commas_not_split_and_chunks_offered():
    s = "We bought apples, pears, and plums at the market today."
    r = syntactic(s)
    assert r["status"] == "no_change" and r["adapted"] == s and len(r["chunks"]) >= 2
    lay = syntactic(s, variant=1)
    assert lay["status"] == "layout_only" and lay["adapted"] == s


def test_conceptual_steps_and_scaffold_never_invents_content():
    r = conceptual("First the water evaporates, then it condenses, and finally it falls as rain.")
    assert r["status"] == "applied" and r["adapted"].startswith("• First the water evaporates")
    assert verify(r["original"], r["adapted"])["numbers_preserved"] is True
    s = conceptual("Inflation reduces purchasing power over time.")
    assert s["status"] == "scaffold_only" and s["changed"] is False
    assert s["scaffold"]["questions"] and "does not explain" in s["scaffold"]["note"]


def test_routing_rejects_unknown_category_and_legacy_route():
    with pytest.raises(ValueError):
        intervene("OTHER_UNCERTAIN", "x")
    assert route("VOCABULARY", "catalyst")["category"] == "VOCABULARY"


def test_plugin_generator_is_tagged_and_removable():
    register_generator("CONCEPTUAL", "fake", lambda sp, se, b, a: "Simple version.")
    try:
        r = intervene("CONCEPTUAL", "x", sentence="A complex idea.")
        assert r["method"] == "plugin:fake" and r["adapted"] == "Simple version."
    finally:
        clear_generators()
    assert intervene("CONCEPTUAL", "x", sentence="A complex idea.")["method"] == "rule_based_v1"


def test_word_diff_and_chunks():
    assert word_diff("a b c", "a x c") == [{"type": "replace", "from": "b", "to": "x"}]
    assert chunks("It rained, so we left because it was late.") == ["It rained,", "so we left", "because it was late."]


@pytest.mark.parametrize("cat,span,sent", [
    ("VOCABULARY", "accelerated", "accelerated"),
    ("SYNTACTIC", "x", "Although the reaction was slow, the catalyst eventually accelerated it."),
    ("SYNTACTIC", "x", "The enzyme binds the substrate, which lowers the energy needed."),
])
def test_rule_outputs_pass_the_verifier_for_known_cases(cat, span, sent):
    r = intervene(cat, span, sentence=sent)
    v = verify(r["original"], r["adapted"])
    assert v["status"] in {"pass", "review"}, v["flags"]
