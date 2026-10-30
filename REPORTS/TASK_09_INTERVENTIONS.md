# Task Report — 09 Targeted Interventions
## Objective
Support-specific interventions with change tracking.
## Files
ML/interventions.py (rewritten; `route` kept for compatibility), DATA/lexicon_demo.json (new, 39 entries), TESTS/test_interventions.py (13 tests).
## What it does (method `rule_based_v1`, deterministic)
- VOCABULARY: gloss (keeps the word, adds a plain-language meaning) or in-place replacement for explicit inflected forms; each entry glossed once.
- SYNTACTIC: conservative sentence splitting (concessive, semicolon, comma+and/but/so, trailing "which" clause; lists are not split) or layout-only chunking.
- CONCEPTUAL: numbered steps when sequence cues exist; otherwise a reading scaffold (questions, key terms taken from the text). No explanation is invented.
- Every result records operations (rule, from, to), word diff, status (applied / no_change / layout_only / scaffold_only), variants for "try another way", and flags `is_heuristic=true`, `is_trained_model_output=false`.
- Unsupported cases say `no_change` and why. A generator plugin hook exists (tagged `plugin:<name>`) for a future LLM; its output must pass verification.
## Limitations
- The lexicon was written by the assistant, is small, and is unreviewed by a linguist or educator. Not suitable for a study as is.
- Sentence splitting is regex-based (abbreviations such as "e.g." can confuse it); rewrite rules cover only a few patterns.
- Conceptual support is scaffolding only; real conceptual explanations need a generator plus verification and a human gate for any credentials.
- Whether these supports help readers is untested (needs HG-02).
