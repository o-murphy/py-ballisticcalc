"""Weapon and ammunition configuration for ballistic calculations.

This module provides classes for defining weapon and ammunition properties used in
ballistic trajectory calculations. It includes sight systems, weapon characteristics,
and ammunition properties with powder temperature sensitivity modeling.

Classes:
    SightReticleStep: Named tuple for reticle adjustment steps.
    SightClicks: Named tuple for sight click adjustments.
    Sight: Sight configuration with focal plane and click sizes.
    Weapon: Weapon properties including sight height, barrel twist, and zero elevation.
    Ammo: Ammunition properties with drag model and powder temperature sensitivity.

Type Aliases:
    SightFocalPlane: Literal type for sight focal plane options ('FFP', 'SFP', 'LWIR').

Examples:
    Basic weapon and ammunition setup:
    ```python
    from py_ballisticcalc import Weapon, Ammo, Sight, DragModel, TableG7, Unit
    
    weapon = Weapon(
        sight_height=Unit.Inch(2.5),
        twist=Unit.Inch(10),
        sight=Sight('FFP', 2, Unit.Mil(0.2), Unit.Mil(0.2))
    )
    
    ammo = Ammo(
        dm=DragModel(0.381, TableG7, Unit.Grain(300), Unit.Inch(0.338)),
        mv=Unit.MPS(815),
        powder_temp=Unit.Celsius(15),
        use_powder_sensitivity=True
    )
    ```
"""
import math
import typing
from dataclasses import dataclass

from typing_extensions import NamedTuple, Union, Optional, Literal, get_args

from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.unit import Velocity, Temperature, Distance, Angular, PreferredUnits

if typing.TYPE_CHECKING:
    from py_ballisticcalc.trajectory_data import TrajectoryData

SightFocalPlane = Literal['FFP', 'SFP', 'LWIR']


class SightReticleStep(NamedTuple):
    """Reticle step adjustments for sight calculations.

    This named tuple lists the angular step size of adjustments (clicks) available on a particular sight.

    Attributes:
        vertical: Vertical angular adjustment step.
        horizontal: Horizontal angular adjustment step.
        
    Example:
        ```python
        step = SightReticleStep(
            vertical=Angular.Mil(0.2),
            horizontal=Angular.Mil(0.2)
        )
        ```
    """

    vertical: Angular
    horizontal: Angular


class SightClicks(NamedTuple):
    """Sight click adjustments as numeric values.
    
    This named tuple represents the number of clicks needed for vertical
    and horizontal sight adjustments, typically used for turret adjustments.
    
    Attributes:
        vertical: Number of vertical clicks for adjustment.
        horizontal: Number of horizontal clicks for adjustment.
        
    Example:
        ```python
        clicks = SightClicks(vertical=5.0, horizontal=2.5)
        ```
    """

    vertical: float
    horizontal: float


@dataclass
class Sight:
    """Sight configuration for ballistic calculations and adjustments.
    
    This class represents the optical sight system mounted on a weapon, including
    the focal plane type, magnification properties, and click adjustment sizes.
    It provides methods for calculating sight adjustments based on target distance
    and magnification settings.
    
    Attributes:
        focal_plane: Type of focal plane ('FFP' for First Focal Plane, 
                    'SFP' for Second Focal Plane, 'LWIR' for Long Wave Infrared).
        scale_factor: Distance representing the scale factor for sight calculations.
        h_click_size: Angular size of horizontal click adjustments.
        v_click_size: Angular size of vertical click adjustments.
    
    Example:
        ```python
        sight = Sight(
            focal_plane='FFP',
            scale_factor=Unit.Meter(100),
            h_click_size=Unit.Mil(0.2),
            v_click_size=Unit.Mil(0.2)
        )
        ```
    """

    focal_plane: SightFocalPlane
    scale_factor: Distance
    h_click_size: Angular
    v_click_size: Angular

    def __init__(self,
                 focal_plane: SightFocalPlane = 'FFP',
                 scale_factor: Optional[Union[float, Distance]] = None,
                 h_click_size: Optional[Union[float, Angular]] = None,
                 v_click_size: Optional[Union[float, Angular]] = None):
        """Initialize a Sight instance with given parameters.
        
        Args:
            focal_plane: Type of focal plane ('FFP', 'SFP', or 'LWIR').
                        Defaults to 'FFP' (First Focal Plane).
            scale_factor: Distance used for sight scale calculations.
                         Required for SFP sights. If None, defaults to 1 unit.
            h_click_size: Angular size of horizontal click adjustments.
                         Must be positive value.
            v_click_size: Angular size of vertical click adjustments.
                         Must be positive value.
                         
        Raises:
            ValueError: If focal_plane is not supported or scale_factor missing for SFP.
            TypeError: If click sizes are not Angular type or not positive.
            
        Example:
            ```python
            # Default FFP sight
            sight = Sight()
            
            # SFP sight with required scale factor
            sight = Sight(
                focal_plane='SFP',
                scale_factor=Unit.Yard(100),
                h_click_size=Unit.MOA(0.25),
                v_click_size=Unit.MOA(0.25)
            )
            ```
        """
        if focal_plane not in get_args(SightFocalPlane):
            raise ValueError("Wrong focal plane")

        if not scale_factor and focal_plane == 'SFP':
            raise ValueError('Scale_factor required for SFP sights')

        if (not isinstance(h_click_size, (Angular, float, int))
            or not isinstance(v_click_size, (Angular, float, int))
        ):
            raise TypeError("Angle expected for 'h_click_size' and 'v_click_size'")

        self.focal_plane = focal_plane
        self.scale_factor = PreferredUnits.distance(scale_factor or 1)
        self.h_click_size = PreferredUnits.adjustment(h_click_size)
        self.v_click_size = PreferredUnits.adjustment(v_click_size)
        if self.h_click_size.raw_value <= 0 or self.v_click_size.raw_value <= 0:
            raise TypeError("'h_click_size' and 'v_click_size' must be positive")

    def _adjust_sfp_reticle_steps(self, target_distance: Union[float, Distance],
                                  magnification: float) -> SightReticleStep:
        """Calculate SFP reticle steps for target distance and magnification.
        
        For Second Focal Plane (SFP) sights, the reticle size remains constant
        regardless of magnification, so adjustments must be scaled accordingly
        based on the relationship between target distance and magnification.
        
        Args:
            target_distance: Distance to target.
            magnification: Current magnification setting of the sight.
            
        Returns:
            SightReticleStep with adjusted horizontal and vertical steps.
            
        Raises:
            AssertionError: If called on non-SFP sight.
            
        Example:
            ```python
            steps = sight._adjust_sfp_reticle_steps(
                target_distance=Unit.Meter(300),
                magnification=10.0
            )
            ```
        """
        assert self.focal_plane == 'SFP', "SFP focal plane required"
        _td = PreferredUnits.distance(target_distance)
        if _td.raw_value <= 0:
            raise ValueError("target_distance must be positive")
        def get_sfp_step(click_size: Angular):
            """Calculate SFP reticle step size for a given click size."""
            scale_ratio = self.scale_factor.raw_value / _td.raw_value
            # Don't need distances conversion because units cancel:
            return click_size.units(click_size.unit_value * scale_ratio * magnification)
        _h_step = get_sfp_step(self.h_click_size)
        _v_step = get_sfp_step(self.v_click_size)
        return SightReticleStep(_h_step, _v_step)

    def get_adjustment(self, target_distance: Distance,
                       drop_angle: Angular, windage_angle: Angular,
                       magnification: float) -> SightClicks:
        """Calculate sight adjustment for target distance and magnification.
        
        This method computes the required sight adjustments (in clicks) based on
        the ballistic solution for a given target distance and current magnification.
        The calculation method varies depending on the focal plane type.
        
        Args:
            target_distance: Distance to the target.
            drop_angle: Required vertical angular adjustment for drop compensation.
            windage_angle: Required horizontal angular adjustment for windage.
            magnification: Current magnification setting of the sight.
            
        Returns:
            SightClicks with vertical and horizontal click adjustments needed.
            
        Raises:
            AttributeError: If focal_plane is not one of the supported types.
            
        Note:
            - SFP sights: Adjustments scaled by target distance and magnification
            - FFP sights: Direct conversion using click sizes
            - LWIR sights: Adjustments scaled by magnification only
            
        Example:
            ```python
            clicks = sight.get_adjustment(
                target_distance=Unit.Meter(500),
                drop_angle=Unit.Mil(2.5),
                windage_angle=Unit.Mil(0.8),
                magnification=12.0
            )
            print(f"Adjust: {clicks.vertical} up, {clicks.horizontal} right")
            ```
        """
        if magnification <= 0:
            raise ValueError("magnification must be positive")
        if self.focal_plane == 'SFP':
            steps = self._adjust_sfp_reticle_steps(target_distance, magnification)
            return SightClicks(
                drop_angle.raw_value / steps.vertical.raw_value,
                windage_angle.raw_value / steps.horizontal.raw_value
            )
        if self.focal_plane == 'FFP':
            return SightClicks(
                drop_angle.raw_value / self.v_click_size.raw_value,
                windage_angle.raw_value / self.h_click_size.raw_value
            )
        if self.focal_plane == 'LWIR':
            return SightClicks(  # adjust clicks to magnification
                drop_angle.raw_value / (self.v_click_size.raw_value / magnification),
                windage_angle.raw_value / (self.h_click_size.raw_value / magnification)
            )
        raise AttributeError("Wrong focal_plane")

    def get_trajectory_adjustment(self, trajectory_point: 'TrajectoryData', magnification: float) -> SightClicks:
        """Calculate sight adjustment from trajectory data point.
        
        This convenience method extracts the necessary adjustment values from a
        TrajectoryData instance and calculates the required sight clicks.
        
        Args:
            trajectory_point: TrajectoryData instance containing ballistic solution.
            magnification: Current magnification setting of the sight.
            
        Returns:
            SightClicks with vertical and horizontal click adjustments needed.
            
        Example:
            ```python
            # Assuming trajectory_result is from Calculator.fire()
            for point in trajectory_result:
                clicks = sight.get_trajectory_adjustment(point, magnification=10.0)
                print(f"At {point.distance}: {clicks.vertical} clicks up")
            ```
        """
        return self.get_adjustment(trajectory_point.distance,
                                   trajectory_point.drop_angle,
                                   trajectory_point.windage_angle,
                                   magnification)


@dataclass
class Weapon:
    """Weapon configuration for ballistic calculations.

    This class represents the physical characteristics of a gun that affect trajectory calculations,
    including sight height, barrel twist rate, zero elevation, and optional sight system configuration.
    
    Attributes:
        sight_height: Vertical distance from line of sight to center of bore,
                     measured at the muzzle perpendicular to the line of sight.
        twist: Distance for barrel rifling to complete one complete turn.
               Positive values indicate right-hand twist, negative for left-hand.
        zero_elevation: Angle of barrel centerline relative to line of sight
                       when the sight is set to "zero" position.
        sight: Optional Sight instance for advanced sight calculations.
        
    Note:
        The sight height is critical for trajectory calculations as it determines
        the offset between the line of sight and the bullet's initial trajectory.
        Barrel twist affects spin drift calculations for long-range shots.
        
    Example:
        ```python
        weapon = Weapon(
            sight_height=Unit.Inch(2.5),
            twist=Unit.Inch(10),
            zero_elevation=Unit.Mil(0),
            sight=Sight('FFP', 100, Unit.Mil(0.2), Unit.Mil(0.2))
        )
        ```
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
        """Initialize a Weapon instance with given parameters.
        
        Args:
            sight_height: Vertical distance from line of sight to center of bore,
                         measured at the muzzle. Defaults to 0 if not specified.
            twist: Distance for barrel rifling to complete one complete turn.
                  Positive value for right-hand twist, negative for left-hand.
                  Defaults to 0 if not specified.
            zero_elevation: Angle of barrel relative to sight line when sight
                           is set to "zero." Typically computed by Calculator.set_weapon_zero().
                           Defaults to 0 if not specified.
            sight: Optional Sight properties for advanced sight calculations.
                  
        Example:
            ```python
            from py_ballisticcalc import Weapon, Unit, Sight

            # Basic weapon configuration
            weapon = Weapon(
                sight_height=Unit.Inch(2.5),
                twist=Unit.Inch(10)
            )
            
            # Advanced weapon with sight system
            weapon = Weapon(
                sight_height=Unit.Inch(2.5),
                twist=Unit.Inch(10),
                zero_elevation=Unit.Mil(0),
                sight=Sight(
                    'FFP', 
                    scale_factor=Unit.Meter(100),
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
    """Ammunition configuration for ballistic calculations.
    
    This class represents the physical and ballistic properties of ammunition,
    including the drag model, muzzle velocity, and powder temperature sensitivity.
    It provides methods for calculating temperature-dependent velocity adjustments.
    
    Attributes:
        dm: DragModel instance defining the projectile's ballistic coefficient
            and drag characteristics.
        mv: Muzzle velocity at the baseline powder temperature.
        powder_temp: Baseline temperature that produces the given muzzle velocity.
        temp_modifier: Change in velocity with temperature as a percentage per 15°C.
                      Can be computed using calc_powder_sens() method.
        use_powder_sensitivity: Flag to enable automatic muzzle velocity adjustment
                               based on powder temperature.
                               
    Note:
        When use_powder_sensitivity is True, the actual muzzle velocity will be
        automatically adjusted based on the difference between the current powder
        temperature and the baseline powder_temp using the temp_modifier.
        
    Example:
        ```python
        ammo = Ammo(
            dm=DragModel(0.381, TableG7, Unit.Grain(300), Unit.Inch(0.338)),
            mv=Unit.MPS(815),
            powder_temp=Unit.Celsius(15),
            temp_modifier=0.123,
            use_powder_sensitivity=True
        )
        ```
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
        """Initialize an Ammo instance with given parameters.
        
        Args:
            dm: DragModel instance defining projectile ballistic characteristics.
            mv: Muzzle velocity at the baseline powder temperature.
            powder_temp: Baseline temperature that produces the given muzzle velocity.
                        If None, defaults to 15°C.
            temp_modifier: Change in velocity with temperature as percentage per 15°C.
                          Can be computed with calc_powder_sens() method.
                          Only applies if use_powder_sensitivity is True.
            use_powder_sensitivity: If True, automatically adjust muzzle velocity
                                   based on powder temperature differences.
                                   
        Example:
            ```python
            from py_ballisticcalc import Ammo, DragModel, TableG7, Unit

            # Basic ammunition without temperature sensitivity
            ammo = Ammo(dm=DragModel(0.381, TableG7), mv=Unit.MPS(815))
            
            # Advanced ammunition with powder temperature sensitivity
            ammo = Ammo(
                dm=DragModel(0.381, TableG7, Unit.Grain(300), Unit.Inch(0.338)),
                mv=Unit.MPS(815),
                powder_temp=Unit.Celsius(15),
                temp_modifier=0.123,
                use_powder_sensitivity=True
            )
            # Calculate sensitivity from known data points
            ammo.calc_powder_sens(Unit.MPS(830), Unit.Celsius(30))
            ```
        """
        self.dm = dm
        self.mv = PreferredUnits.velocity(mv or 0)
        self.powder_temp = PreferredUnits.temperature(powder_temp or Temperature.Celsius(15))
        self.temp_modifier = temp_modifier or 0
        self.use_powder_sensitivity = use_powder_sensitivity

    def calc_powder_sens(self, other_velocity: Union[float, Velocity],
                         other_temperature: Union[float, Temperature]) -> float:
        """Calculate velocity temperature sensitivity and update temp_modifier.
        
        This method calculates the powder temperature sensitivity coefficient
        based on two known velocity/temperature data points and assigns the
        result to the temp_modifier attribute.
        
        Args:
            other_velocity: Known velocity at other_temperature.
            other_temperature: Temperature corresponding to other_velocity.
            
        Returns:
            Temperature modifier in terms of percentage velocity change per 15°C.
            
        Raises:
            ValueError: If other_velocity and temperature are the same as baseline,
                       making calculation impossible.
                       
        Note:
            The calculation uses the formula:
            temp_modifier = (velocity_delta / temperature_delta) * (15 / lower_velocity)
            
            This provides a normalized sensitivity value representing the percentage
            change in velocity per 15°C temperature change.
            
        Example:
            ```python
            # Calculate sensitivity from known velocity drop in cold weather
            sensitivity = ammo.calc_powder_sens(
                other_velocity=Unit.MPS(800),  # Velocity at cold temp
                other_temperature=Unit.Celsius(0)  # Cold temperature
            )
            print(f"Powder sensitivity: {sensitivity:.4f}% per 15°C")
            
            # The temp_modifier is now automatically set
            print(f"Current temp_modifier: {ammo.temp_modifier}")
            ```
        """
        v0 = self.mv >> Velocity.MPS
        t0 = self.powder_temp >> Temperature.Celsius
        v1 = PreferredUnits.velocity(other_velocity) >> Velocity.MPS
        t1 = PreferredUnits.temperature(other_temperature) >> Temperature.Celsius

        if v0 <= 0 or v1 <= 0:
            raise ValueError("calc_powder_sens requires positive muzzle velocities")
        v_delta = math.fabs(v0 - v1)
        t_delta = math.fabs(t0 - t1)
        v_lower = v1 if v1 < v0 else v0

        if v_delta == 0 or t_delta == 0:
            raise ValueError("other_velocity and temperature can't be same as default")
        self.temp_modifier = v_delta / t_delta * (15 / v_lower)  # * 100
        return self.temp_modifier

    def get_velocity_for_temp(self, current_temp: Union[float, Temperature]) -> Velocity:
        """Calculate muzzle velocity adjusted for powder temperature.
        
        This method calculates the muzzle velocity at a given temperature based
        on the baseline velocity, powder temperature, and temperature sensitivity
        modifier. If powder sensitivity is disabled, returns the baseline velocity.
        
        Args:
            current_temp: Temperature of the cartridge powder.
                         
        Returns:
            Muzzle velocity corrected for the specified temperature.
            
        Note:
            The calculation uses the formula:
            `adjusted_velocity = baseline_velocity + (temp_modifier / (15 / baseline_velocity)) * temp_delta`
            ... where temp_delta is the difference between current_temp and powder_temp.
            
            If use_powder_sensitivity is False, returns the baseline muzzle velocity regardless of temperature.

        Examples:
            ```python
            # Get velocity for current conditions
            cold_velocity = ammo.get_velocity_for_temp(Unit.Celsius(-10))
            hot_velocity = ammo.get_velocity_for_temp(Unit.Celsius(35))
            
            print(f"Baseline velocity: {ammo.mv}")
            print(f"Cold weather velocity: {cold_velocity}")
            print(f"Hot weather velocity: {hot_velocity}")
            
            # With powder sensitivity disabled
            ammo.use_powder_sensitivity = False
            constant_velocity = ammo.get_velocity_for_temp(Unit.Celsius(-10))
            # constant_velocity equals ammo.mv regardless of temperature
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
