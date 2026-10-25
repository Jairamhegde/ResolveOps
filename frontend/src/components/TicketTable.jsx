import { FlagLabel, PriorityLabel, StatusLabel } from "./Labels";
import { Person } from "./Avatar";
import { categoryLabel, formatTimestamp, ticketKey, timeAgo } from "../format";
import "./tickettable.css";

// A dense, Jira-style ticket table. Clicking a row (or pressing Enter on it) calls onSelect(ticket).
// `showReporter` adds the employee column, which the employee page leaves out.
function TicketTable({ tickets, onSelect, selectedId, showReporter = true, emptyMessage }) {
  if (tickets.length === 0) {
    return <p className="table-empty">{emptyMessage}</p>;
  }

  return (
    <div className="table-scroll">
      <table className="ticket-table">
        <thead>
          <tr>
            <th scope="col">Key</th>
            <th scope="col">Summary</th>
            {showReporter && <th scope="col">Raised by</th>}
            <th scope="col">Category</th>
            <th scope="col">Priority</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className={ticket.id === selectedId ? "ticket-row ticket-row-selected" : "ticket-row"}
              tabIndex={0}
              onClick={() => onSelect(ticket)}
              onKeyDown={(event) => event.key === "Enter" && onSelect(ticket)}
            >
              <td className="cell-key">{ticketKey(ticket)}</td>
              <td className="cell-summary">
                <span className={ticket.issue_text ? "summary-text" : "summary-text summary-missing"}>
                  {ticket.issue_text || "No description given"}
                </span>
                <FlagLabel flag={ticket.flag} />
              </td>
              {showReporter && (
                <td>
                  <Person name={ticket.reporter} />
                </td>
              )}
              <td className="cell-muted">{categoryLabel(ticket.category)}</td>
              <td>
                <PriorityLabel priority={ticket.priority} />
              </td>
              <td>
                <StatusLabel status={ticket.status} />
              </td>
              <td className="cell-time" title={timeAgo(ticket.created_at)}>
                {formatTimestamp(ticket.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default TicketTable;
