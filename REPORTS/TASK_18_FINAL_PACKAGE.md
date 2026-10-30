# Task Report — 18 Final Package
## Files
ML/cards.py, MODEL_CARD.md, DATASET_CARD.md (generated), LIMITATIONS.md, DEFENSE_GUIDE.md, README.md, DATA/dataset_card.md (pointer), tests in TESTS/test_cards_and_qa.py.
## Design
Cards are generated from artifacts: metrics appear only from research-grade runs; smoke/fixture runs are counted, never quoted; with no research run the model card says "NO VALIDATED MODEL" and the dataset card says "NO GOLD DATASET EXISTS". The dataset card's release status follows ADR-009 in DECISIONS.md: while PENDING it states DO NOT REDISTRIBUTE. A test asserts the committed cards equal the generator output; the QA audit checks the statements exist.
LIMITATIONS.md and DEFENSE_GUIDE.md separate IMPLEMENTED / DEMO / SMOKE-TESTED / VALIDATED and list what must not be claimed.
## Limitations
The cards describe the project state at generation time: regenerate with `python -m ML.cards` after any new artifact. The defense guide is an aid, not a substitute for results.
