import math

import pytest

from py_ballisticcalc.conditions import ShotProps
from py_ballisticcalc.constants import cEarthAngularVelocityRadS
from py_ballisticcalc.vector import Vector

from tests.fixtures_and_helpers import create_7_62_mm_shot


def _expected_local_from_cross(ctx, velocity):
    """Compute expected coriolis acceleration in local ENU coordinates using vector cross product."""
    assert ctx.range_east is not None and ctx.range_north is not None
    assert ctx.cross_east is not None and ctx.cross_north is not None

    vel_east = velocity.x * ctx.range_east + velocity.z * ctx.cross_east
    vel_north = velocity.x * ctx.range_north + velocity.z * ctx.cross_north
    vel_up = velocity.y

    lat_rad = math.asin(ctx.sin_lat)
    omega_vec = (
        0.0,
        cEarthAngularVelocityRadS * math.cos(lat_rad),
        cEarthAngularVelocityRadS * math.sin(lat_rad),
    )
    vel_vec = (vel_east, vel_north, vel_up)

    cross = (
        omega_vec[1] * vel_vec[2] - omega_vec[2] * vel_vec[1],
        omega_vec[2] * vel_vec[0] - omega_vec[0] * vel_vec[2],
        omega_vec[0] * vel_vec[1] - omega_vec[1] * vel_vec[0],
    )
    coriolis_enu = tuple(-2.0 * component for component in cross)

    expected_range = coriolis_enu[0] * ctx.range_east + coriolis_enu[1] * ctx.range_north
    expected_cross = coriolis_enu[0] * ctx.cross_east + coriolis_enu[1] * ctx.cross_north
    expected_up = coriolis_enu[2]
    return Vector(expected_range, expected_up, expected_cross)

def test_shotprops_without_latitude_has_no_coriolis():
    shot = create_7_62_mm_shot()
    shot.azimuth = 90.0
    props = ShotProps.from_shot(shot)
    assert props.coriolis is None


@pytest.mark.parametrize(
    "latitude, azimuth, velocity",
    [
        (45.0, 90.0, Vector(2200.0, 150.0, 35.0)),
        (45.0, 0.0, Vector(2800.0, 0.0, 0.0)),
        (-45.0, 0.0, Vector(2800.0, 0.0, 0.0)),
        (0.0, 90.0, Vector(2800.0, 0.0, 0.0)),
        (45.0, 180.0, Vector(2800.0, 0.0, 0.0)),
        (45.0, 270.0, Vector(2800.0, 0.0, 0.0)),
        (45.0, 45.0, Vector(1800.0, 120.0, 250.0)),
        (89.9, 45.0, Vector(2000.0, 150.0, -20.0)),
        (-89.9, 45.0, Vector(2000.0, -150.0, 20.0)),
        (30.0, 90.0, Vector(0.0, 2600.0, 0.0)),
        (30.0, 45.0, Vector(100.0, 2600.0, 0.0)),
    ],
)
def test_coriolis_acceleration_matches_vector_cross_product(latitude, azimuth, velocity):
    shot = create_7_62_mm_shot()
    shot.latitude = latitude
    shot.azimuth = azimuth
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.full_3d

    accel = ctx.coriolis_acceleration_local(velocity)
    expected = _expected_local_from_cross(ctx, velocity)

    assert math.isclose(accel.x, expected.x, rel_tol=1e-6, abs_tol=1e-9)
    assert math.isclose(accel.y, expected.y, rel_tol=1e-6, abs_tol=1e-9)
    assert math.isclose(accel.z, expected.z, rel_tol=1e-6, abs_tol=1e-9)


@pytest.mark.parametrize(
    "latitude, expected_sign",
    [(45.0, 1), (-45.0, -1), (0.0, 0), (90.0, 1), (-90.0, -1)],
)
def test_flat_fire_horizontal_direction_by_latitude(latitude, expected_sign):
    shot = create_7_62_mm_shot()
    shot.latitude = latitude
    shot.azimuth = None
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.flat_fire_only

    time = 1.75
    distance_ft = 2800.0
    drop_ft = -35.0
    vertical, horizontal = ctx.flat_fire_offsets(time, distance_ft, drop_ft)

    assert vertical == pytest.approx(0.0, abs=1e-12)
    expected_horizontal = cEarthAngularVelocityRadS * distance_ft * ctx.sin_lat * time
    if expected_sign == 0:
        assert math.isclose(horizontal, 0.0, abs_tol=1e-12)
    else:
        assert math.copysign(1.0, horizontal) == expected_sign
        assert math.isclose(horizontal, expected_horizontal, rel_tol=1e-6, abs_tol=1e-9)


@pytest.mark.parametrize("latitude", [45.0, -45.0, 0.0])
def test_full_coriolis_cross_deflection_direction(latitude):
    shot = create_7_62_mm_shot()
    shot.latitude = latitude
    shot.azimuth = 0.0
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.full_3d

    velocity = Vector(2800.0, 0.0, 0.0)
    accel = ctx.coriolis_acceleration_local(velocity)

    expected = _expected_local_from_cross(ctx, velocity)
    expected_cross = expected.z
    if math.isclose(expected_cross, 0.0, abs_tol=1e-12):
        assert math.isclose(accel.z, 0.0, abs_tol=1e-9)
    else:
        assert math.copysign(1.0, accel.z) == math.copysign(1.0, expected_cross)
        assert math.isclose(accel.z, expected_cross, rel_tol=1e-6, abs_tol=1e-9)


@pytest.mark.parametrize("latitude", [60.0, -60.0, 0.0])
def test_full_coriolis_vertical_eotvos_effect(latitude):
    shot = create_7_62_mm_shot()
    shot.latitude = latitude
    shot.azimuth = 90.0
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.full_3d

    velocity = Vector(2800.0, 0.0, 0.0)
    accel = ctx.coriolis_acceleration_local(velocity)

    assert ctx.range_east is not None and ctx.cross_east is not None
    range_east = ctx.range_east
    cross_east = ctx.cross_east
    vel_east = velocity.x * range_east + velocity.z * cross_east
    expected_vertical = 2.0 * cEarthAngularVelocityRadS * ctx.cos_lat * vel_east
    assert accel.y == pytest.approx(expected_vertical, rel=1e-6, abs=1e-9)

    shot.azimuth = 270.0
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.full_3d

    velocity = Vector(2800.0, 0.0, 0.0)
    accel = ctx.coriolis_acceleration_local(velocity)

    assert ctx.range_east is not None and ctx.cross_east is not None
    range_east = ctx.range_east
    cross_east = ctx.cross_east
    vel_east = velocity.x * range_east + velocity.z * cross_east
    expected_vertical = 2.0 * cEarthAngularVelocityRadS * ctx.cos_lat * vel_east
    assert accel.y == pytest.approx(expected_vertical, rel=1e-6, abs=1e-9)


def test_flat_fire_horizontal_matches_formula():
    shot = create_7_62_mm_shot()
    shot.latitude = 45.0
    shot.azimuth = None
    props = ShotProps.from_shot(shot)
    ctx = props.coriolis
    assert ctx is not None and ctx.flat_fire_only

    time = 1.5
    distance_ft = 2500.0
    drop_ft = -40.0
    range_vector = Vector(distance_ft, drop_ft, 0.0)

    adjusted = props.adjust_range_for_coriolis(time, range_vector)
    horizontal_delta = adjusted.z - range_vector.z

    expected_horizontal = cEarthAngularVelocityRadS * distance_ft * ctx.sin_lat * time
    assert math.isclose(horizontal_delta, expected_horizontal, rel_tol=1e-6, abs_tol=1e-9)
    assert adjusted.y == pytest.approx(range_vector.y, abs=1e-9)
