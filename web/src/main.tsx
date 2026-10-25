import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import Home from "./Home.tsx";
import Router from "./Router.tsx";

createRoot(document.getElementById("root")!).render(
  <Router routes={{ "/": <Home />, "/tool": <App /> }} />,
);
