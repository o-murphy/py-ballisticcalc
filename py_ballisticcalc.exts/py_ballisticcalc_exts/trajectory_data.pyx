# noinspection PyUnresolvedReferences
from cython cimport final

from py_ballisticcalc.unit import PreferredUnits

# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.v3d cimport V3dT


@final
cdef class BaseTrajData:
    __slots__ = ('time', 'position', 'velocity', 'mach')

    def __cinit__(BaseTrajData self, double time, V3dT position, V3dT velocity, double mach):
        self.time = time
        self.position = position
        self.velocity = velocity
        self.mach = mach

@final
cdef class TrajectoryData:
    __slots__ = ('time', 'distance', 'velocity',
                 'mach', 'height', 'slant_height', 'drop_adj',
                 'windage', 'windage_adj', 'slant_distance',
                 'angle', 'density_ratio', 'drag', 'energy', 'ogw', 'flag')

    _fields = __slots__

    def __cinit__(TrajectoryData self,
                    double time,
                    object distance,
                    object velocity,
                    double mach,
                    object height,
                    object slant_height,
                    object drop_adj,
                    object windage,
                    object windage_adj,
                    object slant_distance,
                    object angle,
                    double density_ratio,
                    double drag,
                    object energy,
                    object ogw,
                    int flag,
                    ):
        self.time = time
        self.distance = distance
        self.velocity = velocity
        self.mach = mach
        self.height = height
        self.slant_height = slant_height
        self.drop_adj = drop_adj
        self.windage = windage
        self.windage_adj = windage_adj
        self.slant_distance = slant_distance
        self.angle = angle
        self.density_ratio = density_ratio
        self.drag = drag
        self.energy = energy
        self.ogw = ogw
        self.flag = flag

    def formatted(TrajectoryData self) -> tuple[str, ...]:
        """
        :return: matrix of formatted strings for each value of trajectory in default prefer_units
        """

        def _fmt(v, u) -> str:
            """simple formatter"""
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return (
            f'{self.time:.3f} s',
            _fmt(self.distance, PreferredUnits.distance),
            _fmt(self.velocity, PreferredUnits.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.height, PreferredUnits.drop),
            _fmt(self.slant_height, PreferredUnits.drop),
            _fmt(self.drop_adj, PreferredUnits.adjustment),
            _fmt(self.windage, PreferredUnits.drop),
            _fmt(self.windage_adj, PreferredUnits.adjustment),
            _fmt(self.slant_distance, PreferredUnits.distance),
            _fmt(self.angle, PreferredUnits.angular),
            f'{self.density_ratio:.3e}',
            f'{self.drag:.3f}',
            _fmt(self.energy, PreferredUnits.energy),
            _fmt(self.ogw, PreferredUnits.ogw),

            # TrajFlag.name(self.flag)
            f"{self.flag}"  # TODO: fix flag.name
        )

    def in_def_units(TrajectoryData self) -> tuple[float, ...]:
        """
        :return: matrix of floats of the trajectory in default prefer_units
        """
        return (
            self.time,
            self.distance >> PreferredUnits.distance,
            self.velocity >> PreferredUnits.velocity,
            self.mach,
            self.height >> PreferredUnits.drop,
            self.slant_height >> PreferredUnits.drop,
            self.drop_adj >> PreferredUnits.adjustment,
            self.windage >> PreferredUnits.drop,
            self.windage_adj >> PreferredUnits.adjustment,
            self.slant_distance >> PreferredUnits.distance,
            self.angle >> PreferredUnits.angular,
            self.density_ratio,
            self.drag,
            self.energy >> PreferredUnits.energy,
            self.ogw >> PreferredUnits.ogw,
            self.flag
        )
