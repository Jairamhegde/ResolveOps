import { roleLabel } from "../format";
import Avatar from "./Avatar";
import { BrandMark, LogOutIcon } from "./Icons";
import ThemeToggle from "./ThemeToggle";
import "./topbar.css";

// The bar across the top of every signed-in page: the product on the left, who is signed in on the right.
function TopBar({ session, onLogOut }) {
  const name = session.name || session.email;

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <BrandMark />
        <span className="topbar-product">ResolveOps</span>
      </div>

      <div className="topbar-user">
        <ThemeToggle />
        <span className="topbar-divider" aria-hidden="true" />
        <div className="topbar-who">
          <p className="topbar-name" title={session.email}>
            {name}
          </p>
          <p className="topbar-role">{roleLabel(session.role)}</p>
        </div>
        <Avatar name={name} size="medium" />
        <button className="button button-subtle topbar-logout" type="button" onClick={onLogOut} title="Log out">
          <LogOutIcon />
          <span className="topbar-logout-label">Log out</span>
        </button>
      </div>
    </header>
  );
}

export default TopBar;
