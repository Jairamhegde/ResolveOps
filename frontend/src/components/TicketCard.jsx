import Badge from "./Badge";
import { FLAG_TONES, PRIORITY_TONES, STATUS_TONES, readable, timeAgo } from "../ticketFormat";
import "./ticketcard.css";

// One ticket with its full text, status, priority and the AI suggested fix.
function TicketCard({ ticket }) {
  return (
    <article className="ticket-card">
      <header className="ticket-card-header">
        <div>
          <p className="ticket-card-text">{ticket.issue_text}</p>
          <p className="ticket-card-meta">
            #{ticket.id} · {readable(ticket.category) || "uncategorized"} · {timeAgo(ticket.created_at)}
          </p>
        </div>

        <div className="ticket-card-badges">
          <Badge tone={STATUS_TONES[ticket.status]}>{readable(ticket.status)}</Badge>
          {ticket.priority && <Badge tone={PRIORITY_TONES[ticket.priority]}>P{ticket.priority}</Badge>}
          {ticket.flag && ticket.flag !== "none" && <Badge tone={FLAG_TONES[ticket.flag]}>{readable(ticket.flag)}</Badge>}
        </div>
      </header>

      <div className="ticket-card-fix">
        <p className="ticket-card-fix-label">AI suggested fix</p>
        {ticket.suggested_fix ? (
          <p className="ticket-card-fix-text">{ticket.suggested_fix}</p>
        ) : (
          <p className="ticket-card-fix-empty">No fix suggested. This ticket went straight to IT support.</p>
        )}
      </div>
    </article>
  );
}

export default TicketCard;
