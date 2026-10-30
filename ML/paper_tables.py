"""Generate classification paper tables from one verified experiment (Task 16).

Default: refuse partial, smoke, unvalidated or tampered experiments. A fixture
override is for tests only and puts NOT RESEARCH in every table row and heading.
Nothing is estimated, and no paper result exists until real runs are supplied.
"""
import argparse
import csv
import json
import math
from pathlib import Path

from ML.data_validation import PRIMARY_LABELS, file_sha256
from ML.experiment_runner import verify_experiment


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"invalid {name}: finite value in [0, 1] required")
    return value


def _row(model, seed, metric, research):
    if not isinstance(metric.get("n"), int) or metric["n"] < 1:
        raise ValueError("nonempty test metrics required")
    per = metric["per_class"]
    matrix = metric["confusion_matrix"]
    if matrix["labels"] != PRIMARY_LABELS or len(matrix["matrix"]) != 3 or any(len(row) != 3 for row in matrix["matrix"]):
        raise ValueError("confusion matrix must match primary labels")
    counts = [v for row in matrix["matrix"] for v in row]
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in counts) or sum(counts) != metric["n"]:
        raise ValueError("invalid confusion counts or test sample count")
    cm = matrix["matrix"]
    accuracy = sum(cm[i][i] for i in range(3)) / metric["n"]
    if abs(accuracy - _number(metric["accuracy"], "accuracy")) > 1e-6:
        raise ValueError("accuracy disagrees with confusion matrix")
    # Recompute all displayed metrics from counts; no text labels can supply values.
    precision, recall, f1, support = [], [], [], []
    for i in range(3):
        tp, actual, predicted = cm[i][i], sum(cm[i]), sum(row[i] for row in cm)
        precision.append(tp / predicted if predicted else 0.)
        recall.append(tp / actual if actual else 0.)
        f1.append(2 * tp / (actual + predicted) if actual + predicted else 0.)
        support.append(actual)
    expected = {"macro_precision": sum(precision) / 3, "macro_recall": sum(recall) / 3,
                "macro_f1": sum(f1) / 3, "weighted_f1": sum(f * n for f, n in zip(f1, support)) / metric["n"]}
    provided = {"macro_precision": per["macro avg"]["precision"], "macro_recall": per["macro avg"]["recall"],
                "macro_f1": metric["macro_f1"], "weighted_f1": per["weighted avg"]["f1-score"]}
    for name, value in provided.items():
        if abs(_number(value, name) - expected[name]) > 1e-6:
            raise ValueError(f"{name} disagrees with confusion matrix")
    return {"model": model, "seed": seed, "split": "test", "n": metric["n"],
            "accuracy": accuracy, **expected,
            "evidence_status": "research_artifact" if research else "NOT RESEARCH (fixture)"}


def export_tables(experiment_dir, out_dir, allow_fixture=False):
    exp, out = Path(experiment_dir).resolve(), Path(out_dir).resolve()
    m = json.loads((exp / "run_manifest.json").read_text(encoding="utf-8"))
    checked = verify_experiment(exp)
    if not checked["ok"]:
        raise ValueError(f"experiment integrity failed: {checked}")
    research = m.get("status") == "complete" and m.get("data_status") == "research" and \
        m.get("valid_for_scientific_claims") is True and not m.get("smoke")
    if not research and not allow_fixture:
        raise ValueError("verified complete research experiment required; fixture output is not research")
    if m.get("status") != "complete":
        raise ValueError("partial/failed experiments cannot generate a complete comparison table")
    rows = []
    sources = {}
    for relative in sorted(m["artifacts"]):
        if not relative.endswith("results.json"):
            continue
        p = (exp / relative).resolve()
        if not p.is_relative_to(exp):
            raise ValueError("artifact path escapes experiment")
        r = json.loads(p.read_text(encoding="utf-8"))
        if research and (r.get("data_status") != "research" or r.get("smoke") or
                         r.get("valid_for_scientific_claims") is False):
            raise ValueError("non-research run in research comparison")
        meta_path = p.parent / "metadata.json"
        rel_meta = str(meta_path.relative_to(exp)).replace("\\", "/")
        if rel_meta not in m["artifacts"]:
            raise ValueError("run metadata is not included in verified manifest")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("dataset_sha256") != m["dataset"]["sha256"]:
            raise ValueError("run dataset differs from experiment dataset")
        seed = meta.get("seed")
        if "models" in r:
            for model, values in r["models"].items():
                rows.append(_row(model, seed, values["test"], research))
        elif "test" in r:
            if research and r.get("pretrained_weights_used") is not True:
                raise ValueError("transformer result does not confirm pretrained weights")
            rows.append(_row(r.get("arch", "distilbert"), seed, r["test"], research))
        sources[relative] = file_sha256(p)
    if not rows:
        raise ValueError("no classification results found")
    if len({(r["model"], r["seed"]) for r in rows}) != len(rows):
        raise ValueError("duplicate model/seed result")
    if len({r["n"] for r in rows}) != 1:
        raise ValueError("model test sample counts differ")
    if out.is_relative_to(exp):
        raise ValueError("write paper tables outside the frozen experiment directory")
    if out.exists():
        raise FileExistsError("paper output exists; choose a new versioned directory")
    out.mkdir(parents=True)
    with (out / "classification.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    mark = "Classification results" if research else "NOT RESEARCH: fixture classification table"
    lines = [f"# {mark}", "", "One row per model/seed; held-out test split only.", "",
             "| Model | Seed | n | Accuracy | Macro precision | Macro recall | Macro F1 | Weighted F1 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['model']} | {r['seed']} | {r['n']} | " + " | ".join(
            f"{r[k]:.4f}" for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1")) + " |")
    lines += ["", "No significance, comprehension, adaptation-quality or dyslexia-specific effectiveness claim is generated.",
              "Artifact checks establish consistency and provenance; they cannot prove that annotators were human.",
              "A final paper needs dataset/annotation review, ablations, limitations and human outcomes where claimed."]
    (out / "classification.md").write_text("\n".join(lines), encoding="utf-8")
    provenance = {"experiment_id": m["experiment_id"], "data_status": m["data_status"],
                  "evidence_status": "research_artifact" if research else "NOT RESEARCH (fixture)",
                  "run_manifest_sha256": file_sha256(exp / "run_manifest.json"),
                  "dataset_sha256": m["dataset"]["sha256"], "artifact_hashes_verified": True,
                  "source_results": sources, "rounding": "CSV retains full precision; Markdown displays 4 decimals"}
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return provenance


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-fixture", action="store_true", help="test-only export, prominently marked NOT RESEARCH")
    args = ap.parse_args()
    print(json.dumps(export_tables(args.experiment, args.out, args.allow_fixture), indent=2))
