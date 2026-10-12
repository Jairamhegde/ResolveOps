import { useEffect, useState } from "react";
import { fetchCategoryTickets } from "../api";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import TicketCard from "../components/TicketCard";
import "./adminpage.css";

// For the demo the admin page shows one category.
// Later this will come from the logged-in admin's type (network, hardware, software, ...).
const ADMIN_CATEGORY = "network";

// What a network admin works on: every network ticket, most urgent first.
function AdminPage({ token, onUnauthorized }) {
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    fetchCategoryTickets(token, ADMIN_CATEGORY)
      .then((data) => setResult(data))
      .catch((error) => {
        if (error.message === "UNAUTHORIZED") {
          onUnauthorized();
        } else {
          setErrorMessage("Could not load the tickets. Is the backend running?");
        }
      });
  }, [token]);

  return (
    <main className="dashboard">
      <PageHeader title="Network admin" subtitle="Tickets the AI classified as network issues, most urgent first" />

      {errorMessage && <p className="dashboard-message dashboard-error">{errorMessage}</p>}

      {!errorMessage && result === null && <p className="dashboard-message">Loading tickets...</p>}

      {result !== null && (
        <>
          <section className="admin-kpi-row">
            <StatCard label="Network tickets" value={result.total} hint="raised in Slack" />
            <StatCard label="Open" value={result.open} hint="waiting for a fix" />
            <StatCard label="Needs review" value={result.needs_review} hint="flagged by the AI guard" />
          </section>

          {result.tickets.length === 0 && <p className="dashboard-message">No network tickets yet.</p>}

          <section className="admin-ticket-list">
            {result.tickets.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          </section>
        </>
      )}
    </main>
  );
}

export default AdminPage;
