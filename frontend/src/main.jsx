import { createRoot } from "react-dom/client";
import App from "./App";
import CrashScreen from "./components/CrashScreen";
import { applyTheme, savedTheme } from "./theme";
import "./index.css";

applyTheme(savedTheme());

createRoot(document.getElementById("root")).render(
  <CrashScreen>
    <App />
  </CrashScreen>
);
