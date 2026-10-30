**Independent human routing review**

Start the local app and open `http://127.0.0.1:8000/human-review.html`.

1. Recruit at least two independent, language-competent reviewers per language. Different people can cover different languages. The software cannot authenticate reviewer identity or competence.
2. Each reviewer uses their own code and chooses a language. Both start from the original blank pool. Do not consult model labels or each other's judgments.
3. Read the selected text and passage. Choose vocabulary, syntax, concept, or uncertain/multiple. Supply integer confidence **1–5** and a short reason. Skip any row you cannot assess.
4. Use **Save decision and next**. Browser progress is stored by reviewer code, language and exact source-pool hash. Switching devices does not transfer progress.
5. Export completed judgments as JSON. Keep each original export. Use only the latest export for each reviewer/language in a merge.
6. In `learner-lab.html`, enter the configured admin token if needed and select 2–8 independent exports. Merge validates source identity, decisions, declarations and timestamps. It does not train or activate a model.
7. Download the report and raw judgments. `merged.csv` retains all pool rows and their review status. `reviewed.csv` includes rows with at least two independent reviews, preserving disagreements as `OTHER_UNCERTAIN`. Missing second reviews remain archived and cannot become invented training labels.
8. Inspect per-language agreement and pairwise kappa. Undefined statistics stay undefined. Reviewer declarations do not prove genuine authorship. Maintain recruitment and competence records separately.
9. Import the reviewed CSV into the routing experiment only after your team has checked it. Uncertain rows remain in the archive and are excluded only from the three-primary-class fit. The 100-row starter cannot satisfy the existing per-language activation sample requirement; collect appropriate additional data rather than weakening the gate.

`learning.html` is a separate legacy GPT-pilot operations page. Current reader feedback appears in the learner evidence lab; clicking helpfulness is not an independent human routing annotation.
