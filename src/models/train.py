#!/usr/bin/env python3
"""
Phase 5: ML Model Training and Evaluation.
Trains a lightweight Logistic Regression classifier (and Decision Tree comparator)
to predict the probability of future agent failure from runtime signals.
"""

import json
import os
import sys
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.signals.engine import SignalVector

PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models_saved")


def evaluate_model(name: str, model, X: pd.DataFrame, y: pd.Series, split_name: str = "Test") -> dict:
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(int)

    acc = accuracy_score(y, preds)
    prec = precision_score(y, preds, zero_division=0)
    rec = recall_score(y, preds, zero_division=0)
    f1 = f1_score(y, preds, zero_division=0)
    auc = roc_auc_score(y, probs)
    cm = confusion_matrix(y, preds).tolist()

    print(f"\n--- {name} ({split_name} Set Evaluation) ---")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f} (detects {rec*100:.1f}% of failing prefixes)")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC-AUC:   {auc:.4f}")
    print("Confusion Matrix [[TN, FP], [FN, TP]]:")
    print(f"  {cm}")

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": cm,
    }


def train_and_evaluate():
    print("=" * 70)
    print("      PHASE 5: ML MODEL DEVELOPMENT & RISK ESTIMATION")
    print("=" * 70)

    # 1. Load data
    train_path = os.path.join(PROCESSED_DIR, "train_features.csv")
    val_path = os.path.join(PROCESSED_DIR, "val_features.csv")
    test_path = os.path.join(PROCESSED_DIR, "test_features.csv")

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    feature_cols = SignalVector.feature_names()
    target_col = "will_fail"

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_val = val_df[feature_cols]
    y_val = val_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    print(f"\nFeatures ({len(feature_cols)}): {feature_cols}")
    print(f"Train steps: {len(X_train)} (Failures: {y_train.sum()} / {len(y_train)} = {y_train.mean():.1%})")
    print(f"Val steps:   {len(X_val)} (Failures: {y_val.sum()} / {len(y_val)} = {y_val.mean():.1%})")
    print(f"Test steps:  {len(X_test)} (Failures: {y_test.sum()} / {len(y_test)} = {y_test.mean():.1%})")

    # 2. Train Primary Model: Logistic Regression Pipeline
    print("\n[1/3] Training Primary Model: Logistic Regression (balanced class weights)...")
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)

    lr_val_metrics = evaluate_model("Logistic Regression", lr_pipeline, X_val, y_val, "Validation")
    lr_test_metrics = evaluate_model("Logistic Regression", lr_pipeline, X_test, y_test, "Held-out Test")

    # 3. Train Comparison Model: Decision Tree Classifier
    print("\n[2/3] Training Comparison Model: Decision Tree (max_depth=5, balanced)...")
    dt_clf = DecisionTreeClassifier(max_depth=5, class_weight="balanced", random_state=42)
    dt_clf.fit(X_train, y_train)

    dt_val_metrics = evaluate_model("Decision Tree", dt_clf, X_val, y_val, "Validation")
    dt_test_metrics = evaluate_model("Decision Tree", dt_clf, X_test, y_test, "Held-out Test")

    # 4. Save Models & Artifacts
    print("\n[3/3] Saving model artifacts to models_saved/...")
    os.makedirs(MODELS_DIR, exist_ok=True)

    lr_model_path = os.path.join(MODELS_DIR, "logistic_regression.joblib")
    dt_model_path = os.path.join(MODELS_DIR, "decision_tree.joblib")
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")

    joblib.dump(lr_pipeline, lr_model_path)
    joblib.dump(dt_clf, dt_model_path)

    metadata = {
        "primary_model": "LogisticRegression",
        "comparison_model": "DecisionTreeClassifier",
        "feature_names": feature_cols,
        "num_features": len(feature_cols),
        "target": target_col,
        "metrics": {
            "logistic_regression": {
                "validation": lr_val_metrics,
                "test": lr_test_metrics,
            },
            "decision_tree": {
                "validation": dt_val_metrics,
                "test": dt_test_metrics,
            },
        },
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved primary model:    {lr_model_path}")
    print(f"Saved comparison model: {dt_model_path}")
    print(f"Saved metadata:         {metadata_path}")
    print("\nTraining and evaluation successfully completed!")


if __name__ == "__main__":
    train_and_evaluate()
