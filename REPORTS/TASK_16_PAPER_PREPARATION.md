# Task 16 preparation

Objective: generate paper classification tables from actual verified artifacts.

Files: `ML/paper_tables.py`, continuation tests and run guide.
Default exporter refuses partial/unvalidated/smoke/fixture experiments, verifies
all artifact hashes, checks dataset consistency, recomputes displayed metrics
from confusion counts and exports held-out test values with provenance.
It refuses overwriting or writing inside frozen experiments. Explicit fixture
exports are marked NOT RESEARCH in headings and every CSV row.

Tests: fixture rejection, stamped test exports, integrity/tamper handling,
no overwrite and metric/count consistency. Final verification: QA audit.

Limit: no real research tables or findings generated. Complete task 16 only
after gold-data/pretrained runs and requested paper evidence are available.
Next: real experiments followed by the guarded exporter and paper writing.
