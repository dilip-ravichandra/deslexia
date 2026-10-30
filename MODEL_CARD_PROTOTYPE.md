# Current model card

{
  "run_id": "87229885f07a40c08fdebc96456f8344",
  "model": "gated_ensemble_neural_weight0.1 + Logistic Regression",
  "selected_C": 1.0,
  "training_rows": 60,
  "reviewed_rows": 0,
  "data_status": "AI_WEAK_LABEL_PROTOTYPE",
  "valid_for_scientific_claims": false,
  "validation": {
    "macro_f1": 0.8294372294372294,
    "per_class": {
      "VOCABULARY": {
        "precision": 0.6666666666666666,
        "recall": 1.0,
        "f1-score": 0.8,
        "support": 2.0
      },
      "SYNTACTIC": {
        "precision": 1.0,
        "recall": 0.75,
        "f1-score": 0.8571428571428571,
        "support": 4.0
      },
      "CONCEPTUAL": {
        "precision": 0.8,
        "recall": 0.6666666666666666,
        "f1-score": 0.7272727272727273,
        "support": 6.0
      },
      "OTHER_UNCERTAIN": {
        "precision": 0.875,
        "recall": 1.0,
        "f1-score": 0.9333333333333333,
        "support": 7.0
      },
      "accuracy": 0.8421052631578947,
      "macro avg": {
        "precision": 0.8354166666666667,
        "recall": 0.8541666666666666,
        "f1-score": 0.8294372294372294,
        "support": 19.0
      },
      "weighted avg": {
        "precision": 0.8557017543859649,
        "recall": 0.8421052631578947,
        "f1-score": 0.8381863750284803,
        "support": 19.0
      }
    },
    "confusion_matrix": {
      "labels": [
        "VOCABULARY",
        "SYNTACTIC",
        "CONCEPTUAL",
        "OTHER_UNCERTAIN"
      ],
      "matrix": [
        [
          2,
          0,
          0,
          0
        ],
        [
          0,
          3,
          1,
          0
        ],
        [
          1,
          0,
          4,
          1
        ],
        [
          0,
          0,
          0,
          7
        ]
      ]
    },
    "rows": 19,
    "predictions": [
      "VOCABULARY",
      "CONCEPTUAL",
      "CONCEPTUAL",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "VOCABULARY",
      "OTHER_UNCERTAIN",
      "VOCABULARY",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN"
    ]
  },
  "incumbent_validation": {
    "macro_f1": 0.8294372294372294,
    "per_class": {
      "VOCABULARY": {
        "precision": 0.6666666666666666,
        "recall": 1.0,
        "f1-score": 0.8,
        "support": 2.0
      },
      "SYNTACTIC": {
        "precision": 1.0,
        "recall": 0.75,
        "f1-score": 0.8571428571428571,
        "support": 4.0
      },
      "CONCEPTUAL": {
        "precision": 0.8,
        "recall": 0.6666666666666666,
        "f1-score": 0.7272727272727273,
        "support": 6.0
      },
      "OTHER_UNCERTAIN": {
        "precision": 0.875,
        "recall": 1.0,
        "f1-score": 0.9333333333333333,
        "support": 7.0
      },
      "accuracy": 0.8421052631578947,
      "macro avg": {
        "precision": 0.8354166666666667,
        "recall": 0.8541666666666666,
        "f1-score": 0.8294372294372294,
        "support": 19.0
      },
      "weighted avg": {
        "precision": 0.8557017543859649,
        "recall": 0.8421052631578947,
        "f1-score": 0.8381863750284803,
        "support": 19.0
      }
    },
    "confusion_matrix": {
      "labels": [
        "VOCABULARY",
        "SYNTACTIC",
        "CONCEPTUAL",
        "OTHER_UNCERTAIN"
      ],
      "matrix": [
        [
          2,
          0,
          0,
          0
        ],
        [
          0,
          3,
          1,
          0
        ],
        [
          1,
          0,
          4,
          1
        ],
        [
          0,
          0,
          0,
          7
        ]
      ]
    },
    "rows": 19,
    "predictions": [
      "VOCABULARY",
      "CONCEPTUAL",
      "CONCEPTUAL",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "VOCABULARY",
      "OTHER_UNCERTAIN",
      "VOCABULARY",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN",
      "CONCEPTUAL",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN",
      "SYNTACTIC",
      "OTHER_UNCERTAIN"
    ]
  },
  "promotion_eligible": true,
  "selection_rule": "validation macro-F1 and supported-class recall must not decrease",
  "dataset_sha256": "2f8c0de3d5c7c965e84199566873305ddf3b83f02bad2946fae7ae0943ef0f1c",
  "uncertainty_threshold": 0.3,
  "abstention_validation": [
    {
      "threshold": 0.25,
      "accepted_validation_rows": 11,
      "provisional_label_accuracy": 0.8181818181818182
    },
    {
      "threshold": 0.3,
      "accepted_validation_rows": 8,
      "provisional_label_accuracy": 1.0
    },
    {
      "threshold": 0.35,
      "accepted_validation_rows": 3,
      "provisional_label_accuracy": 1.0
    },
    {
      "threshold": 0.4,
      "accepted_validation_rows": 0,
      "provisional_label_accuracy": null
    },
    {
      "threshold": 0.45,
      "accepted_validation_rows": 0,
      "provisional_label_accuracy": null
    },
    {
      "threshold": 0.5,
      "accepted_validation_rows": 0,
      "provisional_label_accuracy": null
    }
  ],
  "abstention_rule": "Maximise accepted validation examples with at least 3 examples and >=90% provisional-label accuracy. This is a small-sample engineering policy, not calibrated confidence.",
  "training_sha256": "fa3c072192f25095d640bb1b6a82558968a866337eec4731f9195c4d1251a040",
  "validation_sha256": "08e9330c98c370b747c6bdd2bc08c13830c5a5093904ba68de06003bbfda1251",
  "candidate_validation": [
    {
      "representation": "tfidf",
      "C": 0.5,
      "macro_f1": 0.35149572649572647
    },
    {
      "representation": "tfidf",
      "C": 1.0,
      "macro_f1": 0.4004329004329004
    },
    {
      "representation": "tfidf",
      "C": 2.0,
      "macro_f1": 0.4303571428571429
    },
    {
      "representation": "linguistic",
      "C": 0.1,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "linguistic",
      "C": 1.0,
      "macro_f1": 0.6726648351648352
    },
    {
      "representation": "linguistic",
      "C": 10.0,
      "macro_f1": 0.6333874458874459
    },
    {
      "representation": "hybrid",
      "C": 0.1,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "hybrid",
      "C": 1.0,
      "macro_f1": 0.6832611832611832
    },
    {
      "representation": "hybrid",
      "C": 10.0,
      "macro_f1": 0.6832611832611832
    },
    {
      "representation": "neural",
      "C": 0.1,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "neural",
      "C": 1.0,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "neural",
      "C": 10.0,
      "macro_f1": 0.6832611832611832
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.1",
      "C": 0.1,
      "macro_f1": 0.6830357142857143
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.25",
      "C": 0.1,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.5",
      "C": 0.1,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.1",
      "C": 1.0,
      "macro_f1": 0.7708333333333333
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.25",
      "C": 1.0,
      "macro_f1": 0.6333874458874459
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.5",
      "C": 1.0,
      "macro_f1": 0.6333874458874459
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.1",
      "C": 10.0,
      "macro_f1": 0.718452380952381
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.25",
      "C": 10.0,
      "macro_f1": 0.5852272727272727
    },
    {
      "representation": "gated_ensemble_linguistic_weight0.5",
      "C": 10.0,
      "macro_f1": 0.6726648351648352
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.1",
      "C": 0.1,
      "macro_f1": 0.6830357142857143
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.25",
      "C": 0.1,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.5",
      "C": 0.1,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.1",
      "C": 1.0,
      "macro_f1": 0.7708333333333333
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.25",
      "C": 1.0,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.5",
      "C": 1.0,
      "macro_f1": 0.6333874458874459
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.1",
      "C": 10.0,
      "macro_f1": 0.746474358974359
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.25",
      "C": 10.0,
      "macro_f1": 0.6333874458874459
    },
    {
      "representation": "gated_ensemble_hybrid_weight0.5",
      "C": 10.0,
      "macro_f1": 0.6832611832611832
    },
    {
      "representation": "gated_ensemble_neural_weight0.1",
      "C": 0.1,
      "macro_f1": 0.6830357142857143
    },
    {
      "representation": "gated_ensemble_neural_weight0.25",
      "C": 0.1,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_neural_weight0.5",
      "C": 0.1,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "gated_ensemble_neural_weight0.1",
      "C": 1.0,
      "macro_f1": 0.8294372294372294
    },
    {
      "representation": "gated_ensemble_neural_weight0.25",
      "C": 1.0,
      "macro_f1": 0.6874999999999999
    },
    {
      "representation": "gated_ensemble_neural_weight0.5",
      "C": 1.0,
      "macro_f1": 0.7373737373737373
    },
    {
      "representation": "gated_ensemble_neural_weight0.1",
      "C": 10.0,
      "macro_f1": 0.7770562770562771
    },
    {
      "representation": "gated_ensemble_neural_weight0.25",
      "C": 10.0,
      "macro_f1": 0.6832611832611832
    },
    {
      "representation": "gated_ensemble_neural_weight0.5",
      "C": 10.0,
      "macro_f1": 0.6832611832611832
    }
  ],
  "limitations": [
    "Small synthetic targeted sample; agreement is between GPT passes, not humans.",
    "Scores measure agreement with provisional labels, not dyslexia benefit.",
    "Raw probabilities and abstention threshold are not calibrated."
  ]
}

See RUN_NEURAL.md and REPORTS/REAL_MODEL_QA.md for pretrained assets, actual generation and limitations.
