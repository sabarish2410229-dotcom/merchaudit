import './StampBadge.css';

const STAMP_CONFIG = {
  APPROVE: { label: 'APPROVED', tone: 'low' },
  'MANUAL REVIEW': { label: 'REVIEW', tone: 'medium' },
  REJECT: { label: 'REJECTED', tone: 'critical' },
};

const BAND_TONE = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
};

/**
 * Renders a decision or risk band as an ink-stamp, echoing how merchant
 * applications were historically stamped by hand during underwriting review.
 */
export default function StampBadge({ decision, band, size = 'md' }) {
  if (decision) {
    const cfg = STAMP_CONFIG[decision] || { label: decision, tone: 'medium' };
    return (
      <span className={`stamp stamp--${cfg.tone} stamp--${size}`}>
        {cfg.label}
      </span>
    );
  }
  if (band) {
    const tone = BAND_TONE[band] || 'medium';
    return <span className={`stamp stamp--${tone} stamp--${size}`}>{band}</span>;
  }
  return null;
}
