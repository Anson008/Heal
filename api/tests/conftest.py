import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sklearn.ensemble import RandomForestRegressor

import artifacts
import config
import kriging
from training import dataset


@pytest.fixture(scope="session")
def models(tmp_path_factory):
    """A tiny but structurally real bundle, so tests need no trained models."""
    rng = np.random.default_rng(0)
    rows = 60

    X = rng.uniform(0, 100, (rows, len(dataset.FEATURES)))
    forest = RandomForestRegressor(n_estimators=5, random_state=0).fit(
        X, X[:, 0] + rng.normal(0, 1, rows)
    )
    spatial = kriging.fit(
        rng.uniform([25, -125], [48, -80], (rows, 2)), rng.normal(0, 1, rows)
    )

    root = tmp_path_factory.mktemp("models")
    artifacts.save(
        artifacts.Bundle(
            metric="MHLTH",
            forest=forest,
            kriging=spatial,
            features=dataset.FEATURES,
            imputation_means=dict.fromkeys(dataset.IMPUTED, 1.0),
            feature_ranges={name: [0.0, 1e6] for name in dataset.FEATURES},
            scores={"test_r2": 0.9, "test_rmse": 0.8},
        ),
        root / "MHLTH",
    )
    return root


@pytest.fixture
def client(models, monkeypatch):
    monkeypatch.setattr(config.settings, "models_dir", models)
    from service.main import app

    with TestClient(app) as connected:
        yield connected


@pytest.fixture
def png():
    """A 100x100 m image, half of it green."""
    pixels = np.zeros((100, 100, 3), np.uint8)
    pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2] = 60, 120, 55
    pixels[:50] = (90, 90, 90)

    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    return buffer.getvalue()
