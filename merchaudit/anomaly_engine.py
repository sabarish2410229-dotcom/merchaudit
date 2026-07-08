"""
Layer 2 — The AI Anomaly Engine (Isolation Forest)

Runs only on merchants that already passed Layer 1's business rules.
Unsupervised by design: fraud patterns shift daily, so we don't rely on
stale "fraud/not fraud" labels. Instead we isolate merchants whose feature
profile structurally doesn't fit the rest of the population.
"""

import numpy as np
import pandas as pd
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

    def _feature_matrix(self, df: pd.DataFrame) -> np.ndarray:
        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")
        return df[self.feature_columns].to_numpy(dtype=float)

    def fit(self, df: pd.DataFrame) -> "AnomalyEngine":
        """Fit the Isolation Forest on a population of merchants (normal + mixed is fine)."""
        X = self._feature_matrix(df)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return a copy of df with two added columns:
          - anomaly_score_raw: sklearn's decision_function output (higher = more normal)
          - anomaly_score: rescaled to 0-1, where 1 = most anomalous
        """
        if not self._fitted:
            raise RuntimeError("AnomalyEngine must be fit() before scoring.")

        X = self._feature_matrix(df)
        X_scaled = self.scaler.transform(X)

        raw = self.model.decision_function(X_scaled)  # higher = more normal
        # Flip and min-max scale to 0-1 so 1.0 = most anomalous
        inverted = -raw
        lo, hi = inverted.min(), inverted.max()
        normalized = (inverted - lo) / (hi - lo) if hi > lo else np.zeros_like(inverted)

        out = df.copy()
        out["anomaly_score_raw"] = raw
        out["anomaly_score"] = normalized
        out["is_anomalous"] = self.model.predict(X_scaled) == -1  # -1 = outlier
        return out

    def fit_score(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.score(df)
