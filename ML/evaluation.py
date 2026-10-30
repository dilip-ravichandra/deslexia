"""Offline adaptation comparison (Task 15 tooling; no participant collection).

One record per educational passage with four condition outputs. Missing model
scores remain null. Text change counts are descriptive alignment measures, not
proof of accessibility, faithfulness, or comprehension. Defaults to unvalidated
output; --allow-fixture is explicitly stamped NOT RESEARCH.
"""
import argparse
import json
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from ML.context import split_sentences
from ML.data_validation import file_sha256
from ML.semantic_verifier import verify

CONDITIONS = ("original", "uniform_simplification", "generic_accessibility", "targeted")
TOKEN_PATTERN = re.compile(r"\w+(?:['’\-]\w+)*|[^\w\s]", re.UNICODE)


def change_metrics(original, adapted):
    """Case/punctuation-sensitive tokens; whitespace/layout changes are separate.

    SequenceMatcher alignment with autojunk disabled; substitutions count source
    tokens and inserted tokens separately. This is not minimum edit distance.
    """
    a, b = TOKEN_PATTERN.findall(original), TOKEN_PATTERN.findall(adapted)
    replaced = deleted = added = 0
    for tag, i, j, k, l in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "replace":
            replaced += j - i
            added += l - k
        elif tag == "delete":
            deleted += j - i
        elif tag == "insert":
            added += l - k
    sa, sb = split_sentences(original), split_sentences(adapted)
    changed_sentences = sum(j - i for tag, i, j, _, _ in
                            SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes()
                            if tag != "equal")
    changed = replaced + deleted
    return {"original_tokens": len(a), "adapted_tokens": len(b),
            "changed_original_tokens": changed, "deleted_tokens": deleted,
            "replaced_original_tokens": replaced, "added_tokens": added,
            "modified_original_token_ratio": changed / len(a) if a else None,
            "unchanged_original_token_ratio": (len(a) - changed) / len(a) if a else None,
            "total_edit_budget": changed + added,
            "original_sentences": len(sa), "changed_original_sentences": changed_sentences,
            "modified_original_sentence_ratio": changed_sentences / len(sa) if sa else None,
            "text_changed": original != adapted,
            "layout_only_change": original != adapted and a == b}


def _mean(values):
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def evaluate(records, allow_fixture=False, embedder=None, nli=None, readability=None):
    """Records contain sample_id, document_id, original, and all three outputs.

    Optional readability callback returns a finite numeric score for each text.
    It is recorded as a score difference; its direction is never assumed.
    """
    if not records:
        raise ValueError("comparison records are empty")
    seen, rows = set(), []
    for rec in records:
        for field in ("sample_id", "document_id", *CONDITIONS):
            if not isinstance(rec.get(field), str) or not rec[field].strip():
                raise ValueError(f"nonblank {field} required for every record")
        if rec["sample_id"] in seen:
            raise ValueError("duplicate sample_id")
        seen.add(rec["sample_id"])
        original = rec["original"]
        # The C3 control changes presentation, not educational text.
        if rec["generic_accessibility"] != original:
            raise ValueError("generic_accessibility must preserve original text exactly")
        by_condition = {}
        for condition in CONDITIONS:
            adapted = rec[condition]
            checks = verify(original, adapted, embedder, nli)
            readability_delta = None
            if readability is not None:
                before, after = float(readability(original)), float(readability(adapted))
                if not math.isfinite(before) or not math.isfinite(after):
                    raise ValueError("readability scorer returned a nonfinite value")
                readability_delta = after - before
            by_condition[condition] = {
                "changes": change_metrics(original, adapted),
                "verification": checks, "readability_score_delta": readability_delta}
        rows.append({"sample_id": rec["sample_id"], "document_id": rec["document_id"],
                     "conditions": by_condition})
    summary = {}
    for condition in CONDITIONS:
        values = [r["conditions"][condition] for r in rows]
        changes = [v["changes"] for v in values]
        source_tokens = sum(c["original_tokens"] for c in changes)
        summary[condition] = {
            "n_passages": len(values),
            "n_text_changed": sum(c["text_changed"] for c in changes),
            "passage_intervention_rate": sum(c["text_changed"] for c in changes) / len(values),
            "modified_original_token_ratio_macro": _mean([c["modified_original_token_ratio"] for c in changes]),
            "modified_original_token_ratio_micro": sum(c["changed_original_tokens"] for c in changes) / source_tokens if source_tokens else None,
            "mean_total_edit_budget": _mean([c["total_edit_budget"] for c in changes]),
            "mean_readability_score_delta": _mean([v["readability_score_delta"] for v in values]),
            "verification_status_counts": dict(Counter(v["verification"]["status"] for v in values)),
            "n_embedding_scored": sum(v["verification"]["embedding_cosine"] is not None for v in values),
            "n_nli_scored": sum(v["verification"]["nli"] is not None for v in values)}
    paired = []
    for r in rows:
        t = r["conditions"]["targeted"]["changes"]
        u = r["conditions"]["uniform_simplification"]["changes"]
        paired.append({"sample_id": r["sample_id"], "document_id": r["document_id"],
                       "edit_budget_targeted_minus_uniform": t["total_edit_budget"] - u["total_edit_budget"],
                       "modified_token_ratio_targeted_minus_uniform":
                       t["modified_original_token_ratio"] - u["modified_original_token_ratio"]
                       if t["modified_original_token_ratio"] is not None else None})
    return {"schema_version": "1.0", "data_status": "fixture_not_research" if allow_fixture else "unvalidated_outputs",
            "valid_for_scientific_claims": False,
            "n_documents": len({r["document_id"] for r in rows}),
            "summary": summary, "paired_comparisons": paired, "passages": rows,
            "notes": ["DESCRIPTIVE ONLY: no comprehension or clinical effectiveness finding is produced.",
                      "Alignment counts use case/punctuation-sensitive SequenceMatcher, not minimum edit distance.",
                      "Inserted tokens contribute to edit budget even if no source tokens were changed.",
                      "Append explanations to the targeted output when evaluating additions; do not omit them.",
                      "Full-passage similarity can conceal a local error; inspect changed spans as well.",
                      "Automatic verification pass is not proof of preserved meaning; thresholds are uncalibrated.",
                      "SARI requires task-matched human reference simplifications and is not computed here.",
                      "Missing embedding/NLI/readability scores are unavailable, never zero-filled.",
                      "Human outcomes require approval, consent, matched passages and a predeclared analysis plan."]}


def write_evaluation(input_path, out_dir, allow_fixture=False):
    p, out = Path(input_path), Path(out_dir)
    records = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = evaluate(records, allow_fixture=allow_fixture)
    result["source"] = {"file": p.name, "sha256": file_sha256(p)}
    if out.exists():
        raise FileExistsError("evaluation output already exists; choose a new versioned directory")
    out.mkdir(parents=True)
    (out / "evaluation.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Adaptation comparison", "", "> NOT RESEARCH: descriptive, unvalidated output.", "",
             "| Condition | Passages | Text changed | Source token change ratio (micro) | Mean edit budget |",
             "|---|---:|---:|---:|---:|"]
    for c, v in result["summary"].items():
        ratio = v["modified_original_token_ratio_micro"]
        lines.append(f"| {c} | {v['n_passages']} | {v['n_text_changed']} | {ratio:.4f} | {v['mean_total_edit_budget']:.2f} |")
    lines += ["", *[f"- {n}" for n in result["notes"]]]
    (out / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comparisons", required=True, help="JSONL: one matched passage per line")
    ap.add_argument("--out", required=True, help="new versioned output directory")
    ap.add_argument("--allow-fixture", action="store_true")
    args = ap.parse_args()
    r = write_evaluation(args.comparisons, args.out, args.allow_fixture)
    print(json.dumps({"data_status": r["data_status"], "valid_for_scientific_claims": False,
                      "n_documents": r["n_documents"]}, indent=2))
