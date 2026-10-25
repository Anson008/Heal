import { useEffect, useState } from "react";
import logoUrl from "./assets/HEALstrata_Logo_white.svg";
import { useNavigate } from "./Router";
const API_DOCS_URL = "/api/docs";
import "./navbar.css";

const MORE_INFO_URL =
  "https://research.usu.edu/rii/tech-transfer/licensing-opportunities/technologies/health-effect-assessment-of-landscape";

function Navbar({ onFeedback }: { onFeedback: () => void }) {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(
    () => typeof window !== "undefined" && window.scrollY > 8,
  );

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`navbar${scrolled ? " is-scrolled" : ""}`}>
      <button
        type="button"
        className="navbar-logo-btn"
        onClick={() => navigate("/")}
        aria-label="Go to home"
      >
        <img src={logoUrl} alt="HEALstrata" className="navbar-logo" />
      </button>

      <div className="navbar-actions">
        <button type="button" className="navbar-btn" onClick={onFeedback}>
          Feedback
        </button>
        <a
          href={MORE_INFO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="navbar-btn"
        >
          More info
        </a>
        <a
          href={API_DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="navbar-btn"
        >
          API docs
        </a>
      </div>
    </nav>
  );
}

export default Navbar;
