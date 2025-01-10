cdef struct _ConfigStruct:
    bint use_powder_sensitivity
    double max_calc_step_size_feet
    double chart_resolution
    double cZeroFindingAccuracy
    double cMinimumVelocity
    double cMaximumDrop
    int cMaxIterations
    double cGravityConstant
    double cMinimumAltitude

cdef _ConfigStruct _early_bind_config(object config)
