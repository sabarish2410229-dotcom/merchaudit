import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import auth, schemas
from ..database import get_db
from ..models_db import AuditLog, Merchant, RiskReport, RuleViolation, User
from merchaudit import config
from merchaudit.business_rules import run_business_rules

router = APIRouter(prefix="/merchants", tags=["audits"])


def _band_for_score(score: float) -> str:
    for lo, hi, label in config.RISK_BANDS:
        if lo <= score < hi:
            return label
    return config.RISK_BANDS[-1][2]


@router.post("/{merchant_id}/audit", response_model=schemas.RiskReportOut, status_code=status.HTTP_201_CREATED)
def run_audit(
    merchant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    engine = request.app.state.anomaly_engine
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="No trained model loaded. Run backend/ml/train_model.py first.",
        )

    merchant_dict = {
        "merchant_id": merchant.merchant_id,
        "chargeback_rate_pct": merchant.chargeback_rate_pct,
        "country_code": merchant.country_code,
        "tax_id": merchant.tax_id,
    }
    rule_result = run_business_rules(merchant_dict)
    has_reject = any(v.severity == "REJECT" for v in rule_result.violations)
    has_flag = any(v.severity == "FLAG" for v in rule_result.violations)

    # Always compute the anomaly score for visibility, even if Layer 1 already rejects,
    # so the report shows the full picture to the analyst.
    row = pd.DataFrame([{
        "merchant_id": merchant.merchant_id,
        "declared_monthly_revenue": merchant.declared_monthly_revenue,
        "actual_avg_transaction_amount": merchant.actual_avg_transaction_amount,
        "actual_max_transaction_amount": merchant.actual_max_transaction_amount,
        "transaction_count_30d": merchant.transaction_count_30d,
        "pct_international_transactions": merchant.pct_international_transactions,
        "pct_night_transactions": merchant.pct_night_transactions,
        "revenue_burst_ratio": merchant.revenue_burst_ratio,
    }])
    scored = engine.score(row)
    anomaly_score = float(scored["anomaly_score"].iloc[0])

    if has_reject:
        risk_score = 100.0
        decision = "REJECT"
    elif has_flag:
        risk_score = max(70.0, anomaly_score * config.RISK_SCORE_ANOMALY_WEIGHT)
        decision = "MANUAL REVIEW"
    else:
        risk_score = anomaly_score * config.RISK_SCORE_ANOMALY_WEIGHT
        decision = "MANUAL REVIEW" if risk_score >= 60 else "APPROVE"

    report = RiskReport(
        merchant_id=merchant.merchant_id,
        risk_score=risk_score,
        risk_band=_band_for_score(risk_score),
        decision=decision,
        anomaly_score=anomaly_score,
        model_version=engine.model_version,
        audited_by=current_user.id,
    )
    db.add(report)
    db.flush()  # get report.id before creating child rows

    for v in rule_result.violations:
        db.add(RuleViolation(risk_report_id=report.id, rule=v.rule, reason=v.reason, severity=v.severity))

    db.add(AuditLog(
        user_id=current_user.id,
        action="RUN_AUDIT",
        target=merchant.merchant_id,
        details=f"decision={decision} risk_score={risk_score:.1f}",
    ))
    db.commit()
    db.refresh(report)
    return report
