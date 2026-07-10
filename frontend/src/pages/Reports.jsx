import { useEffect, useMemo, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip as ReTooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import Layout from '../components/Layout';
import StampBadge from '../components/StampBadge';
import * as api from '../api';
import '../components/ui.css';

const DECISION_COLORS = {
  APPROVE: '#2E7D32',
  'MANUAL REVIEW': '#B4770A',
  REJECT: '#B3261E',
};

const PAGE_SIZE = 10;

export default function Reports() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [decision, setDecision] = useState('');
  const [riskBand, setRiskBand] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    api
      .listReports({ decision: decision || undefined, riskBand: riskBand || undefined, page, pageSize: PAGE_SIZE })
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
      })
      .catch((err) => !cancelled && setError(err.response?.data?.detail || 'Could not load reports.'))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [decision, riskBand, page]);

  const decisionCounts = useMemo(() => {
    const counts = {};
    for (const item of items) counts[item.decision] = (counts[item.decision] || 0) + 1;
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [items]);

  const scoreHistogram = useMemo(() => {
    const buckets = [0, 0, 0, 0, 0]; // 0-20,20-40,40-60,60-80,80-100
    for (const item of items) {
      const idx = Math.min(4, Math.floor(item.risk_score / 20));
      buckets[idx] += 1;
    }
    return buckets.map((count, i) => ({ range: `${i * 20}-${i * 20 + 20}`, count }));
  }, [items]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <Layout>
      <div className="page-header">
        <div>
          <h1>Risk reports</h1>
          <p>Every audit run, filterable by decision and risk band.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="metric-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Decision breakdown (this page)</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={decisionCounts} dataKey="value" nameKey="name" innerRadius={45} outerRadius={70} paddingAngle={2}>
                {decisionCounts.map((entry) => (
                  <Cell key={entry.name} fill={DECISION_COLORS[entry.name] || '#8890A0'} />
                ))}
              </Pie>
              <ReTooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Risk score distribution (this page)</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={scoreHistogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis dataKey="range" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <ReTooltip />
              <Bar dataKey="count" fill="#141C2E" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', gap: 14, marginBottom: 16, flexWrap: 'wrap' }}>
          <div className="field" style={{ minWidth: 180 }}>
            <label>Decision</label>
            <select value={decision} onChange={(e) => { setPage(1); setDecision(e.target.value); }}>
              <option value="">All</option>
              <option value="APPROVE">Approve</option>
              <option value="MANUAL REVIEW">Manual review</option>
              <option value="REJECT">Reject</option>
            </select>
          </div>
          <div className="field" style={{ minWidth: 180 }}>
            <label>Risk band</label>
            <select value={riskBand} onChange={(e) => { setPage(1); setRiskBand(e.target.value); }}>
              <option value="">All</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Loading reports…</div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <h3>No reports match these filters</h3>
            <p>Run an audit from the Merchants page, or widen your filters.</p>
          </div>
        ) : (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Merchant</th>
                  <th>Risk score</th>
                  <th>Band</th>
                  <th>Decision</th>
                  <th>Audited</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id} onClick={() => setSelected(r)}>
                    <td className="mono">{r.merchant_id}</td>
                    <td className="mono">{r.risk_score.toFixed(1)}</td>
                    <td><StampBadge band={r.risk_band} size="sm" /></td>
                    <td><StampBadge decision={r.decision} size="sm" /></td>
                    <td className="mono" style={{ color: 'var(--text-400)', fontSize: 12 }}>
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="pagination">
              <span>Page {page} of {totalPages} — {total} total</span>
              <button className="btn btn--ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn btn--ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </>
        )}
      </div>

      {selected && (
        <div className="drawer-backdrop" onClick={() => setSelected(null)}>
          <div className="drawer" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-400)', marginBottom: 2 }}>MERCHANT</div>
                <h2 className="mono">{selected.merchant_id}</h2>
              </div>
              <button className="btn btn--ghost" onClick={() => setSelected(null)}>Close</button>
            </div>

            <div style={{ margin: '18px 0' }}>
              <StampBadge decision={selected.decision} size="lg" />
            </div>

            <div className="metric-row" style={{ marginBottom: 20 }}>
              <div className="metric-card">
                <div className="metric-card__label">Risk score</div>
                <div className="metric-card__value">{selected.risk_score.toFixed(1)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-card__label">Anomaly score</div>
                <div className="metric-card__value">
                  {selected.anomaly_score != null ? selected.anomaly_score.toFixed(3) : '—'}
                </div>
              </div>
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-600)', marginBottom: 8 }}>
              RULE VIOLATIONS
            </div>
            {selected.rule_violations?.length > 0 ? (
              selected.rule_violations.map((v, i) => (
                <div key={i} style={{ fontSize: 13, padding: '8px 0', borderTop: i > 0 ? '1px solid var(--line)' : 'none' }}>
                  <strong>[{v.severity}] {v.rule}</strong>
                  <div style={{ color: 'var(--text-600)', marginTop: 2 }}>{v.reason}</div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: 13, color: 'var(--text-400)' }}>None — passed all Layer 1 checks.</div>
            )}

            <div style={{ marginTop: 20, fontSize: 12, color: 'var(--text-400)' }}>
              Model version: <span className="mono">{selected.model_version || 'n/a'}</span><br />
              Audited: {new Date(selected.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
