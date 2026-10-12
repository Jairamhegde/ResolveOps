// Helpers for showing a ticket, shared by TicketList and TicketCard.

// Badge colour for each value. Anything not listed shows as "neutral" (grey).
export const PRIORITY_TONES = { 1: "critical", 2: "serious", 3: "warning" };
export const STATUS_TONES = { resolved: "good", active: "info" };
export const FLAG_TONES = { injection: "critical", spam: "serious", unclear: "warning", ai_failed: "warning" };

export function timeAgo(dateText) {
  if (!dateText) return "date unknown";

  const minutes = Math.floor((Date.now() - new Date(dateText)) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  return `${Math.floor(hours / 24)}d ago`;
}

// "pending_response" -> "pending response"
export function readable(text) {
  return (text || "").replaceAll("_", " ");
}
