"""CLI for baselines. Research runs need --manifest from ML/group_split.py and research-valid data."""
import argparse
import json
from ML.baselines import run

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--out", default="ARTIFACTS/baselines")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--allow-fixture", action="store_true",
                    help="pipeline test on non-research data; output is stamped fixture_not_research")
    a = ap.parse_args()
    r = run(a.csv, a.out, a.manifest, a.seed, a.allow_fixture)
    print(json.dumps({"data_status": r["data_status"], "split_sizes": r["split_sizes"],
                      "models": {k: {"test_macro_f1": v["test"]["macro_f1"]} for k, v in r["models"].items()}}, indent=2))
