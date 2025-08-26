import pytest

from py_ballisticcalc import (
    BaseEngineConfigDict,
    Calculator,
    Ammo,
    Shot,
    Distance,
    DragModel,
    Angular,
    TableG7,
    Velocity,
    Weight,
)

def create_7_62_mm_shot():
    """7.62x51mm NATO M118"""
    dm = DragModel(bc=0.243, drag_table=TableG7,
                   weight=Weight.Grain(175), diameter=Distance.Millimeter(7.62), length=Distance.Millimeter(32.0))
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))

def _base_config():
    # Disable early termination constraints to exercise long(er) paths
    return BaseEngineConfigDict(
        cMinimumVelocity=0.0,
        cMinimumAltitude=0.0,
        cMaximumDrop=0.0,
    )


def test_stress_integrate_zero_max(loaded_engine_instance):
    """Run core operations repeatedly to surface leaks or inconsistent state."""
    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = create_7_62_mm_shot()

    # Keep counts modest to avoid long runtime in CI while still exercising paths.
    for _ in range(50):
        # Integrate with modest range and step
        _ = calc.integrate(shot, Distance.Yard(400), Distance.Yard(25))
        # Zero finding at a reasonable distance
        _ = calc.find_zero_angle(shot, Distance.Yard(200))
        # Max range search
    _ = calc.find_max_range(shot, (0, 90))


def test_error_paths_do_not_break_future_calls(loaded_engine_instance):
    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = create_7_62_mm_shot()

    # Force an OutOfRange scenario (excessive slant range)
    with pytest.raises(Exception):
        calc.find_zero_angle(shot, Distance.Mile(50))

    # Subsequent calls should still succeed repeatedly
    for _ in range(10):
        _ = calc.integrate(shot, Distance.Yard(300), Distance.Yard(50))


def test_vertical_apex_path(loaded_engine_instance):
    """Vertical look angle should use apex path without leaking resources."""
    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = create_7_62_mm_shot()
    shot.look_angle = Angular.Degree(90.0)

    # find_max_range should hit the apex-special-case path
    max_range, angle_at_max = calc.find_max_range(shot, (0, 90))
    assert max_range >> Distance.Yard > 0
    assert angle_at_max >> Angular.Degree == pytest.approx(90.0, abs=0.2)


def test_empty_winds_and_small_zero_distance(loaded_engine_instance):
    calc = Calculator(config=_base_config(), engine=loaded_engine_instance)
    shot = create_7_62_mm_shot()
    # No winds should be fine
    shot.winds = []

    # Very small distance triggers early-return path; returned angle ~ look angle
    look = shot.look_angle
    ang = calc.find_zero_angle(shot, Distance.Inch(1))
    assert ang >> Angular.Degree == pytest.approx(look >> Angular.Degree, abs=0.5)
