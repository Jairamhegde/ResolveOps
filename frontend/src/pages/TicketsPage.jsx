import { useState } from "react";
import { fetchTickets } from "../api";
import { useApi } from "../useApi";
import { categoryLabel, isHighSeverity, ticketKey } from "../format";
import PageHeader from "../components/PageHeader";
import CategoryPicker from "../components/CategoryPicker";
import { ErrorMessage, Loading, Section } from "../components/Section";
import TicketTable from "../components/TicketTable";
import TicketDetails from "../components/TicketDetails";
import "./ticketspage.css";

// The quick filters above the table. Each is a test a ticket passes or fails.
const VIEWS = [
  { id: "all", label: "All", test: () => true },
  { id: "open", label: "Active", test: (ticket) => ticket.status !== "resolved" },
  { id: "high", label: "High severity", test: isHighSeverity },
  { id: "review", label: "Needs review", test: (ticket) => ticket.needs_review },
  { id: "resolved", label: "Closed", test: (ticket) => ticket.status === "resolved" },
];

function matchesSearch(ticket, search) {
  const text = `${ticketKey(ticket)} ${ticket.issue_text} ${ticket.reporter || ""}`.toLowerCase();
  return text.includes(search.trim().toLowerCase());
}

// Every ticket the admin can see, with quick filters, search and a details panel.
function TicketsPage({ token, isSuperAdmin }) {
  const [category, setCategory] = useState("");
  const [viewId, setViewId] = useState("open");
  const [search, setSearch] = useState("");
  const [selectedTicket, setSelectedTicket] = useState(null);

  const tickets = useApi(() => fetchTickets(token, category), [token, category]);

  const allTickets = tickets.data || [];
  const view = VIEWS.find((item) => item.id === viewId);
  const shownTickets = allTickets.filter((ticket) => view.test(ticket) && matchesSearch(ticket, search));

  return (
    <div className="page">
      <PageHeader
        title="Tickets"
        subtitle={category ? `${categoryLabel(category)} tickets` : "Click a ticket to see its details and timeline"}
        actions={isSuperAdmin && <CategoryPicker value={category} onChange={setCategory} />}
      />

      {tickets.error && <ErrorMessage message={tickets.error} onRetry={tickets.reload} />}
      {!tickets.data && !tickets.error && <Loading />}

      {tickets.data && (
        <Section
          title={`${shownTickets.length} ${shownTickets.length === 1 ? "ticket" : "tickets"}`}
          flush
          actions={
            <input
              className="field-control ticket-search"
              type="search"
              placeholder="Search text, RO-12 or a name"
              aria-label="Search tickets"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          }
        >
          <div className="view-tabs" role="group" aria-label="Show">
            {VIEWS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={item.id === viewId ? "view-tab view-tab-active" : "view-tab"}
                aria-pressed={item.id === viewId}
                onClick={() => setViewId(item.id)}
              >
                {item.label}
                <span className="view-tab-count">{allTickets.filter(item.test).length}</span>
              </button>
            ))}
          </div>

          <TicketTable
            tickets={shownTickets}
            onSelect={setSelectedTicket}
            selectedId={selectedTicket?.id}
            emptyMessage="No tickets match. Try another filter or clear the search."
          />
        </Section>
      )}

      {selectedTicket && <TicketDetails ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}

export default TicketsPage;
