"""Train one metric end to end."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import artifacts
import kriging

from . import dataset, forest


@dataclass
class Result:
    """A trained metric, scored and ready to be written out."""

    metric: str
    forest: RandomForestRegressor
    kriging: kriging.Model
    max_features: int
    imputation_means: dict[str, float]
    feature_ranges: dict[str, list[float]]
    scores: dict[str, float]
    n_train: int
    n_test: int

    def bundle(self) -> artifacts.Bundle:
        """Repackage as the artifact writer's input."""
        return artifacts.Bundle(
            metric=self.metric,
            forest=self.forest,
            kriging=self.kriging,
            features=dataset.FEATURES,
            imputation_means=self.imputation_means,
            feature_ranges=self.feature_ranges,
            scores=self.scores,
            meta={"n_train": self.n_train, "n_test": self.n_test},
        )


def run(
    metric: str,
    frame: pd.DataFrame | None = None,
    seed: int = 0,
    max_features: int | None = None,
) -> Result:
    """Fit both stages for one metric and score them on the held out tracts."""
    frame = dataset.load() if frame is None else frame
    train, test = dataset.split(frame, seed=seed)

    X = dataset.features(train)
    y = dataset.target(train, metric)
    model = forest.fit(X, y, max_features=max_features, seed=seed)
    spatial = kriging.fit(dataset.coords(train), forest.residuals(model, X, y))

    actual = dataset.target(test, metric)
    correction = spatial.predict(dataset.coords(test))
    predicted = model.predict(dataset.features(test))
    corrected = predicted + correction

    # What the service actually predicts. It receives only an image and a
    # coordinate, so the eight unknown features fall back to training means,
    # and the honest error of a served prediction is measured that way.
    means = dataset.imputation_means(train)
    served_features = dataset.features(test)
    for column, mean in means.items():
        served_features[:, dataset.FEATURES.index(column)] = mean
    served = model.predict(served_features) + correction

    return Result(
        metric=metric,
        forest=model,
        kriging=spatial,
        max_features=model.get_params()["max_features"],
        imputation_means=means,
        feature_ranges=dataset.feature_ranges(train),
        scores={
            "oob_r2": float(model.oob_score_),
            "test_r2_forest": float(r2_score(actual, predicted)),
            "test_r2": float(r2_score(actual, corrected)),
            "test_mae": float(mean_absolute_error(actual, corrected)),
            "test_rmse": float(np.sqrt(mean_squared_error(actual, corrected))),
            "test_r2_served": float(r2_score(actual, served)),
            "test_rmse_served": float(np.sqrt(mean_squared_error(actual, served))),
        },
        n_train=len(train),
        n_test=len(test),
    )
