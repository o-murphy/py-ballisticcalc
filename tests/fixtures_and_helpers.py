import pytest

from py_ballisticcalc import (HitResult, Distance, BaseEngineConfigDict, Calculator, DragModel, TableG1, TableG7,
                              Weight, Velocity, Ammo, Shot, Angular)


def print_out_trajectory_compact(hit_result: HitResult, label="", distance_unit = Distance.Meter,
                                 top_k: int = 5):
    trajectory_length = len(hit_result.trajectory)
    if label:
        print(f'{label}: Length of trajectory: { trajectory_length=}')
    else:
        print(f'Length of trajectory: { trajectory_length=}')

    trajectory = hit_result.trajectory
    if top_k < trajectory_length:
        end_start_top_k = top_k
        start_end_top_k = trajectory_length - top_k - 1
        if end_start_top_k < start_end_top_k:
            trajectory = trajectory[:end_start_top_k] + trajectory[start_end_top_k:]

    for i, p in enumerate(trajectory):
        if i < top_k:
            index_to_print = i + 1
        else:
            index_to_print = (trajectory_length - top_k) + i - top_k
        if i == top_k and i != trajectory_length - (top_k + 1):
            print("...")
        print(f'{index_to_print}. ({p.distance >> distance_unit}, {p.height >> distance_unit})')


@pytest.fixture(autouse=True)
def zero_height_calc(loaded_engine_instance):
    config = BaseEngineConfigDict(
        cMinimumVelocity=0.0,
        cMinimumAltitude=0.0,
        cMaximumDrop=0.0,
    )
    calc = Calculator(config=config, engine=loaded_engine_instance)
    return calc

@pytest.fixture(autouse=True)
def zero_min_velocity_calc(loaded_engine_instance):
    config = BaseEngineConfigDict(
        cMinimumVelocity=0,
    )
    return Calculator(config=config, engine=loaded_engine_instance)


def create_23_mm_shot():
    dm = DragModel(bc=0.759, drag_table=TableG1,
                   weight=Weight.Gram(108), diameter=Distance.Millimeter(23), length=Distance.Millimeter(108.2))
    return Shot(ammo=Ammo(dm, Velocity.MPS(930)))

def create_7_62_mm_shot():
    """7.62x51mm NATO M118"""
    dm = DragModel(bc=0.243, drag_table=TableG7,
                   weight=Weight.Grain(175), diameter=Distance.Millimeter(7.62), length=Distance.Millimeter(32.0))
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(800)))

def create_5_56_mm_shot():
    """5.56x45mm NATO SS109"""
    dm = DragModel(bc=0.151, drag_table=TableG7,
                   weight=Weight.Grain(62), diameter=Distance.Millimeter(5.56), length=Distance.Millimeter(21.0))
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(900)))

def create_0_308_caliber_shot():
    dm = DragModel(bc=0.233, drag_table=TableG7,
                   weight=Weight.Grain(155), diameter=Distance.Inch(0.308), length=Distance.Inch(1.2))
    return Shot(ammo=Ammo(dm, mv=Velocity.MPS(900)))

def shot_with_relative_angle_in_degrees(angle_in_degrees: float):
    shot = create_5_56_mm_shot()
    shot.relative_angle = Angular.Degree(angle_in_degrees)
    return shot
