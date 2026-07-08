"""
Combines Layer 1 (business rules) and Layer 2 (Isolation Forest anomaly score)
into one final risk report per merchant.

Scoring policy:
  - Any Layer 1 REJECT violation -> risk_score = 100, decision = REJECT
  - Any Layer 1 FLAG-only violation (no REJECT) -> risk_score = max(70, anomaly-based score)
  - No Layer 1 violations -> risk_score purely driven by the anomaly score (0-100)

Decision bands come from config.RISK_BANDS.
"""

from dataclasses import dataclass, field

import pandas as pd

from . import config
from .business_rules import run_business_rules


@dataclass
class MerchantRiskReport:
    merchant_id: str
    risk_score: float
    risk_band: str
    decision: str
    rule_violations: list = field(default_factory=list)
    anomaly_score: float | None = None

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "risk_score": round(self.risk_score, 2),
            "risk_band": self.risk_band,
            "decision": self.decision,
            "rule_violations": "; ".join(
                f"[{v.severity}] {v.rule}: {v.reason}" for v in self.rule_violations
            ) or "None",
            "anomaly_score": round(self.anomaly_score, 4) if self.anomaly_score is not None else None,
        }


def _band_for_score(score: float) -> str:
    for lo, hi, label in config.RISK_BANDS:
        if lo <= score < hi:
            return label
    return config.RISK_BANDS[-1][2]


def build_risk_reports(df: pd.DataFrame, scored_df: pd.DataFrame | None = None) -> list[MerchantRiskReport]:
    """
    df: raw merchant records (must include merchant_id and business-rule fields)
    scored_df: same rows, already run through AnomalyEngine.score() (has anomaly_score col).
               If None, only Layer 1 is evaluated (useful for quick rule-only checks).
    """
    reports = []
    anomaly_lookup = {}
    if scored_df is not None:
        anomaly_lookup = dict(zip(scored_df["merchant_id"], scored_df["anomaly_score"]))

    for _, row in df.iterrows():
        merchant = row.to_dict()
        rule_result = run_business_rules(merchant)

        has_reject = any(v.severity == "REJECT" for v in rule_result.violations)
        has_flag = any(v.severity == "FLAG" for v in rule_result.violations)
        anomaly_score = anomaly_lookup.get(merchant["merchant_id"])

        if has_reject:
            risk_score = 100.0
            decision = "REJECT"
        elif has_flag:
            anomaly_component = (anomaly_score or 0.0) * config.RISK_SCORE_ANOMALY_WEIGHT
            risk_score = max(70.0, anomaly_component)
            decision = "MANUAL REVIEW"
        else:
            anomaly_component = (anomaly_score or 0.0) * config.RISK_SCORE_ANOMALY_WEIGHT
            risk_score = anomaly_component
            decision = "MANUAL REVIEW" if risk_score >= 60 else "APPROVE"

        reports.append(
            MerchantRiskReport(
                merchant_id=merchant["merchant_id"],
                risk_score=risk_score,
                risk_band=_band_for_score(risk_score),
                decision=decision,
                rule_violations=rule_result.violations,
                anomaly_score=anomaly_score,
            )
        )
    return reports


def reports_to_dataframe(reports: list[MerchantRiskReport]) -> pd.DataFrame:
    return pd.DataFrame([r.to_dict() for r in reports])
