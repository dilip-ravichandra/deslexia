# Task Report — 10 Semantic Verification
## Files
ML/semantic_verifier.py (rewritten; `basic_verify` kept), TESTS/test_verifier.py (9 tests).
## Layers
Hard (fail): numbers changed, negation count changed, named entities/acronyms dropped, NLI contradiction (if scorer available). Soft (review): entities added, modality/quantifier words changed, low content-word retention, large length change, low embedding cosine / low entailment (if available). Character-overlap ratio is reported as `lexical_char_ratio` and is not presented as semantic similarity.
`EmbeddingScorer` (MiniLM) and `NLIScorer` (DeBERTa-small cross-encoder) load lazily and fail soft: unavailable checks are listed in `checks_unavailable` with the reason and are never replaced by the lexical ratio.
## Honest limits
- `pass` means no automatic flag, not preserved meaning; every result has `meaning_preservation_guaranteed=false`.
- Thresholds are engineering defaults, `thresholds_validated=false`; they need calibration against human judgements of meaning preservation.
- The two model-based scorers were tested only with fakes and with the graceful-failure path; they have not run on real weights.
- Conservative by design: legitimate rewrites that change negation words or drop names are rejected.
