import pandas as pd

from merchaudit.anomaly_engine import AnomalyEngine
from merchaudit.risk_engine import build_risk_reports, reports_to_dataframe
from data.generate_synthetic_data import generate_dataset


def test_anomaly_engine_fit_score_shapes():
    df = generate_dataset(n=100, seed=1)
    engine = AnomalyEngine()
    scored = engine.fit_score(df)

    assert "anomaly_score" in scored.columns
    assert scored["anomaly_score"].between(0, 1).all()
    assert len(scored) == len(df)


def test_anomaly_engine_catches_launderers():
    df = generate_dataset(n=300, seed=2)
    engine = AnomalyEngine()
    scored = engine.fit_score(df)

    launderers = scored[scored["profile_label"] == "transaction_launderer"]
    # Launderers should score as meaningfully more anomalous than normal merchants on average
    normal_avg = scored[scored["profile_label"] == "normal"]["anomaly_score"].mean()
    launderer_avg = launderers["anomaly_score"].mean()
    assert launderer_avg > normal_avg


def test_risk_engine_end_to_end():
    df = generate_dataset(n=200, seed=3)
    engine = AnomalyEngine()
    scored = engine.fit_score(df)

    reports = build_risk_reports(df, scored)
    report_df = reports_to_dataframe(reports)

    assert set(report_df["decision"].unique()) <= {"APPROVE", "MANUAL REVIEW", "REJECT"}
    assert (report_df["risk_score"] >= 0).all() and (report_df["risk_score"] <= 100).all()

    # Anyone with a rule REJECT must have risk_score == 100
    rejects = report_df[report_df["decision"] == "REJECT"]
    assert (rejects["risk_score"] == 100.0).all()
