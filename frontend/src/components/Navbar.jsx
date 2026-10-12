import "./navbar.css";

// The top bar: logo on the left, the page tabs (passed as children) in the middle, the user on the right.
function Navbar({ title, session, onLogout, children }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">R</span>
        <h1 className="navbar-title">{title}</h1>
      </div>

      <div className="navbar-center">{children}</div>

      <div className="navbar-right">
        <div className="navbar-user">
          <p className="navbar-email">{session.email}</p>
          <p className="navbar-role">{session.role.replaceAll("_", " ")}</p>
        </div>

        <button className="navbar-logout" type="button" onClick={onLogout}>
          Log out
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
