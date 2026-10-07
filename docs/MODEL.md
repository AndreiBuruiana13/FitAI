# Trained activity model

The original thesis model is distributed at `app/ai/activity_model.joblib`.

- Type: scikit-learn RandomForestClassifier, 100 decision trees.
- Inputs: six aggregate motion features, matching the backend schema.
- Outputs: RESTING, RUNNING, TYPING, WALKING.
- Training dataset size recorded in metadata: 5,441 labelled windows.
- SHA-256: `5a6198590500e6018df85a92d3386a38a3d298e84198315d60d17e7e1d07796a`

## Publication review

The saved object was loaded with a restricted class allowlist and its attributes inspected. It contains standard classifier settings, feature/class names and learned trees. No custom executable classes, account identifiers, email addresses, network configuration, raw recording tables or attached training-data matrices were found in the inspected object. Learned split thresholds and sample counts remain part of the model; distributing learned parameters is not a formal guarantee against all model privacy inference.

The model successfully loaded and generated a prediction in the checked environment (scikit-learn 1.8.0, joblib 1.5.3). This smoke check does not independently reproduce its recorded accuracy. Joblib files use pickle serialization: load only trusted model files. The backend falls back to heuristics if loading or schema validation fails.

## Evaluation

| Metric | Recorded value |
| --- | ---: |
| Holdout accuracy | 90.17% |
| Holdout macro-F1 | 89.54% |
| Five-fold cross-validation macro-F1 | 90.71% |

Raw personal measurements, labels associated with recording timestamps, databases and device logs are excluded. Reproducing training requires collecting a separate local dataset. The recorded evaluation may be affected by temporal correlation between windows; session- or participant-separated evaluation would give stronger evidence of generalization.
