from merchaudit.business_rules import run_business_rules


def make_merchant(**overrides):
    base = {
        "chargeback_rate_pct": 0.3,
        "country_code": "US",
        "tax_id": "12-3456789",
    }
    base.update(overrides)
    return base


def test_clean_merchant_passes():
    result = run_business_rules(make_merchant())
    assert result.passed
    assert result.violations == []


def test_chargeback_velocity_flags():
    result = run_business_rules(make_merchant(chargeback_rate_pct=2.5))
    assert not result.passed
    assert any(v.rule == "Chargeback Velocity Cap" for v in result.violations)


def test_restricted_country_flags():
    result = run_business_rules(make_merchant(country_code="KP"))
    assert not result.passed
    assert any(v.rule == "Compliance Geofencing" for v in result.violations)


def test_bad_tax_id_flags():
    result = run_business_rules(make_merchant(tax_id="000000000"))
    assert not result.passed
    assert any(v.rule == "Tax Validation" for v in result.violations)


def test_integer_tax_id_does_not_crash():
    # pandas can read an all-digit tax_id column as int64 - must not raise
    result = run_business_rules(make_merchant(tax_id=123456789))
    assert result is not None
