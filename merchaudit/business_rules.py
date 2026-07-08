"""
Layer 1 — The Structured Business Logic (Compliance Gatekeeper)

Deterministic, auditable checks that run *before* any machine learning.
Any single failure here is enough to instantly flag or reject a merchant,
regardless of what the AI layer later says.
"""

from dataclasses import dataclass, field

from . import config


@dataclass
class RuleViolation:
    rule: str
    reason: str
    severity: str = "REJECT"  # REJECT or FLAG


@dataclass
class BusinessRuleResult:
    passed: bool
    violations: list = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "No business rule violations."
        return "; ".join(f"[{v.severity}] {v.rule}: {v.reason}" for v in self.violations)


def check_chargeback_velocity(merchant: dict) -> RuleViolation | None:
    """Flag merchants whose dispute rate is spiking over the threshold."""
    rate = merchant.get("chargeback_rate_pct", 0.0)
    if rate > config.CHARGEBACK_RATE_THRESHOLD_PCT:
        return RuleViolation(
            rule="Chargeback Velocity Cap",
            reason=(
                f"Chargeback rate {rate:.2f}% exceeds the "
                f"{config.CHARGEBACK_RATE_THRESHOLD_PCT}% threshold "
                f"over the last {config.CHARGEBACK_LOOKBACK_DAYS} days."
            ),
            severity="REJECT",
        )
    return None


def check_geofencing(merchant: dict) -> RuleViolation | None:
    """Flag merchants operating out of restricted/sanctioned countries."""
    country = (merchant.get("country_code") or "").upper()
    if country in config.RESTRICTED_COUNTRIES:
        return RuleViolation(
            rule="Compliance Geofencing",
            reason=f"Merchant country '{country}' is on the restricted/sanctioned list.",
            severity="REJECT",
        )
    return None


def _tax_id_checksum_valid(tax_id: str) -> bool:
    """
    Simplified mod-10 checksum validation used as a stand-in for a real
    country-specific tax authority check (e.g. GSTIN/EIN/VAT validators).
    """
    digits = [c for c in tax_id if c.isdigit()]
    if not digits:
        return False
    total = sum(int(d) for d in digits)
    return total % 10 != 0  # arbitrary demo rule: checksum of 0 mod 10 = invalid


def check_tax_validation(merchant: dict) -> RuleViolation | None:
    """Verify the declared tax ID matches the expected format for its country."""
    country = (merchant.get("country_code") or "default").upper()
    tax_id = str(merchant.get("tax_id", ""))
    fmt = config.TAX_ID_FORMATS.get(country, config.TAX_ID_FORMATS["default"])

    cleaned = tax_id.replace("-", "").replace(" ", "")
    if len(cleaned) != fmt["length"] or not cleaned.isdigit():
        return RuleViolation(
            rule="Tax Validation",
            reason=(
                f"Tax ID '{tax_id}' does not match expected {fmt['name']} "
                f"format ({fmt['length']} digits) for country '{country}'."
            ),
            severity="FLAG",
        )
    if not _tax_id_checksum_valid(cleaned):
        return RuleViolation(
            rule="Tax Validation",
            reason=f"Tax ID '{tax_id}' failed checksum validation.",
            severity="FLAG",
        )
    return None


ALL_RULES = [check_chargeback_velocity, check_geofencing, check_tax_validation]


def run_business_rules(merchant: dict) -> BusinessRuleResult:
    """Run every Layer 1 rule against a merchant record and aggregate results."""
    violations = [v for rule_fn in ALL_RULES if (v := rule_fn(merchant)) is not None]
    return BusinessRuleResult(passed=len(violations) == 0, violations=violations)
