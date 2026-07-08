"""
Central configuration for MerchAudit's business rules and risk engine.

Keeping thresholds here (instead of hardcoded in logic) means compliance
teams can tune policy without touching the rule implementation.
"""

# --- Layer 1: Business Logic thresholds ---

# Chargeback velocity: dispute rate (%) within the rolling window that triggers a flag
CHARGEBACK_RATE_THRESHOLD_PCT = 1.0          # industry card-network danger zone starts ~1%
CHARGEBACK_LOOKBACK_DAYS = 30

# Countries considered restricted / heavily sanctioned for this exercise.
# (Illustrative list — a production system would sync this against
# OFAC/UN/EU sanctions lists on a schedule.)
RESTRICTED_COUNTRIES = {
    "IR", "KP", "SY", "CU", "RU", "BY", "MM", "VE",
}

# Tax ID validation: expected length per country (simplified demo rule set)
TAX_ID_FORMATS = {
    "US": {"length": 9, "name": "EIN"},        # e.g. XX-XXXXXXX
    "IN": {"length": 15, "name": "GSTIN"},
    "GB": {"length": 9, "name": "VAT"},
    "default": {"length": 9, "name": "GENERIC"},
}

# --- Layer 2: Isolation Forest configuration ---

ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,
    "contamination": 0.05,   # assume ~5% of merchants are structurally anomalous
    "random_state": 42,
}

ANOMALY_FEATURES = [
    "declared_monthly_revenue",
    "actual_avg_transaction_amount",
    "actual_max_transaction_amount",
    "transaction_count_30d",
    "pct_international_transactions",
    "pct_night_transactions",      # transactions between 12am-5am local time
    "revenue_burst_ratio",         # max single-day volume / declared monthly revenue
]

# --- Combined risk scoring weights ---

# Final score = 0-100. Layer 1 failures short-circuit to REJECT/FLAG (score = 100).
# When Layer 1 passes, the anomaly score (0-1 from Isolation Forest) is rescaled to 0-100.
RISK_SCORE_ANOMALY_WEIGHT = 100

# Score bands for the analyst-facing report
RISK_BANDS = [
    (0, 30, "LOW"),
    (30, 60, "MEDIUM"),
    (60, 85, "HIGH"),
    (85, 101, "CRITICAL"),
]
