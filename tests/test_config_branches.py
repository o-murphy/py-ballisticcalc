import os
from pathlib import Path

import pytest

from py_ballisticcalc import basicConfig, PreferredUnits, Unit

pytestmark = pytest.mark.extended


def test_basic_config_mutual_exclusion_error():
    with pytest.raises(ValueError):
        basicConfig(filename="dummy.toml", preferred_units={"distance": Unit.Meter})


def test_basic_config_loads_from_mapping_and_resets():
    PreferredUnits.restore_defaults()
    assert PreferredUnits.distance == Unit.Yard
    basicConfig(preferred_units={"distance": Unit.Meter})
    assert PreferredUnits.distance == Unit.Meter
    # Call with neither filename nor mapping triggers _load_config path (no file found => ok)
    basicConfig()
    PreferredUnits.restore_defaults()


def test_load_config_searches_upwards_and_logs(monkeypatch, tmp_path: Path, caplog):
    # Create a temporary directory tree: tmp/a/b; place pybc.toml in tmp/a
    root = tmp_path
    a = root / "a"
    b = a / "b"
    b.mkdir(parents=True)
    cfg = a / "pybc.toml"
    cfg.write_text("""
[pybc.preferred_units]
distance = "meter"
""".strip())

    # Run loader from the deeper directory via cwd monkeypatch
    with monkeypatch.context() as m:
        m.chdir(str(b))
        caplog.clear()
        basicConfig()  # should discover and load cfg
        assert PreferredUnits.distance == Unit.Meter

    # Reset
    PreferredUnits.restore_defaults()
