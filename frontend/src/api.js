const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function login(email, password) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (response.status === 401) {
    throw new Error("Wrong email or password");
  }
  if (!response.ok) {
    throw new Error("Could not log in. Is the backend running?");
  }

  return response.json();
}

// GET a dashboard endpoint with the login token.
// Throws "UNAUTHORIZED" when the token is missing or expired, so the page can send the user back to the login page.
async function getWithToken(path, token) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    throw new Error("UNAUTHORIZED");
  }
  if (!response.ok) {
    throw new Error("REQUEST_FAILED");
  }

  return response.json();
}

export function fetchOverview(token) {
  return getWithToken("/api/dashboard/overview", token);
}

export function fetchUsers(token) {
  return getWithToken("/api/dashboard/users", token);
}

export function fetchUserTickets(token, slackId) {
  return getWithToken(`/api/dashboard/user-tickets?slack_id=${encodeURIComponent(slackId)}`, token);
}

export function fetchCategoryTickets(token, category) {
  return getWithToken(`/api/dashboard/category-tickets?category=${encodeURIComponent(category)}`, token);
}
