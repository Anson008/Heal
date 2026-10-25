import numpy as np

import artifacts


def test_round_trips_through_disk(models):
    saved = artifacts.load(models / "MHLTH")
    reloaded = artifacts.load(models / "MHLTH")

    probe = np.random.default_rng(0).uniform(0, 100, (5, len(saved.features)))
    # Forests accumulate across threads, so compare with a tolerance.
    assert np.allclose(saved.forest.predict(probe), reloaded.forest.predict(probe))

    coords = np.array([[34.0, -84.0], [40.7, -74.0]])
    assert np.array_equal(saved.kriging.predict(coords), reloaded.kriging.predict(coords))


def test_metadata_survives(models):
    bundle = artifacts.load(models / "MHLTH")

    assert bundle.metric == "MHLTH"
    assert bundle.features[0] == "Per_olderA"
    assert "LandArea_s" in bundle.imputation_means
    assert set(bundle.feature_ranges) == set(bundle.features)
    assert bundle.meta["kriging"]["coord_order"] == ["latitude", "longitude"]
