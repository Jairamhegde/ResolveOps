import { Component } from "react";

// If a page throws while rendering (for example the backend is mid-deploy and sends an older response),
// show a way out instead of a blank screen. React only supports this as a class component.
class CrashScreen extends Component {
  state = { crashed: false };

  static getDerivedStateFromError() {
    return { crashed: true };
  }

  render() {
    if (!this.state.crashed) return this.props.children;

    return (
      <main className="crash-screen">
        <div className="error-message" role="alert">
          <p>The dashboard couldn't show this page. The server may be updating; try again in a minute.</p>
          <button className="button" type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </main>
    );
  }
}

export default CrashScreen;
