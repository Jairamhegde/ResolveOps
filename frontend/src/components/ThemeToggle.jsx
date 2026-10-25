import { useState } from "react";
import { applyTheme, savedTheme } from "../theme";
import { MoonIcon, SunIcon } from "./Icons";

// Switches between the white dashboard and the dark theme.
function ThemeToggle() {
  const [theme, setTheme] = useState(savedTheme);
  const next = theme === "dark" ? "light" : "dark";

  function toggle() {
    applyTheme(next);
    setTheme(next);
  }

  return (
    <button className="button button-subtle theme-toggle" type="button" onClick={toggle} title={`Switch to ${next} theme`}>
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      <span className="visually-hidden">Switch to {next} theme</span>
    </button>
  );
}

export default ThemeToggle;
