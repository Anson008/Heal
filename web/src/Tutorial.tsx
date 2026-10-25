import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import "./tutorial.css";

export type TutorialStep = {
  /** CSS selector for the element to spotlight (usually a [data-tut="…"]). */
  selector: string;
  title: string;
  /** Description shown in the popup. Write these however you like. */
  body: string;
  /**
   * Close the walkthrough when the spotlighted element is clicked (e.g. the
   * final "Run prediction" step ends as soon as the user runs one).
   */
  dismissOnClick?: boolean;
};

const SPOTLIGHT_PAD = 10;
const CARD_WIDTH = 340;
const GAP = 16;

export default function Tutorial({ steps }: { steps: TutorialStep[] }) {
  const [active, setActive] = useState(() => steps.length > 0);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const step = steps[index];

  const measure = useCallback(() => {
    if (!step) return;
    const el = document.querySelector<HTMLElement>(step.selector);
    setRect(el ? el.getBoundingClientRect() : null);
  }, [step]);

  useLayoutEffect(() => {
    if (!active || !step) return;

    const el = document.querySelector<HTMLElement>(step.selector);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });

    measure();
    const timer = window.setTimeout(measure, 360);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [active, step, measure]);

  const finish = useCallback(() => {
    setActive(false);
  }, []);

  const next = useCallback(() => {
    setIndex((i) => {
      if (i >= steps.length - 1) {
        finish();
        return i;
      }
      return i + 1;
    });
  }, [steps.length, finish]);

  useEffect(() => {
    if (!active || !step?.dismissOnClick) return;
    const el = document.querySelector<HTMLElement>(step.selector);
    if (!el) return;
    el.addEventListener("click", finish);
    return () => el.removeEventListener("click", finish);
  }, [active, step, finish]);

  useEffect(() => {
    if (!active) return;
    document.documentElement.classList.add("tut-lock");
    return () => document.documentElement.classList.remove("tut-lock");
  }, [active]);

  useEffect(() => {
    if (!active) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        finish();
        return;
      }
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (
        e.key === "Enter" &&
        tag !== "INPUT" &&
        tag !== "SELECT" &&
        tag !== "TEXTAREA"
      ) {
        next();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, finish, next]);

  if (!active || !step) return null;

  const isLast = index >= steps.length - 1;

  const box = rect
    ? {
        top: rect.top - SPOTLIGHT_PAD,
        left: rect.left - SPOTLIGHT_PAD,
        width: rect.width + SPOTLIGHT_PAD * 2,
        height: rect.height + SPOTLIGHT_PAD * 2,
      }
    : null;

  let cardStyle: React.CSSProperties;
  let cardClass = "tut-card";

  if (box) {
    const placeAbove = box.top > 220;
    const left = Math.max(
      GAP,
      Math.min(box.left, window.innerWidth - CARD_WIDTH - GAP),
    );
    if (placeAbove) {
      cardStyle = { top: box.top - GAP, left };
      cardClass += " is-above";
    } else {
      cardStyle = { top: box.top + box.height + GAP, left };
    }
  } else {
    cardStyle = { top: "50%", left: "50%", transform: "translate(-50%, -50%)" };
  }

  return (
    <div
      className="tut"
      role="dialog"
      aria-modal="true"
      aria-label="Getting started guide"
    >
      {box ? (
        <>
          <div
            className="tut-spotlight"
            style={{
              top: box.top,
              left: box.left,
              width: box.width,
              height: box.height,
            }}
          />
          {/* Four blockers frame the highlighted area, dimming and capturing
              clicks everywhere except the hole so the user can still use the
              spotlighted controls. */}
          <div
            className="tut-block"
            style={{ top: 0, left: 0, right: 0, height: Math.max(0, box.top) }}
          />
          <div
            className="tut-block"
            style={{ top: box.top + box.height, left: 0, right: 0, bottom: 0 }}
          />
          <div
            className="tut-block"
            style={{
              top: box.top,
              left: 0,
              width: Math.max(0, box.left),
              height: box.height,
            }}
          />
          <div
            className="tut-block"
            style={{
              top: box.top,
              left: box.left + box.width,
              right: 0,
              height: box.height,
            }}
          />
        </>
      ) : (
        <div className="tut-scrim" />
      )}

      <div className={cardClass} style={cardStyle}>
        <p className="tut-step">
          Step {index + 1} of {steps.length}
        </p>
        <h3 className="tut-title">{step.title}</h3>
        <p className="tut-body">{step.body}</p>
        <div className="tut-actions">
          <button type="button" className="tut-skip" onClick={finish}>
            Skip Guide
          </button>
          <button type="button" className="tut-next" onClick={next} autoFocus>
            {isLast ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
