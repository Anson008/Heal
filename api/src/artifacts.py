"""Read and write trained model bundles.

A bundle is a directory per health outcome:

    rf.joblib   the fitted forest, the only pickled object
    krige.npz   the kriging model's arrays
    meta.json   scalars and provenance, readable without unpickling anything
"""

import json
import sys
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

import kriging

SCHEMA_VERSION = 1

FOREST_FILE = "rf.joblib"
KRIGING_FILE = "krige.npz"
META_FILE = "meta.json"

TRACKED_PACKAGES = ["numpy", "scipy", "scikit-learn", "joblib"]


@dataclass
class Bundle:
    """One trained health outcome, in memory."""

    metric: str
    forest: RandomForestRegressor
    kriging: kriging.Model
    features: list[str]
    imputation_means: dict[str, float]
    feature_ranges: dict[str, list[float]]
    scores: dict[str, float]
    meta: dict = field(default_factory=dict)


def _versions() -> dict[str, str]:
    installed = {name: version(name) for name in TRACKED_PACKAGES}

    return {"python": sys.version.split()[0], **installed}


def save(bundle: Bundle, directory: Path) -> Path:
    """Write a bundle, creating the directory if needed."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    forest_params = bundle.forest.get_params()

    joblib.dump(bundle.forest, directory / FOREST_FILE, compress=3)

    np.savez_compressed(
        directory / KRIGING_FILE,
        coords=bundle.kriging.coords,
        weights=bundle.kriging.weights,
        betas=bundle.kriging.betas,
    )

    meta = {
        "schema_version": SCHEMA_VERSION,
        "metric": bundle.metric,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "features": bundle.features,
        "imputation_means": bundle.imputation_means,
        "feature_ranges": bundle.feature_ranges,
        "scores": bundle.scores,
        "forest": {
            "n_estimators": forest_params["n_estimators"],
            "max_features": forest_params["max_features"],
            "min_samples_leaf": forest_params["min_samples_leaf"],
            "random_state": forest_params["random_state"],
        },
        "kriging": {
            "cov_model": "exponential",
            "sill": bundle.kriging.sill,
            "range": bundle.kriging.range,
            "nugget": bundle.kriging.nugget,
            "n_locations": len(bundle.kriging.coords),
            # Recorded so the serving side cannot guess the convention wrong.
            "coord_order": ["latitude", "longitude"],
            "coord_units": "degrees",
        },
        "versions": _versions(),
        **bundle.meta,
    }

    (directory / META_FILE).write_text(json.dumps(meta, indent=2) + "\n")

    return directory


def load(directory: Path) -> Bundle:
    """Read a bundle back, warning if it was written by other library versions."""
    directory = Path(directory)
    meta = json.loads((directory / META_FILE).read_text())

    if meta["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"{directory} uses schema {meta['schema_version']}, "
            f"expected {SCHEMA_VERSION}"
        )

    current = _versions()
    changed = [
        f"{name} {was} -> {current[name]}"
        for name, was in meta["versions"].items()
        if name in current and current[name] != was
    ]
    if changed:
        warnings.warn(
            f"{directory} was trained under {', '.join(changed)}. "
            "Pickled forests are not guaranteed to load correctly across "
            "versions; retrain if predictions look wrong.",
            stacklevel=2,
        )

    arrays = np.load(directory / KRIGING_FILE)
    parameters = meta["kriging"]

    return Bundle(
        metric=meta["metric"],
        forest=joblib.load(directory / FOREST_FILE),
        kriging=kriging.Model(
            coords=arrays["coords"],
            weights=arrays["weights"],
            betas=arrays["betas"],
            sill=parameters["sill"],
            range=parameters["range"],
            nugget=parameters["nugget"],
        ),
        features=meta["features"],
        imputation_means=meta["imputation_means"],
        feature_ranges=meta.get("feature_ranges", {}),
        scores=meta["scores"],
        meta=meta,
    )
