"""Load the HEALstrata tract table and split it into train/test sets."""

from pathlib import Path

import numpy as np
import pandas as pd

# Predictor order taken from train.R's randomForest formula. R's formula
# interface binds columns by name, sklearn binds them by position, so this
# order is canonical and must be reused when building a prediction row.
FEATURES = [
    "Per_olderA",
    "Per_female",
    "Per_white",
    "Income",
    "Per_bachel",
    "PLAND",
    "PD",
    "AREA_MN_Me",
    "SHAPE_AM",
    "COHESION",
    "AI",
    "LandArea_s",
    "CA",
    "PopuDensit",
    "Population",
]

# Predictors unknown at prediction time, where only an image and a coordinate
# are supplied; the training set mean of each is substituted. LandArea_s is the
# tract's own land area in square miles, which the paper groups with the
# socio-demographic variables -- predict.R deriving it from image dimensions is
# a bug, so it is imputed here too.
IMPUTED = [
    "Population",
    "PopuDensit",
    "Per_olderA",
    "Per_female",
    "Per_white",
    "Income",
    "Per_bachel",
    "LandArea_s",
]

METRICS = ["MHLTH", "COPD", "LPA", "DIABETES", "STROKE", "CHD"]

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "data.csv"


def load(path: Path = DEFAULT_PATH) -> pd.DataFrame:
    """Read the tract table, failing loudly if an expected column is absent."""
    frame = pd.read_csv(path)

    missing = [c for c in (*FEATURES, *METRICS, "X", "Y") if c not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

    return frame


def split(frame: pd.DataFrame, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split 70/30, mirroring train.R's `floor(nrow(data) * 0.70)`."""
    size = int(np.floor(len(frame) * 0.70))
    shuffled = np.random.default_rng(seed).permutation(len(frame))

    return frame.iloc[shuffled[:size]], frame.iloc[shuffled[size:]]


def features(frame: pd.DataFrame) -> np.ndarray:
    """Predictor matrix in FEATURES order."""
    return frame[FEATURES].to_numpy(dtype=float)


def target(frame: pd.DataFrame, metric: str) -> np.ndarray:
    """Health outcome column for one metric."""
    if metric not in METRICS:
        raise ValueError(f"Unknown metric {metric!r}, expected one of {METRICS}")

    return frame[metric].to_numpy(dtype=float)


def coords(frame: pd.DataFrame) -> np.ndarray:
    """Kriging coordinates as (latitude, longitude).

    X holds longitude and Y latitude, so this reproduces train.R's
    `s = cbind(train$Y, train$X)`.
    """
    return frame[["Y", "X"]].to_numpy(dtype=float)


def imputation_means(frame: pd.DataFrame) -> dict[str, float]:
    """Training set means the API substitutes for the unknown predictors."""
    return {c: float(frame[c].mean()) for c in IMPUTED}


def feature_ranges(frame: pd.DataFrame) -> dict[str, list[float]]:
    """Training min/max per feature, so the API can flag extrapolation.

    The full extent rather than p5/p95. The API reports these as "the training
    range", and quantiles put 10% of the training tracts themselves outside
    every range by construction, so the warnings they produced were mostly
    describing inputs the model handles perfectly well.
    """
    return {
        column: [float(frame[column].min()), float(frame[column].max())]
        for column in FEATURES
    }
