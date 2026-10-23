import { PRIORITIES, STATUSES } from "../format";
import "./labels.css";

// "P1 Critical" with a marker coloured by urgency.
export function PriorityLabel({ priority }) {
  const info = PRIORITIES[priority];
  if (!info) return <span className="priority">No priority</span>;

  return (
    <span className={`priority priority-${info.tone}`}>
      <span className="priority-marker" aria-hidden="true" />
      <span className="priority-number">P{priority}</span>
      {info.label}
    </span>
  );
}

// A tinted status label: with IT, waiting on the employee, or resolved.
export function StatusLabel({ status }) {
  const info = STATUSES[status] || { label: status, tone: "neutral" };
  return <span className={`lozenge lozenge-${info.tone}`}>{info.label}</span>;
}

// Why the AI guard held a ticket for review.
const FLAG_LABELS = { injection: "Prompt injection", spam: "Spam", unclear: "Unclear", ai_failed: "AI failed" };

export function FlagLabel({ flag }) {
  if (!flag || flag === "none") return null;
  return <span className="lozenge lozenge-critical">{FLAG_LABELS[flag] || flag}</span>;
}

export function AiLabel() {
  return <span className="lozenge lozenge-ai">Fixed by AI</span>;
}
