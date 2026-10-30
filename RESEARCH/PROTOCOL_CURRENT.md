# Preserved research approach and implementation boundaries

DyslexiAdapt localizes a reader-selected difficulty, routes a minimum appropriate intervention, retains the original source, records checks/uncertainty and adapts later support using a language-specific learner history. Presentation settings remain distinct from linguistic categories. Pronunciation is an optional support action; listening requests do not prove pronunciation errors.

## Two learning processes

The initial consented survey sets weak learner-model priors. Explicit support choices, explanation-style choices, undo/regenerate, settings changes and optional helpfulness judgments update the learner evidence model. Term and text-shape relevance plus recency determine how much past requests influence a later selection. Current manual requests take precedence. Dwell, rereading and returning to a tab remain ambiguous observations. They do not automatically label vocabulary, syntax or conceptual difficulty.

The personal evidence model is Dirichlet-style online estimation, with fixed engineering weights and a 30-day half-life. It is not an independently calibrated diagnosis or comprehension predictor. The admin screen shows actual events, before/after need and style parameters, presentation changes and the evidence used for a saved route. Its scores must not be described as neural training accuracy.

Global models are trained in separate reproducible jobs. The agreed primary comparison is TF-IDF vs multilingual DistilBERT vs the same multilingual DistilBERT with the fixed text features on the same human-reviewed three-category routing task and frozen document-group partitions. Unresolved rows remain in the review archive. They are excluded only from the supervised three-class fit; uncertain runtime cases ask for a learner choice. No pilot AI annotations are human gold.

Public CompLex supports a separate English lexical-regression comparison. ASSET supplies human simplification references without a train split. OneStopEnglish supplies reading-level texts. CWID-hi supplies Hindi word labels without sentence contexts. IndicQA supplies publisher-declared expert native QA contexts/questions/answers in Hindi, Kannada and Tamil. None is silently converted into the project's routing labels. Public data do not establish suitability for dyslexia.

## Required research evaluation

Preserve the four original conditions: original text, uniform simplification, uniform accessibility and DyslexiAdapt. Evaluate comprehension, perceived difficulty, reading time, intervention appropriateness, semantic preservation, acceptance and preferences, per language. Ablate localization, routing, checks and personalization. Compare starting-survey-only support with survey plus session evidence using held-out later sessions. Keep participant/document separation and temporal order; never use future signals to predict earlier needs.

Before a study, pre-register primary outcomes, sample-size rationale, allocation/counterbalancing, model versions and analysis. Freeze a shared explanation model/settings for relevant comparison arms so model changes do not confound personalization effects. No comprehension benefit or novelty claim is established by software tests or public lexical metrics. Native explanations, OCR and speech require language-competent evaluation; script matching alone is insufficient.

The current build provides the technical learner loop and separate training/evidence workflow. It does not contain a completed four-condition student study, genuine four-language routing gold benchmark, authenticated human annotation agreement, or clinical/educational effectiveness findings. These missing results must remain visibly missing.
