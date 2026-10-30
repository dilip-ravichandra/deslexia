"""Reproducible experiment runner (Task 14).

One command: validate data -> freeze split -> baselines -> DistilBERT (per seed) -> fusion ablation ->
error analysis -> figures -> run_manifest.json (hashes of config, dataset, code, outputs).

Integrity rules
- experiment_id = hash(config, dataset sha256, code sha256, mode): any change gives a new folder; an identical
  completed experiment is reused (idempotent) unless --force.
- Non-research data is refused unless --allow-fixture / --smoke, and then every output is stamped non-research.
- A step that cannot run (e.g. pretrained weights not downloadable) is recorded as `unavailable` with the
  reason; the experiment becomes `partial` and valid_for_scientific_claims stays false. Nothing is skipped silently.
- valid_for_scientific_claims is true only if research-valid human data, a frozen split, and every required
  step (including real pretrained weights) completed.
"""
import hashlib
import json
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ML.data_validation import PRIMARY_LABELS, check, file_sha256

ROOT = Path(__file__).resolve().parents[1]
KNOWN_BASELINES = {"tfidf_logreg", "tfidf_svm"}
HP_KEYS = {"epochs", "lr", "batch_size", "max_len", "patience", "weight_decay", "warmup_frac"}


def load_config(path):
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".json"):
        cfg = json.loads(text)
    else:
        import yaml
        cfg = yaml.safe_load(text)
    errs = []
    if cfg.get("labels") != PRIMARY_LABELS:
        errs.append(f"labels must be exactly {PRIMARY_LABELS}")
    if not isinstance(cfg.get("seed"), int):
        errs.append("seed must be an integer")
    seeds = cfg.get("seeds", [cfg.get("seed")])
    if not seeds or not all(isinstance(s, int) for s in seeds) or len(set(seeds)) != len(seeds):
        errs.append("seeds must be a non-empty list of distinct integers")
    sp = cfg.get("split", {})
    if sp.get("strategy") not in {"grouped_by_document", "grouped_by_source"}:
        errs.append("split.strategy must be grouped_by_document or grouped_by_source")
    try:
        if abs(sp["train"] + sp["validation"] + sp["test"] - 1) > 1e-6 or min(sp["train"], sp["validation"], sp["test"]) <= 0:
            errs.append("split ratios must be positive and sum to 1")
    except KeyError:
        errs.append("split needs train, validation, test")
    m = cfg.get("models", {})
    if not set(m.get("baselines", [])) <= KNOWN_BASELINES:
        errs.append(f"unknown baselines; allowed {sorted(KNOWN_BASELINES)}")
    unk = set(cfg.get("hyperparameters", {})) - HP_KEYS
    if unk:
        errs.append(f"unknown hyperparameters {sorted(unk)}")
    if errs:
        raise ValueError("invalid config: " + "; ".join(errs))
    cfg.setdefault("seeds", [cfg["seed"]])
    cfg.setdefault("hyperparameters", {})
    cfg.setdefault("analysis", {"bootstrap_resamples": 1000, "top_k_examples": 5})
    return cfg


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def code_sha256(root=ROOT):
    h = hashlib.sha256()
    for p in sorted((Path(root) / "ML").glob("*.py")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


def experiment_id(cfg, dataset_sha, code_sha, mode):
    return hashlib.sha256(canonical({"cfg": cfg, "data": dataset_sha, "code": code_sha, "mode": mode}).encode()).hexdigest()[:12]


def _hash_tree(d, skip=("run_manifest.json",)):
    out = {}
    for p in sorted(Path(d).rglob("*")):
        if p.is_file() and p.name not in skip:
            out[str(p.relative_to(d)).replace("\\", "/")] = file_sha256(p)
    return out


def _versions():
    v = {"python": platform.python_version(), "platform": platform.platform()}
    for m in ("numpy", "pandas", "sklearn", "torch", "transformers", "matplotlib"):
        try:
            v[m] = __import__(m).__version__
        except Exception:
            v[m] = None
    return v


def _figures(exp, analyses, nonresearch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figs = exp / "figures"; figs.mkdir(exist_ok=True)
    mark = "NOT RESEARCH (fixture/smoke)" if nonresearch else ""
    made = []
    for name, res in analyses.items():
        for model, r in res["models"].items():
            tag = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{name}__{model}__{res['split_analysed']}")
            fig, ax = plt.subplots(figsize=(4.2, 3.8))
            cm = [[v if v is not None else 0 for v in row] for row in r["confusion"]["row_normalised"]]
            ax.imshow(cm, vmin=0, vmax=1, cmap="Blues")
            ax.set_xticks(range(3), [l[:4] for l in r["confusion"]["labels"]]); ax.set_yticks(range(3), [l[:4] for l in r["confusion"]["labels"]])
            for i in range(3):
                for j in range(3):
                    ax.text(j, i, str(r["confusion"]["counts"][i][j]), ha="center", va="center", fontsize=9)
            ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(f"{model} ({res['split_analysed']}) n={r['n']}\n{mark}", fontsize=8)
            fig.tight_layout(); p = figs / f"confusion_{tag}.png"; fig.savefig(p, dpi=110); plt.close(fig); made.append(p)
            fig, ax = plt.subplots(figsize=(4.2, 3.0))
            ax.bar(range(3), [v["f1"] for v in r["per_class"].values()]); ax.set_ylim(0, 1)
            ax.set_xticks(range(3), [l[:4] for l in r["per_class"]]); ax.set_ylabel("F1")
            ax.set_title(f"per-class F1: {model} ({res['split_analysed']})\n{mark}", fontsize=8)
            fig.tight_layout(); p = figs / f"perclass_f1_{tag}.png"; fig.savefig(p, dpi=110); plt.close(fig); made.append(p)
            c = r["confidence"]
            if c["available"]:
                fig, ax = plt.subplots(figsize=(4.2, 3.0)); e = c["bin_edges"]; w = e[1] - e[0]
                ax.bar([x + w / 2 for x in e[:-1]], c["hist_correct"], width=w * .9, alpha=.7, label="correct")
                ax.bar([x + w / 2 for x in e[:-1]], c["hist_incorrect"], width=w * .9, alpha=.7, label="incorrect")
                ax.set_xlabel("max softmax probability"); ax.legend(); ax.set_title(f"confidence: {model}\n{mark}", fontsize=8)
                fig.tight_layout(); p = figs / f"confidence_{tag}.png"; fig.savefig(p, dpi=110); plt.close(fig); made.append(p)
    for log in sorted(exp.glob("distilbert/seed*/training_log.jsonl")):
        rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        if rows:
            fig, ax = plt.subplots(figsize=(4.2, 3.0))
            ax.plot([r["epoch"] for r in rows], [r["val_macro_f1"] for r in rows], marker="o"); ax.set_ylim(0, 1)
            ax.set_xlabel("epoch"); ax.set_ylabel("validation macro-F1"); ax.set_title(f"{log.parent.name}\n{mark}", fontsize=8)
            fig.tight_layout(); p = exp / "figures" / f"training_curve_{log.parent.name}.png"; fig.savefig(p, dpi=110); plt.close(fig); made.append(p)
    return made


def run_experiment(config_path, csv_path, out_root="ARTIFACTS/experiments", smoke=False, allow_fixture=False,
                   offline=False, force=False, dry_run=False):
    cfg = load_config(config_path)
    raw = pd.read_csv(csv_path)
    rep = check(raw, "research")
    research_ok = rep.ok
    if not research_ok and not (allow_fixture or smoke):
        raise RuntimeError("Dataset is not research-valid and no --allow-fixture/--smoke was given: "
                           f"{rep.errors}. Nothing was run.")
    data_status = "research" if research_ok else "fixture_not_research"
    dsha, csha = file_sha256(csv_path), code_sha256()
    mode = {"smoke": bool(smoke), "data_status": data_status}
    xid = experiment_id(cfg, dsha, csha, mode)
    exp = Path(out_root) / xid
    steps_plan = ["validate", "split", "baselines"] + (["distilbert"] if (research_ok or smoke) and cfg["models"].get("transformer") else []) \
        + (["ablation"] if cfg["models"].get("fusion") and (research_ok or smoke) else []) + ["error_analysis", "figures"]
    if dry_run:
        return {"experiment_id": xid, "would_run": steps_plan, "data_status": data_status, "out": str(exp)}
    man_path = exp / "run_manifest.json"
    if man_path.exists() and not force:
        checked = verify_experiment(exp)
        if not checked["ok"]:
            raise ValueError(f"existing experiment artifacts changed: {checked}; refusing reuse")
        m = json.loads(man_path.read_text(encoding="utf-8")); m["reused"] = True
        return m
    if man_path.exists() and force:
        raise FileExistsError("refusing to overwrite a recorded experiment; choose a new --out directory")
    exp.mkdir(parents=True, exist_ok=True)
    (exp / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    hp, seeds = cfg["hyperparameters"], cfg["seeds"]
    group = "document_id" if cfg["split"]["strategy"] == "grouped_by_document" else "source_id"
    steps, analyses = {}, {}
    manifest = exp / "split_manifest.json"

    def step(name, fn):
        t0 = time.time()
        try:
            fn()
            steps[name] = {"status": "ok", "seconds": round(time.time() - t0, 2)}
        except RuntimeError as e:
            unavailable = "pretrained weights" in str(e)
            steps[name] = {"status": "unavailable" if unavailable else "failed", "reason": str(e)[:400],
                           "seconds": round(time.time() - t0, 2)}
        except Exception as e:
            steps[name] = {"status": "failed", "reason": f"{type(e).__name__}: {str(e)[:400]}", "seconds": round(time.time() - t0, 2)}

    steps["validate"] = {"status": "ok", "research_valid": research_ok, "errors": rep.errors, "warnings": rep.warnings}
    from ML.group_split import freeze
    sp = cfg["split"]
    step("split", lambda: freeze(csv_path, manifest, group, cfg["seed"], sp["train"], sp["validation"], force=force))
    if steps["split"]["status"] == "ok":
        from ML.baselines import run as run_baselines
        step("baselines", lambda: run_baselines(csv_path, exp / "baselines", manifest, cfg["seed"], allow_fixture=not research_ok))
        if "distilbert" in steps_plan:
            from ML.distilbert_trainer import run as run_tr
            def tr():
                for s in seeds:
                    run_tr(csv_path, exp / "distilbert" / f"seed{s}", manifest, s, smoke, offline,
                           model_name=cfg["models"]["transformer"], arch="hf_head", **hp)
            step("distilbert", tr)
        if "ablation" in steps_plan:
            from ML.ablation import run_ablation
            step("ablation", lambda: run_ablation(csv_path, exp / "ablation", manifest, seeds, smoke, offline,
                                                  model_name=cfg["models"]["transformer"], **hp))
        if steps["baselines"]["status"] == "ok" or any(steps.get(k, {}).get("status") == "ok" for k in ("distilbert", "ablation")):
            from ML.error_analysis import write_error_analysis
            def ea():
                cands = {"baselines": exp / "baselines" / "predictions.csv"}
                for s in seeds[:1]:
                    cands[f"distilbert_seed{s}"] = exp / "distilbert" / f"seed{s}" / "predictions.csv"
                    for arm in ("fusion_off", "fusion_on"):
                        cands[f"{arm}_seed{s}"] = exp / "ablation" / f"{arm}_seed{s}" / "predictions.csv"
                for name, p in cands.items():
                    if p.exists():
                        for sp_name in ("validation", "test"):
                            analyses[name + ":" + sp_name] = write_error_analysis(
                                p, exp / "error_analysis" / name, csv_path, sp_name,
                                cfg["analysis"]["bootstrap_resamples"], cfg["seed"], cfg["analysis"]["top_k_examples"])
            step("error_analysis", ea)
            step("figures", lambda: _figures(exp, analyses, nonresearch=not research_ok or smoke))

    def res_of(p):
        return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None
    required = ["split", "baselines"] + [s for s in ("distilbert", "ablation") if s in steps_plan]
    all_ok = all(steps.get(s, {}).get("status") == "ok" for s in required)
    tr_valid = True
    if "distilbert" in steps_plan:
        tr_valid = all((res_of(exp / "distilbert" / f"seed{s}" / "results.json") or {}).get("valid_for_scientific_claims") for s in seeds)
    ab = res_of(exp / "ablation" / "ablation.json")
    ab_valid = (ab or {}).get("valid_for_scientific_claims", False) if "ablation" in steps_plan else True
    valid = bool(research_ok and not smoke and all_ok and tr_valid and ab_valid)
    if "distilbert" not in steps_plan and cfg["models"].get("transformer"):
        valid = False   # transformer required by config but could not run on this data/mode
    failed = [k for k, v in steps.items() if v["status"] == "failed"]
    unavailable = [k for k, v in steps.items() if v["status"] == "unavailable"]
    status = "failed" if failed else ("partial" if unavailable or not all_ok else "complete")
    m = {"experiment_id": xid, "created_at": datetime.now(timezone.utc).isoformat(), "status": status,
         "data_status": data_status, "smoke": bool(smoke), "valid_for_scientific_claims": valid,
         "steps": steps, "failed_steps": failed, "unavailable_steps": unavailable,
         "config_sha256": hashlib.sha256(canonical(cfg).encode()).hexdigest(),
         "dataset": {"file": Path(csv_path).name, "sha256": dsha, "rows": int(len(raw)),
                     "documents": int(raw["document_id"].nunique()) if "document_id" in raw else None},
         "code_sha256": csha, "seeds": seeds, "versions": _versions(), "command": " ".join(sys.argv),
         "reproduce": f"python -m ML.experiment_runner --config {config_path} --csv {csv_path}"
                      + (" --smoke" if smoke else "") + (" --allow-fixture" if allow_fixture else ""),
         "notes": ["valid_for_scientific_claims requires research-valid human data, a frozen split, and every required "
                   "step (including real pretrained weights) to have completed."]}
    m["artifacts"] = _hash_tree(exp)
    man_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
    return m


def verify_experiment(exp_dir):
    """Recompute artifact hashes and compare with run_manifest.json."""
    exp = Path(exp_dir)
    m = json.loads((exp / "run_manifest.json").read_text(encoding="utf-8"))
    now = _hash_tree(exp)
    return {"ok": now == m["artifacts"],
            "missing": sorted(set(m["artifacts"]) - set(now)),
            "added": sorted(set(now) - set(m["artifacts"])),
            "changed": sorted(k for k in set(now) & set(m["artifacts"]) if now[k] != m["artifacts"][k])}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="EXPERIMENTS/config.yaml")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="ARTIFACTS/experiments")
    ap.add_argument("--smoke", action="store_true", help="tiny local transformer; outputs are non-research")
    ap.add_argument("--allow-fixture", action="store_true", help="permit non-research data (pipeline test only)")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--plan", action="store_true", help="print the plan and exit")
    a = ap.parse_args()
    r = run_experiment(a.config, a.csv, a.out, a.smoke, a.allow_fixture, a.offline, a.force, a.plan)
    print(json.dumps({k: r.get(k) for k in ("experiment_id", "status", "data_status", "valid_for_scientific_claims",
                                           "failed_steps", "unavailable_steps", "would_run", "reused")}, indent=2))
