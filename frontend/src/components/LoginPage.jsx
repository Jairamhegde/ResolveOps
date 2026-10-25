import { useState } from "react";
import { login } from "../api";
import { BrandMark } from "./Icons";
import ThemeToggle from "./ThemeToggle";
import "./loginpage.css";

// The three ways in, in this order. Each is a demo account made by scripts/create_demo_admins.py,
// so a visitor can try every view with one click. `kind` picks the login endpoint.
const ROLES = [
  {
    id: "admin",
    label: "Admin",
    kind: "admin",
    email: "network@demo.com",
    password: "demo-network-123",
    about: "Work the tickets in your own field.",
  },
  {
    id: "super_admin",
    label: "Super admin",
    kind: "admin",
    email: "super@demo.com",
    password: "demo-super-123",
    about: "See every ticket, every field and every admin.",
  },
  {
    id: "user",
    label: "User",
    kind: "employee",
    email: "jairamkansur@gmail.com",
    password: "demo-user-123",
    about: "Follow the tickets you raised in Slack.",
  },
];

// The sign-in form. Calls onLogin(session) when the login works.
// `notice` explains why the user is here, for example after their session ran out.
function LoginPage({ onLogin, notice }) {
  const [roleId, setRoleId] = useState(ROLES[0].id);
  const [email, setEmail] = useState(ROLES[0].email);
  const [password, setPassword] = useState(ROLES[0].password);
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const role = ROLES.find((item) => item.id === roleId);

  function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setErrorMessage("");

    login(email, password, role.kind)
      .then(onLogin)
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setLoading(false));
  }

  function pickRole(newRole) {
    setRoleId(newRole.id);
    setEmail(newRole.email);
    setPassword(newRole.password);
    setErrorMessage("");
  }

  return (
    <main className="login-page">
      <div className="login-theme">
        <ThemeToggle />
      </div>

      <div className="login-column">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-brand">
            <BrandMark />
            ResolveOps
          </div>

          <h1 className="login-title">Sign in to continue</h1>

          {notice && (
            <p className="login-notice" role="status">
              {notice}
            </p>
          )}

          <fieldset className="login-roles">
            <legend className="field">Sign in as</legend>
            <div className="login-role-options">
              {ROLES.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={option.id === roleId ? "login-role login-role-active" : "login-role"}
                  aria-pressed={option.id === roleId}
                  onClick={() => pickRole(option)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <p className="login-role-about">{role.about}</p>
          </fieldset>

          <label className="field">
            Email
            <input
              className="field-control login-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="field">
            Password
            <input
              className="field-control login-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {errorMessage && (
            <p className="login-error" role="alert">
              {errorMessage}
            </p>
          )}

          <button className="button button-primary login-button" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>

          <p className="login-hint">Demo details are filled in for each role. Just pick one and sign in.</p>
        </form>

        <p className="login-footer">IT tickets raised in Slack, triaged by AI, tracked here.</p>
      </div>
    </main>
  );
}

export default LoginPage;
