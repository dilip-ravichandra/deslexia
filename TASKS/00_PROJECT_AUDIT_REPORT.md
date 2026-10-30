# Project Audit Report

## Objective
Audit the repository, environment, current implementation and research constraints to produce a reliable architecture map and an implementation gap list while preserving working code.

## Scope reviewed
- Repository root and project state files
- Startup and run instructions (`START_HERE.md`, `RUN_WINDOWS.md`, `RUN_RESEARCH.md`)
- Core backend and launcher (`BACKEND/app.py`, `launch_interface.py`)
- Research and task tracking (`TASKS/`, `RESEARCH/`, `PROJECT_STATE.json`)
- Data/model pipeline and project documentation (`DATA/`, `ML/`, `EXPERIMENTS/`, `MODEL_CARD.md`, `DATASET_CARD.md`)
- Current status and QA evidence (`CURRENT_RESEARCH_STATUS.md`, `REPORTS/`, `TESTS/`, `QA/`)

## Architecture map

### 1. Product entry points
- `START_WINDOWS.bat` and `START_DYSLEXIADAPT.bat` launch the Windows local stack.
- `launch_interface.py` opens the browser only after the app health check succeeds.
- `BACKEND/app.py` is the FastAPI app and is the main API surface.

### 2. Learner-facing layer
- `FRONTEND/` contains the learner workspace and browser UI.
- The app is designed around localized selection of a difficult span, context collection, support routing, and support acceptance/rejection.
- Presentation preferences (theme, contrast, size, line spacing, focus mode) are treated as a separate layer from linguistic support classification.

### 3. Backend services and logic
- `BACKEND/app.py` validates request schemas, enforces local-only research access, and supports learner/account flows.
- `BACKEND/pipeline.py` provides the pipeline logic for classification and support generation.
- `BACKEND/adaptive.py` manages learner evidence and adaptive behavior.
- `BACKEND/learner.py` stores learner profile and survey-related state.
- `BACKEND/accounts.py` is responsible for local account/session handling.

### 4. Research, data and experiments
- `DATA/` stores source, annotation, and licensing-related material.
- `ML/` contains the modeling and research tooling, including training, validation, evaluation, and paper-table routines.
- `EXPERIMENTS/` contains experiment configs and reproducible run artifacts.
- `RESEARCH/` holds the protocol and evaluation workflow.
- `ARTIFACTS/` and `REPORTS/` contain generated evidence, logs and audit outputs.

### 5. Quality and validation
- `TESTS/` contains the automated test suite.
- `QA/` holds auditing and compliance-oriented checks.
- `PROJECT_STATE.json`, `CURRENT_RESEARCH_STATUS.md`, and `DECISIONS.md` act as the project truth source for current status, decisions, and blocked items.

## Current implementation status
The repository is not a blank prototype. It contains a substantial implementation of:
- multilingual reader flows and learner workspace UX
- local account/profile setup and consented session uses
- learner evidence/adaptive routing logic
- public lexical analysis experiments
- model training pipeline scaffolding and experiment runner
- research-lab views and artifact handling
- QA and audit tooling

The repo clearly distinguishes between:
- working software infrastructure,
- research pipeline scaffolding,
- and genuinely completed research results.

## Implementation gaps and blockers
The codebase documents the following major gaps instead of hiding them:

1. Missing real gold dataset
- No completed human-annotated support-category dataset is bundled.
- The repo explicitly requires human annotation before any research claim.

2. Missing verified model training run
- A real pretrained DistilBERT run is not present.
- The pipeline supports synthetic/smoke checks, but those do not count as research-valid results.

3. Human evaluation and ethics dependencies
- `HG-02` requires institutional approval and consent before participant evaluation.
- The project status lists the human study tasks as blocked pending ethics and appropriate participant collection.

4. Licensing uncertainty for source corpus
- `ADR-009` remains pending because the owner has not confirmed the ShareAlike consequence.
- This blocks formal data release and research dataset packaging decisions.

5. No completed study outcomes
- The project has no finished four-condition learning study with actual participant outcomes.
- There is no independent, frozen held-out routing benchmark with verified results.

6. No paper-ready experimental tables
- `TASKS/16_PAPER.md` remains blocked until valid experiments and outputs exist.

## High-confidence conclusions
- This repository is a substantial technical prototype with a sensible architecture and explicit research boundaries.
- The current implementation is appropriate for local engineering work and future research, but it does not yet contain validated scientific results.
- The project is correctly structured around human annotation, ethics approvals, and license confirmation before claims of effectiveness or dataset readiness.

## Files changed
- `TASKS/00_PROJECT_AUDIT_REPORT.md`
- `PROJECT_STATE.json`

## Tests run
- No automated tests were run for this documentation-only audit task.

## Results
- Audit completed and the repository status was reconciled against the project truth files.
- Architecture map and implementation gap list were captured in this report.
- Research blockers and scientific boundaries remain visible and explicit.

## Limitations
- This is a repo-level audit, not a full scientific validation.
- The project contains significant engineering work, but not yet finished human-data or model-validation evidence.

## Next task
The next task is not a blind implementation pass; it is the next unblocked, evidence-producing step in the research pipeline. The currently listed blocked items (`15` and `16`) remain blocked by human ethics, licensing, and the absence of real experiment artifacts. The repo is therefore ready for the next admissible research step only once those prerequisites are satisfied.
