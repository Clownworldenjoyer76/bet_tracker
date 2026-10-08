import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import "../../app/frontend/src/assets/css/matstheme.css";
import "../../app/frontend/src/assets/css/site-polish.css";
import "./styles/react-transitions.css";

import App from "./App";

const root = document.getElementById("root");

if (!root) {
  throw new Error("React root element was not found.");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter useTransitions>
      <App />
    </BrowserRouter>
  </StrictMode>
);
