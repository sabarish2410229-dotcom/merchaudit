# MerchAudit

**Automated merchant risk auditing for payment processors and acquiring banks.**

MerchAudit flags high-risk merchant applications and live transaction activity *before*
they can be used for transaction laundering, fraud, or sanctions evasion — combining
hard compliance rules with an unsupervised anomaly-detection model.

## The Problem

When a merchant applies for a payment-processing account, some lie on their application.
A business might onboard as a harmless "online bookstore" and then quietly pivot to
processing high-risk or illegal transactions (**transaction laundering**). Catch it too
late, and the processor eats regulatory fines, fraud losses, and chargebacks.

## Architecture

```
[Incoming Merchant Application & Live Data]
                 │
                 ▼
   ┌──────────────────────────────┐
   │   Layer 1: Business Logic    │ ──(Fails Rules?)──> [Instant REJECT / FLAG]
   └──────────────────────────────┘
                 │ (Passes Rules)
                 ▼
   ┌──────────────────────────────┐
   │   Layer 2: AI Anomaly Engine │ ──(High Score?)──> [Flag for Manual Audit]
   └──────────────────────────────┘
                 │ (Low Risk Score)
                 ▼
         [APPROVED ONBOARDING]
```

### Layer 1 — Business Logic (Compliance Gatekeeper)
Deterministic, auditable rules that run before any ML is involved:
- **Chargeback Velocity Caps** — dispute-rate spikes over a threshold in a rolling window
- **Compliance Geofencing** — transactions from restricted/sanctioned countries
- **Tax ID Validation** — checksum/format validation of declared tax & registration numbers

### Layer 2 — AI Anomaly Engine (Isolation Forest)
Fraud patterns shift constantly, so labeled "fraud/not fraud" data goes stale fast.
Instead of supervised learning, MerchAudit uses an **Isolation Forest** — it isolates
data points that structurally don't fit (e.g. a merchant declaring $2k/month in revenue
suddenly processing a $50k burst of international card transactions at 3 AM) and assigns
them a high anomaly score, with no labels required.

### Output
Both layers feed a combined **0–100 credit-risk score** and a report showing exactly
which rules fired and what the anomaly score was, so a human analyst can make the final
call fast.

## Project Structure

```
merchaudit/
├── merchaudit/            # core package
│   ├── config.py          # thresholds & rule configuration
│   ├── business_rules.py  # Layer 1
│   ├── anomaly_engine.py  # Layer 2 (Isolation Forest)
│   └── risk_engine.py     # combines both layers into a final score/report
├── data/
│   └── generate_synthetic_data.py
├── tests/
├── app.py                 # Streamlit analyst dashboard
├── requirements.txt
└── README.md
```

## Setup & Local Run

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# generate a full synthetic dataset (already includes a small sample_merchants.csv)
python data/generate_synthetic_data.py --n 500 --out data/merchants.csv

# run tests
pytest tests/ -v

# launch the dashboard
streamlit run app.py
```

The dashboard defaults to the bundled `data/sample_merchants.csv`. Use the sidebar
uploader to score a different CSV — it just needs the same columns (see
`merchaudit/config.py` → `ANOMALY_FEATURES` plus `country_code`, `tax_id`,
`chargeback_rate_pct`, `merchant_id`).

## Status

🚧 Under active development — see commit history for progress.
