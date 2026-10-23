import { useEffect, useState } from "react";
import { setUnauthorizedHandler } from "./api";
import LoginPage from "./components/LoginPage";
import Sidebar from "./components/Sidebar";
import OverviewPage from "./pages/OverviewPage";
import TicketsPage from "./pages/TicketsPage";
import EmployeesPage from "./pages/EmployeesPage";
import AdminsPage from "./pages/AdminsPage";
import MyTicketsPage from "./pages/MyTicketsPage";

const SESSION_KEY = "resolveops-session";

// The pages in the sidebar. `superAdminOnly` pages are hidden from category admins.
const PAGES = [
  { id: "overview", label: "Overview", Page: OverviewPage },
  { id: "tickets", label: "Tickets", Page: TicketsPage },
  { id: "employees", label: "Employees", Page: EmployeesPage },
  { id: "admins", label: "Admins", Page: AdminsPage, superAdminOnly: true },
];

// The login token's expiry time in ms, or 0 when it can't be read.
function tokenExpiry(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replaceAll("-", "+").replaceAll("_", "/")));
    return payload.exp * 1000;
  } catch {
    return 0;
  }
}

// The saved login ({ token, email, role }), so a refresh doesn't log the user out. Expired logins are dropped.
function loadSavedSession() {
  try {
    const session = JSON.parse(localStorage.getItem(SESSION_KEY));
    return session && tokenExpiry(session.token) > Date.now() ? session : null;
  } catch {
    return null;
  }
}

function pageFromAddress() {
  return window.location.hash.replace("#/", "") || "overview";
}

function App() {
  const [session, setSession] = useState(loadSavedSession);
  const [pageId, setPageId] = useState(pageFromAddress);
  const [notice, setNotice] = useState("");

  const isSuperAdmin = session?.role === "super_admin";
  const pages = PAGES.filter((page) => isSuperAdmin || !page.superAdminOnly);
  const currentPage = pages.find((page) => page.id === pageId) || pages[0];

  function logIn(newSession) {
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(newSession));
    } catch {
      // Storage blocked (private window): the login still works until the page is refreshed.
    }
    setNotice("");
    setSession(newSession);
  }

  function logOut(message = "") {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {
      // Nothing saved, nothing to remove.
    }
    setNotice(message);
    setSession(null);
  }

  function openPage(id) {
    window.location.hash = `/${id}`;
    setPageId(id);
  }

  // A 401 from any request, or the 8-hour token running out, sends the user back to the login page.
  useEffect(() => {
    setUnauthorizedHandler(() => logOut("Your session ended. Sign in again to keep working."));
    if (session === null) return;

    const msLeft = Math.min(tokenExpiry(session.token) - Date.now(), 2 ** 31 - 1);
    const timer = setTimeout(() => logOut("Your session ended after 8 hours. Sign in again to keep working."), msLeft);
    return () => clearTimeout(timer);
  }, [session]);

  useEffect(() => {
    const onAddressChange = () => setPageId(pageFromAddress());
    window.addEventListener("hashchange", onAddressChange);
    return () => window.removeEventListener("hashchange", onAddressChange);
  }, []);

  useEffect(() => {
    if (session === null) document.title = "Sign in – ResolveOps";
    else if (session.role === "employee") document.title = "My tickets – ResolveOps";
    else document.title = `${currentPage.label} – ResolveOps`;
  }, [session, currentPage]);

  if (session === null) {
    return <LoginPage onLogin={logIn} notice={notice} />;
  }

  // Employees only see their own tickets, on a page of their own.
  if (session.role === "employee") {
    return <MyTicketsPage token={session.token} session={session} onLogOut={() => logOut()} />;
  }

  const { Page } = currentPage;

  return (
    <div className="app">
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <Sidebar pages={pages} currentId={currentPage.id} onOpen={openPage} session={session} onLogOut={() => logOut()} />
      <main className="main" id="content" tabIndex={-1}>
        <Page token={session.token} isSuperAdmin={isSuperAdmin} role={session.role} />
      </main>
    </div>
  );
}

export default App;
