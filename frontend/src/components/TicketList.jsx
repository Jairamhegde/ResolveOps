import Badge from "./Badge";
import Panel from "./Panel";
import "./ticketlist.css";

const PRIORITY_TONES = { 1: "critical", 2: "serious", 3: "warning" };
const STATUS_TONES = { resolved: "good", active: "info" };
const FLAG_TONES = { injection: "critical", spam: "serious", unclear: "warning", ai_failed: "warning" };

function timeAgo(dateText) {
  if (!dateText) return "date unknown";

  const minutes = Math.floor((Date.now() - new Date(dateText)) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  return `${Math.floor(hours / 24)}d ago`;
}

// "pending_response" -> "pending response"
function readable(text) {
  return (text || "").replaceAll("_", " ");
}

// A list of tickets in a panel. `showFlag` shows why the AI flagged a ticket instead of its status.
function TicketList({ title, subtitle, tickets, emptyMessage, showFlag = false }) {
  return (
    <Panel title={title} subtitle={subtitle}>
      {tickets.length === 0 ? (
        <p className="ticket-list-empty">{emptyMessage}</p>
      ) : (
        <ul className="ticket-list">
          {tickets.map((ticket) => (
            <li key={ticket.id} className="ticket-row">
              <div className="ticket-main">
                <p className="ticket-text" title={ticket.issue_text}>{ticket.issue_text}</p>
                <p className="ticket-meta">
                  #{ticket.id} · {readable(ticket.category) || "uncategorized"} · {timeAgo(ticket.created_at)}
                </p>
              </div>

              <div className="ticket-badges">
                {showFlag ? (
                  <Badge tone={FLAG_TONES[ticket.flag]}>{readable(ticket.flag)}</Badge>
                ) : (
                  <Badge tone={STATUS_TONES[ticket.status]}>{readable(ticket.status)}</Badge>
                )}
                {ticket.priority && <Badge tone={PRIORITY_TONES[ticket.priority]}>P{ticket.priority}</Badge>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export default TicketList;
