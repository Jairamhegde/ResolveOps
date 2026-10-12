import { useState } from "react";
import { login } from "../api";
import "./loginpage.css";

// The demo super admin made by scripts/create_demo_admins.py. They are filled in so a visitor only clicks "Sign in".
const DEMO_EMAIL = "super@demo.com";
const DEMO_PASSWORD = "demo-super-123";

// The email/password form. Calls onLogin({ token, email, role }) when the login works.
function LoginPage({ onLogin }) {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setErrorMessage("");

    login(email, password)
      .then(onLogin)
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setLoading(false));
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <span className="login-logo">R</span>
        <h1 className="login-title">Sign in to ResolveOps</h1>
        <p className="login-subtitle">IT support dashboard</p>
        <p className="login-hint">Demo account: the details are filled in, just click Sign in.</p>

        <label className="login-label">
          Email
          <input
            className="login-input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className="login-label">
          Password
          <input
            className="login-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {errorMessage && <p className="login-error">{errorMessage}</p>}

        <button className="login-button" type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}

export default LoginPage;
