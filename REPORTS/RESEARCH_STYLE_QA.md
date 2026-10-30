# QA audit

_HONEST SCOPE: automated static and dynamic checks of this repository. It is NOT a penetration test, a
formal accessibility conformance audit (WCAG/VPAT), or a legal review. `pass` means "this check found no
problem", not "the system is secure/accessible/valid"._

Result: 43 pass · 0 warn · 0 fail · high-severity failures: none

| id | category | severity | status | check |
|---|---|---|---|---|
| RI-01 | research-integrity | high | PASS | PROJECT_STATE claims a research model/gold dataset only if research-grade artifacts exist |
| RI-02 | research-integrity | high | PASS | paper results template contains no numbers (all NOT_AVAILABLE) |
| RI-03 | research-integrity | medium | PASS | no research-grade artifacts are bundled (any that exist need provenance verification: the gate is structural) |
| RI-04 | research-integrity | high | PASS | no unqualified metric claims in documentation |
| RI-05 | research-integrity | high | PASS | every result writer stamps data_status |
| RI-06 | research-integrity | high | PASS | research validation rejects seed/AI/synthetic annotators and licences |
| RI-07 | research-integrity | high | PASS | no source corpus or unreviewed data files are bundled (licence decision pending) |
| RI-08 | research-integrity | high | PASS | ADR-009 (source licence) is recorded as PENDING in DECISIONS.md and PROJECT_STATE.json |
| RI-09 | research-integrity | high | PASS | Tasks 15/16 have preparation tooling; participant evaluation and real paper results remain blocked |
| RI-10 | research-integrity | high | PASS | demo suggestions carry no probability/confidence and are not labelled as a trained prediction |
| RI-11 | research-integrity | high | PASS | trainer records pretrained-weights use and fails hard on missing weights |
| SP-01 | security-privacy | high | PASS | no secrets/tokens committed |
| SP-02 | security-privacy | high | PASS | logging and text logging are OFF by default |
| SP-03 | security-privacy | high | PASS | enabled logging stores no learner text by default |
| SP-04 | security-privacy | high | PASS | learner API rejects unknown fields (visual settings cannot reach classification) |
| SP-05 | security-privacy | medium | PASS | input size limits enforced |
| SP-06 | security-privacy | high | PASS | research endpoints: token required when set, local-only otherwise |
| SP-07 | security-privacy | high | PASS | artifact reader blocks traversal and non-artifact paths |
| SP-08 | security-privacy | medium | PASS | front-end loads nothing from external hosts |
| SP-09 | security-privacy | medium | PASS | no innerHTML/eval/document.write in front-end code |
| SP-10 | security-privacy | info | PASS | browser storage keys in use (visual preferences and admin token only) |
| SP-11 | security-privacy | medium | PASS | no wildcard CORS |
| SP-12 | security-privacy | low | PASS | dependency versions are recorded (requirements-lock.txt) |
| UI-01 | ui | medium | PASS | every page declares a language |
| UI-02 | ui | medium | PASS | every page has a viewport meta tag and title |
| UI-03 | ui | high | PASS | every statically declared form control has a label |
| UI-04 | ui | medium | PASS | every statically declared button has an accessible name |
| UI-05 | ui | medium | PASS | focus outlines are not removed without a replacement |
| UI-06 | ui | medium | PASS | no animation/transition without a prefers-reduced-motion rule |
| UI-07 | ui | high | PASS | request code for /api/adapt does not reference visual settings |
| UI-08 | ui | medium | PASS | learner page has an aria-live status region |
| UI-09 | ui | info | PASS | NOT COVERED: real-browser, mobile, screen-reader and user testing (only jsdom checks exist) |
| RP-01 | reproducibility | high | PASS | randomness is seeded in every stochastic module |
| RP-02 | reproducibility | high | PASS | all ML modules import cleanly |
| RP-03 | reproducibility | high | PASS | baseline predictions are identical across two runs with the same seed |
| RP-04 | reproducibility | medium | PASS | runs record library versions |
| RP-05 | reproducibility | medium | PASS | experiment runner hashes and can verify artifacts |
| RP-06 | reproducibility | low | PASS | tested dependency versions recorded |
| RP-07 | reproducibility | medium | PASS | run guides for Windows/Colab/product exist |
| GV-01 | governance | medium | PASS | every completed task has a report |
| GV-02 | governance | medium | PASS | required governance/documentation files exist |
| GV-03 | governance | high | PASS | model card states plainly when no validated model exists |
| GV-04 | governance | high | PASS | dataset card shows the licence as pending and forbids redistribution |

## Details for non-pass items

- **SP-10** (pass): browser storage keys in use (visual preferences and admin token only) — evidence: ["\"da_admin\"", "\"da_lab_theme_v", "'da_width_v", "LOOK_KEY", "key"]
- **UI-09** (pass): NOT COVERED: real-browser, mobile, screen-reader and user testing (only jsdom checks exist) — evidence: null