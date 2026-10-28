"""
TAB-Net Inference Pipeline.

Loads a trained XGBoost / scikit-learn model pipeline from disk and
provides fraud probability predictions for individual transactions.

Design notes:
- Model is loaded once at startup and cached in memory.
- Preprocessing (StandardScaler) is applied using fit parameters from training data only.
- SHAP values are computed using TreeExplainer where available.
- This module does NOT retrain models — training is done offline via ml/train_tabnet.py.
"""
import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
    "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18",
    "V19", "V20", "V21", "V22", "V23", "V24", "V25", "V26", "V27",
    "V28", "Amount",
]

# Module-level model cache
_model_pipeline = None
_model_path: Optional[str] = None
_shap_explainer = None


def _load_model(model_path: str):
    """Load the serialised sklearn pipeline from disk."""
    global _model_pipeline, _model_path, _shap_explainer
    if not os.path.exists(model_path):
        logger.error("Model file not found: %s", model_path)
        return False
    try:
        with open(model_path, "rb") as f:
            _model_pipeline = pickle.load(f)
        _model_path = model_path
        logger.info("Loaded model pipeline from %s", model_path)
        # Try to initialise SHAP explainer for tree models
        try:
            import shap
            from xgboost import XGBClassifier
            # Extract the final estimator from the pipeline
            final_step = list(_model_pipeline.steps)[-1][1]
            if isinstance(final_step, XGBClassifier):
                _shap_explainer = shap.TreeExplainer(final_step)
                logger.info("SHAP TreeExplainer initialised successfully.")
            else:
                _shap_explainer = None
                logger.info("SHAP not available for model type: %s", type(final_step).__name__)
        except Exception as shap_err:
            _shap_explainer = None
            logger.warning("SHAP initialisation failed: %s", shap_err)
        return True
    except Exception as e:
        logger.error("Failed to load model: %s", e)
        _model_pipeline = None
        return False


def get_active_model_path() -> Optional[str]:
    """Return the path to the active model artifact."""
    base_dirs = [
        Path(settings.MODEL_DIR),
        Path(__file__).resolve().parent.parent.parent.parent / settings.MODEL_DIR,
        Path(__file__).resolve().parent.parent.parent.parent.parent / settings.MODEL_DIR,
        Path(__file__).resolve().parent.parent.parent.parent / "backend" / settings.MODEL_DIR,
    ]
    for model_dir in base_dirs:
        if settings.ACTIVE_MODEL_VERSION:
            candidate = model_dir / f"{settings.ACTIVE_MODEL_VERSION}.pkl"
            if candidate.exists():
                return str(candidate.resolve())
        latest = model_dir / "latest.pkl"
        if latest.exists():
            return str(latest.resolve())
    return None


def is_model_loaded() -> bool:
    return _model_pipeline is not None


def ensure_model_loaded() -> bool:
    """Load model if not already loaded. Returns True if model is ready."""
    global _model_pipeline
    if _model_pipeline is not None:
        return True
    path = get_active_model_path()
    if path is None:
        logger.warning("No model artifact found. Run ml/train_tabnet.py to train a model.")
        return False
    return _load_model(path)


def reload_model(model_path: str) -> bool:
    """Force-reload a model from the given path."""
    return _load_model(model_path)


def predict(
    features: Dict[str, float],
    threshold_low: float = 0.3,
    threshold_high: float = 0.7,
) -> Tuple[float, str, Optional[Dict[str, float]]]:
    """
    Score a single transaction.

    Args:
        features: Dict with keys matching FEATURE_NAMES (Time, V1–V28, Amount).
        threshold_low: Probability below which risk is 'low'.
        threshold_high: Probability above which risk is 'high'.

    Returns:
        Tuple of (fraud_probability, risk_category, shap_values_or_None)

    Raises:
        RuntimeError: If model is not loaded.
        ValueError: If required features are missing.
    """
    if not ensure_model_loaded():
        raise RuntimeError(
            "No trained model is available. "
            "Please run 'python ml/train_tabnet.py' and restart the server."
        )
    # Build feature vector in correct order
    missing = [f for f in FEATURE_NAMES if f not in features]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    X = np.array([[features[f] for f in FEATURE_NAMES]], dtype=np.float64)

    # Get probability
    proba = _model_pipeline.predict_proba(X)[0, 1]
    fraud_probability = float(np.clip(proba, 0.0, 1.0))

    # Risk tier
    if fraud_probability < threshold_low:
        risk_category = "low"
    elif fraud_probability < threshold_high:
        risk_category = "medium"
    else:
        risk_category = "high"

    # SHAP values (tree model only, may be None)
    shap_values: Optional[Dict[str, float]] = None
    if _shap_explainer is not None:
        try:
            # Get preprocessed features for SHAP
            # Pipeline steps before the final estimator
            steps = list(_model_pipeline.steps)
            if len(steps) > 1:
                X_transformed = X.copy()
                for name, transformer in steps[:-1]:
                    X_transformed = transformer.transform(X_transformed)
            else:
                X_transformed = X
            sv = _shap_explainer.shap_values(X_transformed)
            # For binary classification XGBoost returns shape (1, n_features)
            if isinstance(sv, list):
                sv = sv[1]  # Positive class
            sv_flat = sv.flatten()
            shap_values = {FEATURE_NAMES[i]: float(sv_flat[i]) for i in range(len(FEATURE_NAMES))}
        except Exception as e:
            logger.warning("SHAP computation failed: %s", e)

    return fraud_probability, risk_category, shap_values


def predict_batch(
    feature_list: List[Dict[str, float]],
    threshold_low: float = 0.3,
    threshold_high: float = 0.7,
) -> List[Tuple[float, str, Optional[Dict[str, float]]]]:
    """Score multiple transactions efficiently."""
    if not ensure_model_loaded():
        raise RuntimeError("No trained model is available.")

    valid_rows = []
    valid_indices = []
    errors = {}
    for i, features in enumerate(feature_list):
        missing = [f for f in FEATURE_NAMES if f not in features]
        if missing:
            errors[i] = f"Missing features: {missing}"
        else:
            valid_rows.append([features[f] for f in FEATURE_NAMES])
            valid_indices.append(i)

    results: List[Optional[Tuple[float, str, Optional[Dict[str, float]]]]] = [None] * len(feature_list)

    if valid_rows:
        X = np.array(valid_rows, dtype=np.float64)
        probas = _model_pipeline.predict_proba(X)[:, 1]

        for idx, (row_idx, proba) in enumerate(zip(valid_indices, probas)):
            proba = float(np.clip(proba, 0.0, 1.0))
            if proba < threshold_low:
                risk = "low"
            elif proba < threshold_high:
                risk = "medium"
            else:
                risk = "high"
            results[row_idx] = (proba, risk, None)  # SHAP omitted for batch efficiency

    for i, err in errors.items():
        results[i] = (-1.0, "error", {"error": err})

    return results
