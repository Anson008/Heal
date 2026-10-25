import { useState, useEffect, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { predict } from "./api";
import "./App.css";
import SaplingLoader from "./saplingLoader";
import Navbar from "./navbar";
import FeedbackModal from "./FeedbackModal";
import Tutorial, { type TutorialStep } from "./Tutorial";
import defaultBeforeImageUrl from "./assets/before.jpeg";
import defaultAfterImageUrl from "./assets/after.jpeg";

const HEALTH_OUTCOMES = [
  "DIABETES",
  "COPD",
  "LPA",
  "STROKE",
  "MHLTH",
  "CHD",
] as const;

const HEALTH_OUTCOME_LABELS: Record<(typeof HEALTH_OUTCOMES)[number], string> =
  {
    DIABETES: "Diabetes",
    COPD: "Chronic Obstructive Pulmonary Disease",
    LPA: "Physical Inactivity",
    STROKE: "Stroke",
    MHLTH: "Poor Mental Health",
    CHD: "Coronary Heart Disease",
  };

function healthOutcomeLabel(code: string): string {
  return (
    HEALTH_OUTCOME_LABELS[code as keyof typeof HEALTH_OUTCOME_LABELS] ?? code
  );
}

const NATIONAL_AVERAGES: Record<
  (typeof HEALTH_OUTCOMES)[number],
  number | null
> = {
  DIABETES: 12,
  COPD: 6,
  LPA: 25.3,
  STROKE: 0.23,
  MHLTH: 12.5,
  CHD: 5,
};

function nationalAverage(code: string): number | null {
  return NATIONAL_AVERAGES[code as keyof typeof NATIONAL_AVERAGES] ?? null;
}

function ImageField({
  id,
  label,
  file,
  onChange,
  fullWidth,
}: {
  id: string;
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
  fullWidth?: boolean;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <div className={`field${fullWidth ? " full-width" : ""}`}>
      <label htmlFor={id}>
        {label} <span className="hint">JPG, JPEG, PNG, WEBP</span>
      </label>
      <label htmlFor={id} className="file-drop">
        <input
          id={id}
          type="file"
          accept="image/*"
          className="visually-hidden"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
        {previewUrl ? (
          <img
            src={previewUrl}
            alt={`${label} preview`}
            className="image-preview"
          />
        ) : (
          <span className="file-drop-placeholder">Click to select image</span>
        )}
      </label>
      {file && <p className="file-name">{file.name}</p>}
    </div>
  );
}

const INFO_POPUP_WIDTH = 230;

function InfoTooltip({
  id,
  text,
  openId,
  onToggle,
}: {
  id: string;
  text: string;
  openId: string | null;
  onToggle: (id: string) => void;
}) {
  const open = openId === id;
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  // The popup is rendered in a portal on document.body so it always floats
  // above overlays (e.g. the tutorial dimming) regardless of ancestor stacking
  // contexts. That means we position it manually from the button's rect.
  useLayoutEffect(() => {
    if (!open) return;

    const update = () => {
      const rect = btnRef.current?.getBoundingClientRect();
      if (!rect) return;
      const left = Math.max(
        8,
        Math.min(
          rect.right - INFO_POPUP_WIDTH,
          window.innerWidth - INFO_POPUP_WIDTH - 8,
        ),
      );
      setPos({ top: rect.bottom + 8, left });
    };

    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  return (
    <span className="info-tooltip">
      <button
        ref={btnRef}
        type="button"
        className="info-tooltip-btn"
        onClick={() => onToggle(id)}
        aria-label="More information"
      >
        ?
      </button>
      {open &&
        pos &&
        createPortal(
          <div
            className="info-tooltip-popup info-tooltip-popup--floating"
            style={{ top: pos.top, left: pos.left, width: INFO_POPUP_WIDTH }}
          >
            <p>{text}</p>
            <button
              type="button"
              className="info-tooltip-close"
              onClick={() => onToggle(id)}
            >
              Close
            </button>
          </div>,
          document.body,
        )}
    </span>
  );
}

type PredictionResponse = {
  prediction: number;
  interval: [number, number] | null;
  confidence: number | null;
  warnings: string[];
};

// The API qualifies every prediction with an interval and a list of ways the
// request sits outside what the model was validated on. Reading only the
// scalar threw all of that away.
function parsePrediction(result: unknown): PredictionResponse | null {
  if (typeof result !== "object" || result === null) return null;
  const body = result as Record<string, unknown>;

  const raw = body.prediction;
  const prediction = typeof raw === "number" ? raw : parseFloat(String(raw));
  if (Number.isNaN(prediction)) return null;

  const bounds = body.prediction_interval;
  const interval =
    Array.isArray(bounds) &&
    bounds.length === 2 &&
    bounds.every((n) => typeof n === "number")
      ? ([bounds[0], bounds[1]] as [number, number])
      : null;

  return {
    prediction,
    interval,
    confidence:
      typeof body.interval_confidence === "number"
        ? body.interval_confidence
        : null,
    warnings: Array.isArray(body.warnings)
      ? body.warnings.filter((note): note is string => typeof note === "string")
      : [],
  };
}

function halfWidth(interval: [number, number] | null): number | null {
  return interval ? (interval[1] - interval[0]) / 2 : null;
}

const TRACT_POPULATION_MIN = 1800;
const TRACT_POPULATION_MAX = 3000;

const DEFAULT_LATITUDE = 40.719;
const DEFAULT_LONGITUDE = -73.9908;
const DEFAULT_LENGTH = 800;
const DEFAULT_WIDTH = 800;

// Raw (unrounded) projected case count for a percentage-point rate over a population.
function casesForPopulation(
  percentagePoints: number,
  population: number,
): number {
  return (Math.abs(percentagePoints) / 100) * population;
}

function caseRange(percentagePoints: number): { low: number; high: number } {
  return {
    low: Math.round(casesForPopulation(percentagePoints, TRACT_POPULATION_MIN)),
    high: Math.round(
      casesForPopulation(percentagePoints, TRACT_POPULATION_MAX),
    ),
  };
}

const countFormatter = new Intl.NumberFormat("en-US");

function confidenceLabel(confidence: number | null | undefined): string {
  return confidence != null ? `${Math.round(confidence * 100)}%` : "95%";
}

async function loadImage(file: File): Promise<HTMLImageElement> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () =>
      reject(new Error(`Could not load ${file.name} as an image.`));
    image.src = dataUrl;
  });
}

// Resamples the image so every output pixel represents exactly 1m^2
async function resizeImageToMeters(
  file: File,
  widthMeters: number,
  lengthMeters: number,
): Promise<File> {
  const image = await loadImage(file);

  const targetW = Math.max(1, Math.round(widthMeters));
  const targetH = Math.max(1, Math.round(lengthMeters));

  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Canvas is not supported in this browser.");
  }
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(image, 0, 0, targetW, targetH);

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/png"),
  );
  if (!blob) {
    throw new Error(`Failed to resize ${file.name}.`);
  }

  const baseName = file.name.replace(/\.[^./\\]+$/, "");
  return new File([blob], `${baseName}-1px1m.png`, { type: "image/png" });
}

async function urlToFile(url: string, filename: string): Promise<File> {
  const response = await fetch(url);
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type });
}

type PredictionResult = {
  value: number;
  mode: "difference" | "single";
  healthOutcome: string;
  beforeValue?: number;
  afterValue?: number;
  // Single mode: the interval on the prevalence itself. Difference mode: the
  // half-width of the interval on the before/after change, in points.
  interval?: [number, number] | null;
  changeMargin?: number | null;
  confidence?: number | null;
};

// First-visit walkthrough. Each step spotlights the form section tagged with the
// matching data-tut attribute below. Edit the `body` text freely.
const TUTORIAL_STEPS: TutorialStep[] = [
  {
    selector: '[data-tut="mode"]',
    title: "Comparison Mode",
    body: "This tool estimates the average prevalence of a selected health outcome within a census tract in relation to greenspace. Choose whether to compare two images or analyze a single image.",
  },
  {
    selector: '[data-tut="imagery"]',
    title: "Imagery",
    body: "Upload a top-down image in PNG, JPEG, JPG, or WEBP format. When comparing two images, make sure they show the same area at the same dimensions. The provided sample images are available for testing.",
  },
  {
    selector: '[data-tut="location"]',
    title: "Location",
    body: "Enter the latitude and longitude of the area. These coordinates identify the census tract used for the estimate. For the most reliable results, use a location in the United States.",
  },
  {
    selector: '[data-tut="dimensions"]',
    title: "Area Size",
    body: "Enter the dimensions of the area in meters. Length measures the vertical distance, and width measures the horizontal distance. Each value must be between 1 and 16,384 meters.",
  },
  {
    selector: '[data-tut="healthOutcome"]',
    title: "Health Outcome",
    body: "Select the health outcome to estimate from the greenspace shown in your image. The result is an average prevalence estimate for the selected census tract, not an individual diagnosis.",
  },
  {
    selector: '[data-tut="submit"]',
    title: "Run the Prediction",
    body: "Run the prediction to analyze the image or images. The result shows the estimated prevalence; in comparison mode, it also summarizes the estimated change between the before and after images.",
    dismissOnClick: true,
  },
];

function App() {
  const [healthOutcome, setHealthOutcome] = useState<string>(
    HEALTH_OUTCOMES[5],
  );
  const [mode, setMode] = useState<"compare" | "single">("compare");
  const [longitude, setLongitude] = useState("");
  const [latitude, setLatitude] = useState("");
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [beforeImage, setBeforeImage] = useState<File | null>(null);
  const [afterImage, setAfterImage] = useState<File | null>(null);
  const [singleImage, setSingleImage] = useState<File | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [openTooltipId, setOpenTooltipId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      urlToFile(defaultBeforeImageUrl, "before.jpeg"),
      urlToFile(defaultAfterImageUrl, "after.jpeg"),
    ])
      .then(([before, after]) => {
        setBeforeImage(before);
        setAfterImage(after);
        // Single-image mode uses one image; default it to the "after" image.
        setSingleImage(after);
      })
      .catch(() => {
        // Defaults are a convenience; leave fields empty if they fail to load.
      });
  }, []);

  function toggleTooltip(id: string) {
    setOpenTooltipId((current) => (current === id ? null : id));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setWarnings([]);
    setResult(null);

    if (mode === "compare") {
      if (!beforeImage || !afterImage) {
        setError("Select both a before and after image to continue.");
        return;
      }
    } else if (!singleImage) {
      setError("Select an image to continue.");
      return;
    }

    const allLocationFieldsEmpty =
      !latitude.trim() && !longitude.trim() && !length.trim() && !width.trim();

    const parsedLatitude = allLocationFieldsEmpty
      ? DEFAULT_LATITUDE
      : parseFloat(latitude);
    const parsedLongitude = allLocationFieldsEmpty
      ? DEFAULT_LONGITUDE
      : parseFloat(longitude);

    if (Number.isNaN(parsedLatitude)) {
      setError("Enter a valid latitude.");
      return;
    }
    if (parsedLatitude < -90 || parsedLatitude > 90) {
      setError("Latitude must be between -90 and 90.");
      return;
    }

    if (Number.isNaN(parsedLongitude)) {
      setError("Enter a valid longitude.");
      return;
    }
    if (parsedLongitude < -180 || parsedLongitude > 180) {
      setError("Longitude must be between -180 and 180.");
      return;
    }

    const parsedLength = allLocationFieldsEmpty
      ? DEFAULT_LENGTH
      : parseFloat(length);
    const parsedWidth = allLocationFieldsEmpty
      ? DEFAULT_WIDTH
      : parseFloat(width);

    if (Number.isNaN(parsedLength) || parsedLength <= 0) {
      setError("Enter a valid length (in meters).");
      return;
    }
    if (parsedLength > 16384) {
      setError("Length must be less than 16384 meters.");
      return;
    }
    if (Number.isNaN(parsedWidth) || parsedWidth <= 0) {
      setError("Enter a valid width (in meters).");
      return;
    }
    if (parsedWidth > 16384) {
      setError("Width must be less than 16384 meters.");
      return;
    }

    async function runPrediction(
      image: File,
      label: string,
    ): Promise<PredictionResponse> {
      const resized = await resizeImageToMeters(
        image,
        parsedWidth,
        parsedLength,
      );
      const data = await predict({
        healthOutcome,
        longitude: parsedLongitude,
        latitude: parsedLatitude,
        image: resized,
      });
      const parsed = parsePrediction(data);
      if (parsed === null) {
        throw new Error(`${label} did not return a numeric prediction.`);
      }
      return parsed;
    }

    setLoading(true);

    try {
      if (mode === "compare" && beforeImage && afterImage) {
        const [before, after] = await Promise.all([
          runPrediction(beforeImage, "Before image"),
          runPrediction(afterImage, "After image"),
        ]);

        // The two predictions carry independent errors of the same size, so the
        // error on their difference is the larger sqrt(2) times one of them.
        const beforeMargin = halfWidth(before.interval);
        const afterMargin = halfWidth(after.interval);

        setWarnings([...new Set([...before.warnings, ...after.warnings])]);
        setResult({
          value:
            ((before.prediction - after.prediction) / before.prediction) * 100,
          mode: "difference",
          healthOutcome,
          beforeValue: before.prediction,
          afterValue: after.prediction,
          changeMargin:
            beforeMargin != null && afterMargin != null
              ? Math.hypot(beforeMargin, afterMargin)
              : null,
          confidence: before.confidence,
        });
      } else if (singleImage) {
        const single = await runPrediction(singleImage, "Image");

        setWarnings(single.warnings);
        setResult({
          value: single.prediction,
          mode: "single",
          healthOutcome,
          interval: single.interval,
          confidence: single.confidence,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar onFeedback={() => setShowFeedback(true)} />

      <FeedbackModal
        open={showFeedback}
        onClose={() => setShowFeedback(false)}
      />

      <Tutorial steps={TUTORIAL_STEPS} />

      <div className="page">
        <div className="panel">
          <p className="eyebrow">HEAL</p>
          <h1 className="title">Run a prediction</h1>
          <p className="subtitle">
            Provide a location, size, and an image to predict what health impact
            an area can have on the community per year.
          </p>

          <div className="card">
            <form onSubmit={handleSubmit}>
              <div className="field" data-tut="mode">
                <label htmlFor="mode">Comparison Mode</label>
                <select
                  id="mode"
                  value={mode}
                  onChange={(e) =>
                    setMode(e.target.value as "compare" | "single")
                  }
                >
                  <option value="compare">Compare Two Images</option>
                  <option value="single">Raw Percentage for One Image</option>
                </select>
                <InfoTooltip
                  id="imagery"
                  text="Compare two images to estimate the change between a before and after image. Calculate the raw percentage to estimate the selected health outcome for a single image; the U.S. average is shown as a reference in the results."
                  openId={openTooltipId}
                  onToggle={toggleTooltip}
                />
              </div>

              <div className="field field-row" data-tut="imagery">
                {mode === "compare" ? (
                  <>
                    <ImageField
                      id="beforeImage"
                      label="Before Image"
                      file={beforeImage}
                      onChange={setBeforeImage}
                    />
                    <ImageField
                      id="afterImage"
                      label="After Image"
                      file={afterImage}
                      onChange={setAfterImage}
                    />
                  </>
                ) : (
                  <ImageField
                    id="singleImage"
                    label="Image"
                    file={singleImage}
                    onChange={setSingleImage}
                    fullWidth
                  />
                )}
              </div>

              <div className="field field-row" data-tut="location">
                <div>
                  <label htmlFor="latitude">Latitude</label>
                  <input
                    id="latitude"
                    type="number"
                    step="any"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="40.7190"
                  />
                </div>
                <div>
                  <label htmlFor="longitude">Longitude</label>
                  <input
                    id="longitude"
                    type="number"
                    step="any"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="-73.9908"
                  />
                </div>
                <InfoTooltip
                  id="location"
                  text="Enter the coordinates of the area you want to analyze. The coordinates identify the census tract used for the estimate."
                  openId={openTooltipId}
                  onToggle={toggleTooltip}
                />
              </div>

              <div className="field field-row" data-tut="dimensions">
                <div>
                  <label htmlFor="length">Length in Meters</label>
                  <input
                    id="length"
                    type="number"
                    min="1"
                    max="16384"
                    step="any"
                    value={length}
                    onChange={(e) => setLength(e.target.value)}
                    placeholder="800"
                  />
                </div>
                <div>
                  <label htmlFor="width">Width in Meters</label>
                  <input
                    id="width"
                    type="number"
                    min="1"
                    max="16384"
                    step="any"
                    value={width}
                    onChange={(e) => setWidth(e.target.value)}
                    placeholder="800"
                  />
                </div>
                <InfoTooltip
                  id="dimensions"
                  text="Enter the area dimensions in meters. Length is the vertical measurement and width is the horizontal measurement. Each value must be between 1 and 16,384 meters."
                  openId={openTooltipId}
                  onToggle={toggleTooltip}
                />
              </div>

              <div className="field" data-tut="healthOutcome">
                <label htmlFor="healthOutcome">Health Outcome</label>
                <select
                  id="healthOutcome"
                  value={healthOutcome}
                  onChange={(e) => setHealthOutcome(e.target.value)}
                >
                  {HEALTH_OUTCOMES.map((outcome) => (
                    <option key={outcome} value={outcome}>
                      {HEALTH_OUTCOME_LABELS[outcome]}
                    </option>
                  ))}
                </select>
                <InfoTooltip
                  id="healthOutcome"
                  text="Select the health outcome to estimate from the greenspace shown in your image. The result is an average prevalence estimate for the selected census tract, not an individual diagnosis."
                  openId={openTooltipId}
                  onToggle={toggleTooltip}
                />
              </div>

              <button
                type="submit"
                className="submit"
                disabled={loading}
                data-tut="submit"
              >
                {loading ? (
                  "Running prediction…"
                ) : (
                  <>
                    Run Prediction
                    <svg
                      className="submit-arrow"
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      aria-hidden="true"
                    >
                      <path
                        d="M2 8h11M9 4l4 4-4 4"
                        stroke="currentColor"
                        strokeWidth="1.75"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </>
                )}
              </button>

              {loading && (
                <>
                  <SaplingLoader />
                  <p className="loading-hint">This could take a few minutes.</p>
                </>
              )}
            </form>

            {error && <div className="status error">{error}</div>}

            {warnings.length > 0 && (
              <div className="status warning">
                <p className="status-heading">
                  This request sits outside what the model was validated on:
                </p>
                <ul>
                  {warnings.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {result != null && (
              <div
                className={`result ${
                  result.mode === "difference" && result.value < 0
                    ? "result-negative"
                    : ""
                }`}
              >
                <p className="result-label">Result</p>
                <div className="prediction-value">
                  <span className="prediction-text">
                    {Math.abs(result.value).toFixed(2)}%
                    {result.mode === "difference" && (
                      <> {result.value >= 0 ? "reduction" : "increase"}</>
                    )}
                  </span>
                </div>
                {(() => {
                  const outcomeLabel = healthOutcomeLabel(result.healthOutcome);
                  const avg = nationalAverage(result.healthOutcome);
                  const population = `${countFormatter.format(
                    TRACT_POPULATION_MIN,
                  )}–${countFormatter.format(TRACT_POPULATION_MAX)}`;

                  if (
                    result.mode === "difference" &&
                    result.beforeValue != null &&
                    result.afterValue != null
                  ) {
                    const pp = result.beforeValue - result.afterValue;
                    const improved = result.value >= 0;
                    const cases = caseRange(pp);
                    const margin = result.changeMargin;
                    const confidence = confidenceLabel(result.confidence);
                    // A change the interval brackets with zero is smaller than
                    // the model's own error on held-out tracts.
                    const indistinguishable =
                      margin != null && Math.abs(pp) < margin;

                    return (
                      <>
                        <p className="prediction-caption">
                          relative {improved ? "reduction" : "increase"} in{" "}
                          {outcomeLabel} prevalence
                        </p>

                        <dl className="result-metrics">
                          <div>
                            <dt>Prevalence</dt>
                            <dd>
                              {result.beforeValue.toFixed(2)}% &rarr;{" "}
                              {result.afterValue.toFixed(2)}%
                            </dd>
                          </div>
                          <div>
                            <dt>Absolute change</dt>
                            <dd>
                              {improved ? "−" : "+"}
                              {Math.abs(pp).toFixed(2)} percentage points
                            </dd>
                          </div>
                          {margin != null && (
                            <div>
                              <dt>{confidence} interval</dt>
                              <dd>
                                {(pp - margin).toFixed(2)} to{" "}
                                {(pp + margin).toFixed(2)} points
                              </dd>
                            </div>
                          )}
                          <div>
                            <dt>U.S. average</dt>
                            <dd>{avg != null ? `${avg.toFixed(2)}%` : "—"}</dd>
                          </div>
                        </dl>

                        <div className="result-impact">
                          <p className="result-impact-label">
                            Projected impact &mdash; community of {population}
                          </p>
                          <ul>
                            <li>
                              &asymp; {countFormatter.format(cases.low)}&ndash;
                              {countFormatter.format(cases.high)}{" "}
                              {improved ? "fewer" : "additional"} {outcomeLabel}{" "}
                              cases per year
                            </li>
                          </ul>
                        </div>

                        <div className="result-footnotes">
                          {indistinguishable && (
                            <p>
                              The interval spans zero: the difference between
                              these two images is smaller than the model’s own
                              error on held-out tracts, so its direction is not
                              established.
                            </p>
                          )}
                          <p>
                            This is a statistical estimate from a predictive
                            model, not a clinical diagnosis or guaranteed
                            outcome. The model is fitted to how greenspace and
                            health vary together across census tracts, which is
                            not the same as what changing the greenspace on one
                            site would do.
                          </p>
                        </div>
                      </>
                    );
                  }

                  const cases = caseRange(result.value);
                  return (
                    <>
                      <p className="prediction-caption">
                        estimated {outcomeLabel} prevalence
                      </p>

                      <dl className="result-metrics">
                        {result.interval && (
                          <div>
                            <dt>
                              {confidenceLabel(result.confidence)} interval
                            </dt>
                            <dd>
                              {result.interval[0].toFixed(2)}% &ndash;{" "}
                              {result.interval[1].toFixed(2)}%
                            </dd>
                          </div>
                        )}
                        <div>
                          <dt>U.S. average</dt>
                          <dd>{avg != null ? `${avg.toFixed(2)}%` : "—"}</dd>
                        </div>
                      </dl>

                      <div className="result-impact">
                        <p className="result-impact-label">
                          Projected for a community of {population}
                        </p>
                        <ul>
                          <li>
                            &asymp; {countFormatter.format(cases.low)}&ndash;
                            {countFormatter.format(cases.high)} {outcomeLabel}{" "}
                            cases per year
                          </li>
                        </ul>
                      </div>

                      <div className="result-footnotes">
                        <p>
                          This is a statistical estimate from a predictive
                          model, not a clinical diagnosis or guaranteed outcome.
                          The interval is the model’s error on held-out tracts,
                          measured in the configuration this API runs in.
                        </p>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
