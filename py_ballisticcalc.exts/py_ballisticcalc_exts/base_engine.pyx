# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from libc.stdlib cimport malloc, free
# noinspection PyUnresolvedReferences
from libc.math cimport fabs, sin, cos, tan, atan, atan2
# noinspection PyUnresolvedReferences
# from py_ballisticcalc_exts.trajectory_data cimport BaseTrajData, TrajectoryData
from py_ballisticcalc_exts.trajectory_data cimport TrajectoryData
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.tflag cimport TFlag
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.cy_bindings cimport (
    Config_t,
    Wind_t,
    Atmosphere_t,
    ShotData_t,
    config_bind,
    update_density_factor_and_mach_for_altitude,
    cy_table_to_mach,
    cy_calculate_curve,
    cy_calculate_by_curve_and_mach_list,
    cy_spin_drift,
    cy_drag_by_mach,
    cy_update_stability_coefficient,
    free_trajectory,
    wind_to_c_vector,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.helpers cimport (
    getCorrection,
    calculateEnergy,
    calculateOgw,
)

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport (
    V3dT, add, sub, mag, mulS
)

from py_ballisticcalc.unit import Angular, Unit, Velocity, Distance, Energy, Weight
from py_ballisticcalc.exceptions import ZeroFindingError, RangeError
from py_ballisticcalc.constants import cMaxWindDistanceFeet
from py_ballisticcalc.engines.base_engine import create_base_engine_config


__all__ = (
    'CythonizedBaseIntegrationEngine',
    '_WindSock',
    'create_trajectory_row',
)

# cdef _TrajectoryDataFilter createTrajectoryDataFilter(TFlag filter_flags, double range_step,
#                   const V3dT *initial_position, const V3dT *initial_velocity,
#                   double time_step = 0.0):
#     return _TrajectoryDataFilter(
#         filter_flags, TFlag.TRAJ_NONE, TFlag.TRAJ_NONE,
#         time_step, range_step,
#         0.0, 0.0, 0.0, 0.0,
#         initial_position[0],  # same as *initial_position
#         initial_velocity[0],  # same as *initial_velocity
#         0.0, 0.0,
#     )

cdef _TrajectoryDataFilter createTrajectoryDataFilter(TFlag filter_flags, double range_step,
                  const V3dT *initial_position, const V3dT *initial_velocity,
                  double time_step = 0.0):
    cdef _TrajectoryDataFilter tdf

    tdf.filter = filter_flags
    tdf.current_flag = TFlag.TRAJ_NONE
    tdf.seen_zero = TFlag.TRAJ_NONE
    tdf.time_step = time_step
    tdf.range_step = range_step
    tdf.time_of_last_record = 0.0
    tdf.next_record_distance = 0.0
    tdf.previous_mach = 0.0
    tdf.previous_time = 0.0
    tdf.previous_position = initial_position[0]
    tdf.previous_velocity = initial_velocity[0]
    tdf.previous_v_mach = 0.0
    tdf.look_angle = 0.0

    tdf.data = <BaseTrajData *>malloc(sizeof(BaseTrajData))
    if tdf.data == NULL:
        raise MemoryError("Failed to allocate BaseTrajData for _TrajectoryDataFilter")

    # *** ВИПРАВЛЕНО: Ініціалізація BaseTrajData за допомогою початкових значень ***
    tdf.data.time = 0.0 # Можливо, тут теж має бути initial_time, якщо це має сенс?
                        # Або 0.0, якщо це час початку відстеження.
    tdf.data.position = initial_position[0] # Копіюємо початкову позицію
    tdf.data.velocity = initial_velocity[0] # Копіюємо початкову швидкість
    tdf.data.mach = 0.0 # Можливо, тут теж initial_mach?

    return tdf

cdef void destroyTrajectoryDataFilter(_TrajectoryDataFilter * tdf):
    """
    Звільняє пам'ять, виділену для поля 'data' у _TrajectoryDataFilter.
    """
    if tdf != NULL and tdf.data != NULL:
        free(tdf.data)
        tdf.data = NULL

cdef void setup_seen_zero(_TrajectoryDataFilter * tdf, double height, double barrel_elevation, double look_angle):
    if height >= 0:
        tdf.seen_zero = <TFlag>(tdf.seen_zero | TFlag.TRAJ_ZERO_UP)
    elif height < 0 and barrel_elevation < look_angle:
        tdf.seen_zero = <TFlag>(tdf.seen_zero | TFlag.TRAJ_ZERO_DOWN)
    tdf.look_angle = look_angle

cdef BaseTrajData *should_record(_TrajectoryDataFilter * tdf, const V3dT *position, const V3dT *velocity, double mach, double time):
    cdef double ratio
    cdef V3dT temp_position, temp_velocity
    cdef V3dT temp_sub_position, temp_mul_position
    cdef V3dT temp_sub_velocity, temp_mul_velocity

    tdf.current_flag = <TFlag>TFlag.TRAJ_NONE
    if (tdf.range_step > 0) and (position.x >= tdf.next_record_distance):
        while tdf.next_record_distance + tdf.range_step < position.x:
            tdf.next_record_distance += tdf.range_step
        if position.x > tdf.previous_position.x:
            ratio = (tdf.next_record_distance - tdf.previous_position.x) / (position.x - tdf.previous_position.x)
            temp_sub_position = sub(position, &tdf.previous_position)
            temp_mul_position = mulS(&temp_sub_position, ratio)
            temp_position = add(&tdf.previous_position, &temp_mul_position)
            temp_sub_velocity = sub(velocity, &tdf.previous_velocity)
            temp_mul_velocity = mulS(&temp_sub_velocity, ratio)
            temp_velocity = add(&tdf.previous_velocity, &temp_mul_velocity)

            # Заповнюємо поля tdf.data інтерпольованими значеннями
            tdf.data.time = tdf.previous_time + (time - tdf.previous_time) * ratio
            tdf.data.position = temp_position
            tdf.data.velocity = temp_velocity
            tdf.data.mach = tdf.previous_mach + (mach - tdf.previous_mach) * ratio

            tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_RANGE)
            tdf.next_record_distance += tdf.range_step
            tdf.time_of_last_record = time
    elif tdf.time_step > 0:
        _check_next_time(tdf, time)

    _check_zero_crossing(tdf, position)
    _check_mach_crossing(tdf, mag(velocity), mach)

    tdf.previous_time = time
    tdf.previous_position = position[0]
    tdf.previous_velocity = velocity[0]
    tdf.previous_mach = mach

    # Повертаємо вказівник на tdf.data, якщо потрібен запис, інакше NULL
    if (tdf.current_flag & tdf.filter) != 0:
        if not (tdf.current_flag & TFlag.TRAJ_RANGE):
            tdf.data.time = time
            tdf.data.position = position[0]
            tdf.data.velocity = velocity[0]
            tdf.data.mach = mach
        return tdf.data
    else:
        return NULL


# cdef BaseTrajData should_record(_TrajectoryDataFilter * tdf, const V3dT *position, const V3dT *velocity, double mach, double time):
#     cdef BaseTrajData data = None
#     cdef double ratio
#     cdef V3dT temp_position, temp_velocity
#     cdef V3dT temp_sub_position, temp_sub_velocity
#     cdef V3dT temp_mul_position, temp_mul_velocity
#
#     # #region DEBUG
#     # if get_debug():
#     #     logger.debug(
#     #         f"should_record called with time={time}, "
#     #         f"position=({position.x}, {position.y}, {position.z}), "
#     #         f"velocity=({velocity.x}, {velocity.y}, {velocity.z}), mach={mach}"
#     #     )
#     # #endregion
#     tdf.current_flag = <TFlag>TFlag.TRAJ_NONE
#     if (tdf.range_step > 0) and (position.x >= tdf.next_record_distance):
#         while tdf.next_record_distance + tdf.range_step < position.x:
#             # Handle case where we have stepped past more than one record distance
#             tdf.next_record_distance += tdf.range_step
#         if position.x > tdf.previous_position.x:
#             # Interpolate to get BaseTrajData at the record distance
#             ratio = (tdf.next_record_distance - tdf.previous_position.x) / (position.x - tdf.previous_position.x)
#             temp_sub_position = sub(position, &tdf.previous_position)
#             temp_mul_position = mulS(&temp_sub_position, ratio)
#             temp_position = add(&tdf.previous_position, &temp_mul_position)
#             temp_sub_velocity = sub(velocity, &tdf.previous_velocity)
#             temp_mul_velocity = mulS(&temp_sub_velocity, ratio)
#             temp_velocity = add(&tdf.previous_velocity, &temp_mul_velocity)
#             data = BaseTrajData(
#                 time=tdf.previous_time + (time - tdf.previous_time) * ratio,
#                 position=temp_position,
#                 velocity=temp_velocity,
#                 mach=tdf.previous_mach + (mach - tdf.previous_mach) * ratio
#             )
#         tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_RANGE)
#         tdf.next_record_distance += tdf.range_step
#         tdf.time_of_last_record = time
#     elif tdf.time_step > 0:
#         _check_next_time(tdf, time)
#     _check_zero_crossing(tdf, position)
#     _check_mach_crossing(tdf, mag(velocity), mach)
#     if (tdf.current_flag & tdf.filter) != 0 and data is None:
#         data = BaseTrajData(time=time, position=position[0],
#                             velocity=velocity[0], mach=mach)
#     tdf.previous_time = time
#     tdf.previous_position = position[0]  # same as *position
#     tdf.previous_velocity = velocity[0]  # same as *velocity
#     tdf.previous_mach = mach
#     #region DEBUG
#     # if get_debug():
#     #     if data is not None:
#     #         logger.debug(
#     #             f"should_record returning BaseTrajData time={data.time}, "
#     #             f"position=({data.position.x}, {data.position.y}, {data.position.z}), "
#     #             f"velocity=({data.velocity.x}, {data.velocity.y}, {data.velocity.z}), mach={data.mach}"
#     #         )
#     #     else:
#     #         logger.debug("should_record returning None")
#     # #endregion
#     return data

cdef void _check_next_time(_TrajectoryDataFilter * tdf, double time):
        if time > tdf.time_of_last_record + tdf.time_step:
            tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_RANGE)
            tdf.time_of_last_record = time

cdef void _check_mach_crossing(_TrajectoryDataFilter * tdf, double velocity, double mach):
    cdef double current_v_mach = velocity / mach
    if tdf.previous_v_mach > 1 >= current_v_mach:
        tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_MACH)
    tdf.previous_v_mach = current_v_mach

cdef void _check_zero_crossing(_TrajectoryDataFilter * tdf, const V3dT *range_vector):
    if range_vector.x > 0:
        # Zero reference line is the sight line defined by look_angle
        reference_height = range_vector.x * tan(tdf.look_angle)
        # If we haven't seen ZERO_UP, we look for that first
        if not (tdf.seen_zero & TFlag.TRAJ_ZERO_UP):
            if range_vector.y >= reference_height:
                tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_ZERO_UP)
                tdf.seen_zero = <TFlag>(tdf.seen_zero | TFlag.TRAJ_ZERO_UP)
        # We've crossed above sight line; now look for crossing back through it
        elif not (tdf.seen_zero & TFlag.TRAJ_ZERO_DOWN):
            if range_vector.y < reference_height:
                tdf.current_flag = <TFlag>(tdf.current_flag | TFlag.TRAJ_ZERO_DOWN)
                tdf.seen_zero = <TFlag>(tdf.seen_zero | TFlag.TRAJ_ZERO_DOWN)


@final
cdef class _WindSock:

    def __cinit__(_WindSock self, object winds):
        self.winds = [
            Wind_t(
                w.velocity.get_in(Unit.FPS),
                w.direction_from.get_in(Unit.Radian),
                w.until_distance.get_in(Unit.Foot),
                w.MAX_DISTANCE_FEET
            ) for w in winds
        ]
        self.current = 0
        self.next_range = cMaxWindDistanceFeet
        self._last_vector_cache = V3dT(0.0, 0.0, 0.0)
        self._length = len(self.winds)

        # Initialize cache correctly
        self.update_cache()

    cdef V3dT current_vector(_WindSock self):
        return self._last_vector_cache

    cdef void update_cache(_WindSock self):
        cdef Wind_t cur_wind
        if self.current < self._length:
            cur_wind = self.winds[self.current]
            self._last_vector_cache = wind_to_c_vector(&cur_wind)
            self.next_range = cur_wind.until_distance
        else:
            self._last_vector_cache = V3dT(0.0, 0.0, 0.0)
            self.next_range = cMaxWindDistanceFeet

    cdef V3dT vector_for_range(_WindSock self, double next_range):
        if next_range >= self.next_range:
        # if next_range + 1e-6 >= self.next_range:
            self.current += 1
            if self.current >= self._length:
                self._last_vector_cache = V3dT(0.0, 0.0, 0.0)
                self.next_range = cMaxWindDistanceFeet
            else:
                self.update_cache()  # This will trigger cache updates.
        return self._last_vector_cache


cdef class CythonizedBaseIntegrationEngine:

    def __cinit__(CythonizedBaseIntegrationEngine self, object _config):
        self._config = create_base_engine_config(_config)
        self.gravity_vector = V3dT(.0, self._config.cGravityConstant, .0)

    # def __dealloc__(TrajectoryCalc self):
    #     free_trajectory(&self._shot_s)

    cdef double get_calc_step(self, double step = 0):
        cdef double preferred_step = self._config_s.cMaxCalcStepSizeFeet
        # cdef double defined_max = 0.5  # const will be better optimized with cython
        if step == 0:
            return preferred_step / 2.0
        return min(step, preferred_step) / 2.0

    @property
    def table_data(self) -> list[object]:
        return self._table_data

    def zero_angle(self, object shot_info, object distance) -> Angular:
        return self._zero_angle(shot_info, distance)

    def trajectory(self, object shot_info, object max_range, object dist_step,
                   bint extra_data = False, double time_step = 0.0) -> object:
        # hack to reload config if it was changed explicit on existed instance
        self._config_s = config_bind(self._config)
        self.gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)

        cdef:
            TFlag filter_flags = TFlag.TRAJ_RANGE

        if extra_data:
            filter_flags = TFlag.TRAJ_ALL

        self._init_trajectory(shot_info)
        cdef list[object] t = self._integrate(max_range._feet, dist_step._feet, filter_flags, time_step)
        self._free_trajectory()
        return t

    cdef void _free_trajectory(self):
        free_trajectory(&self._shot_s)

    cdef void _init_trajectory(self, object shot_info):
        self._table_data = shot_info.ammo.dm.drag_table
        self._shot_s = ShotData_t(
            bc=shot_info.ammo.dm.BC,
            curve=cy_calculate_curve(self._table_data),
            mach_list=cy_table_to_mach(self._table_data),
            look_angle=shot_info.look_angle._rad,
            twist=shot_info.weapon.twist._inch,
            length=shot_info.ammo.dm.length._inch,
            diameter=shot_info.ammo.dm.diameter._inch,
            weight=shot_info.ammo.dm.weight._grain,
            barrel_elevation=shot_info.barrel_elevation._rad,
            barrel_azimuth=shot_info.barrel_azimuth._rad,
            sight_height=shot_info.weapon.sight_height._feet,
            cant_cosine=cos(shot_info.cant_angle._rad),
            cant_sine=sin(shot_info.cant_angle._rad),
            alt0=shot_info.atmo.altitude._feet,
            calc_step=self.get_calc_step(),
            # calc_step=cy_get_calc_step(self._config_s),
            diameter=shot_info.ammo.dm.diameter._inch,
            stability_coefficient=0.0,
            atmo=Atmosphere_t(
                _t0=shot_info.atmo._t0,
                _a0=shot_info.atmo._a0,
                _p0=shot_info.atmo._p0,
                _mach=shot_info.atmo._mach,
                density_ratio=shot_info.atmo.density_ratio,
                cLowestTempC=shot_info.atmo.cLowestTempC,
            )
        )
        self._shot_s.muzzle_velocity = shot_info.ammo.get_velocity_for_temp(shot_info.atmo.powder_temp)._fps
        cy_update_stability_coefficient(&self._shot_s)

        self.ws = _WindSock(shot_info.winds)

    cdef object _zero_angle(CythonizedBaseIntegrationEngine self, object shot_info, object distance):
        # hack to reload config if it was changed explicit on existed instance
        self._config_s = config_bind(self._config)
        self.gravity_vector = V3dT(.0, self._config_s.cGravityConstant, .0)

        cdef:
            # early bindings
            double _cZeroFindingAccuracy = self._config_s.cZeroFindingAccuracy
            double _cMaxIterations = self._config_s.cMaxIterations

        cdef:
            double zero_distance = cos(shot_info.look_angle._rad) * distance._feet
            double height_at_zero = sin(shot_info.look_angle._rad) * distance._feet
            double maximum_range = zero_distance
            int iterations_count = 0
            double zero_finding_error = _cZeroFindingAccuracy * 2

            object t
            double height, last_distance_foot, proportion

        self._init_trajectory(shot_info)
        self._shot_s.barrel_azimuth = 0.0
        self._shot_s.barrel_elevation = atan(height_at_zero / zero_distance)
        self._shot_s.twist = 0
        maximum_range -= 1.5 * self._shot_s.calc_step

        # x = horizontal distance down range, y = drop, z = windage
        while zero_finding_error > _cZeroFindingAccuracy and iterations_count < _cMaxIterations:
            try:
                t = self._integrate(maximum_range, zero_distance, TFlag.TRAJ_NONE)[0]
                height = t.height._feet  # use internal shortcut instead of (t.height >> Distance.Foot)
            except RangeError as e:
                last_distance_foot = e.last_distance._feet
                proportion = (last_distance_foot) / zero_distance
                height = (e.incomplete_trajectory[-1].height._feet) / proportion

            zero_finding_error = fabs(height - height_at_zero)

            if zero_finding_error > _cZeroFindingAccuracy:
                self._shot_s.barrel_elevation -= (height - height_at_zero) / zero_distance
            else:  # last barrel_elevation hit zero!
                break
            iterations_count += 1
        self._free_trajectory()
        if zero_finding_error > _cZeroFindingAccuracy:
            raise ZeroFindingError(zero_finding_error, iterations_count, Angular.Radian(self._shot_s.barrel_elevation))
        return Angular.Radian(self._shot_s.barrel_elevation)


    cdef list[object] _integrate(CythonizedBaseIntegrationEngine self,
                                 double maximum_range, double record_step, TFlag filter_flags, double time_step = 0.0):
        raise NotImplementedError


cdef object create_trajectory_row(double time, const V3dT *range_vector, const V3dT *velocity_vector,
                           double velocity, double mach, double spin_drift, double look_angle,
                           double density_factor, double drag, double weight, TFlag flag):

    cdef:
        double windage = range_vector.z + spin_drift
        double drop_adjustment = getCorrection(range_vector.x, range_vector.y)
        double windage_adjustment = getCorrection(range_vector.x, windage)
        double trajectory_angle = atan2(velocity_vector.y, velocity_vector.x);

    return TrajectoryData(
        time=time,
        distance=_new_feet(range_vector.x),
        velocity=_new_fps(velocity),
        mach=velocity / mach,
        height=_new_feet(range_vector.y),
        target_drop=_new_feet(
            (range_vector.y - range_vector.x * tan(look_angle)) * cos(look_angle)
        ),
        drop_adj=_new_rad(drop_adjustment - (look_angle if range_vector.x else 0)),
        windage=_new_feet(windage),
        windage_adj=_new_rad(windage_adjustment),
        look_distance=_new_feet(range_vector.x / cos(look_angle)),
        angle=_new_rad(trajectory_angle),
        density_factor=density_factor - 1,
        drag=drag,
        energy=_new_ft_lb(calculateEnergy(weight, velocity)),
        ogw=_new_lb(calculateOgw(weight, velocity)),
        flag=flag
    )


cdef object _new_feet(double v):
    d = object.__new__(Distance)
    d._value = v * 12
    d._defined_units = Unit.Foot
    return d


cdef object _new_fps(double v):
    d = object.__new__(Velocity)
    d._value = v / 3.2808399
    d._defined_units = Unit.FPS
    return d


cdef object _new_rad(double v):
    d = object.__new__(Angular)
    d._value = v
    d._defined_units = Unit.Radian
    return d


cdef object _new_ft_lb(double v):
    d = object.__new__(Energy)
    d._value = v
    d._defined_units = Unit.FootPound
    return d


cdef object _new_lb(double v):
    d = object.__new__(Weight)
    d._value = v / 0.000142857143
    d._defined_units = Unit.Pound
    return d