interface ProgressBarProps {
  current: number;
  max: number;
  label?: string;
}

export function ProgressBar({ current, max, label }: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.round((current / max) * 100)) : 0;
  return (
    <div className="ad-progress-wrap">
      <div className="ad-progress-label">
        <span>{label ?? `${current} / ${max} entries`}</span>
        <span>{pct}%</span>
      </div>
      <div className="ad-progress-bar">
        <div className="ad-progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
