"""DistilBERT span-support classifier training (Task 06).

Modes
-----
research : real human-labelled data (research-mode validation + frozen split manifest)
           AND pretrained weights downloaded successfully. Only this mode can support claims.
smoke    : tiny locally initialised model + locally trained tokenizer. Tests the pipeline
           only; outputs are stamped and carry valid_for_scientific_claims=False.

Protocol: validation macro-F1 selects the best epoch (early stopping); the test split is
scored once at the end with that checkpoint. Class-weighted loss from TRAIN counts only.
Runs on Windows / Linux / Colab (CPU or CUDA). A failed weight download is a hard error,
never a silent fallback to random weights.
"""
import json
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ML.baselines import add_model_input, metrics
from ML.data_validation import PRIMARY_LABELS as LABELS, check, file_sha256
from ML.group_split import load_frozen, split
from ML.fusion import FusionClassifier, feature_matrix, fit_scaler, save_fusion

DEFAULTS = dict(model_name="distilbert/distilbert-base-multilingual-cased", epochs=4, lr=5e-5, batch_size=16,
                max_len=128, patience=2, weight_decay=0.01, warmup_frac=0.1)


def set_seed(seed):
    import torch
    torch.set_num_threads(4)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _validate_labels(tr, va, te):
    for name, d in (("train", tr), ("validation", va), ("test", te)):
        if len(d) == 0:
            raise ValueError(f"{name} split is empty")
    missing = set(LABELS) - set(tr.category)
    if missing:
        raise ValueError(f"train split has no examples of {sorted(missing)}")
    warn = [f"{k}: only {v} train examples" for k, v in tr.category.value_counts().items() if v < 10]
    return warn


def _smoke_model_and_tokenizer(texts, max_len):
    from tokenizers import Tokenizer, models, pre_tokenizers, processors, trainers
    from transformers import DistilBertConfig, DistilBertForSequenceClassification, PreTrainedTokenizerFast
    sp = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
    tk = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    tk.pre_tokenizer = pre_tokenizers.Whitespace()
    tk.train_from_iterator(texts, trainers.WordPieceTrainer(vocab_size=600, special_tokens=sp))
    tk.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", tk.token_to_id("[CLS]")), ("[SEP]", tk.token_to_id("[SEP]"))])
    tok = PreTrainedTokenizerFast(tokenizer_object=tk, unk_token="[UNK]", pad_token="[PAD]",
                                  cls_token="[CLS]", sep_token="[SEP]", mask_token="[MASK]")
    cfg = DistilBertConfig(vocab_size=tk.get_vocab_size(), n_layers=2, n_heads=2, dim=64, hidden_dim=128,
                           max_position_embeddings=max_len + 8, num_labels=3,
                           id2label=dict(enumerate(LABELS)), label2id={l: i for i, l in enumerate(LABELS)})
    return DistilBertForSequenceClassification(cfg), tok


def _pretrained(model_name, offline, out):
    from transformers import AutoTokenizer, DistilBertForSequenceClassification
    try:
        tok = AutoTokenizer.from_pretrained(model_name, local_files_only=offline)
        model = DistilBertForSequenceClassification.from_pretrained(
            model_name, num_labels=3, id2label=dict(enumerate(LABELS)),
            label2id={l: i for i, l in enumerate(LABELS)}, local_files_only=offline)
        return model, tok
    except Exception as e:  # network blocked, repo missing, no local cache, ...
        out.mkdir(parents=True, exist_ok=True)
        info = {"status": "PRETRAINED_WEIGHTS_UNAVAILABLE", "model_name": model_name,
                "offline_flag": offline, "error_type": type(e).__name__, "error": str(e)[:500],
                "practical_alternatives": [
                    "run on a machine/Colab with huggingface.co access",
                    "download the model once (git lfs / huggingface-cli download) and pass its folder as model_name",
                    "set offline=True only if the model is already in the local cache"]}
        (out / "DOWNLOAD_FAILED.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        raise RuntimeError(f"Could not load pretrained weights for {model_name!r}: {type(e).__name__}. "
                           f"No training was run. See {out/'DOWNLOAD_FAILED.json'}") from e


def _encode(tok, texts, max_len):
    return tok(list(texts), truncation=True, max_length=max_len, padding=True, return_tensors="pt")


def _logits(model, tok, df, F, ix, max_len, device):
    """Forward pass for rows `ix` of df. F = standardised feature matrix (fusion arches) or None."""
    import torch
    enc = {k: v.to(device) for k, v in _encode(tok, df.model_input.iloc[ix], max_len).items() if k in {'input_ids','attention_mask'}}
    if F is not None:
        enc["features"] = torch.tensor(F[ix], dtype=torch.float, device=device)
    out = model(**enc)
    return out.logits if hasattr(out, "logits") else out


def _predict(model, tok, df, max_len, bs, device, F=None):
    import torch
    model.eval()
    probs = []
    with torch.no_grad():
        for i in range(0, len(df), bs):
            ix = np.arange(i, min(i + bs, len(df)))
            probs.append(torch.softmax(_logits(model, tok, df, F, ix, max_len, device), -1).cpu().numpy())
    p = np.concatenate(probs)
    return p, [LABELS[i] for i in p.argmax(1)]


ARCHS = ("hf_head", "fusion_off", "fusion_on")


def run(csv_path, out_dir, manifest_path=None, seed=42, smoke=False, offline=False, arch="hf_head", **hp):
    import torch
    from sklearn.metrics import f1_score
    if arch not in ARCHS:
        raise ValueError(f"arch must be one of {ARCHS}")
    cfg = {**DEFAULTS, **hp}
    out = Path(out_dir)
    raw = pd.read_csv(csv_path)
    rep = check(raw, "research")
    research_data = rep.ok and manifest_path is not None
    if not smoke and not research_data:
        raise RuntimeError("Not research-valid (need research-mode validation and a frozen split manifest): "
                           f"{rep.errors or 'no manifest'}. Use smoke=True for pipeline tests only.")
    if smoke and research_data:
        pass  # allowed: smoke on real data still stamps smoke; never claims

    set_seed(seed)
    labelled = raw[raw.category.isin(LABELS)]
    excluded = int(len(raw) - len(labelled))
    if manifest_path:
        tr, va, te = (add_model_input(x[x.category.isin(LABELS)]) for x in load_frozen(manifest_path, csv_path))
        split_info = {"manifest": str(manifest_path), "manifest_sha256": file_sha256(manifest_path)}
    else:
        tr, va, te = (add_model_input(x) for x in split(labelled, seed=seed))
        split_info = {"manifest": None, "note": "ad-hoc split; not frozen"}
    warnings = _validate_labels(tr, va, te)

    if smoke:
        model, tok = _smoke_model_and_tokenizer(list(tr.model_input), cfg["max_len"])
        weights = "random_init_tiny_local"
    else:
        model, tok = _pretrained(cfg["model_name"], offline, out)
        weights = f"pretrained:{cfg['model_name']}"
    pretrained = weights.startswith("pretrained:")
    F_tr = F_va = F_te = None
    if arch != "hf_head":
        # train-only standardisation; fusion_off is the matched control (same head, no features)
        mean, std = fit_scaler(feature_matrix(tr))
        F_tr, F_va, F_te = ((feature_matrix(d) - mean) / std for d in (tr, va, te))
        model = FusionClassifier(model.distilbert, use_features=(arch == "fusion_on"))
        if arch == "fusion_off":
            F_tr = F_va = F_te = None
        weights += f"+{arch}"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    l2i = {l: i for i, l in enumerate(LABELS)}
    counts = tr.category.value_counts().reindex(LABELS).values.astype(float)
    weight = torch.tensor(counts.sum() / (3 * counts), dtype=torch.float, device=device)
    lossf = torch.nn.CrossEntropyLoss(weight=weight)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    steps = cfg["epochs"] * int(np.ceil(len(tr) / cfg["batch_size"]))
    warm = max(1, int(cfg["warmup_frac"] * steps))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min((s + 1) / warm, max(0.0, (steps - s) / max(1, steps - warm))))
    gen = np.random.default_rng(seed)

    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "training_log.jsonl"
    log_path.write_text("", encoding="utf-8")
    best, best_state, bad, t0 = (-1.0, -1), None, 0, time.time()
    y = np.array([l2i[c] for c in tr.category])
    for ep in range(1, cfg["epochs"] + 1):
        model.train()
        order = gen.permutation(len(tr))
        tot = 0.0
        for i in range(0, len(order), cfg["batch_size"]):
            ix = order[i:i + cfg["batch_size"]]
            loss = lossf(_logits(model, tok, tr, F_tr, ix, cfg["max_len"], device),
                         torch.tensor(y[ix], device=device))
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
            tot += loss.item() * len(ix)
        _, vp = _predict(model, tok, va, cfg["max_len"], cfg["batch_size"], device, F_va)
        vf1 = float(f1_score(va.category, vp, labels=LABELS, average="macro", zero_division=0))
        with open(log_path, "a") as f:
            f.write(json.dumps({"epoch": ep, "train_loss": tot / len(tr), "val_macro_f1": vf1,
                                "lr": sched.get_last_lr()[0], "elapsed_s": round(time.time() - t0, 1)}) + "\n")
        if vf1 > best[0]:
            best, bad = (vf1, ep), 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= cfg["patience"]:
                break
    model.load_state_dict(best_state)  # selection used validation only

    results = {"data_status": "research" if research_data else "fixture_not_research",
               "arch": arch, "weights": weights, "pretrained_weights_used": pretrained, "smoke": smoke,
               "valid_for_scientific_claims": bool(research_data and pretrained and not smoke),
               "best_epoch": best[1], "labels": LABELS, "excluded_non_primary_rows": excluded,
               "split_sizes": {"train": len(tr), "validation": len(va), "test": len(te)},
               "train_label_counts": tr.category.value_counts().to_dict(), "warnings": warnings}
    preds = []
    for sp, df, Fm in (("validation", va, F_va), ("test", te, F_te)):  # test scored once, after selection
        p, lab = _predict(model, tok, df, cfg["max_len"], cfg["batch_size"], device, Fm)
        results[sp] = metrics(df.category.tolist(), lab)
        if 'language' in df:
            results.setdefault('per_language',{})[sp]={}
            for language in sorted(set(df.language)):
                ix=np.flatnonzero(df.language.to_numpy()==language)
                results['per_language'][sp][language]=metrics(df.category.iloc[ix].tolist(),[lab[i] for i in ix])
        d = pd.DataFrame({"split": sp, "span_id": df["span_id"].values if "span_id" in df else range(len(df)),
                          "true": df.category.values, "pred": lab})
        for j, l in enumerate(LABELS):
            d[f"p_{l}"] = p[:, j]
        preds.append(d)
    pd.concat(preds).to_csv(out / "predictions.csv", index=False)
    if arch == "hf_head":
        model.save_pretrained(out / "model")
        tok.save_pretrained(out / "tokenizer")
    else:
        save_fusion(model, tok, out / "model", mean, std, arch, {"weights": weights, "max_len": cfg["max_len"]})
    meta = {"created_at": datetime.now(timezone.utc).isoformat(), "seed": seed, "hyperparameters": cfg,
            "data_status": results["data_status"], "weights": weights, "arch": arch, "device": device,
            "dataset_file": Path(csv_path).name, "dataset_sha256": file_sha256(csv_path), "split": split_info,
            "versions": {"python": platform.python_version(), "torch": torch.__version__,
                         "transformers": __import__("transformers").__version__,
                         "numpy": np.__version__, "pandas": pd.__version__},
            "platform": platform.platform(), "command": " ".join(sys.argv)}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
