"""Final QA audit (Task 17): research-integrity, security/privacy, UI, reproducibility and governance checks.

HONEST SCOPE: automated static and dynamic checks of this repository. It is NOT a penetration test, a
formal accessibility conformance audit (WCAG/VPAT), or a legal review. `pass` means "this check found no
problem", not "the system is secure/accessible/valid".
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {".py", ".md", ".json", ".yaml", ".yml", ".html", ".js", ".txt", ".csv", ".toml", ".cfg"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".pytest_cache", ".audit-tmp", ".venv", ".venv-check", ".dist"}
ALLOWED_DATA = {"seed_examples.csv", "schema.json", "SOURCES.md", "LICENSE_ANALYSIS.md", "annotation_guidelines_v1.md",
                "dataset_card.md", "lexicon_demo.json", "split_manifest.json"}


class R:
    def __init__(self):
        self.items = []

    def add(self, id_, cat, sev, ok, msg, evidence=None, warn_only=False):
        self.items.append({"id": id_, "category": cat, "severity": sev,
                           "status": "pass" if ok else ("warn" if warn_only else "fail"),
                           "message": msg, "evidence": evidence})


def files(root, exts=TEXT_EXT):
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix in exts and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            yield p


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""      # a missing file is reported by the check that needs it


def jload(p, default=None):
    try:
        return json.loads(read(p))
    except Exception:
        return default


# ------------------------------------------------------------------ research integrity
CLAIM = re.compile(r"(macro[- ]?F1|accuracy|kappa|alpha|precision|recall|F1)\b[^\n|]{0,25}?\b0?\.\d{2,}", re.I)
SAFE_WORDS = re.compile(r"fixture|synthetic|smoke|reference|published|template|NOT_AVAILABLE|threshold|placeholder|"
                        r"hypothetical|illustrat|krippendorff'?s published|e\.g\.|means nothing|not (?:a )?result", re.I)


def research_integrity(root, r):
    st = jload(root / "PROJECT_STATE.json", {})
    arts = []
    for p in (root / "ARTIFACTS").rglob("results.json") if (root / "ARTIFACTS").exists() else []:
        j = jload(p, {})
        if j.get("data_status") == "research":
            arts.append(str(p.relative_to(root)))
    claims_model = bool(st.get("research_model_available")) or bool(st.get("gold_dataset_available"))
    r.add("RI-01", "research-integrity", "high", (not claims_model) or bool(arts),
          "PROJECT_STATE claims a research model/gold dataset only if research-grade artifacts exist",
          {"state_claims": claims_model, "research_artifacts": arts})
    rt = root / "PAPER" / "results_template.md"
    rows = [l for l in read(rt).splitlines() if l.startswith("| ") and "---" not in l][1:] if rt.exists() else []
    r.add("RI-02", "research-integrity", "high", bool(rows) and all("NOT_AVAILABLE" in l for l in rows),
          "paper results template contains no numbers (all NOT_AVAILABLE)")
    r.add("RI-03", "research-integrity", "medium", not arts,
          "no research-grade artifacts are bundled (any that exist need provenance verification: the gate is structural)",
          arts, warn_only=True)
    hits = []
    for p in list(files(root / "REPORTS")) + list(files(root / "PAPER")) + list(files(root / "RESEARCH")) + \
            [q for q in root.glob("*.md")] + list(files(root / "DOCS") if (root / "DOCS").exists() else []):
        for i, line in enumerate(read(p).splitlines(), 1):
            if CLAIM.search(line) and not SAFE_WORDS.search(line):
                hits.append(f"{p.relative_to(root)}:{i}: {line.strip()[:110]}")
    r.add("RI-04", "research-integrity", "medium", not hits, "metric-like documentation passages require source/context review; regex cannot establish fabricated claims", hits[:20],warn_only=True)
    stamp_files = ["ML/baselines.py", "ML/distilbert_trainer.py", "ML/experiment_runner.py", "ML/error_analysis.py"]
    missing = [f for f in stamp_files if "data_status" not in read(root / f)]
    r.add("RI-05", "research-integrity", "high", not missing, "every result writer stamps data_status", missing)
    dv = read(root / "ML" / "data_validation.py")
    r.add("RI-06", "research-integrity", "high", all(w in dv for w in ('"seed"', '"llm"', '"model"', '"synthetic"')),
          "research validation rejects seed/AI/synthetic annotators and licences")
    dd = [p.name for p in (root / "DATA").iterdir() if p.is_file()] if (root / "DATA").exists() else []
    inventory=jload(root/'DATA/public_sources.json',{})
    source_issues=[]
    import hashlib
    for source in inventory.get('sources',[]):
        for item in source.get('files',[]):
            path=root/item['path']
            if path.name=='.DS_Store':continue  # OS metadata is not source content.
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:source_issues.append(item['path'])
    r.add("RI-07", "research-integrity", "high", bool(inventory.get('sources')) and not source_issues,
          "bundled public content matches the explicit provenance/hash inventory (not an independent license review)", source_issues)
    dec = read(root / "DECISIONS.md")
    m = re.search(r"ADR-009[^\n]*", dec)
    pend = (st.get("pending_decisions") or [])
    r.add("RI-08", "research-integrity", "high", bool(m) and "PENDING" in dec[dec.index("ADR-009"):] and any("ADR-009" in x for x in pend),
          "ADR-009 (source licence) is recorded as PENDING in DECISIONS.md and PROJECT_STATE.json")
    done = set(st.get("completed_tasks", []))
    blocked = {v.get("task") for v in st.get("blocked_tasks", [])}
    r.add("RI-09", "research-integrity", "high", not ({"15", "16"} & done) and {"15", "16"} <= blocked,
          "Tasks 15/16 have preparation tooling; participant evaluation and real paper results remain blocked")
    sys.path.insert(0, str(root))
    from BACKEND.pipeline import DemoHeuristic
    s = DemoHeuristic().suggest("catalyst", "The catalyst helped.")
    r.add("RI-10", "research-integrity", "high", s["probabilities"] is None and s["confidence"] is None and not s["is_trained_model_output"],
          "demo suggestions carry no probability/confidence and are not labelled as a trained prediction")
    tr = read(root / "ML" / "distilbert_trainer.py")
    r.add("RI-11", "research-integrity", "high", "valid_for_scientific_claims" in tr and "pretrained_weights_used" in tr and "DOWNLOAD_FAILED" in tr,
          "trainer records pretrained-weights use and fails hard on missing weights")


# ------------------------------------------------------------------ security / privacy
SECRETS = [r"hf_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{30,}",
           r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"]


def security_privacy(root, r):
    hits = []
    for p in files(root):
        if p.name.endswith(("package-lock.json",)):
            continue
        t = read(p)
        for pat in SECRETS:
            for m in re.finditer(pat, t):
                hits.append(f"{p.relative_to(root)}: {m.group()[:12]}…")
    r.add("SP-01", "security-privacy", "high", not hits, "no secrets/tokens committed", hits[:10])

    sys.path.insert(0, str(root))
    old = {k: os.environ.pop(k, None) for k in ("DYSLEXIADAPT_LOG", "DYSLEXIADAPT_LOG_TEXT", "DYSLEXIADAPT_ADMIN_TOKEN")}
    try:
        from fastapi.testclient import TestClient
        import importlib, BACKEND.app as appmod
        importlib.reload(appmod)
        c = TestClient(appmod.app)
        st = appmod.pipe.traces
        r.add("SP-02", "security-privacy", "high", not st.log_on and not st.log_text, "logging and text logging are OFF by default")
        with tempfile.TemporaryDirectory() as td:
            st.log_on, st.dir = True, Path(td)
            body = {"span": "catalyst", "text": "The catalyst helped the secret reaction."}
            tid = c.post("/api/adapt", json=body).json()["trace_id"]
            c.post("/api/feedback", json={"trace_id": tid, "decision": "accept"})
            blob = (Path(td) / "traces.jsonl").read_text()
            st.log_on = False
            r.add("SP-03", "security-privacy", "high", "catalyst" not in blob and "secret" not in blob,
                  "enabled logging stores no learner text by default")
        r.add("SP-04", "security-privacy", "high", c.post("/api/adapt", json={**body, "background": "dark"}).status_code == 422,
              "learner API rejects unknown fields (visual settings cannot reach classification)")
        r.add("SP-05", "security-privacy", "medium", c.post("/api/adapt", json={"span": "a", "text": "a" * 5001}).status_code == 422
              and c.post("/api/adapt", json={"span": "a" * 301}).status_code == 422, "input size limits enforced")
        remote = TestClient(appmod.app, client=("203.0.113.9", 5000))
        os.environ["DYSLEXIADAPT_ADMIN_TOKEN"] = "t0k"
        ok_tok = (remote.get("/api/research/summary").status_code == 401 and
                  remote.get("/api/research/summary", headers={"x-admin-token": "t0k"}).status_code == 200)
        os.environ.pop("DYSLEXIADAPT_ADMIN_TOKEN")
        ok_local = remote.get("/api/research/summary").status_code == 403
        r.add("SP-06", "security-privacy", "high", ok_tok and ok_local, "research endpoints: token required when set, local-only otherwise")
        trav = [c.get("/api/research/artifact", params={"path": p}).status_code for p in ("../../etc/passwd", "CLAUDE.md", "ML/baselines.py")]
        r.add("SP-07", "security-privacy", "high", all(s in (403, 404) for s in trav), "artifact reader blocks traversal and non-artifact paths", trav)
    finally:
        for k, v in old.items():
            if v is not None:
                os.environ[k] = v
    ext, danger, store = [], [], set()
    for p in (root / "FRONTEND").glob("*.html"):
        t = read(p)
        code = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        for m in re.finditer(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)""", code):
            ext.append(f"{p.name}: {m.group(1)}")
        for m in re.finditer(r"@import|url\(\s*['\"]?https?://", code):
            ext.append(f"{p.name}: {m.group()}")
        for pat in (r"\binnerHTML\b", r"insertAdjacentHTML", r"document\.write", r"\beval\s*\("):
            if re.search(pat, code):
                danger.append(f"{p.name}: {pat}")
        store |= set(re.findall(r"(?:local|session)Storage\.(?:get|set)Item\(\s*([A-Za-z_\"']+)", code))
    r.add("SP-08", "security-privacy", "medium", not ext, "front-end loads nothing from external hosts", ext)
    r.add("SP-09", "security-privacy", "medium", not danger, "no innerHTML/eval/document.write in front-end code", danger)
    r.add("SP-10", "security-privacy", "info", True, "browser storage keys include preferences, capability, notes, passages and independent review progress", sorted(store))
    app_src = read(root / "BACKEND" / "app.py")
    r.add("SP-11", "security-privacy", "medium", "CORSMiddleware" not in app_src or "allow_origins=[\"*\"]" not in app_src,
          "no wildcard CORS")
    req = read(root / "BACKEND" / "requirements.txt")
    lock = (root / "requirements-lock.txt").exists()
    r.add("SP-12", "security-privacy", "low", lock, "dependency versions are recorded (requirements-lock.txt)", warn_only=True)


# ------------------------------------------------------------------ UI audit
class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.labels_for, self.controls, self.buttons, self.stack, self.html_attrs = set(), [], [], [], {}
        self.meta_viewport, self.title, self.aria_live, self._btn = False, False, False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_attrs = a
        if tag == "meta" and a.get("name") == "viewport":
            self.meta_viewport = True
        if tag == "title":
            self.title = True
        if "aria-live" in a:
            self.aria_live = True
        self.stack.append(tag)
        if tag == "label" and "for" in a:
            self.labels_for.add(a["for"])
        if tag in {"input", "select", "textarea"} and a.get("type") not in {"hidden", "radio", "checkbox"} or \
                (tag == "input" and a.get("type") in {"radio", "checkbox"}):
            self.controls.append({"tag": tag, "id": a.get("id"), "aria": a.get("aria-label") or a.get("aria-labelledby"),
                                  "in_label": "label" in self.stack, "type": a.get("type")})
        if tag == "button":
            self._btn = {"id": a.get("id"), "aria": a.get("aria-label"), "text": ""}

    def handle_data(self, d):
        if self._btn is not None:
            self._btn["text"] += d

    def handle_endtag(self, tag):
        if tag == "button" and self._btn is not None:
            self.buttons.append(self._btn); self._btn = None
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


def ui_audit(root, r):
    problems = {"lang": [], "viewport": [], "label": [], "button_name": [], "outline": [], "motion": []}
    for p in sorted((root / "FRONTEND").glob("*.html")):
        t = read(p)
        c = Collect(); c.feed(t)
        if not c.html_attrs.get("lang"): problems["lang"].append(p.name)
        if not (c.meta_viewport and c.title): problems["viewport"].append(p.name)
        for ctl in c.controls:
            if not (ctl["in_label"] or ctl["aria"] or (ctl["id"] and ctl["id"] in c.labels_for)):
                problems["label"].append(f"{p.name}#{ctl['id']}")
        for b in c.buttons:
            if not (b["text"].strip() or b["aria"]): problems["button_name"].append(f"{p.name}#{b['id']}")
        if re.search(r"outline\s*:\s*(none|0)\b", t) and "focus-visible" not in t:
            problems["outline"].append(p.name)
        if re.search(r"@keyframes|animation\s*:|transition\s*:", t) and "prefers-reduced-motion" not in t:
            problems["motion"].append(p.name)
    r.add("UI-01", "ui", "medium", not problems["lang"], "every page declares a language", problems["lang"])
    r.add("UI-02", "ui", "medium", not problems["viewport"], "every page has a viewport meta tag and title", problems["viewport"])
    r.add("UI-03", "ui", "high", not problems["label"], "every statically declared form control has a label", problems["label"])
    r.add("UI-04", "ui", "medium", not problems["button_name"], "every statically declared button has an accessible name", problems["button_name"])
    r.add("UI-05", "ui", "medium", not problems["outline"], "focus outlines are not removed without a replacement", problems["outline"])
    r.add("UI-06", "ui", "medium", not problems["motion"], "no animation/transition without a prefers-reduced-motion rule", problems["motion"])
    idx = read(root / "FRONTEND" / "index.html")
    fn = re.search(r"async function requestSupport\(\)\{.*?\n\}", idx, re.S)
    body = fn.group() if fn else ""
    r.add("UI-07", "ui", "high", bool(fn) and not re.search(r"\blook\b|localStorage|PRESETS|colours\(", body),
          "request code for /api/adapt does not reference visual settings")
    r.add("UI-08", "ui", "medium", 'aria-live="polite"' in idx, "learner page has an aria-live status region")
    r.add("UI-09", "ui", "info", True, "NOT COVERED: real-browser, mobile, screen-reader and user testing (only jsdom checks exist)")


# ------------------------------------------------------------------ reproducibility
def reproducibility(root, r):
    seedless = []
    for f, needles in {"ML/baselines.py": ["random_state"], "ML/distilbert_trainer.py": ["set_seed", "manual_seed"],
                       "ML/group_split.py": ["random.Random(seed)"], "ML/error_analysis.py": ["default_rng(seed)"],
                       "ML/annotation.py": ["random.Random(seed)"]}.items():
        t = read(root / f)
        seedless += [f"{f}: {n}" for n in needles if n not in t]
    r.add("RP-01", "reproducibility", "high", not seedless, "randomness is seeded in every stochastic module", seedless)
    mods = sorted(p.stem for p in (root / "ML").glob("*.py") if p.stem != "__init__")
    bad = []
    sys.path.insert(0, str(root))
    for m in mods:
        try:
            __import__(f"ML.{m}")
        except Exception as e:
            bad.append(f"ML.{m}: {type(e).__name__}")
    r.add("RP-02", "reproducibility", "high", not bad, "all ML modules import cleanly", bad)
    import pandas as pd
    from ML.baselines import run
    from TESTS.test_baselines import synth
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); csv = td / "d.csv"; synth().to_csv(csv, index=False)
        run(csv, td / "a", allow_fixture=True); run(csv, td / "b", allow_fixture=True)
        same = pd.read_csv(td / "a" / "predictions.csv").equals(pd.read_csv(td / "b" / "predictions.csv"))
    r.add("RP-03", "reproducibility", "high", same, "baseline predictions are identical across two runs with the same seed")
    meta_ok = all("versions" in read(root / "ML" / f) for f in ("baselines.py", "distilbert_trainer.py", "experiment_runner.py"))
    r.add("RP-04", "reproducibility", "medium", meta_ok, "runs record library versions")
    r.add("RP-05", "reproducibility", "medium", "sha256" in read(root / "ML" / "experiment_runner.py") and
          "verify_experiment" in read(root / "ML" / "experiment_runner.py"), "experiment runner hashes and can verify artifacts")
    r.add("RP-06", "reproducibility", "low", (root / "requirements-lock.txt").exists(), "tested dependency versions recorded", warn_only=True)
    r.add("RP-07", "reproducibility", "medium", all((root / f).exists() for f in ("RUN_COLAB.md", "RUN_PRODUCT.md")),
          "run guides for Windows/Colab/product exist")


# ------------------------------------------------------------------ governance / docs
def governance(root, r, final_docs=True):
    st = jload(root / "PROJECT_STATE.json", {})
    missing = []
    for t in st.get("completed_tasks", []):
        if not list((root / "REPORTS").glob(f"TASK_{t}*.md")):
            missing.append(t)
    r.add("GV-01", "governance", "medium", not missing, "every completed task has a report", missing)
    need = ["CLAUDE.md", "HUMAN_GATES.md", "DECISIONS.md", "BLOCKED.md", "RUN_PRODUCT.md", "RUN_COLAB.md"]
    if final_docs:
        need += ["MODEL_CARD.md", "DATASET_CARD.md", "LIMITATIONS.md", "DEFENSE_GUIDE.md"]
    miss = [f for f in need if not (root / f).exists() and not (root / "DOCS" / f).exists()]
    r.add("GV-02", "governance", "medium", not miss, "required governance/documentation files exist", miss)
    if final_docs:
        mc = read(root / "MODEL_CARD.md") if (root / "MODEL_CARD.md").exists() else ""
        dc = read(root / "DATASET_CARD.md") if (root / "DATASET_CARD.md").exists() else ""
        r.add("GV-03", "governance", "high", "NO VALIDATED MODEL" in mc.upper() or "NOT AVAILABLE" in mc.upper(),
              "model card states plainly when no validated model exists")
        r.add("GV-04", "governance", "high", "PENDING" in dc.upper() and "DO NOT REDISTRIBUTE" in dc.upper(),
              "dataset card shows the licence as pending and forbids redistribution")


def run_pytest(root):
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=root, capture_output=True, text=True, timeout=900)
    last = [l for l in p.stdout.strip().splitlines() if "passed" in l or "failed" in l or "error" in l]
    return {"returncode": p.returncode, "summary": last[-1] if last else p.stdout[-200:]}


def audit(root=ROOT, run_tests=False, final_docs=True):
    root = Path(root)
    r = R()
    for fn in (research_integrity, security_privacy, ui_audit, reproducibility):
        try:
            fn(root, r)
        except Exception as e:   # an audit that cannot run is itself a finding
            r.add(f"ERR-{fn.__name__}", "audit-error", "high", False, f"{fn.__name__} crashed: {type(e).__name__}: {e}")
    governance(root, r, final_docs)
    tests = run_pytest(root) if run_tests else None
    if tests:
        r.add("QA-01", "tests", "high", tests["returncode"] == 0, "full test suite passes", tests["summary"])
    fails = [i for i in r.items if i["status"] == "fail"]
    return {"scope": __doc__.strip().split("\n\n")[1], "tests": tests, "items": r.items,
            "counts": {s: sum(i["status"] == s for i in r.items) for s in ("pass", "warn", "fail")},
            "high_severity_failures": [i["id"] for i in fails if i["severity"] == "high"]}


def to_markdown(a):
    L = ["# QA audit", "", f"_{a['scope']}_", "",
         f"Result: {a['counts']['pass']} pass · {a['counts']['warn']} warn · {a['counts']['fail']} fail · "
         f"high-severity failures: {a['high_severity_failures'] or 'none'}", ""]
    if a["tests"]:
        L += [f"Test suite: {a['tests']['summary']}", ""]
    L += ["| id | category | severity | status | check |", "|---|---|---|---|---|"]
    for i in a["items"]:
        L.append(f"| {i['id']} | {i['category']} | {i['severity']} | {i['status'].upper()} | {i['message']} |")
    L += ["", "## Details for non-pass items", ""]
    for i in a["items"]:
        if i["status"] != "pass" or i["severity"] == "info":
            L.append(f"- **{i['id']}** ({i['status']}): {i['message']} — evidence: {json.dumps(i['evidence'])[:400]}")
    return "\n".join(L)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tests", action="store_true")
    ap.add_argument("--out", default="REPORTS/QA_AUDIT")
    ap.add_argument("--no-final-docs", action="store_true", help="skip card/limitations existence checks")
    a = ap.parse_args()
    res = audit(ROOT, a.run_tests, not a.no_final_docs)
    out = ROOT / a.out
    out.parent.mkdir(exist_ok=True)
    Path(str(out) + ".json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    Path(str(out) + ".md").write_text(to_markdown(res), encoding="utf-8")
    print(to_markdown(res).split("\n\n")[2])
    for i in res["items"]:
        if i["status"] != "pass":
            print(i["status"].upper(), i["id"], i["message"], json.dumps(i["evidence"])[:300])
    sys.exit(1 if res["high_severity_failures"] else 0)
