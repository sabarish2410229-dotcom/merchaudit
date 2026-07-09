"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(default="analyst", pattern="^(analyst|admin)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Merchant ---

class MerchantCreate(BaseModel):
    merchant_id: str
    business_name_type: str
    country_code: str
    tax_id: str
    declared_monthly_revenue: float
    actual_avg_transaction_amount: float
    actual_max_transaction_amount: float
    transaction_count_30d: int
    pct_international_transactions: float
    pct_night_transactions: float
    revenue_burst_ratio: float
    chargeback_rate_pct: float


class MerchantOut(MerchantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# --- Risk Reports ---

class RuleViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule: str
    reason: str
    severity: str


class RiskReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    merchant_id: str
    risk_score: float
    risk_band: str
    decision: str
    anomaly_score: Optional[float]
    model_version: Optional[str]
    created_at: datetime
    rule_violations: list[RuleViolationOut] = []


class PaginatedReports(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RiskReportOut]
