# Helper functions to create unit objects
cdef object _new_feet(double val)    
cdef object _new_fps(double val)    
cdef object _new_rad(double val)
cdef object _new_ft_lb(double val)
cdef object _new_lb(double val)
# Additional angular helper for MOA-based fields
cdef object _new_moa(double val)