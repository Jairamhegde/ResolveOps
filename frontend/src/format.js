// Labels and formatting shared by the pages. Kept in one place so every page names things the same way.

export const CATEGORIES = [
  { value: "network", label: "Network" },
  { value: "hardware", label: "Hardware" },
  { value: "software", label: "Software" },
  { value: "account_access", label: "Account access" },
  { value: "other", label: "Other" },
];

export const PRIORITIES = {
  1: { label: "Critical", tone: "critical" },
  2: { label: "High", tone: "high" },
  3: { label: "Medium", tone: "medium" },
  4: { label: "Low", tone: "low" },
  5: { label: "Minimal", tone: "low" },
};

export const STATUSES = {
  active: { label: "With IT", tone: "info" },
  pending_response: { label: "Waiting on employee", tone: "warning" },
  resolved: { label: "Resolved", tone: "good" },
};

// The admin type stored in admin.role, as people read it.
const ROLE_LABELS = {
  super_admin: "Super admin",
  network: "Network admin",
  hardware: "Hardware admin",
  software: "Software admin",
  iam: "Account access admin",
  other: "Other issues admin",
  employee: "User",
};

export function roleLabel(role) {
  return ROLE_LABELS[role] || role;
}

export function categoryLabel(category) {
  const normalized = (category || "").toLowerCase().replaceAll(" ", "_");
  const match = CATEGORIES.find((item) => item.value === normalized);
  return match ? match.label : "Uncategorized";
}

export function ticketKey(ticket) {
  return `RO-${ticket.id}`;
}

export function isHighSeverity(ticket) {
  return ticket.priority <= 2;
}

// The backend sends some timestamps without a time zone, but they are all UTC.
function parseUtc(text) {
  return new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(text) ? text : `${text}Z`);
}

// "18 Oct 2026, 20:32" in the viewer's time zone.
export function formatTimestamp(text) {
  if (!text) return "Unknown";
  return parseUtc(text).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// "3h ago", "4d ago"
export function timeAgo(text) {
  if (!text) return "";
  const minutes = Math.floor((Date.now() - parseUtc(text)) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// Must match SLA_WINDOWS in backend/sla.py. P1 is never escalated.
const SLA_HOURS = { 2: 2, 3: 6, 4: 12, 5: 24 };

// When the SLA job will raise this ticket's priority, or "" when it never will.
export function slaText(ticket) {
  const hours = SLA_HOURS[ticket.priority];
  const since = ticket.escalated_at || ticket.created_at;
  if (ticket.status !== "active" || !hours || !since) return "";

  const minutesLeft = Math.round((parseUtc(since).getTime() + hours * 3600000 - Date.now()) / 60000);
  if (minutesLeft <= 0) return `Past its ${hours}h window. Moves to P${ticket.priority - 1} at the next SLA check.`;
  const left = minutesLeft < 60 ? `${minutesLeft}m` : `${Math.floor(minutesLeft / 60)}h ${minutesLeft % 60}m`;
  return `Moves to P${ticket.priority - 1} in ${left} if no one resolves it.`;
}
