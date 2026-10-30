"""Feature-fusion ablation (Task 07): matched transformer-only control vs transformer + features.

Both arms share split, seed list, hyperparameters, head and pooling; only the feature branch differs.
Results are descriptive. No significance claim is made here; with few seeds or a small test set
differences are not evidence.
"""
import json
from pathlib import Path

import numpy as np

from ML.distilbert_trainer import run

MIN_SEEDS_FOR_CLAIM = 5


def run_ablation(csv_path, out_dir, manifest_path=None, seeds=(42, 43, 44, 45, 46), smoke=False,
                 offline=False, **hp):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = {"fusion_off": [], "fusion_on": []}
    claims = []
    for s in seeds:
        for arch in rows:
            r = run(csv_path, out / f"{arch}_seed{s}", manifest_path, s, smoke, offline, arch=arch, **hp)
            rows[arch].append({"seed": s, "val_macro_f1": r["validation"]["macro_f1"],
                               "test_macro_f1": r["test"]["macro_f1"], "test_accuracy": r["test"]["accuracy"],
                               "best_epoch": r["best_epoch"]})
            claims.append(r["valid_for_scientific_claims"])
            n_test, data_status = r["split_sizes"]["test"], r["data_status"]

    def agg(arch, key):
        v = np.array([x[key] for x in rows[arch]])
        return {"mean": float(v.mean()), "std": float(v.std(ddof=1)) if len(v) > 1 else None}

    summary = {a: {k: agg(a, k) for k in ("val_macro_f1", "test_macro_f1", "test_accuracy")} for a in rows}
    paired = [on["test_macro_f1"] - off["test_macro_f1"] for on, off in zip(rows["fusion_on"], rows["fusion_off"])]
    res = {"data_status": data_status, "seeds": list(seeds), "n_test": n_test,
           "per_seed": rows, "summary": summary,
           "paired_test_macro_f1_diff_on_minus_off": {"values": paired, "mean": float(np.mean(paired))},
           "valid_for_scientific_claims": bool(all(claims)),
           "interpretation": ("DESCRIPTIVE ONLY. " + (
               f"Fewer than {MIN_SEEDS_FOR_CLAIM} seeds: " if len(seeds) < MIN_SEEDS_FOR_CLAIM else "")
               + "no significance testing is performed; small test sets make differences unreliable.")}
    (out / "ablation.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--out", default="ARTIFACTS/ablation")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--epochs", type=int, default=4)
    a = ap.parse_args()
    r = run_ablation(a.csv, a.out, a.manifest, a.seeds, a.smoke, a.offline, epochs=a.epochs)
    print(json.dumps({k: r[k] for k in ["data_status", "valid_for_scientific_claims", "interpretation"]}, indent=2))
