"""Read-only views over REAL artifacts for the Research Lab. Nothing here is generated or estimated:
if a file does not exist the corresponding section is simply absent and flagged as such."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "ARTIFACTS"
ALLOWED_ROOTS = [ART, ROOT / "DATA", ROOT / "REPORTS"]
MAX_BYTES = 2_000_000


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def _kind(res):
    if "models" in res and "tfidf_logreg" in res.get("models", {}):
        return "baselines"
    if res.get("arch", "").startswith("fusion"):
        return "fusion"
    if "weights" in res:
        return "distilbert"
    return "unknown"


def _run_view(results_path):
    d = results_path.parent
    res, meta = _json(results_path), (_json(d / "metadata.json") if (d / "metadata.json").exists() else {})
    kind = _kind(res)
    sha = str(meta.get("dataset_sha256", ""))
    is_research = res.get("data_status") == "research" and (
        res.get("valid_for_scientific_claims", True) if kind != "baselines" else True)
    view = {"path": str(d.relative_to(ROOT)), "kind": kind, "data_status": res.get("data_status"),
            "is_research_result": bool(is_research), "arch": res.get("arch"), "weights": res.get("weights"),
            "pretrained_weights_used": res.get("pretrained_weights_used"),
            "valid_for_scientific_claims": res.get("valid_for_scientific_claims"),
            "experiment_id": f"{d.name}@{sha[:8]}" if sha else d.name,
            "seed": meta.get("seed"), "created_at": meta.get("created_at"), "dataset_sha256": sha or None,
            "versions": meta.get("versions"), "split_sizes": res.get("split_sizes"),
            "train_label_counts": res.get("train_label_counts"), "warnings": res.get("warnings", [])}
    if kind == "baselines":
        view["models"] = {k: {"validation": v["validation"], "test": v["test"], "selected_C": v.get("selected_C")}
                          for k, v in res["models"].items()}
    else:
        view["validation"], view["test"] = res.get("validation"), res.get("test")
        view["best_epoch"] = res.get("best_epoch")
        log = d / "training_log.jsonl"
        if log.exists():
            view["training_log"] = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    return view


def _experiments():
    out = []
    for p in sorted(ART.glob("experiments/*/run_manifest.json")) if ART.exists() else []:
        m = _json(p)
        out.append({"path": str(p.parent.relative_to(ROOT)), "experiment_id": m.get("experiment_id"),
                    "status": m.get("status"), "data_status": m.get("data_status"), "smoke": m.get("smoke"),
                    "valid_for_scientific_claims": bool(m.get("valid_for_scientific_claims")),
                    "steps": {k: v.get("status") for k, v in (m.get("steps") or {}).items()},
                    "failed_steps": m.get("failed_steps"), "unavailable_steps": m.get("unavailable_steps"),
                    "dataset": m.get("dataset"), "seeds": m.get("seeds"), "versions": m.get("versions"),
                    "created_at": m.get("created_at"), "reproduce": m.get("reproduce"),
                    "code_sha256": m.get("code_sha256"), "config_sha256": m.get("config_sha256")})
    return out


def _error_analyses():
    out = []
    for p in sorted(ART.rglob("error_analysis_*.json")) if ART.exists() else []:
        a = _json(p)
        out.append({"path": str(p.relative_to(ROOT)), "split_analysed": a.get("split_analysed"),
                    "data_status": a.get("data_status"), "valid_for_scientific_claims": bool(a.get("valid_for_scientific_claims")),
                    "caveat": a.get("caveat"), "models": a.get("models", {})})
    return out


def research_summary(model_status):
    runs = [_run_view(p) for p in sorted(p for p in ART.rglob("results.json") if "prototype" not in p.relative_to(ART).parts)] if ART.exists() else []
    ablations = []
    for p in sorted(ART.rglob("ablation.json")) if ART.exists() else []:
        a = _json(p)
        ablations.append({"path": str(p.relative_to(ROOT)), **{k: a.get(k) for k in (
            "data_status", "valid_for_scientific_claims", "seeds", "n_test", "summary",
            "paired_test_macro_f1_diff_on_minus_off", "interpretation")}})
    agreement = [{"path": str(p.relative_to(ROOT)), **_json(p)} for p in sorted(ART.rglob("agreement.json"))] \
        if ART.exists() else []
    split = ROOT / "DATA" / "split_manifest.json"
    ds = None
    if split.exists():
        m = _json(split)
        ds = {"path": "DATA/split_manifest.json", "dataset_file": m.get("dataset_file"),
              "dataset_sha256": m.get("dataset_sha256"), "seed": m.get("seed"), "group": m.get("group"),
              "n_groups": {k: len(v["groups"]) for k, v in m.get("splits", {}).items()},
              "leakage": m.get("leakage")}
    return {"model_status": model_status, "dataset_split": ds, "agreement": agreement,
            "runs": [r for r in runs if r["is_research_result"]],
            "non_research_runs": [r for r in runs if not r["is_research_result"]],
            "ablations": ablations,
            "experiments": [e for e in _experiments() if e["valid_for_scientific_claims"]],
            "non_research_experiments": [e for e in _experiments() if not e["valid_for_scientific_claims"]],
            "error_analyses": [e for e in _error_analyses() if e["valid_for_scientific_claims"]],
            "non_research_error_analyses": [e for e in _error_analyses() if not e["valid_for_scientific_claims"]],
            "traces": {"present": (ART / "traces" / "traces.jsonl").exists()},
            "notes": ["Sections are empty when no real artifact exists; nothing is estimated or filled in.",
                      "non_research_runs are smoke/fixture outputs and must not be cited as results."]}


def read_artifact(rel):
    p = (ROOT / rel).resolve()
    if not any(p.is_relative_to(r.resolve()) for r in ALLOWED_ROOTS):
        raise PermissionError("path outside allowed artifact folders")
    if not p.is_file():
        raise FileNotFoundError(rel)
    if p.stat().st_size > MAX_BYTES:
        raise PermissionError("file too large to display")
    if p.suffix not in {".json", ".jsonl", ".md", ".csv", ".txt"}:
        raise PermissionError("file type not displayable")
    return {"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "content": p.read_text(encoding="utf-8")}


def list_traces(limit=100):
    p = ART / "traces" / "traces.jsonl"
    if not p.exists():
        return {"present": False, "records": [], "note": "trace logging is off (set DYSLEXIADAPT_LOG=1) or empty"}
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    return {"present": True, "records": [json.loads(l) for l in lines if l.strip()]}
