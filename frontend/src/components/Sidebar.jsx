import "./sidebar.css";

// The left navigation: one link per page.
function Sidebar({ pages, currentId, onOpen }) {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav" aria-label="Dashboard pages">
        <p className="sidebar-heading">Dashboard</p>
        {pages.map(({ id, label, Icon }) => (
          <a
            key={id}
            href={`#/${id}`}
            className={id === currentId ? "sidebar-link sidebar-link-active" : "sidebar-link"}
            aria-current={id === currentId ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onOpen(id);
            }}
          >
            <Icon />
            {label}
          </a>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;
