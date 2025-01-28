import pytest

from py_ballisticcalc import HitResult, Distance, InterfaceConfigDict, Calculator, DragModel, TableG1, Weight, Ammo, \
    Velocity, Weapon, Shot, Angular


def print_out_trajectory_compact(hit_result: HitResult, label="", distance_unit: Distance = Distance.Meter,
                                 top_k: int = 5):
    trajectory_length = len(hit_result.trajectory)
    if label:
        print(f'{label}: Length of trajectory: { trajectory_length=}')
    else:
        print(f'Length of trajectory: { trajectory_length=}')


    trajectory = hit_result.trajectory
    if top_k<trajectory_length:
        end_start_top_k = top_k
        start_end_top_k = trajectory_length - top_k-1
        if end_start_top_k<start_end_top_k:
            trajectory = trajectory[:end_start_top_k]+trajectory[start_end_top_k:]

    for i, p in enumerate(trajectory):
        if i<top_k:
            index_to_print = i+1
        else:
            index_to_print = (trajectory_length-top_k)+i-top_k
        if i==top_k and i!=trajectory_length-(top_k+1):
            print("...")
        print(f'{index_to_print}. ({p.distance>>distance_unit}, {p.height>>distance_unit})')


@pytest.fixture()
def zero_height_calc():
    config = InterfaceConfigDict(
        cMinimumVelocity=0,
        cMinimumAltitude=Distance.Meter(0),
        cMaximumDrop=Distance.Meter(0),
    )
    calc = Calculator(_config=config)
    return calc


def create_shot():
    drag_model = DragModel(
        bc=0.759,
        drag_table=TableG1,
        weight=Weight.Gram(108),
        diameter=Distance.Millimeter(23),
        length=Distance.Millimeter(108.2),
    )
    ammo = Ammo(drag_model, Velocity.MPS(930))
    gun = Weapon()
    shot = Shot(
        weapon=gun,
        ammo=ammo,
    )
    return shot


def shot_with_relative_angle_in_degrees(angle_in_degrees: float):
    shot = create_shot()
    shot.relative_angle = Angular.Degree(angle_in_degrees)
    return shot


@pytest.fixture()
def zero_min_velocity_calc():
    config = InterfaceConfigDict(
        cMinimumVelocity=0,
    )
    return Calculator(_config=config)
