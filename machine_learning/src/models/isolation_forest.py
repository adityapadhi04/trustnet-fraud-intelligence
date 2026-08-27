"""
TRUSTNET - Unsupervised Anomaly Detection Baseline (Isolation Forest)
Loads chronological features, imputes cold starts, fits Isolation Forest on
non-fraud behaviors in the training split, and logs anomaly scores and statistics.
"""

import os
import json
import joblib
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    average_precision_score
)

# ML approved feature list
FEATURES = [
    "amount",
    "amount_deviation",
    "is_new_device",
    "is_new_ip",
    "location_deviation_km",
    "hour_of_day",
    "day_of_week",
    "velocity_1h",
    "velocity_24h",
    "recipient_in_degree",
    "sender_out_degree"
]

TARGET = "is_fraud_labeled"


def load_and_split_data(filepath: str):
    """
    Loads features, sorts chronologically, and performs a 70/15/15 temporal split.
    """
    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    total_rows = len(df)
    train_idx = int(total_rows * 0.70)
    val_idx = train_idx + int(total_rows * 0.15)
    
    train_df = df.iloc[:train_idx]
    val_df = df.iloc[train_idx:val_idx]
    test_df = df.iloc[val_idx:]
    
    return train_df, val_df, test_df


def train_and_evaluate(processed_csv_path: str, model_dir: str):
    """
    Orchestrates the Isolation Forest training and anomaly reporting pipeline.
    """
    os.makedirs(model_dir, exist_ok=True)
    
    # 1. Load and split datasets chronologically
    train_df, val_df, test_df = load_and_split_data(processed_csv_path)
    
    # Extract only ML features (fraud target is completely excluded during training)
    X_train = train_df[FEATURES].copy()
    X_val = val_df[FEATURES].copy()
    X_test = test_df[FEATURES].copy()
    
    # 2. Impute Cold Starts for Isolation Forest (requires non-NaN values)
    # Using neutral defaults: amount deviation = 1.0 (mean), location deviation = 0.0 (no movement)
    impute_defaults = {
        "amount_deviation": 1.0,
        "location_deviation_km": 0.0
    }
    X_train.fillna(impute_defaults, inplace=True)
    X_val.fillna(impute_defaults, inplace=True)
    X_test.fillna(impute_defaults, inplace=True)
    
    # 3. Train Isolation Forest
    # Contamination set to 3.0% to reflect the ~3% fraud prevalence rate in train set
    print("=" * 60)
    print("TRUSTNET UNSUPERVISED BASELINE MODEL (ISOLATION FOREST)")
    print("=" * 60)
    print(f"Training split rows (unlabeled): {len(X_train)}")
    print(f"Testing split rows (unlabeled):  {len(X_test)}")
    print("-" * 60)
    
    model = IsolationForest(
        n_estimators=100,
        contamination=0.03,
        random_state=42
    )
    model.fit(X_train)
    
    # 4. Predict anomaly scores
    # sklearn decision_function returns negative values for anomalies and positive for inliers
    # We map to anomaly_score = -decision_function() so higher positive scores represent greater anomaly risk.
    raw_decision_test = model.decision_function(X_test)
    anomaly_scores_test = -raw_decision_test
    
    # sklearn predict outputs -1 for anomalies and 1 for inliers.
    # Map to binary target format: 1 for anomaly (fraud prediction), 0 for normal
    y_pred_anomaly = (model.predict(X_test) == -1).astype(int)
    
    # 5. Evaluate Anomaly Predictions against Ground Truth labels
    y_test = test_df[TARGET]
    
    precision = precision_score(y_test, y_pred_anomaly, zero_division=0)
    recall = recall_score(y_test, y_pred_anomaly, zero_division=0)
    f1 = f1_score(y_test, y_pred_anomaly, zero_division=0)
    roc_auc = roc_auc_score(y_test, anomaly_scores_test)
    avg_precision = average_precision_score(y_test, anomaly_scores_test)
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred_anomaly).ravel()
    
    # 6. Report Anomaly Statistics
    print("Isolation Forest Score Stats on Test Set:")
    print(f"Min Anomaly Score:     {anomaly_scores_test.min():.4f}")
    print(f"Max Anomaly Score:     {anomaly_scores_test.max():.4f}")
    print(f"Mean Anomaly Score:    {anomaly_scores_test.mean():.4f}")
    print(f"Anomalies Flagged:     {y_pred_anomaly.sum()} (out of {len(y_pred_anomaly)} test samples)")
    print("-" * 60)
    print("Performance (Alignment of unsupervised anomalies with actual fraud labels):")
    print(f"Precision:             {precision:.4f}")
    print(f"Recall:                {recall:.4f}")
    print(f"F1-Score:              {f1:.4f}")
    print(f"ROC-AUC on scores:     {roc_auc:.4f}")
    print(f"Average Precision:     {avg_precision:.4f}")
    print(f"Confusion Matrix:      TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print("-" * 60)
    
    # 7. Save model binary using joblib
    model_path = os.path.join(model_dir, "isolation_forest_baseline.pkl")
    joblib.dump(model, model_path)
    print(f"Saved serialization model to: {model_path}")
    
    # 8. Save metadata JSON
    metadata = {
        "model_type": "Isolation Forest",
        "features": FEATURES,
        "random_seed": 42,
        "contamination": 0.03,
        "training_timestamp": datetime.now().isoformat(),
        "splits": {
            "train_rows": len(X_train),
            "test_rows": len(X_test)
        },
        "score_statistics": {
            "min_score": float(anomaly_scores_test.min()),
            "max_score": float(anomaly_scores_test.max()),
            "mean_score": float(anomaly_scores_test.mean()),
            "flagged_anomalies": int(y_pred_anomaly.sum())
        },
        "alignment_metrics_vs_target": {
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "average_precision": float(avg_precision),
            "confusion_matrix": {
                "tp": int(tp),
                "fp": int(fp),
                "tn": int(tn),
                "fn": int(fn)
            }
        }
    }
    
    metadata_path = os.path.join(model_dir, "isolation_forest_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Saved model metadata to: {metadata_path}")
    print("=" * 60)


if __name__ == "__main__":
    # If run directly
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    raw_features_path = os.path.join(base_dir, "datasets", "processed_features.csv")
    model_save_dir = os.path.join(base_dir, "models")
    
    if os.path.exists(raw_features_path):
        train_and_evaluate(raw_features_path, model_save_dir)
    else:
        print(f"Processed features file not found: {raw_features_path}")
