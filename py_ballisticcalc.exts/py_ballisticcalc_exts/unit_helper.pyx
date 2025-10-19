# cython: freethreading_compatible=True
from py_ballisticcalc.unit import Distance, Angular, Velocity, Weight, Energy, Unit


# Helper functions to create unit objects
cdef object _new_feet(double val):
    return Distance(val, Unit.Foot)
    
cdef object _new_fps(double val):
    return Velocity(val, Unit.FPS)
    
cdef object _new_rad(double val):
    return Angular(val, Unit.Radian)
    
cdef object _new_ft_lb(double val):
    return Energy(val, Unit.FootPound)
    
cdef object _new_lb(double val):
    return Weight(val, Unit.Pound)

# Additional angular helper for MOA-based fields
cdef object _new_moa(double val):
    return Angular(val, Unit.MOA)