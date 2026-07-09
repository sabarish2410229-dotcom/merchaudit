"""
Backend API tests.

Uses a temporary SQLite DB and a freshly-trained tiny model so tests are
fully isolated from any real merchaudit.db / models/current/ on disk.
"""

import os
import tempfile

import pytest


@pytest.fixture(scope="module")
def client():
    # Point the app at an isolated temp DB and temp model BEFORE importing it,
    # since database.py and main.py read these env vars at import time.
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    model_dir = os.path.join(tmp_dir, "model")

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["MODEL_DIR"] = model_dir
    os.environ["JWT_SECRET"] = "test-secret"

    from data.generate_synthetic_data import generate_dataset
    from merchaudit.anomaly_engine import AnomalyEngine

    df = generate_dataset(n=200, seed=99)
    engine = AnomalyEngine()
    engine.fit(df, dataset_version="test-dataset")
    engine.save(model_dir)

    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_token(client):
    client.post("/auth/register", json={
        "email": "test-analyst@merchaudit.dev",
        "password": "testpass123",
        "role": "analyst",
    })
    resp = client.post("/auth/login", data={
        "username": "test-analyst@merchaudit.dev",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["model_loaded"] is True


def test_register_and_login(client):
    resp = client.post("/auth/register", json={
        "email": "someone@merchaudit.dev",
        "password": "password123",
        "role": "analyst",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "someone@merchaudit.dev"

    resp = client.post("/auth/login", data={
        "username": "someone@merchaudit.dev",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_fails(client):
    client.post("/auth/register", json={
        "email": "wrongpass@merchaudit.dev", "password": "correctpass123", "role": "analyst",
    })
    resp = client.post("/auth/login", data={
        "username": "wrongpass@merchaudit.dev", "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client):
    resp = client.get("/reports")
    assert resp.status_code == 401


MERCHANT_PAYLOAD_TEMPLATE = {
    "business_name_type": "online bookstore",
    "country_code": "US",
    "tax_id": "12-3456789",
    "declared_monthly_revenue": 2000,
    "actual_avg_transaction_amount": 500,
    "actual_max_transaction_amount": 55000,
    "transaction_count_30d": 300,
    "pct_international_transactions": 88,
    "pct_night_transactions": 70,
    "revenue_burst_ratio": 27.5,
    "chargeback_rate_pct": 0.4,
}


def test_create_merchant_and_run_audit_flags_launderer(client, auth_token):
    payload = {**MERCHANT_PAYLOAD_TEMPLATE, "merchant_id": "TEST-LAUNDERER-01"}
    resp = client.post("/merchants", json=payload, headers=auth_headers(auth_token))
    assert resp.status_code == 201

    resp = client.post("/merchants/TEST-LAUNDERER-01/audit", headers=auth_headers(auth_token))
    assert resp.status_code == 201
    report = resp.json()
    # This profile is deliberately shaped like the transaction-laundering pattern:
    # should score meaningfully anomalous, not collapse to 0.
    assert report["anomaly_score"] > 0.5
    assert report["decision"] in ("MANUAL REVIEW", "REJECT")


def test_restricted_country_merchant_is_rejected(client, auth_token):
    payload = {
        **MERCHANT_PAYLOAD_TEMPLATE,
        "merchant_id": "TEST-SANCTIONED-01",
        "country_code": "KP",
        "declared_monthly_revenue": 5000,
        "actual_max_transaction_amount": 1000,
        "transaction_count_30d": 40,
        "pct_international_transactions": 10,
        "pct_night_transactions": 5,
        "revenue_burst_ratio": 0.5,
    }
    resp = client.post("/merchants", json=payload, headers=auth_headers(auth_token))
    assert resp.status_code == 201

    resp = client.post("/merchants/TEST-SANCTIONED-01/audit", headers=auth_headers(auth_token))
    assert resp.status_code == 201
    report = resp.json()
    assert report["decision"] == "REJECT"
    assert report["risk_score"] == 100.0
    assert any(v["rule"] == "Compliance Geofencing" for v in report["rule_violations"])


def test_duplicate_merchant_id_rejected(client, auth_token):
    payload = {**MERCHANT_PAYLOAD_TEMPLATE, "merchant_id": "TEST-DUP-01"}
    resp1 = client.post("/merchants", json=payload, headers=auth_headers(auth_token))
    assert resp1.status_code == 201
    resp2 = client.post("/merchants", json=payload, headers=auth_headers(auth_token))
    assert resp2.status_code == 400


def test_list_reports_pagination_and_filter(client, auth_token):
    resp = client.get("/reports?page=1&page_size=5", headers=auth_headers(auth_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert body["total"] >= 2

    resp = client.get("/reports?decision=REJECT", headers=auth_headers(auth_token))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["decision"] == "REJECT"


def test_get_reports_for_unknown_merchant_404s(client, auth_token):
    resp = client.get("/reports/NO-SUCH-MERCHANT", headers=auth_headers(auth_token))
    assert resp.status_code == 404
