"""
Lightweight Real-Time Agent Failure Risk Predictor.
Accepts runtime signals from RuntimeSignalsEngine and estimates
the probability of future agent failure using the trained classifier.

Strict constraint: Only estimates failure-risk probability.
Does NOT select interventions or generate natural-language explanations.
"""

import json
import os
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from src.signals.engine import SignalVector

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DEFAULT_MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "models_saved",
    "logistic_regression.joblib"
)
DEFAULT_METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "models_saved",
    "model_metadata.json"
)


class AgentFailurePredictor:
    """
    Inference wrapper for the trained lightweight agent failure prediction model.
    Guarantees strict feature order alignment between training and inference.
    """

    def __init__(self, model_path: Optional[str] = None, metadata_path: Optional[str] = None):
        self.model_path = os.path.abspath(model_path or DEFAULT_MODEL_PATH)
        self.metadata_path = os.path.abspath(metadata_path or DEFAULT_METADATA_PATH)

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Trained model not found at {self.model_path}. "
                "Please run `python src/models/train.py` first."
            )

        self.model = joblib.load(self.model_path)

        # Load canonical feature ordering from metadata if available, else from SignalVector
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                meta = json.load(f)
                self.feature_names: List[str] = meta.get("feature_names", SignalVector.feature_names())
        else:
            self.feature_names = SignalVector.feature_names()

    def predict_risk(self, signals: Union[SignalVector, Dict[str, Any], np.ndarray]) -> float:
        """
        Estimate failure risk probability for a single execution step.

        Parameters
        ----------
        signals : SignalVector | dict | np.ndarray
            The runtime signal vector produced by the Signals Engine at current step t.

        Returns
        -------
        float
            Failure-risk probability in range [0.0, 1.0].
            - p < 0.30: Low risk (Trajectory currently healthy).
            - 0.30 <= p < 0.60: Moderate/Uncertain risk (Early warning / candidate for LLM Judge verification).
            - p >= 0.60: High risk (Decisive failure imminent or actively unfolding).
        """
        if isinstance(signals, SignalVector):
            feat_dict = signals.to_features_dict()
            vector = [float(feat_dict[k]) for k in self.feature_names]
        elif isinstance(signals, dict):
            vector = [float(signals[k]) for k in self.feature_names]
        elif isinstance(signals, (np.ndarray, list)):
            if len(signals) != len(self.feature_names):
                raise ValueError(
                    f"Expected vector of length {len(self.feature_names)}, got {len(signals)}"
                )
            vector = [float(x) for x in signals]
        else:
            raise TypeError(f"Unsupported signal type: {type(signals)}")

        df = pd.DataFrame([vector], columns=self.feature_names)
        proba = float(self.model.predict_proba(df)[0, 1])
        return round(proba, 4)

    def predict_batch(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Estimate failure risk for a batch of step feature records.
        """
        aligned_df = features_df[self.feature_names]
        probas = self.model.predict_proba(aligned_df)[:, 1]
        return probas.astype(np.float32)
