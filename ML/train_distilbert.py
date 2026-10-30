"""CLI. Research run (needs real gold CSV, frozen manifest, and downloadable weights):
    python -m ML.train_distilbert --csv DATA/gold.csv --manifest DATA/split_manifest.json
Pipeline smoke test (no downloads, no claims):
    python -m ML.train_distilbert --csv some.csv --smoke
Windows/Colab: same commands; add --offline only if weights are already cached."""
import argparse
import json
from ML.distilbert_trainer import run

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--out", default="ARTIFACTS/distilbert")
    ap.add_argument("--model", default="distilbert/distilbert-base-multilingual-cased", help="hub id or local folder")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    r = run(a.csv, a.out, a.manifest, a.seed, a.smoke, a.offline, model_name=a.model,
            epochs=a.epochs, lr=a.lr, batch_size=a.batch_size)
    print(json.dumps({k: r[k] for k in ["data_status", "weights", "valid_for_scientific_claims",
                                        "best_epoch", "split_sizes"]}, indent=2))
