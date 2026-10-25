"""The two stage prediction, and the checks that qualify it."""

import numpy as np
from artifacts import Bundle

import config
import landscape

# Out-of-range values in these say the imagery does not resolve greenspace the
# way the 1 m training classification did, rather than describing the site.
# The other four computed features are not checked: COHESION and AI are
# normalised and say little on their own, CA scales with the extent so it
# restates the area check, and PLAND is checked against the paper's envelope
# below. Checking all seven put at least one warning on ~30% of the training
# tracts themselves, which taught readers to ignore the whole set.
GRANULARITY = ["PD", "AREA_MN_Me", "SHAPE_AM"]

CONFIDENCE = 0.95
Z_SCORE = 1.959963984540054

# A degree of latitude is ~111 km everywhere and longitude scales by cos(lat).
# This only has to tell "inside a training city" from "a different state", so
# the spherical approximation is far more precision than it needs.
KM_PER_DEGREE = 111.0

# Beyond three correlation ranges the Gaussian process term is numerically
# zero, and the kriging correction is the fitted linear trend in latitude and
# longitude, extrapolated with no nearby data behind it.
RANGES_BEYOND_TRAINING = 3.0


def interval(bundle: Bundle, value: float) -> list[float] | None:
    """A 95% prediction interval, or None if the bundle records no error.

    Uses the error measured in the configuration the service actually runs in,
    with the unknown features imputed. `test_rmse` is the fallback for bundles
    trained before that was recorded, and it is far too narrow: it describes a
    model given true socio-demographics, which a request never supplies.
    """
    rmse = bundle.scores.get("test_rmse_served", bundle.scores.get("test_rmse"))
    if rmse is None:
        return None

    margin = Z_SCORE * rmse

    # These are prevalence percentages, so the lower bound cannot go negative.
    return [max(0.0, value - margin), value + margin]


def nearest_training_tract(bundle: Bundle, latitude: float, longitude: float) -> float:
    """Kilometres from this location to the closest tract the model was fit on."""
    coords = np.asarray(bundle.kriging.coords, dtype=float)
    north = coords[:, 0] - latitude
    east = (coords[:, 1] - longitude) * np.cos(np.radians(latitude))

    return float(np.hypot(north, east).min() * KM_PER_DEGREE)


def coverage(bundle: Bundle, latitude: float, longitude: float) -> str | None:
    """A note if the location is outside the training set's spatial reach.

    The training tracts come from five metropolitan areas. Anywhere else the
    spatial stage has no neighbouring residual to read and falls back to a
    plane in latitude and longitude, which is the one input dimension where the
    model extrapolates with no data at all.
    """
    distance = nearest_training_tract(bundle, latitude, longitude)
    reach = RANGES_BEYOND_TRAINING * bundle.kriging.range * KM_PER_DEGREE

    if distance <= reach:
        return None

    return (
        f"the nearest tract this model was trained on is {distance:.0f} km away, "
        f"past the {reach:.0f} km reach of its fitted spatial correlation; the "
        "location correction here is an extrapolated trend rather than a local "
        "estimate"
    )


def warnings(
    bundle: Bundle,
    metrics: dict[str, float],
    hectares: float,
    latitude: float,
    longitude: float,
) -> list[str]:
    """Ways this request sits outside what the model was validated on.

    Deliberately few. A check that fires on inputs the model handles fine costs
    more than it earns, because it teaches whoever reads the list to skip it.
    """
    notes = []

    if not config.MIN_AREA_HECTARES <= hectares <= config.MAX_AREA_HECTARES:
        notes.append(
            f"image covers {hectares:.1f} ha, outside the model's validated range "
            f"of {config.MIN_AREA_HECTARES:.0f}-{config.MAX_AREA_HECTARES:.0f} ha"
        )

    greenspace = metrics["PLAND"]
    if not config.MIN_GREENSPACE_PERCENT <= greenspace <= config.MAX_GREENSPACE_PERCENT:
        notes.append(
            f"greenspace is {greenspace:.1f}%, outside the validated range of "
            f"{config.MIN_GREENSPACE_PERCENT:.0f}-{config.MAX_GREENSPACE_PERCENT:.0f}%"
        )

    # One note covering all three. They move together -- a coarse classification
    # shifts patch density, mean patch size and shape at once -- so reporting
    # them separately said the same thing up to three times.
    coarse = []
    for feature in GRANULARITY:
        span = bundle.feature_ranges.get(feature)
        if span is None or span[0] <= metrics[feature] <= span[1]:
            continue
        coarse.append(f"{feature} {metrics[feature]:.1f} vs {span[0]:.1f}-{span[1]:.1f}")

    if coarse:
        notes.append(
            f"patch structure is outside the training range ({'; '.join(coarse)}); "
            "the imagery may not resolve greenspace at the 1 m granularity the "
            "model was trained on"
        )

    out_of_coverage = coverage(bundle, latitude, longitude)
    if out_of_coverage:
        notes.append(out_of_coverage)

    return notes


def predict(bundle: Bundle, image, longitude: float, latitude: float):
    """Forest prediction plus the kriged residual correction for the location."""
    metrics = landscape.metrics(image)

    # Socio-demographics and the tract's land area are unknown from an image, so
    # the bundle's training means stand in for them.
    row = {**bundle.imputation_means, **metrics}
    features = np.array([[row[name] for name in bundle.features]])

    correction = bundle.kriging.predict([[latitude, longitude]])[0]
    value = float(bundle.forest.predict(features)[0] + correction)

    width, height = image.size
    hectares = width * height / 10_000

    return (
        value,
        hectares,
        interval(bundle, value),
        warnings(bundle, metrics, hectares, latitude, longitude),
    )
