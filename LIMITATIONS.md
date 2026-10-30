# Current real-model build

RUN_NEURAL.md supersedes the historical prototype status below. Real MiniLM, Qwen and NLI weights were downloaded and exercised. The small GPT-labelled test remains a technical pilot, not evidence of dyslexia benefit. Automatic semantic verification can still fail.

# Current adaptive continuation

`RUN_ADAPTIVE.md` supersedes the historical status below where applicable. A local TF-IDF classifier trained on GPT-weak labels is bundled; feedback preferences persist opt-in; contextual support and evaluated prototype retraining are implemented. No dyslexia-benefit claim is validated. Generative model weights are not bundled. The older research pipeline and its data gates remain unchanged.

## Historical baseline audit (before adaptive continuation)

# Limitations (read before citing or demoing anything)

Status labels: **IMPLEMENTED** (code + tests), **DEMO** (placeholder/rule of thumb), **SMOKE-TESTED** (runs on synthetic or tiny data), **VALIDATED** (research-grade evidence). Nothing in this project is VALIDATED.

## Scientific validity
- No human-annotated dataset exists (HG-01). No classifier has been trained on real labels; every score ever produced here came from synthetic fixtures or a tiny random-initialised model and means nothing.
- DistilBERT has never been trained with pretrained weights in this project (weights were not downloadable in the build environment). The code path for real weights is untested on real weights.
- The research gate (`valid_for_scientific_claims`, `data_status: research`) is structural: it checks provenance columns, annotator ids and a frozen split. It cannot prove annotators were human or labels correct.
- The label scheme (Vocabulary / Syntactic / Conceptual) is an operational scheme; whether annotators can apply it reliably is unknown until agreement is measured.
- Protocol items not implemented: the "no context" ablation, the intervention-metrics suite (intervention rate, readability delta, changed-token counts across conditions) and human appropriateness ratings (Task 15, blocked on ethics approval); paper tables (Task 16, blocked on real results).
- Feature fusion helps or not is unknown; only a matched control and a descriptive ablation runner exist.

## Interventions and verification
- Interventions are deterministic rules, not a trained or generative model. The vocabulary lexicon (39 entries) was written by the assistant and has not been reviewed by a linguist or educator.
- Sentence splitting is regex-based and can mis-handle abbreviations; only a handful of rewrite patterns exist. Conceptual support is a scaffold of questions; it does not explain ideas.
- Whether any intervention helps readers has not been tested with readers.
- Semantic checks are heuristic. "pass" means no automatic flag, never "meaning preserved". Thresholds are uncalibrated. The embedding/NLI scorers have not run on real weights. Rules are deliberately conservative (some valid rewrites are rejected).

## Product and interface
- The category suggestion in the app is a rule of thumb (no probability, no confidence), announced as practice mode.
- The learner interface was tested with jsdom only: not in real browsers, on phones, with screen readers, or with readers who have dyslexia. No claim is made that any colour, font, spacing or focus mode helps.
- No learner authentication, rate limiting or hosting hardening; do not expose publicly.
- The QA audit (`QA/audit.py`) is automated checking, not a penetration test or accessibility conformance audit.

## Data and licensing
- Source licence decision ADR-009 is PENDING; no dataset or passage pool is bundled and nothing may be redistributed. Hub licence tags are uploader-declared. The CC BY-SA version is unconfirmed. This repository does not give legal advice.
- Simple Wikipedia is already simplified, so hard spans may be scarce.

## Environment
- Developed and tested on Linux (CPU). Windows and Colab instructions exist but were not run. Package versions are recorded in `requirements-lock.txt` for information only.

## Ethics
- No diagnosis, medical inference or clinical claim is made or supported. Any participant study needs institutional approval and consent first (HG-02).
