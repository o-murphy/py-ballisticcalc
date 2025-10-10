#ifndef RK4_H
#define RK4_H

#include "v3d.h"
#include "bclib.h"

V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff, 
                     const ShotProps_t *shot_props_ptr, const V3dT *ground_velocity_ptr);

#endif // RK4_H