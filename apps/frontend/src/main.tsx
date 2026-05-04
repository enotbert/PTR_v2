import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Only register service worker in production builds
if (import.meta.env.PROD) {
  // Register service worker for offline support
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js");
    });
  }
}

const el = document.getElementById("root");
if (!el) {
  throw new Error('Missing root element with id "root"');
}

createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
);