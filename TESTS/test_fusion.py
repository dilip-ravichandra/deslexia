import json
import numpy as np
import pandas as pd
import pytest
import torch
from ML.features import FEATURE_NAMES, span_context_features, linguistic_features
from ML.context import build_context, sentence_around, locate_span
from ML.distilbert_trainer import run
from ML.ablation import run_ablation
from ML.fusion import load_fusion, FusionClassifier, feature_matrix
from TESTS.test_baselines import synth  # SYNTHETIC fixture only

FAST = dict(epochs=1, batch_size=32, max_len=24, patience=1)


def test_features_are_text_only_and_fixed_order():
    forbidden = ("color", "colour", "contrast", "font", "spacing", "size", "focus", "background", "visual")
    assert not any(f in n for n in FEATURE_NAMES for f in forbidden)
    v = span_context_features("catalyst", "The reaction was slow. The", "eventually sped it up. Then it ended.")
    assert len(v) == len(FEATURE_NAMES) == 10 and v[0] == 1.0 and v[1] == 8.0


def test_context_builder():
    text = "One idea. Although it was slow, the catalyst sped it up. Another idea."
    c = build_context(text, "catalyst")
    assert c["sentence"] == "Although it was slow, the catalyst sped it up."
    assert text[c["span_start"]:c["span_end"]] == "catalyst"
    assert locate_span("a b a", "a", 4) == (4, 5)
    with pytest.raises(ValueError):
        locate_span("abc", "zzz")
    with pytest.raises(ValueError):
        locate_span("a b a", "a", 2)
    with pytest.raises(ValueError):
        build_context("x" * 6000, "x")


def test_matched_control_has_no_feature_branch_and_fusion_does():
    from transformers import DistilBertConfig, DistilBertModel
    enc = DistilBertModel(DistilBertConfig(n_layers=1, n_heads=2, dim=16, hidden_dim=32, vocab_size=50))
    off, on = FusionClassifier(enc, use_features=False), FusionClassifier(enc, use_features=True)
    assert off.proj is None and on.proj is not None
    assert off.classifier.in_features == 16 and on.classifier.in_features == 32
    ids = torch.tensor([[1, 2, 3]])
    assert off(ids).shape == (1, 3) and on(ids, features=torch.zeros(1, 10)).shape == (1, 3)
    with pytest.raises(ValueError):
        on(ids)


def test_fusion_smoke_run_saves_and_reloads(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    r = run(p, tmp_path / "o", smoke=True, arch="fusion_on", **FAST)
    assert r["arch"] == "fusion_on" and r["valid_for_scientific_claims"] is False and "fusion_on" in r["weights"]
    m, tok, cfg = load_fusion(tmp_path / "o" / "model")
    assert cfg["feature_names"] == FEATURE_NAMES and cfg["use_features"] is True
    df = pd.read_csv(p).head(4)
    df["model_input"] = df.context_before.fillna("") + " [SPAN] " + df.text + " [/SPAN] " + df.context_after.fillna("")
    F = (feature_matrix(df) - np.array(cfg["scaler_mean"])) / np.array(cfg["scaler_std"])
    enc = tok(list(df.model_input), padding=True, return_tensors="pt", truncation=True, max_length=24)
    with torch.no_grad():
        out = m(enc["input_ids"], enc["attention_mask"], features=torch.tensor(F, dtype=torch.float))
    assert out.shape == (4, 3)


def test_unknown_arch_rejected(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    with pytest.raises(ValueError):
        run(p, tmp_path / "o", smoke=True, arch="nope")


def test_ablation_structure_and_guards(tmp_path):
    p = tmp_path / "d.csv"; synth().to_csv(p, index=False)
    r = run_ablation(p, tmp_path / "ab", seeds=(1, 2), smoke=True, **FAST)
    assert set(r["per_seed"]) == {"fusion_off", "fusion_on"} and len(r["per_seed"]["fusion_on"]) == 2
    assert r["valid_for_scientific_claims"] is False
    assert "DESCRIPTIVE ONLY" in r["interpretation"] and "Fewer than 5 seeds" in r["interpretation"]
    assert (tmp_path / "ab" / "ablation.json").exists()
    assert len(r["paired_test_macro_f1_diff_on_minus_off"]["values"]) == 2
