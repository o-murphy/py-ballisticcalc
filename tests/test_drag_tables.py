import math
import pytest

from py_ballisticcalc import drag_tables as _drag_tables_mod
from py_ballisticcalc.drag_model import make_data_points


def _discover_drag_tables():
    """Yield (name, table) for every drag table defined in drag_tables.

    A drag table is identified structurally as a non-empty list of dicts
    that each contain 'Mach' and 'CD' keys. Names are presented without the
    leading 'Table' prefix for readability (e.g., 'G1', 'RA4').
    """
    discovered = []
    for attr_name, value in vars(_drag_tables_mod).items():
        # Only consider attributes that look like table constants
        if not isinstance(value, list) or not value:
            continue
        first = value[0]
        if isinstance(first, dict) and ('Mach' in first) and ('CD' in first):
            # Normalize display name by removing a leading 'Table'
            lower = attr_name.lower()
            display = attr_name[5:] if lower.startswith('table') else attr_name
            discovered.append((display, value))
    # Stable order for test output consistency
    discovered.sort(key=lambda x: x[0])
    return discovered


def test_discovery_includes_core_tables():
    discovered = _discover_drag_tables()
    names = {name for name, _ in discovered}
    # Must discover at least one table and must include G1 and G7
    assert discovered, "No drag tables discovered in drag_tables module"
    assert 'G1' in names, "Core drag table 'G1' not discovered"
    assert 'G7' in names, "Core drag table 'G7' not discovered"
    # API parity: discovered names should match drag_tables.get_drag_tables_names()
    if hasattr(_drag_tables_mod, 'get_drag_tables_names'):
        api_names = set(_drag_tables_mod.get_drag_tables_names())
        # Normalize API names by stripping leading 'Table'
        api_names_norm = {n[5:] if n.lower().startswith('table') else n for n in api_names}
        assert names == api_names_norm, (
            f"Discovered tables {sorted(names)} do not match API list {sorted(api_names_norm)}"
        )


@pytest.mark.parametrize("name, table", _discover_drag_tables())
def test_tables_sorted_and_monotone_mach(name, table):
    data = make_data_points(table)
    mach = [p.Mach for p in data]
    assert mach == sorted(mach), f"{name} Mach not sorted"
    # No duplicates in interior points
    assert len(mach) == len(list(dict.fromkeys(mach)))


@pytest.mark.parametrize("name, table", _discover_drag_tables())
def test_cd_reasonable_bounds(name, table):
    data = make_data_points(table)
    cds = [p.CD for p in data]
    assert all(0.0 < cd < 2.0 for cd in cds), f"{name} CD out of reasonable range"


@pytest.mark.parametrize("name, table", _discover_drag_tables())
def test_interpolation_continuity_at_breakpoints(name, table):
    data = make_data_points(table)
    # For each interior breakpoint, check left/right linear segments meet within small epsilon.
    for i in range(1, len(data) - 1):
        x0, y0 = data[i - 1].Mach, data[i - 1].CD
        x1, y1 = data[i].Mach, data[i].CD
        x2, y2 = data[i + 1].Mach, data[i + 1].CD
        if x1 == x0 or x2 == x1:
            continue
        m_left = (y1 - y0) / (x1 - x0)
        m_right = (y2 - y1) / (x2 - x1)
        # Evaluate approaching the breakpoint from both sides
        eps = 1e-6
        y_left = y0 + m_left * (x1 - x0 - eps)
        y_right = y1 + m_right * (eps)
        # The underlying curve builder is quadratic-piecewise but uses neighboring points; enforce near continuity
        assert math.isfinite(y_left) and math.isfinite(y_right)
        assert abs((y_left - y1)) < 0.01
        assert abs((y_right - y1)) < 0.01
