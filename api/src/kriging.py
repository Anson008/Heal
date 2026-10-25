"""Universal kriging over the forest's residuals.

Replaces geoR's likfit / krige.control / krige.conv. The model is

    y(s) = [1, lat, lon] . beta + Z(s) + noise

with Z an isotropic Gaussian process under an exponential covariance,
    C(h) = sill * exp(-h / range),
and an independent nugget. Covariance parameters are fitted by maximum
likelihood, matching likfit rather than the least squares variogram fits
that GSTools and PyKrige perform.
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import LinAlgError, cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.spatial.distance import cdist, pdist, squareform

MAX_ITERATIONS = 200


def _design(coords: np.ndarray) -> np.ndarray:
    """Trend design matrix, mirroring geoR's `trend = ~ s[,1] + s[,2]`."""
    return np.column_stack([np.ones(len(coords)), coords])


def _generalised_least_squares(
    factored: tuple, design: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Trend coefficients and residuals under a factored correlation matrix."""
    weighted = cho_solve(factored, design)
    betas = np.linalg.solve(design.T @ weighted, weighted.T @ values)

    return betas, values - design @ betas


def _negative_log_likelihood(
    log_parameters: np.ndarray,
    distances: np.ndarray,
    design: np.ndarray,
    values: np.ndarray,
) -> float:
    """Profiled likelihood over the range and the nugget-to-sill ratio.

    The sill has a closed form given the other two, so it is profiled out
    rather than optimised, which keeps the search two dimensional.
    """
    scale, ratio = np.exp(log_parameters)

    correlation = np.exp(-distances / scale)
    correlation[np.diag_indices_from(correlation)] += ratio

    try:
        factored = cho_factor(correlation, lower=True, overwrite_a=True)
    except LinAlgError:
        return np.inf

    _, residuals = _generalised_least_squares(factored, design, values)
    sill = residuals @ cho_solve(factored, residuals) / len(values)
    log_determinant = 2 * np.sum(np.log(np.diag(factored[0])))

    return len(values) * np.log(sill) + log_determinant


@dataclass
class Model:
    """A fitted kriging model, stored as plain numbers and arrays."""

    coords: np.ndarray  # (n, 2) training locations, (latitude, longitude)
    weights: np.ndarray  # (n,) dual weights; see predict
    betas: np.ndarray  # (3,) trend coefficients for [1, lat, lon]
    sill: float
    range: float
    nugget: float

    def predict(self, at: np.ndarray) -> np.ndarray:
        """Krige at one or more (latitude, longitude) locations.

        The sill cancels between the covariance vector and the weights, so
        this needs only the correlation function. Cost is one distance
        calculation against the training locations, not a solve.
        """
        at = np.atleast_2d(at)
        correlation = np.exp(-cdist(at, self.coords) / self.range)

        return _design(at) @ self.betas + correlation @ self.weights


def fit(coords: np.ndarray, values: np.ndarray) -> Model:
    """Fit covariance parameters and the trend by maximum likelihood."""
    distances = squareform(pdist(coords))
    design = _design(coords)

    # train.R's starting range. A nugget equal to the partial sill is a
    # neutral start; likfit begins from a fixed guess in the same way.
    span = distances.max()
    start = np.log([span / 3, 1.0])

    # Wide enough that a real optimum is always interior, bounded so that
    # degenerate input cannot walk the search out to where exp() overflows.
    bounds = [
        (np.log(span * 1e-6), np.log(span * 1e2)),
        (np.log(1e-10), np.log(1e10)),
    ]

    fitted = minimize(
        _negative_log_likelihood,
        start,
        args=(distances, design, values),
        method="Nelder-Mead",
        bounds=bounds,
        options={"maxiter": MAX_ITERATIONS},
    )
    scale, ratio = np.exp(fitted.x)

    # Recover the profiled sill and the trend at the optimum.
    correlation = np.exp(-distances / scale)
    correlation[np.diag_indices_from(correlation)] += ratio
    factored = cho_factor(correlation, lower=True, overwrite_a=True)

    betas, residuals = _generalised_least_squares(factored, design, values)
    weights = cho_solve(factored, residuals)
    sill = float(residuals @ weights / len(values))

    return Model(
        coords=coords,
        weights=weights,
        betas=betas,
        sill=sill,
        range=float(scale),
        nugget=float(ratio * sill),
    )
