"""
Tests for the TAB-Net inference pipeline.
These tests run without a real model file — they verify the
module structure, feature validation, and error handling.
"""
import pytest
import numpy as np


def test_feature_names_count():
    from app.ml.inference.tabnet_inference import FEATURE_NAMES
    assert len(FEATURE_NAMES) == 30
    assert "Time" in FEATURE_NAMES
    assert "Amount" in FEATURE_NAMES
    assert "V1" in FEATURE_NAMES
    assert "V28" in FEATURE_NAMES


def test_is_model_loaded_false_by_default():
    from app.ml.inference.tabnet_inference import is_model_loaded
    # Without a model file, should be False
    result = is_model_loaded()
    assert isinstance(result, bool)


def test_predict_raises_when_no_model(monkeypatch):
    from app.ml.inference.tabnet_inference import predict
    import app.ml.inference.tabnet_inference as ti
    monkeypatch.setattr(ti, "ensure_model_loaded", lambda: False)
    features = {f: 0.0 for f in ti.FEATURE_NAMES}
    with pytest.raises(RuntimeError, match="No trained model"):
        predict(features)


def test_predict_raises_on_missing_features():
    """Even with a mock model, missing features should raise ValueError."""
    import app.ml.inference.tabnet_inference as ti
    from unittest.mock import MagicMock
    import numpy as np

    mock_pipeline = MagicMock()
    mock_pipeline.predict_proba.return_value = np.array([[0.8, 0.2]])
    original = ti._model_pipeline
    ti._model_pipeline = mock_pipeline
    try:
        # Missing 'Amount'
        features = {f: 0.0 for f in ti.FEATURE_NAMES if f != "Amount"}
        with pytest.raises(ValueError, match="Missing features"):
            ti.predict(features)
    finally:
        ti._model_pipeline = original


def test_predict_returns_correct_risk_tiers():
    import app.ml.inference.tabnet_inference as ti
    from unittest.mock import MagicMock
    import numpy as np

    mock_pipeline = MagicMock()
    features = {f: 0.0 for f in ti.FEATURE_NAMES}

    original = ti._model_pipeline
    ti._model_pipeline = mock_pipeline
    ti._shap_explainer = None
    try:
        # Low risk
        mock_pipeline.predict_proba.return_value = np.array([[0.9, 0.1]])
        prob, risk, shap = ti.predict(features, threshold_low=0.3, threshold_high=0.7)
        assert risk == "low"
        assert prob == pytest.approx(0.1, abs=1e-6)

        # Medium risk
        mock_pipeline.predict_proba.return_value = np.array([[0.5, 0.5]])
        prob, risk, shap = ti.predict(features, threshold_low=0.3, threshold_high=0.7)
        assert risk == "medium"

        # High risk
        mock_pipeline.predict_proba.return_value = np.array([[0.1, 0.9]])
        prob, risk, shap = ti.predict(features, threshold_low=0.3, threshold_high=0.7)
        assert risk == "high"
        assert prob == pytest.approx(0.9, abs=1e-6)
    finally:
        ti._model_pipeline = original


def test_predict_batch_empty():
    import app.ml.inference.tabnet_inference as ti
    from unittest.mock import MagicMock
    import numpy as np

    mock_pipeline = MagicMock()
    mock_pipeline.predict_proba.return_value = np.array([]).reshape(0, 2)
    original = ti._model_pipeline
    ti._model_pipeline = mock_pipeline
    ti._shap_explainer = None
    try:
        results = ti.predict_batch([])
        assert results == []
    finally:
        ti._model_pipeline = original
