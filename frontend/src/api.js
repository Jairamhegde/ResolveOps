const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchOverview() {
  const response = await fetch(`${API_URL}/api/dashboard/overview`);

  if (!response.ok) {
    throw new Error("Could not load the dashboard overview");
  }

  return response.json();
}
