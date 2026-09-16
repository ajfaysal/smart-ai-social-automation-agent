from pathlib import Path

import numpy as np

from video_text_cleaner import _region_mask


def test_normalized_fixed_region_is_converted_to_pixel_mask():
    mask = _region_mask((100, 200), [{"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.3}], 0)
    assert mask.shape == (100, 200)
    assert int(mask[25, 50]) == 255
    assert int(mask[90, 190]) == 0


def test_empty_regions_produce_empty_mask():
    mask = _region_mask((32, 64), [], 0)
    assert not np.any(mask)
