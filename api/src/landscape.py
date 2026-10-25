"""Landscape metrics from an aerial image.

Reimplements the class-level FRAGSTATS 4.2 metrics the model was trained on.
The training columns came from FRAGSTATS itself, so the formulas here follow its
definitions rather than any library's approximation of them: patches are
delineated with the 8-neighbour rule, while perimeters, COHESION and AI count
4-neighbour cell surfaces.

`LandArea_s` is deliberately absent. The paper groups it with the
socio-demographic variables — it is the tract's own land area in square miles,
not a property of the uploaded image, and `predict.R` computing it from image
dimensions is a bug.
"""

import numpy as np
from scipy import ndimage

GREEN_THRESHOLD = 10
QUEEN = np.ones((3, 3), dtype=int)

FEATURES = ["CA", "PLAND", "PD", "AREA_MN_Me", "SHAPE_AM", "COHESION", "AI"]

EMPTY = dict.fromkeys(FEATURES, 0.0)


def green_mask(image) -> np.ndarray:
    """Classify greenspace, reproducing `(G - R > 10) & (G - B > 10)`.

    The int16 cast is load bearing. R promotes raster arithmetic to numeric, but
    numpy keeps uint8 and wraps, so `G=10, R=20` would give 246 and read as green.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    return (green - red > GREEN_THRESHOLD) & (green - blue > GREEN_THRESHOLD)


def _patch_areas_and_perimeters(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-patch cell counts and perimeters, both in cell units."""
    labels, count = ndimage.label(mask, structure=QUEEN)
    areas = np.bincount(labels.ravel(), minlength=count + 1)[1:]

    # A cell contributes 4 surfaces; every shared edge with a same-patch
    # neighbour hides two of them. Diagonal neighbours share no surface, which
    # is why this stays 4-neighbour even though patches are 8-connected.
    horizontal = labels[:, :-1]
    vertical = labels[:-1, :]
    shared_h = (horizontal == labels[:, 1:]) & (horizontal > 0)
    shared_v = (vertical == labels[1:, :]) & (vertical > 0)

    internal = np.bincount(
        np.concatenate([horizontal[shared_h], vertical[shared_v]]),
        minlength=count + 1,
    )[1:]

    return areas, 4 * areas - 2 * internal


def _like_adjacencies(mask: np.ndarray) -> int:
    """4-neighbour adjacencies between green cells, single count."""
    return int((mask[:, :-1] & mask[:, 1:]).sum() + (mask[:-1, :] & mask[1:, :]).sum())


def _max_like_adjacencies(cells: int) -> int:
    """The most adjacencies `cells` cells could have, as a compact square block."""
    side = int(np.sqrt(cells))
    remainder = cells - side * side

    if remainder == 0:
        return 2 * side * (side - 1)
    if remainder <= side:
        return 2 * side * (side - 1) + 2 * remainder - 1

    return 2 * side * (side - 1) + 2 * remainder - 2


def from_mask(mask: np.ndarray, cell_size: float = 1.0) -> dict[str, float]:
    """Class-level metrics for the green class.

    `cell_size` is the ground length of one pixel in metres; the frontend
    resizes uploads so that one pixel is one metre.
    """
    total_cells = mask.size
    green_cells = int(mask.sum())

    if green_cells == 0 or total_cells == 0:
        return dict(EMPTY)

    areas, perimeters = _patch_areas_and_perimeters(mask)
    cell_area = cell_size**2

    # SHAPE, COHESION and AI are defined on cell counts, so they are computed
    # before any conversion to ground units.
    shape = 0.25 * perimeters / np.sqrt(areas)
    shape_am = float((shape * areas).sum() / areas.sum())

    denominator = float((perimeters * np.sqrt(areas)).sum())
    scaling = 1 - 1 / np.sqrt(total_cells)
    cohesion = (
        100.0
        if scaling <= 0 or denominator == 0
        else float((1 - perimeters.sum() / denominator) / scaling * 100)
    )

    reachable = _max_like_adjacencies(green_cells)
    aggregation = (
        100.0 if reachable == 0 else float(_like_adjacencies(mask) / reachable * 100)
    )

    hectares = green_cells * cell_area / 10_000
    landscape_hectares = total_cells * cell_area / 10_000

    return {
        "CA": hectares,
        "PLAND": 100.0 * green_cells / total_cells,
        "PD": len(areas) / landscape_hectares * 100,
        "AREA_MN_Me": float(areas.mean()) * cell_area,
        "SHAPE_AM": shape_am,
        "COHESION": cohesion,
        "AI": aggregation,
    }


def metrics(image, cell_size: float = 1.0) -> dict[str, float]:
    """Classify an image and measure its greenspace."""
    return from_mask(green_mask(image), cell_size=cell_size)
