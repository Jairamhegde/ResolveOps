import "./pageheader.css";

// The title at the top of each page. Anything passed as children shows on the right.
function PageHeader({ title, subtitle, children }) {
  return (
    <header className="page-header">
      <div>
        <h2 className="page-header-title">{title}</h2>
        {subtitle && <p className="page-header-subtitle">{subtitle}</p>}
      </div>
      {children}
    </header>
  );
}

export default PageHeader;
