"""Module for Weapon and Ammo properties definitions"""
import math
from dataclasses import dataclass

from typing_extensions import NamedTuple, Union, Optional, Any, Literal, get_args

from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.unit import Velocity, Temperature, Distance, Angular, PreferredUnits

TrajectoryData: Any


SightFocalPlane = Literal['FFP', 'SFP', 'LWIR']


class SightReticleStep(NamedTuple):
    """Reticle step"""

    vertical: Angular
    horizontal: Angular


class SightClicks(NamedTuple):
    """SightClicks tuple"""

    vertical: float
    horizontal: float


@dataclass
class Sight:
    """Sight data for sight specific adjustment calculation"""

    focal_plane: SightFocalPlane
    scale_factor: Distance
    h_click_size: Angular
    v_click_size: Angular

    # def __post_init__(self):
    def __init__(self,
                 focal_plane: SightFocalPlane = 'FFP',
                 scale_factor: Optional[Union[float, Distance]] = None,
                 h_click_size: Optional[Union[float, Angular]] = None,
                 v_click_size: Optional[Union[float, Angular]] = None):

        if focal_plane not in get_args(SightFocalPlane):
            raise ValueError("Wrong focal plane")

        if not scale_factor and focal_plane == 'SFP':
            raise ValueError('Scale_factor required for SFP sights')

        if (
                not isinstance(h_click_size, (Angular, float, int))
                or not isinstance(v_click_size, (Angular, float, int))
        ):
            raise TypeError("type Angular expected for 'h_click_size' and 'v_click_size'")

        self.focal_plane = focal_plane
        self.scale_factor = PreferredUnits.distance(scale_factor or 1)
        self.h_click_size = PreferredUnits.adjustment(h_click_size)
        self.v_click_size = PreferredUnits.adjustment(v_click_size)

        if self.h_click_size.raw_value <= 0 or self.v_click_size.raw_value <= 0:
            raise TypeError("'h_click_size' and 'v_click_size' have to be positive")

    def _adjust_sfp_reticle_steps(self, target_distance: Union[float, Distance],
                                  magnification: float) -> SightReticleStep:
        """Calculates the SFP reticle steps for a target distance and magnification"""

        assert self.focal_plane == 'SFP', "SFP focal plane required"

        # adjust reticle scale relative to target distance and magnification
        def get_sfp_step(click_size: Angular):
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
        return SightReticleStep(_h_step, _v_step)

    def get_adjustment(self, target_distance: Distance,
                       drop_adj: Angular, windage_adj: Angular,
                       magnification: float):
        """Calculate adjustment for target distance and magnification"""

        if self.focal_plane == 'SFP':
            steps = self._adjust_sfp_reticle_steps(target_distance, magnification)
            return SightClicks(
                drop_adj.raw_value / steps.vertical.raw_value,
                windage_adj.raw_value / steps.horizontal.raw_value
            )
        if self.focal_plane == 'FFP':
            return SightClicks(
                drop_adj.raw_value / self.v_click_size.raw_value,
                windage_adj.raw_value / self.h_click_size.raw_value
            )
        if self.focal_plane == 'LWIR':
            # adjust clicks to magnification
            return SightClicks(
                drop_adj.raw_value / (self.v_click_size.raw_value / magnification),
                windage_adj.raw_value / (self.h_click_size.raw_value / magnification)
            )
        raise AttributeError("Wrong focal_plane")

    def get_trajectory_adjustment(self, trajectory_point: 'TrajectoryData', magnification: float) -> SightClicks:
        """Calculate adjustment for target distance and magnification for `TrajectoryData` instance"""

        return self.get_adjustment(trajectory_point.distance,
                                   trajectory_point.drop_adj,
                                   trajectory_point.windage_adj,
                                   magnification)


@dataclass
class Weapon:
    """
    A base class for creating Weapon.

    Attributes:
        sight_height: Sight height
        twist: Twist
        zero_elevation: Zero elevation
        sight: Sight properties
    """

    sight_height: Distance
    twist: Distance
    zero_elevation: Angular
    sight: Optional[Sight]

    def __init__(self,
                 sight_height: Optional[Union[float, Distance]] = None,
                 twist: Optional[Union[float, Distance]] = None,
                 zero_elevation: Optional[Union[float, Angular]] = None,
                 sight: Optional[Sight] = None):
        """
        Create a new weapon instance with given parameters

        Args:
            sight_height: Vertical distance from center of bore line to center of sight line.
            twist: Distance for barrel rifling to complete one complete turn.
                Positive value => right-hand twist, negative value => left-hand twist.
            zero_elevation: Angle of barrel relative to sight line when sight is set to "zero."
                (Typically computed by ballistic Calculator.)
            sight: Sight properties

        Example:
            This is how you can create a weapon

            ```python
            from py_ballisticcalc import Weapon, Unis, Sight

            weapon = Weapon(
                sight_height=Unit.Inch(2.),
                twist=Unit.Inch(10.),
                zero_elevation=Unit.Mil(0),
                sight=Sight(
                    'FFP', 2,
                    h_click_size=Unit.Mil(0.2),
                    v_click_size=Unit.Mil(0.2)
                )
            )
            ```
        """
        self.sight_height = PreferredUnits.sight_height(sight_height or 0)
        self.twist = PreferredUnits.twist(twist or 0)
        self.zero_elevation = PreferredUnits.angular(zero_elevation or 0)
        self.sight = sight


@dataclass
class Ammo:
    """
    A base class for creating Weapon.

    Attributes:
        dm: DragModel for projectile
        mv: Muzzle Velocity
        powder_temp: Baseline temperature that produces the given mv
        temp_modifier: Change in velocity w temperature: % per 15°C.
            Can be computed with .calc_powder_sens().  Only applies if:
                Settings.use_powder_sensitivity = True
        use_powder_sensitivity: Flag to allow to adjust muzzle velocity to the powder sensitivity

    """

    dm: DragModel
    mv: Velocity
    powder_temp: Temperature
    temp_modifier: float
    use_powder_sensitivity: bool = False

    def __init__(self,
                 dm: DragModel,
                 mv: Union[float, Velocity],
                 powder_temp: Optional[Union[float, Temperature]] = None,
                 temp_modifier: float = 0,
                 use_powder_sensitivity: bool = False):
        """
        Create a new ammo instance with given parameters

        Args:
            dm: drag model
            mv: muzzle velocity at given powder temperature
            powder_temp: powder temperature
            temp_modifier: Change in velocity w temperature: % per 15°C.
                Can be computed with .calc_powder_sens().  Only applies if:
                Ammo.use_powder_sensitivity = True
            use_powder_sensitivity: should adjust muzzle velocity using powder sensitivity

        Example:
            This is how you can create a weapon

            ```python
            from py_ballisticcalc import Ammo, Unit, DragModel

            ammo = Ammo(
                dm=DragModel(
                    bc=0.381,
                    drag_table=TableG7,
                    weight=Unit.Grain(300),
                    length=Unit.Inch(1.7),
                    diameter=Unit.Inch(0.338),
                ),
                mv=Unit.MPS(815),
                powder_temp=Unit.Celsius(15),
                temp_modifier=0.123,
                use_powder_sensitivity=True,
            )
            ```
        """
        self.dm = dm
        self.mv = PreferredUnits.velocity(mv or 0)
        self.powder_temp = PreferredUnits.temperature(powder_temp or Temperature.Celsius(15))
        self.temp_modifier = temp_modifier or 0
        self.use_powder_sensitivity = use_powder_sensitivity

    def calc_powder_sens(self, other_velocity: Union[float, Velocity],
                         other_temperature: Union[float, Temperature]) -> float:
        """Calculates velocity correction by temperature change; assigns to self.temp_modifier

        Args:
            other_velocity: other velocity at other_temperature
            other_temperature: other temperature

        Returns:
            temperature modifier in terms %v_delta/15°C

        Example:
            ```python
            powder_sensitivity = ammo.calc_powder_sens(
                Unit.MPS(830),
                Unit.Celsius(200)
            )
            ```
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

    def get_velocity_for_temp(self, current_temp: Union[float, Temperature]) -> Velocity:
        """Calculates muzzle velocity at temperature, based on temp_modifier.

        Args:
            current_temp: Temperature of cartridge powder

        Returns:
            Muzzle velocity corrected to current_temp

        Example:
            ```python
            muzzle_velocity = ammo.get_velocity_for_temp(
                Unit.Celsius(200)
            )
            ```
        """
        if not self.use_powder_sensitivity:
            return self.mv
        try:
            v0 = self.mv >> Velocity.MPS
            t0 = self.powder_temp >> Temperature.Celsius
            t1 = PreferredUnits.temperature(current_temp) >> Temperature.Celsius
            t_delta = t1 - t0
            muzzle_velocity = self.temp_modifier / (15 / v0) * t_delta + v0
        except ZeroDivisionError:
            muzzle_velocity = 0
        return Velocity.MPS(muzzle_velocity)


__all__ = ('Weapon', 'Ammo', 'Sight', 'SightFocalPlane', 'SightClicks', 'SightReticleStep')
