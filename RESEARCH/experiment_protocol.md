# Experiment Protocol

## Classification conditions
A. Majority
B. TF-IDF + Logistic Regression
C. TF-IDF + Linear SVM
D. DistilBERT
E. DistilBERT + linguistic features

## Split
Use document/source grouped splitting. Freeze the split before final test evaluation.

## Classification metrics
Accuracy, macro precision, macro recall, macro F1, weighted F1, per-class metrics, confusion matrix.

## Intervention metrics
- intervention rate
- changed token count
- changed sentence count
- readability delta
- embedding similarity
- NLI consistency
- entity preservation
- number preservation
- human appropriateness

## Ablations
- no context
- no linguistic features
- no NLI
- no entity/number preservation
- no learner localization
