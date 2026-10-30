# DistilBERT + Linguistic Feature Fusion

DistilBERT representation
+
explicit linguistic features
→ feature projection
→ concatenation
→ dropout
→ 3-class classifier.

Candidate features:
- token count
- character count
- average token length
- long-word ratio
- punctuation count
- sentence count
- characters per sentence

Run an ablation against transformer-only.
