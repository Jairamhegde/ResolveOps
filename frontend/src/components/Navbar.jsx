import "./navbar.css";

function Navbar({ title, updatedAt }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">R</span>
        <div>
          <h1 className="navbar-title">{title}</h1>
          <p className="navbar-subtitle">AI helpdesk overview</p>
        </div>
      </div>

      {updatedAt && (
        <p className="navbar-live">
          <span className="navbar-live-dot" />
          Live · updated {updatedAt.toLocaleTimeString()}
        </p>
      )}
    </nav>
  );
}

export default Navbar;
