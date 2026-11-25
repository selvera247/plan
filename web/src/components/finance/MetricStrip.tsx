export type Metric = {
  label: string;
  value: string | number;
};

export type MetricStripProps = {
  metrics: Metric[];
};

export function MetricStrip({ metrics }: MetricStripProps) {
  if (!metrics.length) return null;
  return (
    <dl className="gf-metrics" aria-label="Result metrics">
      {metrics.map((m) => (
        <div key={m.label}>
          <dt className="gf-metric__label">{m.label}</dt>
          <dd className="gf-metric__value">{m.value}</dd>
        </div>
      ))}
    </dl>
  );
}
