# pylint: disable=missing-class-docstring,missing-function-docstring,too-many-lines
# pylint: disable=line-too-long,invalid-name,attribute-defined-outside-init
"""pure python trajectory calculation backend"""

import math
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from enum import Enum, auto
from deprecated import deprecated

from typing_extensions import Optional, NamedTuple, Union, List, Tuple, Dict, TypedDict, TypeVar

from py_ballisticcalc.conditions import Shot, Wind
from py_ballisticcalc.drag_model import DragDataPoint
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError, OutOfRangeError, SolverRuntimeError
from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc.logger import logger
from py_ballisticcalc.trajectory_data import TrajectoryData, TrajFlag, HitResult
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Energy, Pressure, Temperature, Unit
from py_ballisticcalc.vector import Vector

__all__ = (
    'create_base_engine_config',
    'BaseEngineConfig',
    'BaseEngineConfigDict',
    'DEFAULT_BASE_ENGINE_CONFIG',
    'BaseIntegrationEngine',
    'calculate_energy',
    'calculate_ogw',
    'get_correction',
    'create_trajectory_row',
    '_TrajectoryDataFilter',
    '_WindSock',
    'CurvePoint',
    '_ShotProps',
    '_ZeroCalcStatus',
    'with_no_minimum_velocity',
)

cZeroFindingAccuracy: float = 0.000005  # Max allowed slant-error in feet to end zero search
cMaxIterations: int = 40  # maximum number of iterations for zero search
cMinimumAltitude: float = -1500  # feet, below sea level
cMaximumDrop: float = -15000  # feet, maximum drop from the muzzle to continue trajectory
cMinimumVelocity: float = 50.0  # fps, minimum velocity to continue trajectory
cGravityConstant: float = -32.17405  # feet per second squared
cStepMultiplier: float = 1.0  # Multiplier for engine's default step, for changing integration speed & precision


@dataclass
class BaseEngineConfig:
    cZeroFindingAccuracy: float = cZeroFindingAccuracy
    cMaxIterations: int = cMaxIterations
    cMinimumAltitude: float = cMinimumAltitude
    cMaximumDrop: float = cMaximumDrop
    cMinimumVelocity: float = cMinimumVelocity
    cGravityConstant: float = cGravityConstant
    cStepMultiplier: float = cStepMultiplier


DEFAULT_BASE_ENGINE_CONFIG: BaseEngineConfig = BaseEngineConfig()


class BaseEngineConfigDict(TypedDict, total=False):
    cZeroFindingAccuracy: Optional[float]
    cMaxIterations: Optional[int]
    cMinimumAltitude: Optional[float]
    cMaximumDrop: Optional[float]
    cMinimumVelocity: Optional[float]
    cGravityConstant: Optional[float]
    cStepMultiplier: Optional[float]


def create_base_engine_config(interface_config: Optional[BaseEngineConfigDict] = None) -> BaseEngineConfig:
    config = asdict(DEFAULT_BASE_ENGINE_CONFIG)
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return BaseEngineConfig(**config)


class CurvePoint(NamedTuple):
    """Coefficients for quadratic interpolation"""
    a: float
    b: float
    c: float


class BaseTrajData(NamedTuple):
    """Minimal data for one point in ballistic trajectory"""
    time: float
    position: Vector
    velocity: Vector
    mach: float


class _TrajectoryDataFilter:
    """
    Determines when to record trajectory data points based on range and time.
    For range steps, interpolates between integration steps to get the exact point.
    There is no interpolation for other points of interest (APEX, MACH, ZERO), unless
        they correspond to a range step, in which case they are interpolated to the range step.
    """
    filter: Union[TrajFlag, int]
    current_flag: Union[TrajFlag, int]
    seen_zero: Union[TrajFlag, int]
    time_of_last_record: float
    time_step: float
    range_step: float
    previous_mach: float
    previous_time: float
    previous_position: Vector
    previous_velocity: Vector
    previous_v_mach: float
    next_record_distance: float
    look_angle: float

    def __init__(self, filter_flags: Union[TrajFlag, int], range_step: float,
                 initial_position: Vector, initial_velocity: Vector,
                 barrel_angle_rad: float, look_angle_rad: float = 0.0,
                 time_step: float = 0.0):
        """If a time_step is indicated, then we will record a row at least that often in the trajectory"""
        self.filter: Union[TrajFlag, int] = filter_flags
        self.current_flag: Union[TrajFlag, int] = TrajFlag.NONE
        self.seen_zero: Union[TrajFlag, int] = TrajFlag.NONE
        self.time_step: float = time_step
        self.range_step: float = range_step
        self.time_of_last_record: float = 0.0
        self.next_record_distance: float = 0.0
        self.previous_mach: float = 0.0
        self.previous_time: float = 0.0
        self.previous_position: Vector = initial_position
        self.previous_velocity: Vector = initial_velocity
        self.previous_v_mach: float = 0.0  # Previous velocity in Mach terms
        self.look_angle: float = look_angle_rad
        if self.filter & TrajFlag.ZERO:
            if initial_position.y >= 0:
                self.seen_zero |= TrajFlag.ZERO_UP
            elif initial_position.y < 0 and barrel_angle_rad < self.look_angle:
                self.seen_zero |= TrajFlag.ZERO_DOWN

    # pylint: disable=too-many-positional-arguments
    def should_record(self, position: Vector, velocity: Vector, mach: float,
                      time: float) -> Optional[BaseTrajData]:
        self.current_flag = TrajFlag.NONE
        data = None
        if (self.range_step > 0) and (position.x >= self.next_record_distance):
            while self.next_record_distance + self.range_step < position.x:
                # Handle case where we have stepped past more than one record distance
                self.next_record_distance += self.range_step
            if position.x > self.previous_position.x:
                # Interpolate to get BaseTrajData at the record distance
                ratio = (self.next_record_distance - self.previous_position.x) / (
                        position.x - self.previous_position.x)
                data = BaseTrajData(
                    time=self.previous_time + (time - self.previous_time) * ratio,
                    position=self.previous_position + (  # type: ignore[operator]
                            position - self.previous_position) * ratio,
                    velocity=self.previous_velocity + (  # type: ignore[operator]
                            velocity - self.previous_velocity) * ratio,
                    mach=self.previous_mach + (mach - self.previous_mach) * ratio
                )
            self.current_flag |= TrajFlag.RANGE
            self.next_record_distance += self.range_step
            self.time_of_last_record = time
        elif self.time_step > 0:
            self.check_next_time(time)
        if self.filter & TrajFlag.ZERO:
            self.check_zero_crossing(position)
        if self.filter & TrajFlag.MACH:
            self.check_mach_crossing(velocity.magnitude(), mach)
        if self.filter & TrajFlag.APEX:
            self.check_apex(velocity)
        if bool(self.current_flag & self.filter) and data is None:
            data = BaseTrajData(time=time, position=position,
                                velocity=velocity, mach=mach)
        self.previous_time = time
        self.previous_position = position
        self.previous_velocity = velocity
        self.previous_mach = mach
        return data

    def check_next_time(self, time: float):
        if time > self.time_of_last_record + self.time_step:
            self.current_flag |= TrajFlag.RANGE
            self.time_of_last_record = time

    def check_mach_crossing(self, velocity: float, mach: float):
        current_v_mach = velocity / mach
        if self.previous_v_mach > 1 >= current_v_mach:  # (velocity / mach <= 1) and (previous_mach > 1)
            self.current_flag |= TrajFlag.MACH
        self.previous_v_mach = current_v_mach

    def check_zero_crossing(self, range_vector: Vector):
        # Especially with non-zero look_angle, rounding can suggest multiple adjacent zero-crossings
        #   self.seen_zero prevents recording more than one.
        if range_vector.x > 0:
            # Zero reference line is the sight line defined by look_angle
            reference_height = range_vector.x * math.tan(self.look_angle)
            # If we haven't seen ZERO_UP, we look for that first
            if not (self.seen_zero & TrajFlag.ZERO_UP):  # pylint: disable=superfluous-parens
                if range_vector.y >= reference_height:
                    self.current_flag |= TrajFlag.ZERO_UP
                    self.seen_zero |= TrajFlag.ZERO_UP
            # We've crossed above sight line; now look for crossing back through it
            elif not (self.seen_zero & TrajFlag.ZERO_DOWN):  # pylint: disable=superfluous-parens
                if range_vector.y < reference_height:
                    self.current_flag |= TrajFlag.ZERO_DOWN
                    self.seen_zero |= TrajFlag.ZERO_DOWN

    def check_apex(self, velocity_vector: Vector):
        """
        The apex is defined as the point, after launch, where the vertical component of velocity
            goes from positive to negative.
        """
        if velocity_vector.y <= 0 and self.previous_velocity.y > 0:
            self.current_flag |= TrajFlag.APEX


class _WindSock:
    """
    Currently this class assumes that requests for wind readings will only be made in order of increasing range.
    This assumption is violated if the projectile is blown or otherwise moves backwards.
    """
    winds: tuple['Wind', ...]
    current_index: int
    next_range: float

    def __init__(self, winds: Union[Tuple["Wind", ...], None]):
        """
        Initializes the _WindSock class.

        Args:
            winds (Union[Tuple[Wind, ...], None], optional): A tuple of Wind objects. Defaults to None.
        """
        self.winds: Tuple["Wind", ...] = winds or tuple()
        self.current_index: int = 0
        self.next_range: float = Wind.MAX_DISTANCE_FEET
        self._last_vector_cache: Union["Vector", None] = None
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    def current_vector(self) -> "Vector":
        """
        Returns the current cached wind vector.

        Raises:
            RuntimeError: If no wind vector has been cached.

        Returns:
            Vector: The current cached wind vector.
        """
        if not self._last_vector_cache:
            raise RuntimeError("No cached wind vector")
        return self._last_vector_cache

    def update_cache(self) -> None:
        """Updates the cache only if needed or if forced during initialization."""
        if self.current_index < self._length:
            cur_wind = self.winds[self.current_index]
            self._last_vector_cache = cur_wind.vector
            self.next_range = cur_wind.until_distance >> Distance.Foot
        else:
            self._last_vector_cache = Vector(0.0, 0.0, 0.0)
            self.next_range = Wind.MAX_DISTANCE_FEET

    def vector_for_range(self, next_range: float) -> "Vector":
        """
        Updates the wind vector if `next_range` surpasses `self.next_range`.

        Args:
            next_range (float): The range to check against the current wind segment.

        Returns:
            Vector: The wind vector for the given range.
        """
        if next_range >= self.next_range:
            self.current_index += 1
            if self.current_index >= self._length:
                self._last_vector_cache = Vector(0.0, 0.0, 0.0)
                self.next_range = Wind.MAX_DISTANCE_FEET
            else:
                self.update_cache()  # This will trigger cache updates.
        return self.current_vector()


@dataclass
class _ShotProps:
    """Properties for a Shot used in trajectory calculations, converted to internal units."""
    shot: Shot
    bc: float  # Ballistic coefficient
    curve: List[CurvePoint]
    mach_list: List[float]

    look_angle_rad: float
    twist_inch: float  # Twist rate of barrel rifling, in inches of length to make one full rotation.
    length_inch: float  # Length of the bullet in inches
    diameter_inch: float  # Diameter of the bullet in inches
    weight_grains: float  # Weight of the bullet in grains
    barrel_elevation_rad: float  # Barrel elevation angle in radians
    barrel_azimuth_rad: float  # Barrel azimuth angle in radians
    sight_height_ft: float  # Height of the sight above the bore in feet
    cant_cosine: float  # Cosine of the cant angle
    cant_sine: float  # Sine of the cant angle
    alt0_ft: float  # Initial altitude in feet
    calc_step: float  # Calculation step size
    muzzle_velocity_fps: float  # Muzzle velocity in feet per second
    stability_coefficient: float = field(init=False)

    def __post_init__(self):
        self.stability_coefficient = self._calc_stability_coefficient()

    @property
    def winds(self) -> Tuple[Wind, ...]:
        return self.shot.winds

    def drag_by_mach(self, mach: float) -> float:
        """
        Calculates a standard drag factor (SDF) for the given Mach number.  Where:
            Drag force = V^2 * AirDensity * C_d * S / 2m
                       = V^2 * density_ratio * SDF
        Where:
            - density_ratio = LocalAirDensity / StandardDensity = rho / rho_0
            - StandardDensity of Air = rho_0 = 0.076474 lb/ft^3
            - S is cross-section = d^2 pi/4, where d is bullet diameter in inches
            - m is bullet mass in pounds
            - bc contains m/d^2 in units lb/in^2, which is multiplied by 144 to convert to lb/ft^2

        Thus:
            - The magic constant found here = StandardDensity * pi / (4 * 2 * 144)

        Args:
            mach (float): The Mach number.

        Returns:
            float: The standard drag factor at the given Mach number.
        """
        # cd = calculate_by_curve(self._table_data, self._curve, mach)
        # use calculation over list[double] instead of list[DragDataPoint]
        cd = _calculate_by_curve_and_mach_list(self.mach_list, self.curve, mach)
        return cd * 2.08551e-04 / self.bc

    def spin_drift(self, time) -> float:
        """
        Litz spin-drift approximation

        Args:
            time: Time of flight

        Returns:
            windage due to spin drift, in feet
        """
        if (self.stability_coefficient != 0) and (self.twist_inch != 0):
            sign = 1 if self.twist_inch > 0 else -1
            return sign * (1.25 * (self.stability_coefficient + 1.2)
                           * math.pow(time, 1.83)) / 12
        return 0

    def _calc_stability_coefficient(self) -> float:
        """
        Calculates the Miller stability coefficient.

        Returns:
            float: The Miller stability coefficient.
        """
        if self.twist_inch and self.length_inch and self.diameter_inch and self.shot.atmo.pressure.raw_value:
            twist_rate = math.fabs(self.twist_inch) / self.diameter_inch
            length = self.length_inch / self.diameter_inch
            # Miller stability formula
            sd = 30 * self.weight_grains / (
                    math.pow(twist_rate, 2) * math.pow(self.diameter_inch, 3) * length * (1 + math.pow(length, 2))
            )
            # Velocity correction factor
            fv = math.pow(self.muzzle_velocity_fps / 2800, 1.0 / 3.0)
            # Atmospheric correction
            ft = self.shot.atmo.temperature >> Temperature.Fahrenheit
            pt = self.shot.atmo.pressure >> Pressure.InHg
            ftp = ((ft + 460) / (59 + 460)) * (29.92 / pt)
            return sd * fv * ftp
        return 0

    def get_density_and_mach_for_altitude(self, drop: float):
        return self.shot.atmo.get_density_and_mach_for_altitude(self.alt0_ft + drop)


class _ZeroCalcStatus(Enum):
    DONE = auto()  # Zero angle found, just return it
    CONTINUE = auto()  # Continue searching for zero angle


class ZeroFindingProps(NamedTuple):
    status: _ZeroCalcStatus
    look_angle_rad: float
    slant_range_ft: Optional[float] = None
    target_x_ft: Optional[float] = None
    target_y_ft: Optional[float] = None
    start_height_ft: Optional[float] = None


def with_no_minimum_velocity(method):
    def wrapper(self, *args, **kwargs):
        restore = None
        if getattr(self._config, "cMinimumVelocity", None) != 0:
            restore = self._config.cMinimumVelocity
            self._config.cMinimumVelocity = 0
        try:
            return method(self, *args, **kwargs)
        finally:
            if restore is not None:
                self._config.cMinimumVelocity = restore
    return wrapper


_BaseEngineConfigDictT = TypeVar("_BaseEngineConfigDictT", bound='BaseEngineConfigDict', covariant=True)


# pylint: disable=too-many-instance-attributes
class BaseIntegrationEngine(ABC, EngineProtocol[_BaseEngineConfigDictT]):
    """
    All calculations are done in imperial units of feet and fps.
    """
    APEX_IS_MAX_RANGE_RADIANS: float = 0.0003  # Radians from vertical where the apex is max range
    ALLOWED_ZERO_ERROR_FEET: float = 1e-2  # Allowed range error (along sight line), in feet, for zero angle
    SEPARATE_ROW_TIME_DELTA: float = 1e-5  # Difference in seconds required for a TrajFlag to generate separate rows

    def __init__(self, _config: _BaseEngineConfigDictT):
        """
        Initializes the class.

        Args:
            _config (BaseEngineConfig): The configuration object.
        """
        self._config: BaseEngineConfig = create_base_engine_config(_config)
        self.gravity_vector: Vector = Vector(.0, self._config.cGravityConstant, .0)

    def get_calc_step(self) -> float:
        """Get step size for integration."""
        return self._config.cStepMultiplier

    def _init_trajectory(self, shot_info: Shot) -> _ShotProps:
        """
        Converts Shot properties into floats dimensioned in internal units.

        Args:
            shot_info (Shot): Information about the shot.
        """
        return _ShotProps(
            shot=shot_info,
            bc=shot_info.ammo.dm.BC,
            curve=calculate_curve(shot_info.ammo.dm.drag_table),
            mach_list=_get_only_mach_data(shot_info.ammo.dm.drag_table),
            look_angle_rad=shot_info.look_angle >> Angular.Radian,
            twist_inch=shot_info.weapon.twist >> Distance.Inch,
            length_inch=shot_info.ammo.dm.length >> Distance.Inch,
            diameter_inch=shot_info.ammo.dm.diameter >> Distance.Inch,
            weight_grains=shot_info.ammo.dm.weight >> Weight.Grain,
            barrel_elevation_rad=shot_info.barrel_elevation >> Angular.Radian,
            barrel_azimuth_rad=shot_info.barrel_azimuth >> Angular.Radian,
            sight_height_ft=shot_info.weapon.sight_height >> Distance.Foot,
            cant_cosine=math.cos(shot_info.cant_angle >> Angular.Radian),
            cant_sine=math.sin(shot_info.cant_angle >> Angular.Radian),
            alt0_ft=shot_info.atmo.altitude >> Distance.Foot,
            calc_step=self.get_calc_step(),
            muzzle_velocity_fps=shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp) >> Velocity.FPS,
        )

    def find_max_range(self, shot_info: Shot, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[
        Distance, Angular]:
        """
        Finds the maximum range along shot_info.look_angle, and the launch angle to reach it.

        Args:
            shot_info (Shot): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for max range.
                                                               Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum slant-range and the launch angle to reach it.

        Raises:
            ValueError: If the angle bracket excludes the look_angle.

        TODO: Make sure user hasn't restricted angle bracket to exclude the look_angle.
            ... and check for weird situations, like backward-bending trajectories,
            where the max range occurs with launch angle less than the look angle.
        """
        props = self._init_trajectory(shot_info)
        return self._find_max_range(props, angle_bracket_deg)

    @with_no_minimum_velocity
    def _find_max_range(self, props: _ShotProps, angle_bracket_deg: Tuple[float, float] = (0, 90)) -> Tuple[
        Distance, Angular]:
        """
        Internal function to find the maximum slant range via golden-section search.

        Args:
            props (_ShotProps): The shot information: gun, ammo, environment, look_angle.
            angle_bracket_deg (Tuple[float, float], optional): The angle bracket in degrees to search for max range.
                                                               Defaults to (0, 90).

        Returns:
            Tuple[Distance, Angular]: The maximum slant range and the launch angle to reach it.

        Raises:
            ValueError: If the angle bracket excludes the look_angle.

        TODO: Presently this only (barely) works for horizontal look-angle because:
                1. We have no way to stop integrator when it hits ZERO_DOWN, and
                2. Integrator doesn't interpolate for that flag value.
            Here what we get is the distance of the first point computed by integrator after return to horizontal.
        """
        # region Virtually vertical shot
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            max_range = self._find_apex(props).slant_distance
            return max_range, Angular.Radian(props.look_angle_rad)
        # endregion Virtually vertical shot

        if props.look_angle_rad > 0:
            warnings.warn("Code does not yet support non-horizontal look angles.", UserWarning)

        restore_cMaximumDrop = None
        if self._config.cMaximumDrop:
            restore_cMaximumDrop = self._config.cMaximumDrop
            self._config.cMaximumDrop = 0  # We want to run trajectory until it returns to horizontal

        t_calls = 0
        cache: Dict[float, float] = {}

        def range_for_angle(angle_rad: float) -> float:
            """Horizontal range to zero (in feet) for given launch angle in radians."""
            if angle_rad in cache:
                return cache[angle_rad]
            props.barrel_elevation_rad = angle_rad
            nonlocal t_calls
            t_calls += 1
            logger.debug(f"range_for_angle call #{t_calls} for angle {math.degrees(angle_rad)} degrees")
            t = self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.NONE)[-1]
            cache[angle_rad] = t.distance >> Distance.Foot
            return cache[angle_rad]

        # region Golden-section search
        inv_phi = (math.sqrt(5) - 1) / 2  # 0.618...
        inv_phi_sq = inv_phi ** 2
        a, b = (math.radians(deg) for deg in angle_bracket_deg)
        h = b - a
        c = a + inv_phi_sq * h
        d = a + inv_phi * h
        yc = range_for_angle(c)
        yd = range_for_angle(d)
        for _ in range(100):  # 100 iterations is more than enough for high precision
            if h < 1e-5:  # Angle tolerance in radians
                break
            if yc > yd:
                b, d, yd = d, c, yc
                h = b - a
                c = a + inv_phi_sq * h
                yc = range_for_angle(c)
            else:
                a, c, yc = c, d, yd
                h = b - a
                d = a + inv_phi * h
                yd = range_for_angle(d)
        angle_at_max_rad = (a + b) / 2
        # endregion
        max_range_ft = range_for_angle(angle_at_max_rad)

        if restore_cMaximumDrop is not None:
            self._config.cMaximumDrop = restore_cMaximumDrop
        logger.debug(f"._find_max_range required {t_calls} trajectory calculations")
        return Distance.Feet(max_range_ft), Angular.Radian(angle_at_max_rad)

    def find_apex(self, shot_info: Shot) -> TrajectoryData:
        """
        Finds the apex of the trajectory, where apex is defined as the point
            where the vertical component of velocity goes from positive to negative.

        Args:
            shot_info (Shot): The shot information.
        
        Returns:
            TrajectoryData: The trajectory data at the apex of the trajectory.
        
        Raises:
            SolverRuntimeError: If no apex is found in the trajectory data.
            ValueError: If barrel elevation is not > 0.
        """
        props = self._init_trajectory(shot_info)
        return self._find_apex(props)

    @with_no_minimum_velocity
    def _find_apex(self, props: _ShotProps) -> TrajectoryData:
        """
        Internal implementation to find the apex of the trajectory.

        Args:
            props (_ShotProps): The shot properties.

        Returns:
            TrajectoryData at the trajectory's apex (where velocity.y goes from positive to negative).            

        Raises:
            SolverRuntimeError: If no apex is found in the trajectory data.
            ValueError: If barrel elevation is not > 0.
        """
        if props.barrel_elevation_rad <= 0:
            raise ValueError("Barrel elevation must be greater than 0 to find apex.")
        hit = self._integrate(props, 9e9, 9e9, filter_flags=TrajFlag.APEX)
        apex = hit.flag(TrajFlag.APEX)
        if not apex:
            raise SolverRuntimeError("No apex flagged in trajectory data")
        return apex

    def _init_zero_calculation(self, props: _ShotProps, distance: Distance) -> ZeroFindingProps:
        """
        Initializes the zero calculation for the given shot and distance.
            Handles edge cases.

        Args:
            props (_ShotProps): The shot information, with look_angle to the target.
            distance (Distance): The slant distance to the target.

        Returns:
            ZeroFindingProps
        """

        slant_range_ft = distance >> Distance.Foot
        target_x_ft = slant_range_ft * math.cos(props.look_angle_rad)
        target_y_ft = slant_range_ft * math.sin(props.look_angle_rad)
        start_height_ft = -props.sight_height_ft * props.cant_cosine

        # region Edge cases
        if abs(slant_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=props.look_angle_rad)
        if abs(slant_range_ft) < 2.0 * max(abs(start_height_ft), props.calc_step):
            # Very close shot; ignore gravity and drag
            return ZeroFindingProps(_ZeroCalcStatus.DONE,
                                    look_angle_rad=math.atan2(target_y_ft + start_height_ft, target_x_ft))
        if abs(props.look_angle_rad - math.radians(90)) < self.APEX_IS_MAX_RANGE_RADIANS:
            # Virtually vertical shot; just check if it can reach the target
            max_range = self._find_apex(props).slant_distance
            if (max_range >> Distance.Foot) < slant_range_ft:
                raise OutOfRangeError(distance, max_range, _new_rad(props.look_angle_rad))
            return ZeroFindingProps(_ZeroCalcStatus.DONE, look_angle_rad=props.look_angle_rad)
        # endregion Edge cases

        return ZeroFindingProps(_ZeroCalcStatus.CONTINUE,
                                props.look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft)

    def find_zero_angle(self, shot_info: Shot, distance: Distance, lofted: bool = False) -> Angular:
        """
        Finds the barrel elevation needed to hit sight line at a specific distance,
            using unimodal root-finding that is guaranteed to succeed if a solution exists (e.g., Ridder's method).

        Args:
            shot_info (Shot): The shot information.
            distance (Distance): Slant distance to the target.
            lofted (bool, optional): If True, find the higher angle that hits the zero point.

        Returns:
            Angular: Barrel elevation needed to hit the zero point.
        """
        props = self._init_trajectory(shot_info)
        return self._find_zero_angle(props, distance, lofted)

    @with_no_minimum_velocity
    def _find_zero_angle(self, props: _ShotProps, distance: Distance, lofted: bool = False) -> Angular:
        """
        Internal implementation to find the barrel elevation needed to hit sight line at a specific distance,
            using Ridder's method for guaranteed convergence.

        Args:
            props (_ShotProps): The shot information.
            distance (Distance): The distance to the target.
            lofted (bool, optional): If True, find the higher angle that hits the zero point.

        Returns:
            Angular: Barrel elevation needed to hit the zero point.

        TODO: Cache the trajectory calculations in _find_max_range to apply in Ridder's method.
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = (
            self._init_zero_calculation(props, distance)
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad)

        # Make mypy happy
        assert start_height_ft is not None
        assert target_x_ft is not None
        assert target_y_ft is not None
        assert slant_range_ft is not None

        # 1. Find the maximum possible range to establish a search bracket.
        # TODO: In many scenarios this is unnecessarily expensive: We can confirm that the target is within
        #      range without precisely determining the max range at the look angle, and Ridder's method on
        #      the full interval 0-90° would be faster.
        max_range, angle_at_max = self._find_max_range(props)
        max_range_ft = max_range >> Distance.Foot
        angle_at_max_rad = angle_at_max >> Angular.Radian

        # 2. Handle edge cases based on max range.
        if slant_range_ft > max_range_ft:
            raise OutOfRangeError(distance, max_range, Angular.Radian(look_angle_rad))
        if abs(slant_range_ft - max_range_ft) < self.ALLOWED_ZERO_ERROR_FEET:
            return angle_at_max

        def error_at_distance(angle_rad: float) -> float:
            """Target miss (in feet) for given launch angle."""
            props.barrel_elevation_rad = angle_rad
            t = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                return 9e9
            return (t.height >> Distance.Foot) - target_y_ft - abs((t.distance >> Distance.Foot) - target_x_ft)

        # 3. Establish search bracket for the zero angle.
        if lofted:
            low_angle, high_angle = angle_at_max_rad, math.radians(89.9)
        else:
            sight_height_adjust = 0.0
            if start_height_ft > 0:
                sight_height_adjust = math.atan2(start_height_ft, target_x_ft)
            low_angle, high_angle = look_angle_rad - sight_height_adjust, angle_at_max_rad

        f_low = error_at_distance(low_angle)
        f_high = error_at_distance(high_angle)

        if f_low * f_high >= 0:
            reason = f"No {'lofted' if lofted else 'low'} zero trajectory in elevation range "
            reason += f"({Angular.Radian(low_angle) >> Angular.Degree:.2f}, "
            reason += f"{Angular.Radian(high_angle) >> Angular.Degree:.2f} deg). "
            reason += f"Errors at bracket: f(low)={f_low:.2f}, f(high)={f_high:.2f}"
            raise ZeroFindingError(target_y_ft, 0, Angular.Radian(props.barrel_elevation_rad), reason=reason)

        # 4. Ridder's method implementation.  Absent bugs, this method is guaranteed to converge in
        #    log₂(range / accuracy) = log₂(π/2 / cZeroFindingAccuracy) iterations.
        for _ in range(self._config.cMaxIterations):
            mid_angle = (low_angle + high_angle) / 2.0
            f_mid = error_at_distance(mid_angle)

            # s is the updated point using the root of the linear function through (low_angle, f_low) and (high_angle, f_high)
            # and the quadratic function that passes through those points and (mid_angle, f_mid)
            s = math.sqrt(f_mid**2.0 - f_low * f_high)
            if s == 0.0:
                break  # Should not happen if f_low and f_high have opposite signs

            next_angle = mid_angle + (mid_angle - low_angle) * (math.copysign(1, f_low - f_high) * f_mid / s)
            if abs(next_angle - mid_angle) < self._config.cZeroFindingAccuracy:
                return Angular.Radian(next_angle)

            f_next = error_at_distance(next_angle)
            # Update the bracket
            if f_mid * f_next < 0:
                low_angle, f_low = mid_angle, f_mid
                high_angle, f_high = next_angle, f_next
            elif f_low * f_next < 0:
                high_angle, f_high = next_angle, f_next
            elif f_high * f_next < 0:
                low_angle, f_low = next_angle, f_next
            else:
                break  # If we are here, something is wrong, the root is not bracketed anymore

            if abs(high_angle - low_angle) < self._config.cZeroFindingAccuracy:
                return Angular.Radian((low_angle + high_angle) / 2)

        raise ZeroFindingError(target_y_ft, self._config.cMaxIterations, Angular.Radian((low_angle + high_angle) / 2),
                               reason="Ridder's method failed to converge."
        )

    def zero_angle(self, shot_info: Shot, distance: Distance) -> Angular:
        props = self._init_trajectory(shot_info)
        try:
            return self._zero_angle(props, distance)
        except ZeroFindingError as e:
            logger.warning(f"Failed to find zero angle using base iterative method: {e}")
            # Fallback to guaranteed method
            return self._find_zero_angle(props, distance)

    def _zero_angle(self, props: _ShotProps, distance: Distance) -> Angular:
        """
        Iterative algorithm to find barrel elevation needed for a particular zero

        Args:
            props (_ShotProps): Shot parameters
            distance (Distance): Sight distance to zero (i.e., along Shot.look_angle),
                                 a.k.a. slant range to target.

        Returns:
            Angular: Barrel elevation to hit height zero at zero distance along sight line
        """
        status, look_angle_rad, slant_range_ft, target_x_ft, target_y_ft, start_height_ft = (
            self._init_zero_calculation(props, distance)
        )
        if status is _ZeroCalcStatus.DONE:
            return Angular.Radian(look_angle_rad)

        assert target_x_ft is not None  # Make mypy happy
        assert target_y_ft is not None  # Make mypy happy
        assert slant_range_ft is not None  # Make mypy happy
        _cZeroFindingAccuracy = self._config.cZeroFindingAccuracy
        _cMaxIterations = self._config.cMaxIterations

        #region Ensure we can see drop at the target distance when launching along slant angle.
        required_drop_ft = target_x_ft / 2.0 - target_y_ft
        restore_cMaximumDrop = None
        if abs(self._config.cMaximumDrop) < required_drop_ft:
            restore_cMaximumDrop = self._config.cMaximumDrop
            self._config.cMaximumDrop = required_drop_ft
        restore_cMinimumAltitude = None
        if (self._config.cMinimumAltitude - props.alt0_ft) > required_drop_ft:
            restore_cMinimumAltitude = self._config.cMinimumAltitude
            self._config.cMinimumAltitude = props.alt0_ft - required_drop_ft
        #endregion

        iterations_count = 0
        range_error_ft = 9e9  # Absolute value of error from target distance along sight line
        prev_range_error_ft = 9e9
        prev_height_error_ft = 9e9
        damping_factor = 1.0  # Start with no damping
        damping_rate = 0.7  # Damping rate for correction
        last_correction = 0.0
        height_error_ft = _cZeroFindingAccuracy * 2  # Absolute value of error from sight line in feet at zero distance

        while iterations_count < _cMaxIterations:
            # Check height of trajectory at the zero distance (using current props.barrel_elevation)
            t = self._integrate(props, target_x_ft, target_x_ft, filter_flags=TrajFlag.NONE)[-1]
            if t.time == 0.0:
                logger.warning("Integrator returned initial point. Consider removing constraints.")
                break

            current_distance = t.distance >> Distance.Foot  # Horizontal distance
            if 2 * current_distance < target_x_ft and props.barrel_elevation_rad == 0.0 and look_angle_rad < 1.5:
                # Degenerate case: little distance and zero elevation; try with some elevation
                props.barrel_elevation_rad = 0.01
                continue

            height_diff_ft = t.slant_height >> Distance.Foot
            look_dist_ft = t.slant_distance >> Distance.Foot
            range_diff_ft = look_dist_ft - slant_range_ft
            range_error_ft = math.fabs(range_diff_ft)
            height_error_ft = math.fabs(height_diff_ft)
            trajectory_angle = t.angle >> Angular.Radian  # Flight angle at current distance
            sensitivity = math.tan(props.barrel_elevation_rad - look_angle_rad) * math.tan(trajectory_angle - look_angle_rad)
            if sensitivity < -0.5:
                denominator = look_dist_ft
            else:
                denominator = look_dist_ft * (1 + sensitivity)
            if abs(denominator) > 1e-9:
                correction = -height_diff_ft / denominator
            else:
                raise ZeroFindingError(height_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                      'Correction denominator is zero')

            if range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # We're still trying to reach zero_distance
                if range_error_ft > prev_range_error_ft - 1e-6:  # We're not getting closer to zero_distance
                    raise ZeroFindingError(range_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                          'Distance non-convergent')
            elif height_error_ft > math.fabs(prev_height_error_ft):  # Error is increasing, we are diverging
                damping_factor *= damping_rate  # Apply damping to prevent overcorrection
                if damping_factor < 0.3:
                    raise ZeroFindingError(height_error_ft, iterations_count, Angular.Radian(props.barrel_elevation_rad),
                          'Error non-convergent')
                logger.debug(f'Tightened damping to {damping_factor:.2f} after {iterations_count} iterations')
                props.barrel_elevation_rad -= last_correction  # Revert previous adjustment
                correction = last_correction
            elif damping_factor < 1.0:
                logger.debug('Resetting damping factor to 1.0')
                damping_factor = 1.0

            prev_range_error_ft = range_error_ft
            prev_height_error_ft = height_error_ft

            if height_error_ft > cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
                # Adjust barrel elevation to close height at zero distance
                applied_correction = correction * damping_factor
                props.barrel_elevation_rad += applied_correction
                last_correction = applied_correction
            else:  # Current barrel_elevation hit zero: success!
                break
            iterations_count += 1

        if restore_cMaximumDrop is not None:
            self._config.cMaximumDrop = restore_cMaximumDrop
        if restore_cMinimumAltitude is not None:
            self._config.cMinimumAltitude = restore_cMinimumAltitude

        if height_error_ft > _cZeroFindingAccuracy or range_error_ft > self.ALLOWED_ZERO_ERROR_FEET:
            # ZeroFindingError contains an instance of last barrel elevation; so caller can check how close zero is
            raise ZeroFindingError(height_error_ft, iterations_count, _new_rad(props.barrel_elevation_rad))
        return _new_rad(props.barrel_elevation_rad)

    def integrate(self, shot_info: Shot,
                        max_range: Distance,
                        dist_step: Optional[Distance] = None,
                        time_step: float = 0.0,
                        filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
                        dense_output: bool = False,
                        **kwargs) -> HitResult:
        """
        Integrates the trajectory for the given shot.

        Args:
            shot_info (Shot): The shot information.
            max_range (Distance): Maximum range of the trajectory (if float then treated as feet).
            dist_step (Optional[Distance]): Distance step for recording RANGE TrajectoryData rows.
            filter_flags (Union[TrajFlag, int], optional): Flags to filter trajectory data. Defaults to TrajFlag.RANGE.
            time_step (float, optional): Time step for recording trajectory data. Defaults to 0.0.
            dense_output (bool, optional): If True, HitResult will save BaseTrajData for interpolating TrajectoryData.

        Returns:
            HitResult: Object for describing the trajectory.
        """
        props = self._init_trajectory(shot_info)
        range_limit_ft = max_range >> Distance.Foot
        if dist_step is None:
            range_step_ft = range_limit_ft
        else:
            range_step_ft = dist_step >> Distance.Foot
        return self._integrate(props, range_limit_ft, range_step_ft, time_step, filter_flags, dense_output)

    @abstractmethod
    def _integrate(self, props: _ShotProps, range_limit_ft: float, range_step_ft: float,
                   time_step: float = 0.0, filter_flags: Union[TrajFlag, int] = TrajFlag.NONE,
                   dense_output: bool = False, **kwargs) -> HitResult:
        """
        Creates HitResult for the specified shot.

        Args:
            props (Shot): Information specific to the shot.
            range_limit_ft (float): Feet down-range to stop calculation.
            range_step_ft (float): Frequency (in feet down-range) to record TrajectoryData.
            filter_flags (Union[TrajFlag, int]): Bitfield for trajectory points of interest to record.
            time_step (float, optional): If > 0 then record TrajectoryData after this many seconds elapse
                since last record, as could happen when trajectory is nearly vertical and there is too little
                movement down-range to trigger a record based on range.  (Defaults to 0.0)
            dense_output (bool, optional): If True, HitResult will save BaseTrajData at each integration step,
                for interpolating TrajectoryData.

        Returns:
            HitResult: Object describing the trajectory.
        """
        raise NotImplementedError

    def _make_row(self,
                  props: _ShotProps,
                  time: float,
                  range_vector: Vector,
                  velocity_vector: Vector,
                  mach: float,
                  flag: Union[TrajFlag, int] = TrajFlag.NONE):

        spin_drift = props.spin_drift(time)
        velocity = velocity_vector.magnitude()
        windage = range_vector.z + spin_drift
        drop_adjustment = get_correction(range_vector.x, range_vector.y)
        windage_adjustment = get_correction(range_vector.x, windage)
        trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

        look_angle_cos = math.cos(props.look_angle_rad)
        look_angle_sin = math.sin(props.look_angle_rad)

        density_ratio, _ = props.get_density_and_mach_for_altitude(range_vector.y)
        drag = props.drag_by_mach(velocity / mach)

        return TrajectoryData(
            time=time,
            distance=_new_feet(range_vector.x),
            velocity=_new_fps(velocity),
            mach=velocity / mach,
            height=_new_feet(range_vector.y),
            slant_height=_new_feet(range_vector.y * look_angle_cos - range_vector.x * look_angle_sin),
            drop_adj=_new_rad(drop_adjustment - (props.look_angle_rad if range_vector.x else 0)),
            windage=_new_feet(windage),
            windage_adj=_new_rad(windage_adjustment),
            slant_distance=_new_feet(range_vector.x * look_angle_cos + range_vector.y * look_angle_sin),
            angle=_new_rad(trajectory_angle),
            density_ratio=density_ratio,
            drag=drag,
            energy=_new_ft_lb(calculate_energy(props.weight_grains, velocity)),
            ogw=_new_lb(calculate_ogw(props.weight_grains, velocity)),
            flag=flag
        )


# pylint: disable=too-many-positional-arguments
@deprecated(reason="Use BaseIntegrationEngine._make_row instead.")
def create_trajectory_row(time: float, range_vector: Vector, velocity_vector: Vector,
                          velocity: float, mach: float, spin_drift: float, look_angle: float,
                          density_ratio: float, drag: float, weight: float,
                          flag: Union[TrajFlag, int]) -> TrajectoryData:
    """
    Creates a TrajectoryData object representing a single row of trajectory data.

    Args:
        time (float): Time of flight in seconds.
        range_vector (Vector): Position vector in feet.
        velocity_vector (Vector): Velocity vector in fps.
        velocity (float): Velocity magnitude in fps.
        mach (float): Mach number.
        spin_drift (float): Spin drift in feet.
        look_angle (float): Slant angle in radians.
        density_ratio (float): Density ratio (rho / rho_0).
        drag (float): Drag value.
        weight (float): Weight value.
        flag (Union[TrajFlag, int]): Flag value.

    Returns:
        TrajectoryData: A TrajectoryData object representing the trajectory data.
    """
    warnings.warn("This method is deprecated", DeprecationWarning)

    windage = range_vector.z + spin_drift
    drop_adjustment = get_correction(range_vector.x, range_vector.y)
    windage_adjustment = get_correction(range_vector.x, windage)
    trajectory_angle = math.atan2(velocity_vector.y, velocity_vector.x)

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector.y),
        slant_height=_new_feet(range_vector.y * math.cos(look_angle) - range_vector.x * math.sin(look_angle)),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        slant_distance=_new_feet(range_vector.x * math.cos(look_angle) + range_vector.y * math.sin(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_ratio=density_ratio - 1,
        drag=drag,
        energy=_new_ft_lb(calculate_energy(weight, velocity)),
        ogw=_new_lb(calculate_ogw(weight, velocity)),
        flag=flag
    )


def _new_feet(v: float):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


def _new_fps(v: float):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


def _new_rad(v: float):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


def _new_ft_lb(v: float):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


def _new_lb(v: float):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d


def get_correction(distance: float, offset: float) -> float:
    """Calculates the sight adjustment in radians.

    Args:
        distance (float): The distance to the target in feet.
        offset (float): The offset from the target in feet.

    Returns:
        float: The sight adjustment in radians.
    """
    if distance != 0:
        return math.atan(offset / distance)
    return 0  # None


def calculate_energy(bullet_weight: float, velocity: float) -> float:
    """Calculates the kinetic energy of a projectile.

    Args:
        bullet_weight (float): The weight of the bullet in pounds.
        velocity (float): The velocity of the bullet in feet per second.

    Returns:
        float: The kinetic energy of the projectile in foot-pounds.
    """
    return bullet_weight * math.pow(velocity, 2) / 450400


def calculate_ogw(bullet_weight: float, velocity: float) -> float:
    """Calculates the optimal game weight for a projectile.

    Args:
        bullet_weight (float): The weight of the bullet in pounds.
        velocity (float): The velocity of the bullet in feet per second.

    Returns:
        float: The optimal game weight in pounds.
    """
    return math.pow(bullet_weight, 2) * math.pow(velocity, 3) * 1.5e-12


def calculate_curve(data_points: List[DragDataPoint]) -> List[CurvePoint]:
    """Piecewise quadratic interpolation of drag curve
    Args:
        data_points: List[{Mach, CD}] data_points in ascending Mach order
    Returns:
        List[CurvePoints] to interpolate drag coefficient
    """
    # rate, x1, x2, x3, y1, y2, y3, a, b, c
    # curve = []
    # curve_point
    # num_points, len_data_points, len_data_range

    rate = (data_points[1].CD - data_points[0].CD
            ) / (data_points[1].Mach - data_points[0].Mach)
    curve = [CurvePoint(0, rate, data_points[0].CD - data_points[0].Mach * rate)]
    len_data_points = int(len(data_points))
    len_data_range = len_data_points - 1

    for i in range(1, len_data_range):
        x1 = data_points[i - 1].Mach
        x2 = data_points[i].Mach
        x3 = data_points[i + 1].Mach
        y1 = data_points[i - 1].CD
        y2 = data_points[i].CD
        y3 = data_points[i + 1].CD
        a = ((y3 - y1) * (x2 - x1) - (y2 - y1) * (x3 - x1)) / (
            (x3 * x3 - x1 * x1) * (x2 - x1) - (x2 * x2 - x1 * x1) * (x3 - x1))
        b = (y2 - y1 - a * (x2 * x2 - x1 * x1)) / (x2 - x1)
        c = y1 - (a * x1 * x1 + b * x1)
        curve_point = CurvePoint(a, b, c)
        curve.append(curve_point)

    num_points = len_data_points
    rate = (data_points[num_points - 1].CD - data_points[num_points - 2].CD) / \
           (data_points[num_points - 1].Mach - data_points[num_points - 2].Mach)
    curve_point = CurvePoint(
        0, rate, data_points[num_points - 1].CD - data_points[num_points - 2].Mach * rate
    )
    curve.append(curve_point)
    return curve


# # use ._get_only_mach_data with ._calculate_by_curve_and_mach_list because it's faster
# def calculate_by_curve(data: List[DragDataPoint], curve: List[CurvePoint], mach: float) -> float:
#     """
#     Binary search for drag coefficient based on Mach number
#     :param data: data
#     :param curve: Output of calculate_curve(data)
#     :param mach: Mach value for which we're searching for CD
#     :return float: drag coefficient
#     """
#     num_points = int(len(curve))
#     mlo = 0
#     mhi = num_points - 2
#
#     while mhi - mlo > 1:
#         mid = int(math.floor(mhi + mlo) / 2.0)
#         if data[mid].Mach < mach:
#             mlo = mid
#         else:
#             mhi = mid
#
#     if data[mhi].Mach - mach > mach - data[mlo].Mach:
#         m = mlo
#     else:
#         m = mhi
#     curve_m = curve[m]
#     return curve_m.c + mach * (curve_m.b + curve_m.a * mach)


# Function to convert a list of DragDataPoint to an array of doubles containing only Mach values
def _get_only_mach_data(data: List[DragDataPoint]) -> List[float]:
    """
    Extracts Mach values from a list of DragDataPoint objects.

    Args:
        data (List[DragDataPoint]): A list of DragDataPoint objects.

    Returns:
        List[float]: A list containing only the Mach values from the input data.
    """
    return [dp.Mach for dp in data]


def _calculate_by_curve_and_mach_list(mach_list: List[float], curve: List[CurvePoint], mach: float) -> float:
    """
    Calculates a value based on a piecewise quadratic curve and a list of Mach values.

    This function performs a binary search on the `mach_list` to find the segment
    of the `curve` relevant to the input `mach` number and then interpolates
    the value using the quadratic coefficients of that curve segment.

    Args:
        mach_list (List[float]): A sorted list of Mach values corresponding to the `curve` points.
        curve (List[CurvePoint]): A list of CurvePoint objects, where each object
            contains quadratic coefficients (a, b, c) for a Mach number segment.
        mach (float): The Mach number at which to calculate the value.

    Returns:
        float: The calculated value based on the interpolated curve at the given Mach number.
    """
    num_points = len(curve)
    mlo = 0
    mhi = num_points - 2

    while mhi - mlo > 1:
        mid = (mhi + mlo) // 2
        if mach_list[mid] < mach:
            mlo = mid
        else:
            mhi = mid

    if mach_list[mhi] - mach > mach - mach_list[mlo]:
        m = mlo
    else:
        m = mhi
    curve_m = curve[m]
    return curve_m.c + mach * (curve_m.b + curve_m.a * mach)
