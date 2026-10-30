"""DistilBERT + linguistic-feature fusion (Task 07).

FusionClassifier: encoder CLS vector -> concat(projected features) -> dropout -> 3-class linear.
`use_features=False` gives the matched transformer-only control (same CLS pooling, dropout and
linear head), so an ablation changes ONE thing: whether the features are present. (The Hugging
Face DistilBertForSequenceClassification head has an extra pre-classifier layer, so it is not a
matched control.)
"""
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ML.features import FEATURE_NAMES, span_context_features

LABELS = ["VOCABULARY", "SYNTACTIC", "CONCEPTUAL"]


class FusionClassifier(nn.Module):
    def __init__(self, encoder, n_features=len(FEATURE_NAMES), proj_dim=16, dropout=0.1,
                 num_labels=3, use_features=True):
        super().__init__()
        self.encoder = encoder
        hidden = encoder.config.dim
        self.use_features = use_features
        self.proj = nn.Sequential(nn.Linear(n_features, proj_dim), nn.ReLU()) if use_features else None
        self.drop = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden + (proj_dim if use_features else 0), num_labels)

    def forward(self, input_ids, attention_mask=None, features=None, **_):
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
        if self.use_features:
            if features is None:
                raise ValueError("features required when use_features=True")
            h = torch.cat([h, self.proj(features)], dim=-1)
        return self.classifier(self.drop(h))


def feature_matrix(df):
    return np.array([span_context_features(r.text, r.context_before if isinstance(r.context_before, str) else "",
                                           r.context_after if isinstance(r.context_after, str) else "")
                     for r in df.itertuples()], dtype=np.float32)


def fit_scaler(train_matrix):
    mean = train_matrix.mean(0)
    std = np.maximum(train_matrix.std(0), 1e-6)
    return mean, std  # statistics from TRAIN only


def save_fusion(model, tok, out, mean, std, arch, extra=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out / "fusion_model.pt")
    cfg = {"arch": arch, "labels": LABELS, "feature_names": FEATURE_NAMES,
           "scaler_mean": mean.tolist(), "scaler_std": std.tolist(),
           "use_features": model.use_features, "proj_dim": 16, "dropout": model.drop.p,
           "encoder_config": model.encoder.config.to_dict(), **(extra or {})}
    (out / "fusion_config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tok.save_pretrained(out / "tokenizer")


def load_fusion(model_dir):
    """Rebuild from saved config + weights (no download needed)."""
    from transformers import AutoTokenizer, DistilBertConfig, DistilBertModel
    d = Path(model_dir)
    cfg = json.loads((d / "fusion_config.json").read_text(encoding="utf-8"))
    enc = DistilBertModel(DistilBertConfig.from_dict(cfg["encoder_config"]))
    m = FusionClassifier(enc, len(cfg["feature_names"]), cfg["proj_dim"], cfg["dropout"], 3, cfg["use_features"])
    m.load_state_dict(torch.load(d / "fusion_model.pt", map_location="cpu", weights_only=True))
    m.eval()
    return m, AutoTokenizer.from_pretrained(d / "tokenizer",local_files_only=True), cfg
