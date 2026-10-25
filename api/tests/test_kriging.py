import numpy as np
from scipy.linalg import cho_factor
from scipy.spatial.distance import cdist, pdist, squareform

import kriging


def sample(rows=120, seed=0):
    rng = np.random.default_rng(seed)
    points = rng.uniform(0, 10, (rows, 2))
    distances = squareform(pdist(points))
    covariance = 2.0 * np.exp(-distances / 3.0) + 0.5 * np.eye(rows)
    values = np.linalg.cholesky(covariance) @ rng.standard_normal(rows)

    return points, values


def test_matches_the_augmented_universal_kriging_system():
    """The dual form must agree with the bordered Lagrange formulation."""
    points, values = sample()
    model = kriging.fit(points, values)
    rows = len(points)

    covariance = model.sill * np.exp(-squareform(pdist(points)) / model.range)
    covariance += model.nugget * np.eye(rows)
    design = np.column_stack([np.ones(rows), points])
    system = np.block([[covariance, design], [design.T, np.zeros((3, 3))]])

    probes = np.random.default_rng(1).uniform(0, 10, (20, 2))
    reference = []
    for probe in probes:
        right = np.concatenate(
            [model.sill * np.exp(-cdist([probe], points)[0] / model.range), [1.0, *probe]]
        )
        reference.append(np.linalg.solve(system, right)[:rows] @ values)

    assert np.allclose(model.predict(probes), reference, atol=1e-9)


def test_interpolates_exactly_without_a_nugget():
    points, values = sample()
    model = kriging.fit(points, values)
    rows = len(points)

    correlation = np.exp(-squareform(pdist(points)) / model.range) + 1e-12 * np.eye(rows)
    design = np.column_stack([np.ones(rows), points])
    betas, residuals = kriging._generalised_least_squares(
        cho_factor(correlation, lower=True), design, values
    )
    model.betas = betas
    model.weights = np.linalg.solve(correlation, residuals)

    assert np.allclose(model.predict(points), values, atol=1e-6)


def test_predicts_a_single_location_and_a_batch():
    points, values = sample()
    model = kriging.fit(points, values)

    assert model.predict(points[0]).shape == (1,)
    assert model.predict(points[:7]).shape == (7,)
