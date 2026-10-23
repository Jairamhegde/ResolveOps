import "./section.css";

// A titled white panel. `flush` lets a table run to the panel's edges.
export function Section({ title, subtitle, actions, flush = false, children }) {
  return (
    <section className={flush ? "section section-flush" : "section"}>
      <header className="section-header">
        <div>
          <h2 className="section-title">{title}</h2>
          {subtitle && <p className="section-subtitle">{subtitle}</p>}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}

// A failed request: what went wrong and a button to try again.
export function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message" role="alert">
      <p>{message}</p>
      <button className="button" type="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

export function Loading({ label = "Loading…" }) {
  return (
    <p className="loading" role="status">
      {label}
    </p>
  );
}
