import "./badge.css";

// A small label with a coloured dot. `tone` picks the colour: good, info, warning, serious, critical or neutral.
function Badge({ tone = "neutral", children }) {
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" />
      {children}
    </span>
  );
}

export default Badge;
