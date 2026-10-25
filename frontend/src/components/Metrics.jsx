import "./metrics.css";

// A row of headline numbers, one card each, like the gadgets on a Jira dashboard.
export function MetricStrip({ label, children }) {
  return (
    <section className="metric-strip" aria-label={label}>
      {children}
    </section>
  );
}

// One number. `ai` marks a number the AI produced with the magenta used for everything the AI does.
// `alert` marks a number that needs someone's attention when it isn't zero.
export function Metric({ label, value, detail, ai = false, alert = false }) {
  let className = "metric";
  if (ai) className += " metric-ai";
  if (alert && Number(value) > 0) className += " metric-alert";

  return (
    <div className={className}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      {detail && <p className="metric-detail">{detail}</p>}
    </div>
  );
}
