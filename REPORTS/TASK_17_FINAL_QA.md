# Task Report — 17 Final QA
## Files
QA/audit.py, TESTS/test_cards_and_qa.py, requirements-lock.txt, REPORTS/QA_AUDIT.md/.json (generated).
## What was audited (automated)
Research integrity (state vs artifacts, no numbers in the paper template, no unqualified metric claims in docs, data_status stamping, gold-label guards, licence-pending/no bundled corpus, blocked tasks 15/16, demo labelling); security/privacy (secret scan, logging defaults, no learner text in logs, extra-field rejection, input limits, admin gating, path traversal, external resources, unsafe DOM APIs, storage keys, CORS); UI (language, viewport, labels, button names, focus outlines, motion, no visual settings in the API request code, live region); reproducibility (seeding, imports, same-seed determinism, version recording, hashing, run guides); governance (reports for completed tasks, required docs, cards).
## Defects found and fixed during the audit
1. `FRONTEND/adjudication.html` built markup with `innerHTML` and an escape that missed quotes, so a hostile CSV cell could inject markup: rewritten with DOM APIs; a jsdom test now feeds hostile CSV content.
2. Same page: the file input had no label: fixed.
3. Dependency versions were not recorded: `requirements-lock.txt` added (informational).
4. The audit's own claim detector had an over-broad allow-list ("test" let "…on the test set" through): tightened and unit-tested.
Earlier tasks also fixed: inference max-length bug (Task 11 tests), failing grouped split (Task 04).
## Not covered
Penetration testing, dependency vulnerability scanning, real-browser/mobile/screen-reader accessibility, user testing, load testing, legal review of licences. The audit cannot prove annotators were human.
## Result
See REPORTS/QA_AUDIT.md for the latest run (written by `python -m QA.audit --run-tests`).
