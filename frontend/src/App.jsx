import { useState } from "react";
import Navbar from "./components/Navbar";
import PageTabs from "./components/PageTabs";
import LoginPage from "./components/LoginPage";
import UserPage from "./pages/UserPage";
import AdminPage from "./pages/AdminPage";
import SuperAdminPage from "./pages/SuperAdminPage";

const SESSION_KEY = "resolveops-session";

const PAGES = [
  { id: "user", label: "As user" },
  { id: "admin", label: "As admin" },
  { id: "super_admin", label: "As super admin" },
];

// The saved login ({ token, email, role }), so a page refresh doesn't log the user out.
function loadSavedSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY));
  } catch {
    return null;
  }
}

function App() {
  const [session, setSession] = useState(loadSavedSession);
  const [currentPage, setCurrentPage] = useState("super_admin");

  function handleLogin(newSession) {
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(newSession));
    } catch {
      // Storage blocked (private window): the login still works until the page is refreshed.
    }
    setSession(newSession);
  }

  function handleLogout() {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {
      // Nothing saved, nothing to remove.
    }
    setSession(null);
    setCurrentPage("super_admin");
  }

  if (session === null) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <>
      <Navbar title="ResolveOps" session={session} onLogout={handleLogout}>
        <PageTabs pages={PAGES} currentPage={currentPage} onChange={setCurrentPage} />
      </Navbar>

      {currentPage === "user" && <UserPage token={session.token} onUnauthorized={handleLogout} />}
      {currentPage === "admin" && <AdminPage token={session.token} onUnauthorized={handleLogout} />}
      {currentPage === "super_admin" && <SuperAdminPage token={session.token} onUnauthorized={handleLogout} />}
    </>
  );
}

export default App;
