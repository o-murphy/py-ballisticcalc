from cython cimport final


@final
cdef _ConfigStruct _early_bind_config(object config):
    return _ConfigStruct(
        config.use_powder_sensitivity,
        config.max_calc_step_size_feet,
        config.chart_resolution,
        config.cZeroFindingAccuracy,
        config.cMinimumVelocity,
        config.cMaximumDrop,
        config.cMaxIterations,
        config.cGravityConstant,
        config.cMinimumAltitude,
    )
