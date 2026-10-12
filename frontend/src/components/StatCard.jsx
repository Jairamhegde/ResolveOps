import "./statcard.css";

// `highlight` makes the card stand out, for the one number the dashboard is about.
function StatCard({ label, value, hint, highlight = false }) {
  return (
    <div className={highlight ? "stat-card stat-card-highlight" : "stat-card"}>
      <p className="stat-label">{label}</p>
      <p className="stat-value">{value}</p>
      {hint && <p className="stat-hint">{hint}</p>}
    </div>
  );
}

export default StatCard;
