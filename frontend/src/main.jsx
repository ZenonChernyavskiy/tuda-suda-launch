import React from "react";
import { createRoot } from "react-dom/client";
import { TonConnectUIProvider } from "@tonconnect/ui-react";

import App from "./App.jsx";
import "./styles.css";

const manifestUrl =
  import.meta.env.VITE_TONCONNECT_MANIFEST_URL ||
  `${window.location.origin}/tonconnect-manifest.json`;

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <TonConnectUIProvider manifestUrl={manifestUrl}>
      <App />
    </TonConnectUIProvider>
  </React.StrictMode>,
);
