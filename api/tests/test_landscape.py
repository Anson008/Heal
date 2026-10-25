import numpy as np

import landscape


class Fake:
    """Stands in for a PIL image without needing an encoder."""

    def __init__(self, array):
        self.array = array

    def convert(self, _):
        return self.array


def test_square_patch_has_shape_index_one():
    mask = np.zeros((100, 100), bool)
    mask[45:55, 45:55] = True

    assert landscape.from_mask(mask)["SHAPE_AM"] == 1.0


def test_checkerboard_has_no_like_adjacency():
    board = np.indices((100, 100)).sum(0) % 2 == 0

    assert landscape.from_mask(board)["AI"] == 0.0


def test_solid_block_is_maximally_aggregated():
    metrics = landscape.from_mask(np.ones((100, 100), bool))

    assert metrics["AI"] == 100.0
    assert metrics["COHESION"] == 100.0
    assert metrics["PLAND"] == 100.0


def test_empty_mask_returns_zeros_without_dividing_by_zero():
    assert landscape.from_mask(np.zeros((40, 40), bool)) == landscape.EMPTY


def test_class_area_recovers_the_landscape_extent():
    mask = np.zeros((100, 100), bool)
    mask[45:55, 45:55] = True
    metrics = landscape.from_mask(mask)

    assert metrics["CA"] / (metrics["PLAND"] / 100) == 1.0  # 100 x 100 m is 1 ha


def test_dark_pixels_do_not_wrap_around_to_green():
    dark = np.zeros((4, 4, 3), np.uint8)
    dark[..., 0], dark[..., 1], dark[..., 2] = 20, 10, 20

    assert not landscape.green_mask(Fake(dark)).any()


def test_grass_is_green():
    grass = np.zeros((4, 4, 3), np.uint8)
    grass[..., 0], grass[..., 1], grass[..., 2] = 60, 120, 55

    assert landscape.green_mask(Fake(grass)).all()
