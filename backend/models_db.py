"""
ORM models.

Schema:
  User            — analyst/admin accounts (JWT auth, RBAC)
  Merchant        — a merchant application/record submitted for auditing
  RiskReport      — the output of running a merchant through both layers
  RuleViolation   — individual Layer 1 rule failures tied to a RiskReport
  AuditLog        — who did what, when (every mutating action gets one)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ANALYST)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=_uuid)
    merchant_id = Column(String, unique=True, index=True, nullable=False)  # external/business id e.g. M00001
    business_name_type = Column(String, nullable=False)
    country_code = Column(String, nullable=False)
    tax_id = Column(String, nullable=False)

    declared_monthly_revenue = Column(Float, nullable=False)
    actual_avg_transaction_amount = Column(Float, nullable=False)
    actual_max_transaction_amount = Column(Float, nullable=False)
    transaction_count_30d = Column(Integer, nullable=False)
    pct_international_transactions = Column(Float, nullable=False)
    pct_night_transactions = Column(Float, nullable=False)
    revenue_burst_ratio = Column(Float, nullable=False)
    chargeback_rate_pct = Column(Float, nullable=False)

    created_at = Column(DateTime, default=_now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    risk_reports = relationship("RiskReport", back_populates="merchant", cascade="all, delete-orphan")


class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(String, primary_key=True, default=_uuid)
    merchant_id = Column(String, ForeignKey("merchants.merchant_id"), nullable=False, index=True)

    risk_score = Column(Float, nullable=False)
    risk_band = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    anomaly_score = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)

    created_at = Column(DateTime, default=_now)
    audited_by = Column(String, ForeignKey("users.id"), nullable=True)

    merchant = relationship("Merchant", back_populates="risk_reports")
    rule_violations = relationship("RuleViolation", back_populates="risk_report", cascade="all, delete-orphan")


class RuleViolation(Base):
    __tablename__ = "rule_violations"

    id = Column(String, primary_key=True, default=_uuid)
    risk_report_id = Column(String, ForeignKey("risk_reports.id"), nullable=False, index=True)
    rule = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # REJECT or FLAG

    risk_report = relationship("RiskReport", back_populates="rule_violations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)         # e.g. "CREATE_MERCHANT", "RUN_AUDIT", "LOGIN"
    target = Column(String, nullable=True)           # e.g. merchant_id affected
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
