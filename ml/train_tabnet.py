"""
TAB-Net Training Script
=======================
Trains XGBoost, Random Forest, and Logistic Regression baselines on the
ULB/Kaggle creditcard.csv benchmark dataset.

Usage:
    python ml/train_tabnet.py --data ml/data/creditcard.csv --output ml_models/

Requirements:
    pip install scikit-learn xgboost imbalanced-learn shap pandas numpy

Dataset:
    Download creditcard.csv from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
    Place it in ml/data/creditcard.csv

Important:
    - Preprocessing is fit ONLY on training data to prevent leakage.
    - SMOTE is applied ONLY within training folds.
    - Source-reported metrics (99.92% accuracy, 0.885 macro F1, 0.884 PR-AUC) are NOT
      reproduced here; this script reports independently computed metrics.
    - The trained model is saved to ml_models/latest.pkl for inference.
"""
import argparse
import json
import logging
import os
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
)

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
    "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18",
    "V19", "V20", "V21", "V22", "V23", "V24", "V25", "V26", "V27",
    "V28", "Amount",
]
TARGET_COL = "Class"


def load_data(path: str) -> tuple:
    logger.info("Loading dataset from %s", path)
    df = pd.read_csv(path)
    missing = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing columns: {missing}")
    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values
    logger.info("Dataset loaded: %d samples, %d positives (%.4f%%)",
                len(y), y.sum(), 100 * y.mean())
    return X, y, df


def evaluate_pipeline(pipeline, X, y) -> dict:
    """Evaluate a fitted pipeline on a held-out set."""
    y_prob = pipeline.predict_proba(X)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    cm = confusion_matrix(y, y_pred)
    tn, fp, fn, tp = cm.ravel()
    return {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "f1": float(f1_score(y, y_pred, zero_division=0)),
        "macro_f1": float(f1_score(y, y_pred, average="macro", zero_division=0)),
        "pr_auc": float(average_precision_score(y, y_prob)),
        "roc_auc": float(roc_auc_score(y, y_prob)),
        "fpr": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
        "confusion_matrix": cm.tolist(),
    }


def train_all(data_path: str, output_dir: str, test_fraction: float = 0.2, n_splits: int = 5):
    X, y, df = load_data(data_path)

    # Chronological train/test split (no shuffle — preserve time ordering to avoid leakage)
    split_idx = int(len(X) * (1 - test_fraction))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    logger.info("Train: %d samples | Test: %d samples", len(y_train), len(y_test))

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # ── 1. Logistic Regression Baseline ───────────────────────────────────────
    logger.info("Training Logistic Regression baseline...")
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
    ])
    lr_pipeline.fit(X_train, y_train)
    results["logistic_regression"] = evaluate_pipeline(lr_pipeline, X_test, y_test)
    logger.info("LR — PR-AUC: %.4f | F1: %.4f", results["logistic_regression"]["pr_auc"], results["logistic_regression"]["f1"])

    # ── 2. Random Forest Baseline ──────────────────────────────────────────────
    logger.info("Training Random Forest baseline...")
    rf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=42,
            n_jobs=-1, max_depth=20, min_samples_split=5,
        )),
    ])
    rf_pipeline.fit(X_train, y_train)
    results["random_forest"] = evaluate_pipeline(rf_pipeline, X_test, y_test)
    logger.info("RF — PR-AUC: %.4f | F1: %.4f", results["random_forest"]["pr_auc"], results["random_forest"]["f1"])

    # ── 3. XGBoost (primary TAB-Net model) ────────────────────────────────────
    logger.info("Training XGBoost (primary TAB-Net)...")
    try:
        from xgboost import XGBClassifier
        # Handle class imbalance via scale_pos_weight
        scale_pos = float((y_train == 0).sum()) / float((y_train == 1).sum())
        xgb_pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=scale_pos,
                eval_metric="aucpr",
                random_state=42,
                n_jobs=-1,
                verbosity=0,
            )),
        ])
        xgb_pipeline.fit(X_train, y_train)
        results["xgboost"] = evaluate_pipeline(xgb_pipeline, X_test, y_test)
        logger.info("XGBoost — PR-AUC: %.4f | F1: %.4f | ROC-AUC: %.4f",
                    results["xgboost"]["pr_auc"],
                    results["xgboost"]["f1"],
                    results["xgboost"]["roc_auc"])

        # Save XGBoost as 'latest' model for inference
        best_pipeline = xgb_pipeline
        best_name = "xgboost"
    except ImportError:
        logger.warning("XGBoost not installed. Using Random Forest as primary model.")
        best_pipeline = rf_pipeline
        best_name = "random_forest"
        results["xgboost"] = {"error": "xgboost not installed"}

    # ── Save model and metadata ────────────────────────────────────────────────
    model_path = str(output_dir_path / "latest.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(best_pipeline, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Saved primary model to %s", model_path)

    metadata = {
        "model_name": f"XGBoost TAB-Net v1" if best_name == "xgboost" else "Random Forest TAB-Net v1",
        "channel": "tab_net",
        "version_tag": "1.0.0",
        "feature_names": FEATURE_COLS,
        "training_info": {
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test)),
            "train_positives": int(y_train.sum()),
            "test_positives": int(y_test.sum()),
            "test_fraction": test_fraction,
            "split_strategy": "chronological (no shuffle — avoids temporal leakage)",
        },
        "evaluation_results": results,
        "important_notes": [
            "Metrics are computed on the held-out test set using this training run.",
            "Source-reported figures (99.92% accuracy, 0.885 macro F1, 0.884 PR-AUC) are NOT reproduced here.",
            "Thresholds (0.3 low, 0.7 high) are configurable defaults — validate on your deployment data.",
            "SMOTE was NOT applied (scale_pos_weight used instead to avoid in-test leakage).",
        ],
    }
    metadata_path = str(output_dir_path / "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info("Saved metadata to %s", metadata_path)

    # Print summary
    print("\n" + "=" * 60)
    print("CARD-Net TAB-Net Training Summary")
    print("=" * 60)
    for model_name, metrics in results.items():
        if "error" in metrics:
            print(f"\n{model_name}: {metrics['error']}")
            continue
        print(f"\n{model_name.upper()}:")
        print(f"  Accuracy : {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall   : {metrics['recall']:.4f}")
        print(f"  F1-Score : {metrics['f1']:.4f}")
        print(f"  Macro F1 : {metrics['macro_f1']:.4f}")
        print(f"  PR-AUC   : {metrics['pr_auc']:.4f}")
        print(f"  ROC-AUC  : {metrics['roc_auc']:.4f}")
        print(f"  FPR      : {metrics['fpr']:.4f}")
    print("\n[NOTE] Source-reported metrics (99.92% acc, 0.885 macro F1)")
    print("   have NOT been independently verified in this training run.")
    print("   Report only the metrics printed above as current results.")
    print("=" * 60)

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CARD-Net TAB-Net Training Script")
    parser.add_argument("--data", default="ml/data/creditcard.csv", help="Path to creditcard.csv")
    parser.add_argument("--output", default="ml_models", help="Output directory for model artifacts")
    parser.add_argument("--test-fraction", type=float, default=0.2)
    args = parser.parse_args()

    if not os.path.exists(args.data):
        logger.error("Dataset not found at %s", args.data)
        logger.error("Download creditcard.csv from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        sys.exit(1)

    train_all(args.data, args.output, test_fraction=args.test_fraction)
