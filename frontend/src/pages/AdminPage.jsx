import { useEffect, useState } from "react";
import { fetchCategoryTickets } from "../api";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import TicketCard from "../components/TicketCard";
import "./adminpage.css";

// For the demo the admin page shows one category.
// Later this will come from the logged-in admin's type (network, hardware, software, ...).
const ADMIN_CATEGORY = "network";

const PRIORITY_OPTIONS = [
  { value: "all", label: "All priorities" },
  { value: "1", label: "P1 · Critical" },
  { value: "2", label: "P2 · High" },
  { value: "3", label: "P3 · Medium" },
  { value: "4", label: "P4 · Low" },
  { value: "5", label: "P5 · Minimal" },
];

// What a network admin works on: every network ticket, most urgent first.
function AdminPage({ token, onUnauthorized }) {
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedPriority, setSelectedPriority] = useState("all");

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

  // The tickets that match the chosen priority, or all of them.
  let shownTickets = [];
  if (result !== null) {
    shownTickets = result.tickets.filter(
      (ticket) => selectedPriority === "all" || ticket.priority === Number(selectedPriority)
    );
  }

  return (
    <main className="dashboard">
      <PageHeader title="Network admin" subtitle="Tickets the AI classified as network issues, most urgent first">
        <label className="priority-filter">
          Priority
          <select
            className="priority-filter-select"
            value={selectedPriority}
            onChange={(event) => setSelectedPriority(event.target.value)}
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </PageHeader>

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

          {result.tickets.length > 0 && shownTickets.length === 0 && (
            <p className="dashboard-message">No tickets with this priority.</p>
          )}

          <section className="admin-ticket-list">
            {shownTickets.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          </section>
        </>
      )}
    </main>
  );
}

export default AdminPage;
