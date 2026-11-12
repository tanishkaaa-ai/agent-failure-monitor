"""
Unit Tests for Phase 5 ML Failure Prediction Component.
Validates model loading, prediction function, feature ordering,
and probability ranges.
"""

import os
import numpy as np
import pytest
from src.models.predictor import AgentFailurePredictor
from src.signals.engine import RuntimeSignalsEngine, SignalVector

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models_saved", "logistic_regression.joblib")


def test_model_artifact_exists():
    assert os.path.exists(MODEL_PATH), f"Model file must exist at {MODEL_PATH}"


def test_predictor_initialization():
    predictor = AgentFailurePredictor()
    assert predictor.model is not None
    assert len(predictor.feature_names) == 24
    assert predictor.feature_names == SignalVector.feature_names()


def test_predict_risk_from_signal_vector():
    predictor = AgentFailurePredictor()
    engine = RuntimeSignalsEngine(task_prompt="Calculate derivative")

    # Step 0
    sig0 = engine.update({"role": "user", "thought": "", "action": "", "content": "Calculate derivative of x^2"})
    prob0 = predictor.predict_risk(sig0)
    assert isinstance(prob0, float)
    assert 0.0 <= prob0 <= 1.0

    # Step 1: Normal agent action
    sig1 = engine.update({"role": "MathSolver", "thought": "Differentiating x^2", "action": "", "content": "2x"})
    prob1 = predictor.predict_risk(sig1)
    assert isinstance(prob1, float)
    assert 0.0 <= prob1 <= 1.0


def test_predict_risk_from_dict():
    predictor = AgentFailurePredictor()
    feature_dict = {f: 0.0 for f in predictor.feature_names}
    feature_dict["tool_failure_rate"] = 1.0
    feature_dict["consecutive_tool_failures"] = 3.0
    feature_dict["active_retry_count"] = 2.0

    prob = predictor.predict_risk(feature_dict)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0
    # High failures and retries should yield elevated failure probability
    assert prob > 0.40, f"Expected elevated probability for failing signals, got {prob}"


def test_predict_risk_from_numpy():
    predictor = AgentFailurePredictor()
    vec = np.zeros(24, dtype=np.float32)
    prob = predictor.predict_risk(vec)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_feature_order_mismatch_detection():
    predictor = AgentFailurePredictor()
    # Wrong vector length
    short_vec = np.zeros(10, dtype=np.float32)
    with pytest.raises(ValueError):
        predictor.predict_risk(short_vec)

