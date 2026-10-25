import { useEffect } from "react";
import { AiLabel, FlagLabel, PriorityLabel, StatusLabel } from "./Labels";
import { Person } from "./Avatar";
import { CloseIcon, SparkleIcon } from "./Icons";
import { categoryLabel, formatTimestamp, slaText, ticketKey, timeAgo } from "../format";
import "./ticketdetails.css";

// Who closed a resolved ticket: the AI's fix, or the Slack ID of the admin who ran /resolve.
function resolvedByText(ticket) {
  if (ticket.status !== "resolved") return "Not resolved yet";
  if (ticket.resolved_by === "ai") return "The AI's suggested fix";
  return ticket.resolved_by ? `IT admin (${ticket.resolved_by})` : "IT admin";
}

// Everything about one ticket, in a panel on the right like Jira's issue view. Escape or Close closes it.
function TicketDetails({ ticket, onClose }) {
  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const sla = slaText(ticket);

  return (
    <div className="details-backdrop" onClick={onClose}>
      <aside
        className="details"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="details-header">
          <p className="details-key">IT Support / {ticketKey(ticket)}</p>
          <button className="button button-subtle details-close" type="button" onClick={onClose} autoFocus aria-label="Close">
            <CloseIcon />
          </button>
        </header>

        <div className="details-body">
          <h2 id="details-title" className="details-title">
            {ticket.issue_text || "No description given"}
          </h2>

          <div className="details-labels">
            <StatusLabel status={ticket.status} />
            {ticket.resolved_by === "ai" && <AiLabel />}
            <FlagLabel flag={ticket.flag} />
          </div>

          <section className="details-fix">
            <h3 className="details-fix-title">
              <SparkleIcon />
              AI suggested fix
            </h3>
            <p>{ticket.suggested_fix || "No fix suggested. This ticket went straight to IT support."}</p>
          </section>

          {sla && <p className="details-sla">{sla}</p>}

          <section className="details-panel">
            <h3 className="details-panel-title">Details</h3>
            <dl className="details-fields">
              <dt>Priority</dt>
              <dd>
                <PriorityLabel priority={ticket.priority} />
              </dd>

              <dt>Category</dt>
              <dd>{categoryLabel(ticket.category)}</dd>

              <dt>Raised by</dt>
              <dd>
                <Person name={ticket.reporter} />
              </dd>

              <dt>Created</dt>
              <dd>
                {formatTimestamp(ticket.created_at)} <span className="details-muted">({timeAgo(ticket.created_at)})</span>
              </dd>

              <dt>Last escalated</dt>
              <dd>{ticket.escalated_at ? formatTimestamp(ticket.escalated_at) : "Never"}</dd>

              <dt>Resolved by</dt>
              <dd>{resolvedByText(ticket)}</dd>

              <dt>Needs review</dt>
              <dd>{ticket.needs_review ? "Yes, held by the AI guard" : "No"}</dd>
            </dl>
          </section>
        </div>
      </aside>
    </div>
  );
}

export default TicketDetails;
