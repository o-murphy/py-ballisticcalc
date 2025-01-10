from py_ballisticcalc_exts._data_repr cimport _DataRepr
from py_ballisticcalc.unit import PreferredUnits


cdef class TrajectoryData(_DataRepr):

    def __cinit__(TrajectoryData self,
                    double time,
                    object distance,
                    object velocity,
                    double mach,
                    object height,
                    object target_drop,
                    object drop_adj,
                    object windage,
                    object windage_adj,
                    object look_distance,
                    object angle,
                    double density_factor,
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
        self.target_drop = target_drop
        self.drop_adj = drop_adj
        self.windage = windage
        self.windage_adj = windage_adj
        self.look_distance = look_distance
        self.angle = angle
        self.density_factor = density_factor
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
            _fmt(self.target_drop, PreferredUnits.drop),
            _fmt(self.drop_adj, PreferredUnits.adjustment),
            _fmt(self.windage, PreferredUnits.drop),
            _fmt(self.windage_adj, PreferredUnits.adjustment),
            _fmt(self.look_distance, PreferredUnits.distance),
            _fmt(self.angle, PreferredUnits.angular),
            f'{self.density_factor:.3e}',
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
            self.target_drop >> PreferredUnits.drop,
            self.drop_adj >> PreferredUnits.adjustment,
            self.windage >> PreferredUnits.drop,
            self.windage_adj >> PreferredUnits.adjustment,
            self.look_distance >> PreferredUnits.distance,
            self.angle >> PreferredUnits.angular,
            self.density_factor,
            self.drag,
            self.energy >> PreferredUnits.energy,
            self.ogw >> PreferredUnits.ogw,
            self.flag
        )
