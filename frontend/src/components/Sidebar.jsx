import { roleLabel } from "../format";
import "./sidebar.css";

// The left navigation: the brand, one link per page, and who is signed in.
function Sidebar({ pages, currentId, onOpen, session, onLogOut }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark" aria-hidden="true" />
        ResolveOps
      </div>

      <nav className="sidebar-nav" aria-label="Dashboard pages">
        {pages.map((page) => (
          <a
            key={page.id}
            href={`#/${page.id}`}
            className={page.id === currentId ? "sidebar-link sidebar-link-active" : "sidebar-link"}
            aria-current={page.id === currentId ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onOpen(page.id);
            }}
          >
            {page.label}
          </a>
        ))}
      </nav>

      <div className="sidebar-user">
        <p className="sidebar-email" title={session.email}>
          {session.email}
        </p>
        <p className="sidebar-role">{roleLabel(session.role)}</p>
        <button className="sidebar-logout" type="button" onClick={onLogOut}>
          Log out
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
