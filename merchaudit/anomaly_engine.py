"""
Layer 2 — The AI Anomaly Engine (Isolation Forest)

Runs only on merchants that already passed Layer 1's business rules.
Unsupervised by design: fraud patterns shift daily, so we don't rely on
stale "fraud/not fraud" labels. Instead we isolate merchants whose feature
profile structurally doesn't fit the rest of the population.

Supports train-once/infer-many usage via save()/load(): a training job
(see backend/ml/train_model.py) fits the model once and persists it with
joblib; production code paths only ever call load() + score(), never fit().
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from . import config


class AnomalyEngine:
    def __init__(self, feature_columns: list | None = None, **iso_forest_kwargs):
        self.feature_columns = feature_columns or config.ANOMALY_FEATURES
        params = {**config.ISOLATION_FOREST_PARAMS, **iso_forest_kwargs}
        self.model = IsolationForest(**params)
        self.scaler = StandardScaler()
        self._fitted = False
        self.metadata: dict = {}

    def _feature_matrix(self, df: pd.DataFrame) -> np.ndarray:
        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")
        return df[self.feature_columns].to_numpy(dtype=float)

    def fit(self, df: pd.DataFrame, dataset_version: str = "unspecified") -> "AnomalyEngine":
        """Fit the Isolation Forest on a population of merchants (normal + mixed is fine)."""
        X = self._feature_matrix(df)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True

        train_raw = self.model.decision_function(X_scaled)
        train_inverted = -train_raw

        self.metadata = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "n_training_samples": len(df),
            "dataset_version": dataset_version,
            "feature_columns": self.feature_columns,
            "feature_version": "v1",
            "sklearn_version": sklearn.__version__,
            "model_params": self.model.get_params(),
            "train_score_min": float(train_inverted.min()),
            "train_score_max": float(train_inverted.max()),
        }
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return a copy of df with two added columns:
          - anomaly_score_raw: sklearn's decision_function output (higher = more normal)
          - anomaly_score: rescaled to 0-1 using the TRAINING-time score range, where
            1.0 = most anomalous.
        """
        if not self._fitted:
            raise RuntimeError("AnomalyEngine must be fit() before scoring.")

        X = self._feature_matrix(df)
        X_scaled = self.scaler.transform(X)

        raw = self.model.decision_function(X_scaled)
        inverted = -raw

        lo = self.metadata.get("train_score_min")
        hi = self.metadata.get("train_score_max")
        if lo is None or hi is None:
            lo, hi = inverted.min(), inverted.max()

        if hi > lo:
            normalized = (inverted - lo) / (hi - lo)
            normalized = np.clip(normalized, 0.0, 1.0)
        else:
            normalized = np.zeros_like(inverted)

        out = df.copy()
        out["anomaly_score_raw"] = raw
        out["anomaly_score"] = normalized
        out["is_anomalous"] = self.model.predict(X_scaled) == -1
        return out

    def fit_score(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.score(df)

    def save(self, model_dir: str) -> None:
        """Persist the fitted model, scaler, and metadata to disk (train-once workflow)."""
        if not self._fitted:
            raise RuntimeError("Cannot save an unfitted AnomalyEngine.")
        out = Path(model_dir)
        out.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, out / "isolation_forest.joblib")
        joblib.dump(self.scaler, out / "scaler.joblib")
        with open(out / "metadata.json", "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)

    @classmethod
    def load(cls, model_dir: str) -> "AnomalyEngine":
        """Load a previously-trained model for inference-only use (no fit() call)."""
        src = Path(model_dir)
        engine = cls()
        engine.model = joblib.load(src / "isolation_forest.joblib")
        engine.scaler = joblib.load(src / "scaler.joblib")
        with open(src / "metadata.json") as f:
            engine.metadata = json.load(f)
        engine.feature_columns = engine.metadata.get("feature_columns", engine.feature_columns)
        engine._fitted = True
        return engine

    @property
    def model_version(self) -> str:
        return self.metadata.get("dataset_version", "unversioned")
