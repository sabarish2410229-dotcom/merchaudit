"""
MerchAudit — Analyst Dashboard (Streamlit)

Upload merchant data (or use the bundled sample), run it through both
defense layers, and review the resulting risk reports and case detail.

Uses the same train-once/infer-many model as the API (see
backend/ml/train_model.py) so scores are consistent across both surfaces,
instead of silently refitting a brand-new model on every dashboard run.
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from merchaudit.anomaly_engine import AnomalyEngine
from merchaudit.risk_engine import build_risk_reports, reports_to_dataframe

st.set_page_config(page_title="MerchAudit", page_icon="🛡️", layout="wide")

MODEL_DIR = os.getenv("MODEL_DIR", "models/current")

BAND_COLORS = {
    "LOW": "#2E7D32",
    "MEDIUM": "#F9A825",
    "HIGH": "#EF6C00",
    "CRITICAL": "#C62828",
}


@st.cache_data(show_spinner=False)
def load_default_data() -> pd.DataFrame:
    return pd.read_csv("data/sample_merchants.csv", dtype={"tax_id": str})


@st.cache_resource(show_spinner=False)
def get_engine() -> tuple[AnomalyEngine | None, str]:
    """
    Load the persisted train-once model. Returns (engine, status_message).
    Falls back to fitting on the currently-loaded data only if no trained
    model exists yet, so the dashboard still works before you've run
    backend/ml/train_model.py, but prefers the persisted model whenever
    it's available (matches production behavior, not a fresh fit each run).
    """
    try:
        engine = AnomalyEngine.load(MODEL_DIR)
        return engine, f"Using trained model (version: {engine.model_version})"
    except FileNotFoundError:
        return None, "No trained model found — run `python backend/ml/train_model.py` for consistent scoring."


def run_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    engine, _ = get_engine()
    if engine is None:
        # Dev-mode fallback only: fits on whatever is currently loaded.
        # Scores from this path are NOT comparable across runs/uploads.
        engine = AnomalyEngine()
        scored = engine.fit_score(df)
    else:
        scored = engine.score(df)
    reports = build_risk_reports(df, scored)
    report_df = reports_to_dataframe(reports)
    return df.merge(report_df, on="merchant_id")


def band_badge(band: str) -> str:
    color = BAND_COLORS.get(band, "#666")
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:0.8rem;font-weight:600;">{band}</span>'


# --- Sidebar ---
st.sidebar.title("🛡️ MerchAudit")
st.sidebar.caption("Two-layer merchant risk auditing")

uploaded = st.sidebar.file_uploader("Upload merchant CSV", type=["csv"])
if uploaded is not None:
    df_raw = pd.read_csv(uploaded, dtype={"tax_id": str})
    st.sidebar.success(f"Loaded {len(df_raw)} merchants from upload.")
else:
    df_raw = load_default_data()
    st.sidebar.info(f"Using bundled sample data ({len(df_raw)} merchants).")

st.sidebar.markdown("---")
_, model_status = get_engine()
st.sidebar.caption(f"🤖 {model_status}")
st.sidebar.markdown(
    "**Layer 1** — Chargeback velocity, geofencing, tax ID validation\n\n"
    "**Layer 2** — Isolation Forest anomaly detection"
)

# --- Run pipeline ---
with st.spinner("Running business rules + anomaly engine..."):
    result_df = run_pipeline(df_raw)

# --- Header ---
st.title("MerchAudit — Merchant Risk Dashboard")
st.caption("Automated gatekeeper for merchant onboarding & transaction monitoring")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Merchants Audited", len(result_df))
col2.metric("Approved", int((result_df["decision"] == "APPROVE").sum()))
col3.metric("Manual Review", int((result_df["decision"] == "MANUAL REVIEW").sum()))
col4.metric("Rejected", int((result_df["decision"] == "REJECT").sum()))

st.markdown("---")

# --- Charts ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    decision_counts = result_df["decision"].value_counts().reset_index()
    decision_counts.columns = ["decision", "count"]
    fig = px.pie(
        decision_counts, names="decision", values="count",
        title="Decision Breakdown",
        color="decision",
        color_discrete_map={"APPROVE": "#2E7D32", "MANUAL REVIEW": "#F9A825", "REJECT": "#C62828"},
    )
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    fig2 = px.histogram(
        result_df, x="risk_score", nbins=25,
        title="Risk Score Distribution",
        color_discrete_sequence=["#455A64"],
    )
    fig2.add_vline(x=60, line_dash="dash", line_color="#EF6C00")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- Filterable case table ---
st.subheader("Case Review")

filter_col1, filter_col2 = st.columns([1, 3])
with filter_col1:
    decision_filter = st.multiselect(
        "Filter by decision",
        options=["APPROVE", "MANUAL REVIEW", "REJECT"],
        default=["MANUAL REVIEW", "REJECT"],
    )

filtered = result_df[result_df["decision"].isin(decision_filter)] if decision_filter else result_df
filtered = filtered.sort_values("risk_score", ascending=False)

st.dataframe(
    filtered[[
        "merchant_id", "business_name_type", "country_code", "risk_score",
        "risk_band", "decision", "anomaly_score", "rule_violations",
    ]],
    use_container_width=True,
    height=400,
)

st.markdown("---")

# --- Merchant drill-down ---
st.subheader("Merchant Drill-Down")
selected_id = st.selectbox("Select a merchant to inspect", options=filtered["merchant_id"].tolist())

if selected_id:
    record = result_df[result_df["merchant_id"] == selected_id].iloc[0]

    d1, d2 = st.columns([2, 1])
    with d1:
        st.markdown(f"### {selected_id} — {record['business_name_type'].title()}")
        st.markdown(band_badge(record["risk_band"]), unsafe_allow_html=True)
        st.write("")
        st.write(f"**Decision:** {record['decision']}")
        st.write(f"**Risk Score:** {record['risk_score']:.1f} / 100")
        st.write(f"**Anomaly Score:** {record['anomaly_score']:.3f}" if pd.notna(record["anomaly_score"]) else "")
        st.write(f"**Rule Violations:** {record['rule_violations']}")

    with d2:
        st.metric("Declared Revenue", f"${record['declared_monthly_revenue']:,.0f}")
        st.metric("Max Txn Amount", f"${record['actual_max_transaction_amount']:,.0f}")
        st.metric("Intl Txns", f"{record['pct_international_transactions']:.0f}%")
        st.metric("Night Txns", f"{record['pct_night_transactions']:.0f}%")

st.markdown("---")
st.caption(
    "MerchAudit is a demonstration project combining deterministic compliance rules "
    "with unsupervised anomaly detection. Not intended for production use without "
    "further validation against real transaction data and current sanctions lists."
)
