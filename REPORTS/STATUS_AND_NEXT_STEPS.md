# Status and next steps

See CONTINUE_HERE.md for exact commands.

## Ready
- Existing data, training, intervention, backend, learner and research tooling.
- Annotation batch preparation and human-return resolution into reviewed gold candidates.
- Offline four-condition adaptation comparison and a human-study preparation protocol.
- Guarded held-out classification table generation from verified experiment artifacts.
- Regression fixes described in REPORTS/CONTINUATION_AUDIT.md.

## Still needed
1. Confirm source licensing (ADR-009/HG-03), select approved spans, and obtain
   independent human annotations (HG-01). AI will not supply gold labels.
2. Review agreement/adjudications, freeze the grouped split and train/evaluate
   baselines, pretrained DistilBERT and fusion on real data.
3. Review intervention resources and calibrate semantic checks. Conceptual
   scaffolding currently does not supply a domain explanation.
4. Supply actual paired intervention outputs for offline comparison.
5. Obtain institutional approval/consent (HG-02) before collecting participants.
6. Export real paper tables, write results and complete the paper only when
   the required evidence exists. No real findings were produced here.
7. Test real browsers, phones and screen readers.

No demo, synthetic fixture or random-init smoke output is research evidence.
