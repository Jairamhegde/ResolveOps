import "./panel.css";

// A white card with a title. Charts and ticket lists sit inside one.
function Panel({ title, subtitle, children }) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2 className="panel-title">{title}</h2>
        {subtitle && <p className="panel-subtitle">{subtitle}</p>}
      </header>
      {children}
    </section>
  );
}

export default Panel;
