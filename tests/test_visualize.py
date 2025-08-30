import pytest

from py_ballisticcalc import Calculator, Distance
from tests.fixtures_and_helpers import create_7_62_mm_shot  # type: ignore[attr-defined]

pytestmark = pytest.mark.extended


def test_dataframe_and_plot_smoke(loaded_engine_instance):
    calc = Calculator(engine=loaded_engine_instance)
    shot = create_7_62_mm_shot()
    hr = calc.fire(shot, Distance.Yard(300), Distance.Yard(25))

    # pandas DataFrame integration
    try:
        df = hr.dataframe()
        assert set(("distance", "height")).issubset(df.columns)
    except ImportError as e:
        # Allow running without pandas
        assert "py_ballisticcalc[charts]" in str(e)

    # matplotlib plot integration
    try:
        ax = hr.plot()
        assert ax is not None

        # add time axis explicitly to cover code path
        try:
            from py_ballisticcalc.visualize.plot import (
                add_time_of_flight_axis,
                add_danger_space_overlay,
            )
            add_time_of_flight_axis(ax, hr, time_precision=0)

            # overlay danger space
            ds = hr.danger_space(Distance.Yard(200), Distance.Inch(18))
            add_danger_space_overlay(ds, ax, label="Test DS")
        except ImportError as e:
            # Allow running without matplotlib
            assert "py_ballisticcalc[charts]" in str(e)
    except ImportError as e:
        # Allow running without matplotlib
        assert "py_ballisticcalc[charts]" in str(e)
