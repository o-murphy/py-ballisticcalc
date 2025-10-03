"""
Lightweight Cython data types for trajectory rows and interpolation helpers.

This module mirrors a subset of the Python API in py_ballisticcalc.trajectory_data:
 - BaseTrajDataT: minimal row with time, position (V3dT), velocity (V3dT), mach.
 - TrajectoryDataT: Python-facing richer row used mainly for formatting or tests.
 - interpolate_3_pt / interpolate_2_pt: monotone PCHIP and linear helpers.

Primary producer/consumer is the Cython engines which operate on a dense C buffer
and convert to these types as needed for interpolation or presentation.
"""
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.trajectory_data cimport TrajFlag_t
# noinspection PyUnresolvedReferences
from py_ballisticcalc.vector import Vector
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.interp cimport _interpolate_3_pt
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.unit_helper cimport (
    _new_feet, 
    _new_fps, 
    _new_ft_lb, 
    _new_lb, 
    _new_rad, 
    _new_moa,
)


cdef object _v3d_to_vector(V3dT v):
    """Convert C V3dT -> Python Vector"""
    return Vector(<float>v.x, <float>v.y, <float>v.z)


@final
cdef class BaseTrajDataT:
    __slots__ = ('time', '_position', '_velocity', 'mach')

    def __cinit__(self, double time, V3dT position, V3dT velocity, double mach):
        self.time = time
        self._position = position
        self._velocity = velocity
        self.mach = mach

    # Hot-path C accessors (used by Cython code directly)
    cdef V3dT c_position(self):
        return self._position

    cdef V3dT c_velocity(self):
        return self._velocity

    # Python-facing properties return Vector, not dict
    @property
    def position(self):
        return _v3d_to_vector(self._position)

    @property
    def velocity(self):
        return _v3d_to_vector(self._velocity)

    # Back-compat names used elsewhere in ext code
    @property
    def position_vector(self):
        return _v3d_to_vector(self._position)

    @property
    def velocity_vector(self):
        return _v3d_to_vector(self._velocity)

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                   object p0, object p1, object p2):
        """
        Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) interpolation of a BaseTrajData point.

        Args:
            key_attribute (str): Can be 'time', 'mach', or a vector component like 'position.x' or 'velocity.z'.
            key_value (float): The value to interpolate.
            p0, p1, p2 (BaseTrajDataT): Any three points surrounding the point where key_attribute==value.

        Returns:
            BaseTrajData: The interpolated data point.

        Raises:
            AttributeError: If the key_attribute is not a member of BaseTrajData.
            ZeroDivisionError: If the interpolation fails due to zero division.
                               (This will result if two of the points are identical).
        """
        cdef:
            double x0, x1, x2
            double time, px, py, pz, vx, vy, vz, mach
            BaseTrajDataT _p0
            BaseTrajDataT _p1
            BaseTrajDataT _p2

        _p0 = <BaseTrajDataT> p0
        _p1 = <BaseTrajDataT> p1
        _p2 = <BaseTrajDataT> p2

        # Determine independent variable values from key_attribute
        if key_attribute == 'time':
            x0 = _p0.time
            x1 = _p1.time
            x2 = _p2.time
        elif key_attribute == 'mach':
            x0 = _p0.mach
            x1 = _p1.mach
            x2 = _p2.mach
        elif key_attribute == 'position.x':
            x0 = _p0._position.x
            x1 = _p1._position.x
            x2 = _p2._position.x
        elif key_attribute == 'position.y':
            x0 = _p0._position.y
            x1 = _p1._position.y
            x2 = _p2._position.y
        elif key_attribute == 'position.z':
            x0 = _p0._position.z
            x1 = _p1._position.z
            x2 = _p2._position.z
        elif key_attribute == 'velocity.x':
            x0 = _p0._velocity.x
            x1 = _p1._velocity.x
            x2 = _p2._velocity.x
        elif key_attribute == 'velocity.y':
            x0 = _p0._velocity.y
            x1 = _p1._velocity.y
            x2 = _p2._velocity.y
        elif key_attribute == 'velocity.z':
            x0 = _p0._velocity.z
            x1 = _p1._velocity.z
            x2 = _p2._velocity.z
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        # Guard against degenerate segments
        if x0 == x1 or x0 == x2 or x1 == x2:
            raise ZeroDivisionError("Duplicate x for interpolation")

        # Helper for scalar interpolation using PCHIP
        def _interp(double y0, double y1, double y2) -> double:
            return _interpolate_3_pt(key_value, x0, x1, x2, y0, y1, y2)

        # Interpolate all scalar fields
        time = key_value if key_attribute == 'time' else _interp(_p0.time, _p1.time, _p2.time)
        px = _interp(_p0._position.x, _p1._position.x, _p2._position.x)
        py = _interp(_p0._position.y, _p1._position.y, _p2._position.y)
        pz = _interp(_p0._position.z, _p1._position.z, _p2._position.z)
        vx = _interp(_p0._velocity.x, _p1._velocity.x, _p2._velocity.x)
        vy = _interp(_p0._velocity.y, _p1._velocity.y, _p2._velocity.y)
        vz = _interp(_p0._velocity.z, _p1._velocity.z, _p2._velocity.z)
        mach = key_value if key_attribute == 'mach' else _interp(_p0.mach, _p1.mach, _p2.mach)

        # Construct the resulting BaseTrajDataT
        return BaseTrajDataT(time, V3dT(px, py, pz), V3dT(vx, vy, vz), mach)


# Small Python factory for tests and convenience
def make_base_traj_data(double time, double px, double py, double pz,
                        double vx, double vy, double vz, double mach):
    return BaseTrajDataT(time, V3dT(px, py, pz), V3dT(vx, vy, vz), mach)

@final
cdef class TrajectoryDataT:
    __slots__ = ('time', 'distance', 'velocity',
                 'mach', 'height', 'slant_height', 'drop_angle',
                 'windage', 'windage_angle', 'slant_distance',
                 'angle', 'density_ratio', 'drag', 'energy', 'ogw', 'flag')
    _fields = __slots__

    def __cinit__(self,
                  double time,
                  object distance,
                  object velocity,
                  double mach,
                  object height,
                  object slant_height,
                  object drop_angle,
                  object windage,
                  object windage_angle,
                  object slant_distance,
                  object angle,
                  double density_ratio,
                  double drag,
                  object energy,
                  object ogw,
                  int flag):
        self.time = time
        self.distance = distance
        self.velocity = velocity
        self.mach = mach
        self.height = height
        self.slant_height = slant_height
        self.drop_angle = drop_angle
        self.windage = windage
        self.windage_angle = windage_angle
        self.slant_distance = slant_distance
        self.angle = angle
        self.density_ratio = density_ratio
        self.drag = drag
        self.energy = energy
        self.ogw = ogw
        self.flag = flag

    @staticmethod
    def interpolate(str key_attribute, double key_value,
                    TrajectoryDataT t0, TrajectoryDataT t1, TrajectoryDataT t2,
                    int flag):
        """
        Interpolate a TrajectoryDataT using PCHIP (monotone Hermite) for all fields.

        key_attribute: 'time', 'mach', or 'slant_height' (feet raw value).
        key_value: location at which to interpolate (raw units if dimensioned).
        """
        cdef:
            double x0, x1, x2
            double time, mach, density_ratio, drag
            object distance, velocity, height, slant_height, drop_angle
            object windage, windage_angle, slant_distance, angle, energy, ogw

        if key_attribute == 'time':
            x0, x1, x2 = t0.time, t1.time, t2.time
        elif key_attribute == 'mach':
            x0, x1, x2 = t0.mach, t1.mach, t2.mach
        elif key_attribute == 'slant_height':
            x0, x1, x2 = t0.slant_height._feet, t1.slant_height._feet, t2.slant_height._feet
        else:
            raise AttributeError(f"Cannot interpolate on '{key_attribute}'")

        # The key_value is the 'x' for the interpolation.
        # Arguments mapped to _interpolate_3_pt: (x, x0, x1, x2, y0, y1, y2)

        # Scalar fields (time, mach)
        time = key_value if key_attribute == 'time' else _interpolate_3_pt(key_value, x0, x1, x2, t0.time, t1.time, t2.time)
        mach = key_value if key_attribute == 'mach' else _interpolate_3_pt(key_value, x0, x1, x2, t0.mach, t1.mach, t2.mach)

        # Dimensioned fields (distance, velocity, height, etc.)
        distance = _new_feet(_interpolate_3_pt(key_value, x0, x1, x2, t0.distance._feet, t1.distance._feet, t2.distance._feet))
        velocity = _new_fps(_interpolate_3_pt(key_value, x0, x1, x2, t0.velocity._fps, t1.velocity._fps, t2.velocity._fps))
        height = _new_feet(_interpolate_3_pt(key_value, x0, x1, x2, t0.height._feet, t1.height._feet, t2.height._feet))
        slant_height = _new_feet(_interpolate_3_pt(key_value, x0, x1, x2, t0.slant_height._feet, t1.slant_height._feet, t2.slant_height._feet))
        drop_angle = _new_moa(_interpolate_3_pt(key_value, x0, x1, x2, t0.drop_angle._moa, t1.drop_angle._moa, t2.drop_angle._moa))
        windage = _new_feet(_interpolate_3_pt(key_value, x0, x1, x2, t0.windage._feet, t1.windage._feet, t2.windage._feet))
        windage_angle = _new_moa(_interpolate_3_pt(key_value, x0, x1, x2, t0.windage_angle._moa, t1.windage_angle._moa, t2.windage_angle._moa))
        slant_distance = _new_feet(_interpolate_3_pt(key_value, x0, x1, x2, t0.slant_distance._feet, t1.slant_distance._feet, t2.slant_distance._feet))
        angle = _new_rad(_interpolate_3_pt(key_value, x0, x1, x2, t0.angle._rad, t1.angle._rad, t2.angle._rad))

        # Other scalar fields (density_ratio, drag)
        density_ratio = _interpolate_3_pt(key_value, x0, x1, x2, t0.density_ratio, t1.density_ratio, t2.density_ratio)
        drag = _interpolate_3_pt(key_value, x0, x1, x2, t0.drag, t1.drag, t2.drag)

        # Dimensioned fields (energy, ogw)
        energy = _new_ft_lb(_interpolate_3_pt(key_value, x0, x1, x2, t0.energy._ft_lb, t1.energy._ft_lb, t2.energy._ft_lb))
        ogw = _new_lb(_interpolate_3_pt(key_value, x0, x1, x2, t0.ogw._lb, t1.ogw._lb, t2.ogw._lb))

        return TrajectoryDataT(time, distance, velocity, mach, height, slant_height,
                               drop_angle, windage, windage_angle, slant_distance,
                               angle, density_ratio, drag, energy, ogw,
                               <TrajFlag_t>flag)
