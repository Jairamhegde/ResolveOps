import Badge from "./Badge";
import Panel from "./Panel";
import { FLAG_TONES, PRIORITY_TONES, STATUS_TONES, readable, timeAgo } from "../ticketFormat";
import "./ticketlist.css";

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
