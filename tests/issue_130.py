from typing import NamedTuple

from matplotlib import pyplot as plt

from py_ballisticcalc import (
    loadMetricUnits,
    DragModel,
    TableG1,
    Weight,
    Distance,
    Ammo,
    Velocity,
    Temperature,
    Weapon,
    Calculator,
    Shot,
    Angular,
    InterfaceConfigDict,
    RangeError,
    HitResult,
)


class WeaponData(NamedTuple):
    weapon: Weapon
    ammo: Ammo

    @property
    def muzzle_velocity(self):
        return ammo.mv

    def compute_trajectory(
            self, angle_in_degrees: float, distance_in_meters: float, extra_data=True
    ):
        gun = Weapon()

        shot = Shot(
            weapon=gun,
            ammo=ammo,
            relative_angle=Angular.Degree(angle_in_degrees),
        )
        config = InterfaceConfigDict(
            cMinimumVelocity=0, cMinimumAltitude=-1, cMaximumDrop=-1
        )

        calc = Calculator(config=config)
        try:
            shot_result = calc.fire(
                shot, Distance.Meter(distance_in_meters), extra_data=extra_data
            )
        except RangeError as e:
            if e.reason in [
                RangeError.MaximumDropReached,
                RangeError.MinimumAltitudeReached,
            ]:
                shot_result = HitResult(shot, e.incomplete_trajectory, extra=extra_data)
            else:
                raise e
        return shot_result


if __name__ == "__main__":
    loadMetricUnits()
    dm = DragModel(
        0.62, TableG1, Weight.Grain(661), Distance.Inch(0.51), Distance.Inch(2.3)
    )
    ammo = Ammo(dm, Velocity.MPS(850), Temperature.Celsius(15))
    weapon = Weapon(sight_height=Distance.Centimeter(9), twist=Distance.Inch(15))
    weapon_data = WeaponData(weapon, ammo)
    shot = weapon_data.compute_trajectory(angle_in_degrees=1, distance_in_meters=1000)
    shot.plot()
    plt.show()
    df = shot.dataframe()
    print(f"{df.columns=}")
    df_formatted = shot.dataframe(formatted=True)
    print(f"{df_formatted.columns=}")
