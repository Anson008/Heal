"""Fit the random forest stage of the model."""

import numpy as np
from sklearn.ensemble import RandomForestRegressor

N_ESTIMATORS = 1500
TUNE_ESTIMATORS = 500  # train.R's tuneRF(ntreeTry = 500)
STEP_FACTOR = 1.5  # train.R's tuneRF(stepFactor = 1.5)

# randomForest's regression default. sklearn defaults to 1, which grows far
# larger trees than train.R did and bloats the saved model.
MIN_SAMPLES_LEAF = 5


def candidates(n_features: int) -> list[int]:
    """max_features values to try, mirroring tuneRF's search around p / 3."""
    start = max(1, n_features // 3)
    tried = {start}

    for direction in (STEP_FACTOR, 1 / STEP_FACTOR):
        value = start
        while True:
            value = int(value * direction)
            if not 1 <= value <= n_features or value in tried:
                break
            tried.add(value)

    return sorted(tried)


def _forest(max_features: int, n_estimators: int, seed: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_features=max_features,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        oob_score=True,
        random_state=seed,
        n_jobs=-1,
    )


def tune(X: np.ndarray, y: np.ndarray, seed: int = 0) -> int:
    """Pick max_features by out-of-bag error, standing in for tuneRF."""
    scored: dict[int, float] = {}

    for max_features in candidates(X.shape[1]):
        forest = _forest(max_features, TUNE_ESTIMATORS, seed).fit(X, y)
        scored[max_features] = float(np.mean((y - forest.oob_prediction_) ** 2))

    return min(scored, key=lambda max_features: scored[max_features])


def fit(
    X: np.ndarray,
    y: np.ndarray,
    max_features: int | None = None,
    seed: int = 0,
) -> RandomForestRegressor:
    """Fit the full forest, tuning max_features first when not supplied."""
    if max_features is None:
        max_features = tune(X, y, seed=seed)

    return _forest(max_features, N_ESTIMATORS, seed).fit(X, y)


def residuals(
    forest: RandomForestRegressor,
    X: np.ndarray,
    y: np.ndarray,
    oob: bool = True,
) -> np.ndarray:
    """Residuals for the kriging stage to model.

    Out-of-bag predictions are used by default. train.R differenced against
    in-sample predictions, which a 1500 tree forest fits closely enough that
    the residuals understate the error the model actually makes on new data.
    """
    predicted = forest.oob_prediction_ if oob else forest.predict(X)

    return y - predicted
