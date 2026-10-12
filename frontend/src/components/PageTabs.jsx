import "./pagetabs.css";

// The navigation between pages. `pages` is a list of { id, label }.
function PageTabs({ pages, currentPage, onChange }) {
  return (
    <div className="page-tabs">
      {pages.map((page) => (
        <button
          key={page.id}
          type="button"
          className={page.id === currentPage ? "page-tab page-tab-active" : "page-tab"}
          onClick={() => onChange(page.id)}
        >
          {page.label}
        </button>
      ))}
    </div>
  );
}

export default PageTabs;
