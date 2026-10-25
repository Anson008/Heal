"""Trained bundles, read once at startup and held in memory."""

from pathlib import Path

import artifacts

_loaded: dict[str, artifacts.Bundle] = {}


def load(directory: Path) -> list[str]:
    """Read every bundle directory under `directory`, keyed by metric."""
    if not directory.is_dir():
        raise RuntimeError(f"No model directory at {directory}")

    _loaded.clear()
    for path in sorted(p for p in directory.iterdir() if p.is_dir()):
        bundle = artifacts.load(path)

        # One row gains nothing from fanning across cores, and a single thread
        # makes responses byte-for-byte reproducible.
        bundle.forest.n_jobs = 1
        _loaded[bundle.metric] = bundle

    if not _loaded:
        raise RuntimeError(f"No bundles found under {directory}")

    return available()


def get(metric: str) -> artifacts.Bundle | None:
    return _loaded.get(metric)


def available() -> list[str]:
    return sorted(_loaded)
