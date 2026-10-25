// Light or dark theme. Light (the white dashboard) is the default; the choice is remembered in this browser.

const THEME_KEY = "resolveops-theme";

export function savedTheme() {
  try {
    return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

// index.css switches every colour on <html data-theme="dark">.
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#1a1a1e" : "#ffffff");
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // Storage blocked (private window): the theme still applies until the page is refreshed.
  }
}
