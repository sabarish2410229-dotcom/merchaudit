from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import auth, schemas
from ..database import get_db
from ..models_db import RiskReport, User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=schemas.PaginatedReports)
def list_reports(
    decision: Optional[str] = Query(None, pattern="^(APPROVE|MANUAL REVIEW|REJECT)$"),
    risk_band: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    q = db.query(RiskReport)
    if decision:
        q = q.filter(RiskReport.decision == decision)
    if risk_band:
        q = q.filter(RiskReport.risk_band == risk_band)

    total = q.count()
    items = (
        q.order_by(RiskReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.PaginatedReports(total=total, page=page, page_size=page_size, items=items)


@router.get("/{merchant_id}", response_model=list[schemas.RiskReportOut])
def get_reports_for_merchant(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    reports = (
        db.query(RiskReport)
        .filter(RiskReport.merchant_id == merchant_id)
        .order_by(RiskReport.created_at.desc())
        .all()
    )
    if not reports:
        raise HTTPException(status_code=404, detail="No risk reports found for this merchant")
    return reports
