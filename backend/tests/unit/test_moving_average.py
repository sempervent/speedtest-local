import pytest

from app.services.stats_service import moving_average


def test_moving_average_basic():
    vals = [1.0, 2.0, 3.0, None, 5.0]
    ma = moving_average(vals, window=2)
    assert ma[0] == pytest.approx(1.0)
    assert ma[1] == pytest.approx(1.5)
    assert ma[2] == pytest.approx(2.5)
    assert ma[3] == pytest.approx(3.0)  # window [2, None] -> only 2.0
    assert ma[4] == pytest.approx(5.0)  # None skipped in window [None, 5.0]


def test_moving_average_window_invalid():
    with pytest.raises(ValueError):
        moving_average([1.0], window=0)
