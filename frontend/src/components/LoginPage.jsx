import { useState } from "react";
import { login } from "../api";
import "./sidebar.css";
import "./loginpage.css";

const ACCOUNT_KINDS = [
  { id: "admin", label: "IT admin" },
  { id: "employee", label: "Employee" },
];

// Demo accounts made by scripts/create_demo_admins.py, so a visitor can try each view with one click.
const DEMO_ACCOUNTS = [
  { label: "Super admin", kind: "admin", email: "super@demo.com", password: "demo-super-123" },
  { label: "Network admin", kind: "admin", email: "network@demo.com", password: "demo-network-123" },
  { label: "Employee", kind: "employee", email: "employee@demo.com", password: "demo-employee-123" },
];

// The sign-in form for admins and employees. Calls onLogin(session) when the login works.
// `notice` explains why the user is here, for example after their session ran out.
function LoginPage({ onLogin, notice }) {
  const [kind, setKind] = useState("admin");
  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState(DEMO_ACCOUNTS[0].password);
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setErrorMessage("");

    login(email, password, kind)
      .then(onLogin)
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setLoading(false));
  }

  function pickKind(newKind) {
    const demo = DEMO_ACCOUNTS.find((account) => account.kind === newKind);
    setKind(newKind);
    setEmail(demo.email);
    setPassword(demo.password);
    setErrorMessage("");
  }

  function pickDemoAccount(account) {
    setKind(account.kind);
    setEmail(account.email);
    setPassword(account.password);
    setErrorMessage("");
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <span className="brand-mark" aria-hidden="true" />
          ResolveOps
        </div>

        <div>
          <h1 className="login-title">Sign in</h1>
          <p className="login-subtitle">
            {kind === "admin" ? "Track and resolve your team's IT tickets." : "See the tickets you raised in Slack and what happened to them."}
          </p>
        </div>

        {notice && (
          <p className="login-notice" role="status">
            {notice}
          </p>
        )}

        <div className="login-kinds" role="group" aria-label="Sign in as">
          {ACCOUNT_KINDS.map((option) => (
            <button
              key={option.id}
              type="button"
              className={option.id === kind ? "login-kind login-kind-active" : "login-kind"}
              aria-pressed={option.id === kind}
              onClick={() => pickKind(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>

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

        <button className="login-button" type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <div className="login-demo">
          <p>Demo accounts</p>
          <div className="login-demo-buttons">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className={account.email === email ? "login-demo-button login-demo-active" : "login-demo-button"}
                onClick={() => pickDemoAccount(account)}
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </main>
  );
}

export default LoginPage;
