"""
TRUSTNET - Supervised Fraud Prediction Baseline (XGBoost)
Loads chronological engineered features, splits data temporally, handles class
imbalance using dynamic weights, and logs performance metrics.
"""

import os
import json
from datetime import datetime
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
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
    Orchestrates the XGBoost training and evaluation pipeline.
    """
    os.makedirs(model_dir, exist_ok=True)
    
    # 1. Load and split datasets chronologically
    train_df, val_df, test_df = load_and_split_data(processed_csv_path)
    
    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_val, y_val = val_df[FEATURES], val_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]
    
    # 2. Compute class weighting to handle imbalance (scale_pos_weight = sum_neg / sum_pos)
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    scale_pos_weight = float(num_neg) / float(num_pos) if num_pos > 0 else 1.0
    
    print("=" * 60)
    print("TRUSTNET SUPERVISED BASELINE MODEL (XGBOOST)")
    print("=" * 60)
    print(f"Training split rows:   {len(train_df)} (Fraud: {num_pos}, Ratio: {num_pos/len(train_df)*100:.2f}%)")
    print(f"Validation split rows: {len(val_df)} (Fraud: {y_val.sum()}, Ratio: {y_val.sum()/len(val_df)*100:.2f}%)")
    print(f"Testing split rows:    {len(test_df)} (Fraud: {y_test.sum()}, Ratio: {y_test.sum()/len(test_df)*100:.2f}%)")
    print(f"Computed scale_pos_weight: {scale_pos_weight:.2f}")
    print("-" * 60)
    
    # 3. Train baseline XGBoost classifier
    # Keep learning rate modest and max_depth small to prevent overfitting
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss"
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # 4. Predict probabilities on test split
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # Threshold at 0.5 to get class predictions
    y_pred = (y_prob >= 0.5).astype(int)
    
    # 5. Evaluate Metrics
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    avg_precision = average_precision_score(y_test, y_prob)
    
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_prob)
    pr_auc = auc(rec_curve, prec_curve)
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    print("XGBoost Evaluation Metrics on Test Split:")
    print(f"Precision:         {precision:.4f}")
    print(f"Recall:            {recall:.4f} (Catch Rate)")
    print(f"F1-Score:          {f1:.4f}")
    print(f"ROC-AUC:           {roc_auc:.4f}")
    print(f"PR-AUC (Trapezoid):{pr_auc:.4f}")
    print(f"Average Precision: {avg_precision:.4f}")
    print(f"Confusion Matrix:  TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print("-" * 60)
    
    # 6. Save model binary
    model_path = os.path.join(model_dir, "xgboost_baseline.json")
    model.save_model(model_path)
    print(f"Saved native model to: {model_path}")
    
    # 7. Save metadata JSON
    metadata = {
        "model_type": "XGBoost",
        "features": FEATURES,
        "target": TARGET,
        "random_seed": 42,
        "training_timestamp": datetime.now().isoformat(),
        "splits": {
            "train": {
                "start": train_df["timestamp"].min().isoformat(),
                "end": train_df["timestamp"].max().isoformat(),
                "rows": len(train_df),
                "fraud_count": int(num_pos)
            },
            "validation": {
                "start": val_df["timestamp"].min().isoformat(),
                "end": val_df["timestamp"].max().isoformat(),
                "rows": len(val_df),
                "fraud_count": int(y_val.sum())
            },
            "test": {
                "start": test_df["timestamp"].min().isoformat(),
                "end": test_df["timestamp"].max().isoformat(),
                "rows": len(test_df),
                "fraud_count": int(y_test.sum())
            }
        },
        "evaluation_metrics": {
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "average_precision": float(avg_precision),
            "confusion_matrix": {
                "tp": int(tp),
                "fp": int(fp),
                "tn": int(tn),
                "fn": int(fn)
            }
        }
    }
    
    metadata_path = os.path.join(model_dir, "xgboost_metadata.json")
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
