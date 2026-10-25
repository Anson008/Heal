// A document for building a landing page

import { useEffect, useRef, useState } from "react";
import "./Home.css";
import Navbar from "./navbar";
import FeedbackModal from "./FeedbackModal";
import { useNavigate } from "./Router";

export default function Home() {
  const bgRef = useRef<HTMLImageElement>(null);
  const navigate = useNavigate();
  const [showFeedback, setShowFeedback] = useState(false);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) return;

    let ticking = false;

    const updatePosition = () => {
      if (bgRef.current) {
        bgRef.current.style.transform = `translate3d(0, ${
          window.scrollY * 0.35
        }px, 0)`;
      }
      ticking = false;
    };

    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(updatePosition);
        ticking = true;
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="page">
      <Navbar onFeedback={() => setShowFeedback(true)} />

      <FeedbackModal
        open={showFeedback}
        onClose={() => setShowFeedback(false)}
      />

      <img
        ref={bgRef}
        className="page__bg"
        src="/gradient_landscape_plans.jpg"
        alt=""
        aria-hidden="true"
      />
      <div className="page__overlay" />

      <section className="hero__content">
        <h1 className="hero__title">
          What if human health was the design priority?
        </h1>
        <button
          type="button"
          className="hero__cta"
          onClick={() => navigate("/tool")}
        >
          Use the HEAL Tool
        </button>
        <section className="section_break">
          <h2 className="section_break__title">About</h2>
          <p className="section_break__description">
            We offer proven predictive health modeling to help communities and
            developers build better by design.
          </p>
          <p className="about_text">
            Our patent-pending HEAL Tool uses multi-layered AI modeling to
            predict the impacts of greenspace decisions in urban development.
          </p>
        </section>
        <section className="section_break">
          <h2 className="section_break__title">Contact Us</h2>
          <div className="contact_list">
            <div className="contact_person">
              <p className="contact_name">Vikki Ballard</p>
              <p className="contact_title">Chief Executive Officer</p>
              <a className="contact_email" href="mailto:vikki@healstrata.com">
                vikki@healstrata.com
              </a>
            </div>
            <div className="contact_person">
              <p className="contact_name">Carter Johnson</p>
              <p className="contact_title">Chief Technology Officer</p>
              <a className="contact_email" href="mailto:carter@healstrata.com">
                carter@healstrata.com
              </a>
            </div>
            <div className="contact_person">
              <p className="contact_name">Dallin Tew</p>
              <p className="contact_title">Chief Product Officer</p>
              <a className="contact_email" href="mailto:dallin@healstrata.com">
                dallin@healstrata.com
              </a>
            </div>
          </div>
        </section>
      </section>
    </div>
  );
}
