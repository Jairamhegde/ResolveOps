const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Called when the server says the login token is missing or expired. App sets it to "log out".
let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

// `kind` is "admin" or "employee": each has its own login endpoint.
export async function login(email, password, kind) {
  const path = kind === "employee" ? "/api/auth/employee-login" : "/api/auth/login";
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error("Can't reach the server. Check that the backend is running and allows this address (CORS).");
  }

  if (response.status === 401) {
    throw new Error(`That email and password don't match an ${kind === "employee" ? "employee" : "admin"} account.`);
  }
  if (!response.ok) {
    throw new Error("The server couldn't sign you in. Try again in a moment.");
  }

  return response.json();
}

// GET a dashboard endpoint with the login token.
async function get(path, token) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    onUnauthorized();
    throw new Error("Your session has ended. Sign in again.");
  }
  if (!response.ok) {
    throw new Error("The server didn't answer. Try again in a moment.");
  }

  return response.json();
}

// `category` is optional: leave it empty for every category (super admins only).
function categoryQuery(category) {
  return category ? `?category=${encodeURIComponent(category)}` : "";
}

export function fetchSummary(token, category) {
  return get(`/api/dashboard/summary${categoryQuery(category)}`, token);
}

export function fetchTickets(token, category) {
  return get(`/api/dashboard/tickets${categoryQuery(category)}`, token);
}

export function fetchUsers(token) {
  return get("/api/dashboard/users", token);
}

export function fetchUserDashboard(token, slackId) {
  return get(`/api/dashboard/users/${encodeURIComponent(slackId)}`, token);
}

export function fetchAdmins(token) {
  return get("/api/dashboard/admins", token);
}

export function fetchMyTickets(token) {
  return get("/api/dashboard/my-tickets", token);
}
