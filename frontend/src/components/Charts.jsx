import "./charts.css";

function percent(part, total) {
  return total ? Math.round((part / total) * 100) : 0;
}

// Where every ticket stands right now, as one stacked bar with a legend.
export function StatusBreakdown({ metrics }) {
  const parts = [
    { key: "ai", label: "Fixed by the AI", count: metrics.solved_by_ai },
    { key: "admin", label: "Fixed by IT", count: metrics.solved_by_admin },
    { key: "waiting", label: "Waiting on employee", count: metrics.pending_response },
    { key: "active", label: "With IT now", count: metrics.active },
  ];

  return (
    <div className="breakdown">
      <div className="breakdown-bar" role="img" aria-label={parts.map((part) => `${part.label}: ${part.count}`).join(", ")}>
        {parts
          .filter((part) => part.count > 0)
          .map((part) => (
            <span key={part.key} className={`breakdown-part breakdown-${part.key}`} style={{ flexGrow: part.count }} />
          ))}
      </div>

      <ul className="breakdown-legend">
        {parts.map((part) => (
          <li key={part.key}>
            <span className={`breakdown-swatch breakdown-${part.key}`} aria-hidden="true" />
            <span className="breakdown-label">{part.label}</span>
            <strong>{part.count}</strong>
            <span className="breakdown-percent">{percent(part.count, metrics.total)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Labelled horizontal bars, one per row. `rows` is a list of { label, count }.
export function BarList({ rows }) {
  const largest = Math.max(1, ...rows.map((row) => row.count));

  return (
    <ul className="bar-list">
      {rows.map((row) => (
        <li key={row.label} className="bar-list-row">
          <span className="bar-list-label">{row.label}</span>
          <span className="bar-list-track">
            <span className="bar-list-bar" style={{ width: `${(row.count / largest) * 100}%` }} />
          </span>
          <span className="bar-list-count">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

// Tickets raised per day. `days` is a list of { day: "2026-10-18", count }.
export function DayChart({ days }) {
  const largest = Math.max(1, ...days.map((day) => day.count));
  const total = days.reduce((sum, day) => sum + day.count, 0);

  return (
    <figure className="day-chart" aria-label={`${total} tickets raised in the last ${days.length} days`}>
      <div className="day-chart-bars">
        {days.map((day) => {
          const date = new Date(`${day.day}T00:00:00`);
          const label = date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
          return (
            <div key={day.day} className="day-chart-column" title={`${label}: ${day.count} tickets`}>
              <span className="day-chart-count">{day.count > 0 ? day.count : ""}</span>
              <span className="day-chart-bar" style={{ height: `${(day.count / largest) * 100}%` }} />
            </div>
          );
        })}
      </div>
      <figcaption className="day-chart-axis">
        <span>{new Date(`${days[0].day}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
        <span>Today</span>
      </figcaption>
    </figure>
  );
}
