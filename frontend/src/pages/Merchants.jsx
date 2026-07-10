import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import StampBadge from '../components/StampBadge';
import * as api from '../api';
import '../components/ui.css';

const FIELDS = [
  { name: 'merchant_id', label: 'Merchant ID', placeholder: 'M00042' },
  { name: 'business_name_type', label: 'Business type', placeholder: 'online bookstore' },
  { name: 'country_code', label: 'Country code', placeholder: 'US' },
  { name: 'tax_id', label: 'Tax ID', placeholder: '12-3456789' },
  { name: 'declared_monthly_revenue', label: 'Declared monthly revenue ($)', type: 'number', placeholder: '8000' },
  { name: 'actual_avg_transaction_amount', label: 'Avg transaction amount ($)', type: 'number', placeholder: '150' },
  { name: 'actual_max_transaction_amount', label: 'Max transaction amount ($)', type: 'number', placeholder: '500' },
  { name: 'transaction_count_30d', label: 'Transactions (30d)', type: 'number', placeholder: '50' },
  { name: 'pct_international_transactions', label: 'Intl transactions (%)', type: 'number', placeholder: '5' },
  { name: 'pct_night_transactions', label: 'Night transactions (%)', type: 'number', placeholder: '2' },
  { name: 'revenue_burst_ratio', label: 'Revenue burst ratio', type: 'number', placeholder: '0.3', step: '0.01' },
  { name: 'chargeback_rate_pct', label: 'Chargeback rate (%)', type: 'number', placeholder: '0.2', step: '0.01' },
];

const NUMERIC_FIELDS = new Set(FIELDS.filter((f) => f.type === 'number').map((f) => f.name));

export default function Merchants() {
  const navigate = useNavigate();
  const [form, setForm] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [lastReport, setLastReport] = useState(null);

  function handleChange(name, value) {
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    setLastReport(null);
    try {
      const payload = { ...form };
      for (const key of NUMERIC_FIELDS) {
        payload[key] = parseFloat(payload[key]);
      }
      await api.createMerchant(payload);
      const report = await api.runAudit(payload.merchant_id);
      setLastReport(report);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create or audit merchant.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      <div className="page-header">
        <div>
          <h1>New merchant intake</h1>
          <p>Submit an application to run it through both defense layers.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="field-grid">
            {FIELDS.map((f) => (
              <div className="field" key={f.name}>
                <label htmlFor={f.name}>{f.label}</label>
                <input
                  id={f.name}
                  type={f.type || 'text'}
                  step={f.step}
                  required
                  placeholder={f.placeholder}
                  value={form[f.name] ?? ''}
                  onChange={(e) => handleChange(f.name, e.target.value)}
                />
              </div>
            ))}
          </div>

          <button className="btn btn--primary" type="submit" disabled={submitting} style={{ marginTop: 20 }}>
            {submitting ? 'Running audit…' : 'Submit & run audit'}
          </button>
        </form>
      </div>

      {lastReport && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h3>Audit result</h3>
            <StampBadge decision={lastReport.decision} size="lg" />
          </div>
          <div className="metric-row" style={{ marginBottom: 0 }}>
            <div className="metric-card">
              <div className="metric-card__label">Risk score</div>
              <div className="metric-card__value">{lastReport.risk_score.toFixed(1)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Risk band</div>
              <div className="metric-card__value" style={{ fontSize: 18 }}>
                <StampBadge band={lastReport.risk_band} />
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-card__label">Anomaly score</div>
              <div className="metric-card__value">
                {lastReport.anomaly_score != null ? lastReport.anomaly_score.toFixed(3) : '—'}
              </div>
            </div>
          </div>
          {lastReport.rule_violations?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-600)', marginBottom: 6 }}>
                RULE VIOLATIONS
              </div>
              {lastReport.rule_violations.map((v, i) => (
                <div key={i} style={{ fontSize: 13, padding: '6px 0', borderTop: i > 0 ? '1px solid var(--line)' : 'none' }}>
                  <strong>[{v.severity}] {v.rule}</strong> — {v.reason}
                </div>
              ))}
            </div>
          )}
          <button
            className="btn btn--secondary"
            style={{ marginTop: 16 }}
            onClick={() => navigate('/reports')}
          >
            View all reports
          </button>
        </div>
      )}
    </Layout>
  );
}
