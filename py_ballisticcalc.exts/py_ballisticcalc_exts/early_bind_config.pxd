cdef struct _Config:
    bint use_powder_sensitivity
    double max_calc_step_size_feet
    double cZeroFindingAccuracy
    double cMinimumVelocity
    double cMaximumDrop
    double cMaxIterations
    double cGravityConstant

cdef _Config _early_bind_config(object config)
