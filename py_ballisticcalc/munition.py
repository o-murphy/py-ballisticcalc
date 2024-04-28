"""Module for Weapon and Ammo properties definitions"""
import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import NamedTuple

from .drag_model import DragModel
from .unit import Velocity, Temperature, Distance, Angular, PreferredUnits, Dimension, AbstractUnitType

__all__ = ('Weapon', 'Ammo', 'Sight')


@dataclass
class Sight(PreferredUnits.Mixin):
    class FocalPlane(IntEnum):
        FFP = 1  # First focal plane
        SFP = 2  # Second focal plane
        LWIR = 10  # LWIR based device with scalable reticle
        # and adjusted click size to it's magnification

    class ReticleStep(NamedTuple):
        vertical: Angular
        horizontal: Angular

    class Clicks(NamedTuple):
        vertical: float
        horizontal: float

    focal_plane: FocalPlane = field(default=FocalPlane.FFP)
    scale_factor: [float, Distance] = Dimension(prefer_units='distance')
    h_click_size: [float, Angular] = Dimension(prefer_units='adjustment')
    v_click_size: [float, Angular] = Dimension(prefer_units='adjustment')

    def __post_init__(self):
        if self.focal_plane not in Sight.FocalPlane.__members__.values():
            raise ValueError("Wrong focal plane")
        if not self.scale_factor and self.focal_plane == Sight.FocalPlane.SFP:
            raise ValueError('Scale_factor required for SFP sights')
        if (
                not isinstance(self.h_click_size, Angular)
                or not isinstance(self.v_click_size, Angular)
        ):
            raise TypeError("type Angular expected for 'h_click_size' and 'v_click_size'")
        if self.h_click_size.raw_value <= 0 or self.v_click_size.raw_value <= 0:
            raise TypeError("'h_click_size' and 'v_click_size' have to be positive")

    def _adjust_sfp_reticle_steps(self, target_distance: [float, Distance], magnification: float) -> ReticleStep:
        assert self.focal_plane == Sight.FocalPlane.SFP, "SFP focal plane required"

        # adjust reticle scale relative to target distance and magnification
        def get_sfp_step(click_size: [Angular, AbstractUnitType]):
            # Don't need distances conversion cause of it's destroying there
            return click_size.units(
                click_size.unit_value
                * self.scale_factor.raw_value
                / _td.raw_value
                * magnification
            )

        _td = PreferredUnits.distance(target_distance)
        _h_step = get_sfp_step(self.h_click_size)
        _v_step = get_sfp_step(self.v_click_size)
        return Sight.ReticleStep(_v_step, _v_step)

    def get_adjustment(self, target_distance: Distance,
                       drop_adj: Angular, windage_adj: Angular,
                       magnification: float):

        if self.focal_plane == Sight.FocalPlane.SFP:
            steps = self._adjust_sfp_reticle_steps(target_distance, magnification)
            return Sight.Clicks(
                drop_adj.raw_value / steps.vertical.raw_value,
                windage_adj.raw_value / steps.horizontal.raw_value
            )
        elif self.focal_plane == Sight.FocalPlane.FFP:
            return Sight.Clicks(
                drop_adj.raw_value / self.v_click_size.raw_value,
                windage_adj.raw_value / self.h_click_size.raw_value
            )
        elif self.focal_plane == Sight.FocalPlane.LWIR:
            # adjust clicks to magnification
            return Sight.Clicks(
                drop_adj.raw_value / (self.v_click_size.raw_value / magnification),
                windage_adj.raw_value / (self.h_click_size.raw_value / magnification)
            )
        raise AttributeError("Wrong focal_plane")

    def get_trajectory_adjustment(self, trajectory_point: 'TrajectoryData', magnification: float) -> Clicks:
        return self.get_adjustment(trajectory_point.distance,
                                   trajectory_point.drop_adj,
                                   trajectory_point.windage_adj,
                                   magnification)


@dataclass
class Weapon(PreferredUnits.Mixin):
    """
    :param sight_height: Vertical distance from center of bore line to center of sight line.
    :param twist: Distance for barrel rifling to complete one complete turn.
        Positive value => right-hand twist, negative value => left-hand twist.
    :param zero_elevation: Angle of barrel relative to sight line when sight is set to "zero."
        (Typically computed by ballistic Calculator.)
    """
    sight_height: [float, Distance] = Dimension(prefer_units='sight_height')
    twist: [float, Distance] = Dimension(prefer_units='twist')
    zero_elevation: [float, Angular] = Dimension(prefer_units='angular')
    sight: [Sight, None] = field(default=None)

    def __post_init__(self):
        if not self.sight_height:
            self.sight_height = 0
        if not self.twist:
            self.twist = 0
        if not self.zero_elevation:
            self.zero_elevation = 0


@dataclass
class Ammo(PreferredUnits.Mixin):
    """
    :param dm: DragModel for projectile
    :param mv: Muzzle Velocity
    :param powder_temp: Baseline temperature that produces the given mv
    :param temp_modifier: Change in velocity w temperature: % per 15°C.
        Can be computed with .calc_powder_sens().  Only applies if:
            Settings.USE_POWDER_SENSITIVITY = True
    """
    dm: DragModel = field(default=None)
    mv: [float, Velocity] = Dimension(prefer_units='velocity')
    powder_temp: [float, Temperature] = Dimension(prefer_units='temperature')
    temp_modifier: float = field(default=0)

    def __post_init__(self):
        if not self.powder_temp:
            self.powder_temp = Temperature.Celsius(15)

    def calc_powder_sens(self, other_velocity: [float, Velocity],
                         other_temperature: [float, Temperature]) -> float:
        """Calculates velocity correction by temperature change; assigns to self.temp_modifier
        :param other_velocity: other velocity at other_temperature
        :param other_temperature: other temperature
        :return: temperature modifier in terms %v_delta/15°C
        """
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = PreferredUnits.velocity(other_velocity) >> Velocity.MPS
        t1 = PreferredUnits.temperature(other_temperature) >> Temperature.Celsius

        v_delta = math.fabs(v0 - v1)
        t_delta = math.fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError(
                "Temperature modifier error, other velocity"
                " and temperature can't be same as default"
            )
        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100
        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp: [float, Temperature]) -> Velocity:
        """Calculates muzzle velocity at temperature, based on temp_modifier.
        :param current_temp: Temperature of cartridge powder
        :return: Muzzle velocity corrected to current_temp
        """
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        t1 = PreferredUnits.temperature(current_temp) >> Temperature.Celsius
        t_delta = t1 - t0
        muzzle_velocity = self.temp_modifier / (15 / v0) * t_delta + v0
        return Velocity.MPS(muzzle_velocity)
