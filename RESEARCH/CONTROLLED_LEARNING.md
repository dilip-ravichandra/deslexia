# Improving DyslexiAdapt over time

## What the upgraded Research Lab does now
The local private page reads actual model/dataset/experiment artifacts. It now provides readiness indicators, a guarded terminal-command builder for baselines or DistilBERT, an improvement-workflow guide, JSON export and Markdown research-note export.

The command builder does not run a model or start a cloud job. It does not relax research validation, automatically create gold data, register a model, or invent results. Choose a new unused output version for every run. Known recorded output versions are rejected by the builder. Check that the output directory is unused before running a copied command, since lower-level training commands may overwrite outputs.

## Two different meanings of adaptation
1. Presentation adaptation: colour, text size, line/letter spacing, font and reading column respond immediately to the learner's choices. This already works and does not train a model.
2. Model improvement: new approved labelled examples can support a later training version. Feedback must first be interpreted and reviewed. This is a planned controlled cycle, rather than per-click weight updates.

## Recommended cycle
- Ask for informed permission before collecting identifiable or participant text; respect institutional approval requirements. Keep persistent logs off while preparing the product.
- A helpful/not-helpful click is feedback, not a correct support-category label and not proof of meaning preservation.
- Build a human review batch with selected text, immediate context, source URL/licence, document ID and provenance. Current minimal trace logs do not provide this full training dataset.
- Review labels under the project's annotation protocol. Single-annotator exploratory data, AI-assisted labels and reviewed gold data must keep distinct provenance. Human feedback is not silently converted into gold.
- Exclude examples related to held-out documents. Version all datasets and preserve a frozen comparison design. Do not repeatedly tune on the final test set.
- Train candidates locally using the existing validated pipeline. Compare validation results, class-specific failures and intervention/meaning quality. A newer model is not necessarily better.
- Deliberately register an eligible candidate, keeping the previous registry/version for rollback. Restart the backend to load the selection. The current loader supports probabilistic sklearn and fusion models; standalone DistilBERT training is available for comparison but is not a currently supported registry kind.

## Why a perfect answer cannot be promised
The category classifier chooses the support type. The intervention engine provides the support itself. Training the classifier does not create a capable conceptual explanation model. The current conceptual engine offers guiding questions. Improving answer content therefore needs a separate intervention/model task, source grounding and quality evaluation. Meaning checks can miss errors, so the learner needs the original text, a comparison and an undo option.

## Reporting
The Research Lab's Markdown export describes the artifact state and recorded run metrics; it is not a final paper or participant result. Smoke outputs are excluded. Use the existing verified `ML.paper_tables` exporter for final experimental tables after a complete research-valid experiment.

No paid endpoints, GPU jobs, training subscriptions or APIs were added by this upgrade. CPU/GPU time, memory and download availability still depend on the machine.
