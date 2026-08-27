# TRUSTNET - Machine Learning Module

This directory contains the machine learning pipelines for fraud detection, behavioral profiling, and model explanations.

## Planned Structure
- `src/preprocessing/`: Scripts for data cleaning, scaling, and feature engineering.
- `src/models/`: Script modules to train and evaluate supervised and unsupervised models.
- `src/explainers/`: SHAP-based interpretability generation for transactions.
- `models/`: (Git ignored) Saved weights and model binaries (`.pkl`, `.joblib`).

## Models & Libraries
- **XGBoost**: Supervised model to classify transaction fraud probability based on historical features.
- **Isolation Forest**: Unsupervised model to detect behavioral anomalies without prior labels.
- **SHAP**: Computes Shapley additive explanation values to output local feature impact on the generated risk score.
