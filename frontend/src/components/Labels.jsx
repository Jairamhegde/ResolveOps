import { PRIORITIES, STATUSES } from "../format";
import { PriorityIcon, SparkleIcon } from "./Icons";
import "./labels.css";

// Which arrow each priority gets, from two arrows up (P1) to two arrows down (P5).
const PRIORITY_LEVELS = { 1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal" };

// "P1 Critical" with a Jira-style arrow coloured by urgency.
export function PriorityLabel({ priority }) {
  const info = PRIORITIES[priority];
  if (!info) return <span className="priority">No priority</span>;

  const level = PRIORITY_LEVELS[priority];
  return (
    <span className={`priority priority-${level}`}>
      <PriorityIcon level={level} />
      <span className="priority-number">P{priority}</span>
      {info.label}
    </span>
  );
}

// A status lozenge: with IT, waiting on the employee, or resolved.
export function StatusLabel({ status }) {
  const info = STATUSES[status] || { label: status, tone: "neutral" };
  return <span className={`lozenge lozenge-${info.tone}`}>{info.label}</span>;
}

// Why the AI guard held a ticket for review.
const FLAG_LABELS = { injection: "Prompt injection", spam: "Spam", unclear: "Unclear", ai_failed: "AI failed" };

export function FlagLabel({ flag }) {
  if (!flag || flag === "none") return null;
  return <span className="lozenge lozenge-critical lozenge-subtle">{FLAG_LABELS[flag] || flag}</span>;
}

export function AiLabel() {
  return (
    <span className="lozenge lozenge-ai">
      <SparkleIcon />
      Fixed by AI
    </span>
  );
}
