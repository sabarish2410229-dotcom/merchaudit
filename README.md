# MerchAudit

**Automated merchant risk auditing for payment processors and acquiring banks**

MerchAudit is a two-layer gatekeeper that screens merchant applications and live transaction behavior before onboarding, catching both outright policy violations and subtler patterns consistent with **transaction laundering** — where a merchant registers as one type of business and quietly uses the account to process high-risk or illegal transactions instead.

---

## The Problem

When a merchant applies for a payment-processing account, some lie on their application. A business might onboard as a harmless "online bookstore" and then pivot to processing transactions it was never approved for. Catch it too late, and the processor eats regulatory fines, fraud losses, and chargebacks. Manually reviewing every application doesn't scale, and naive rule lists miss anything that doesn't match a known pattern.

MerchAudit addresses both failure modes with one pipeline: hard compliance rules for the non-negotiables, and an unsupervised anomaly model for the patterns rules can't anticipate.

---

## Key Differentiators

### 1. Two-Layer Defense, Not a Single Score
Most fraud-screening demos train one model and call it done. MerchAudit deliberately separates **deterministic compliance logic** from **statistical anomaly detection**, because they answer different questions. A sanctions-list match isn't a "maybe" — it's a hard reject, and a model shouldn't get a vote. Everything past that gate is inherently fuzzier, which is where the ML layer earns its keep.

- **Layer 1 — Business Rules (Compliance Gatekeeper):** Chargeback velocity caps, restricted-country geofencing, and tax ID format/checksum validation. Deterministic, auditable, zero-tolerance.
- **Layer 2 — Isolation Forest (Anomaly Engine):** Runs only on merchants that already passed Layer 1. Isolates merchants whose transaction *structure* doesn't fit the population — e.g. a merchant declaring $2k/month suddenly processing a $50k international burst at 3 AM — without needing any "fraud/not fraud" labels.

### 2. Unsupervised by Design
Labeled fraud data goes stale fast — bad actors adapt faster than labels get collected. Isolation Forest needs no fraud labels at all; it flags merchants whose feature profile structurally doesn't fit the rest of the population, so detection keeps working as fraud patterns shift, not just against patterns seen at training time.

### 3. Explainable, Analyst-Facing Output
Every merchant gets a **0–100 risk score**, a risk band (LOW/MEDIUM/HIGH/CRITICAL), a decision (APPROVE / MANUAL REVIEW / REJECT), and — critically — a plain-language breakdown of *which* rule fired or how anomalous the transaction profile looked. Nothing is a black-box number an analyst has to trust blindly.

---

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

**Pattern:** Merchant record → Layer 1 rule checks → (if passed) Layer 2 Isolation Forest scoring → combined risk report → Streamlit dashboard for analyst review.

---

## Tech Stack

**Core:** Python, pandas, NumPy, scikit-learn (Isolation Forest, StandardScaler)
**Dashboard:** Streamlit, Plotly
**Testing:** pytest
**Deployment:** Railway (Nixpacks, Procfile)

---

## Core Features

| Module | Description |
|---|---|
| **Business Rules Engine** | Chargeback velocity caps, restricted-country geofencing, tax ID format/checksum validation — all configurable in one place |
| **Anomaly Engine** | Isolation Forest trained on the merchant population's transaction features; returns a normalized 0–1 anomaly score per merchant |
| **Risk Engine** | Combines both layers into a single 0–100 risk score, risk band, and APPROVE/MANUAL REVIEW/REJECT decision |
| **Synthetic Data Generator** | Produces realistic mixed populations (normal / rule-violating / transaction-laundering merchants) for development, testing, and demoing |
| **Analyst Dashboard** | Streamlit app with decision breakdown charts, risk score distribution, filterable case table, and per-merchant drill-down |

---

## Local Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# generate a full synthetic dataset (a small sample_merchants.csv is already bundled)
python data/generate_synthetic_data.py --n 500 --out data/merchants.csv

# run tests
pytest tests/ -v

# launch the dashboard
streamlit run app.py
```

The dashboard defaults to the bundled `data/sample_merchants.csv`. Use the sidebar uploader to score a different CSV — it needs the same columns (see `merchaudit/config.py` → `ANOMALY_FEATURES`, plus `merchant_id`, `country_code`, `tax_id`, `chargeback_rate_pct`).

## Known Limitations & Future Work

This project was scoped as a demonstration of the two-layer architecture, not a production compliance system. Honest gaps, in order of what a production version would need next:

- **Synthetic data only** — both the rule thresholds and the Isolation Forest are tuned against generated data with realistic but artificial patterns, not real transaction history. Real deployment would need calibration against actual fulfillment/fraud outcomes.
- **Static sanctions list** — `RESTRICTED_COUNTRIES` is a small illustrative set. A production system would sync against live OFAC/UN/EU sanctions lists on a schedule, not a hardcoded set.
- **No entity-linking / graph layer** — Isolation Forest scores each merchant independently. It can't see that several "unrelated" merchants share a bank account, device, or IP — a common real-world laundering pattern. A network/graph analysis layer is the natural next step.
- **No persistent database** — merchant records and risk reports are processed in-memory per session; there's no audit-trail storage or historical case tracking across runs.
- **No authentication/RBAC** — the dashboard has no login or role separation between analysts and admins.
- **Simplified tax ID validation** — the checksum rule is an illustrative stand-in, not a real per-country tax authority validator (e.g. actual GSTIN/EIN/VAT algorithms).

---

## Project Structure

```
merchaudit/
├── merchaudit/             # core package
│   ├── config.py           # thresholds & rule configuration
│   ├── business_rules.py   # Layer 1
│   ├── anomaly_engine.py   # Layer 2 (Isolation Forest)
│   └── risk_engine.py      # combines both layers into a final score/report
├── data/
│   ├── generate_synthetic_data.py
│   └── sample_merchants.csv
├── tests/
│   ├── test_business_rules.py
│   └── test_risk_engine.py
├── app.py                  # Streamlit analyst dashboard
├── Procfile / railway.json # Railway deployment config
├── requirements.txt
└── README.md
```
