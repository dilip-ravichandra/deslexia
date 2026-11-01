# Architecture + Research Decisions

ADR-001: Primary labels are Vocabulary, Syntactic and Conceptual.

ADR-002: MVP localization is learner-guided span selection. Automatic localization is future work.

ADR-003: The classifier predicts a computational support category. It does not diagnose dyslexia or infer a medical cause.

ADR-004: Compare Majority, TF-IDF Logistic Regression, TF-IDF Linear SVM, DistilBERT, and DistilBERT + linguistic features.

ADR-005: Semantic verification combines embedding similarity, NLI/entailment, entity preservation, number preservation and human evaluation.

ADR-006: The research question is whether localized, learner-guided intervention can support comprehension while changing fewer text units and preserving more original content than uniform simplification.

ADR-007: Accessibility preferences are a separate presentation layer.

ADR-008: Human annotation is required for gold labels.

## ADR-009 (APPROVED BY OWNER FOR ENGINEERING USE; formal legal/institutional review still advised): free-only resources and source corpus
- Constraint from the project owner: use only free, safe datasets, models and services.
- Proposed source pool: juno-labs/simple_wikipedia (CC BY-SA 3.0), built with ML/source_pool.py. Consequence: the annotated dataset must be released under CC BY-SA-compatible terms with attribution.
- Proposed models: distilbert/distilbert-base-uncased, sentence-transformers/all-MiniLM-L6-v2, cross-encoder/nli-deberta-v3-small (all Apache-2.0 per Hub metadata).
- No free dataset provides support-category labels; gold labels remain human-only (ADR-008 / HG-01).
- Status: owner approved the proposed CC BY-SA-compatible source pool on 2026-11-01. This records an engineering/content decision, not legal advice or institutional approval.
- Required attribution for copied text: source title/article identifier, source URL, author/history link where available, applicable CC BY-SA version/link, and a notice that the project made excerpts/selection/annotation changes. Combined text-plus-annotation releases must retain compatible ShareAlike terms unless an institution confirms another treatment.

- 2026-10-09 update to ADR-009: owner had not confirmed. The decision was subsequently confirmed as above; analysis remains in DATA/LICENSE_ANALYSIS.md and no pipeline component silently converts source text into routing labels.
