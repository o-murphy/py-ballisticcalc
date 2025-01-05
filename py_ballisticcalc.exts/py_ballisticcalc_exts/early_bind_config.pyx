from cython cimport final
from py_ballisticcalc_exts.early_bind_config cimport _Config


@final
cdef _Config _early_bind_config(object config):
    return _Config(
        config.use_powder_sensitivity,
        config.max_calc_step_size_feet,
        config.cZeroFindingAccuracy,
        config.cMinimumVelocity,
        config.cMaximumDrop,
        config.cMaxIterations,
        config.cGravityConstant,
    )
