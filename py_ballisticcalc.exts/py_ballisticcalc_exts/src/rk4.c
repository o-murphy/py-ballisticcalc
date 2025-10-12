#include <math.h>
#include "rk4.h"
#include "v3d.h"
#include "bclib.h"

/**
 * @brief Calculate the derivative of velocity with respect to time (acceleration).
 * * Assumes all necessary types (V3dT, ShotProps_t, Coriolis_t) and vector
 * functions (mulS, mag, sub, add, Coriolis_t_coriolis_acceleration_local) 
 * are declared and defined in relevant C headers.
 * * @param v_ptr Pointer to the relative velocity vector (velocity - wind).
 * @param gravity_vector_ptr Pointer to the gravity vector.
 * @param km_coeff Drag coefficient.
 * @param shot_props_ptr Pointer to shot properties (for Coriolis data).
 * @param ground_velocity_ptr Pointer to ground velocity vector (for Coriolis calculation).
 * @return V3dT The acceleration vector (dv/dt).
 */
V3dT _calculate_dvdt(const V3dT *v_ptr, const V3dT *gravity_vector_ptr, double km_coeff, 
                     const ShotProps_t *shot_props_ptr, const V3dT *ground_velocity_ptr)
{
    // Local variables for components and result
    V3dT drag_force_component;
    V3dT coriolis_acceleration;
    V3dT acceleration; // The return value

    // Bullet velocity changes due to drag and gravity
    // drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr))
    // Note: Assuming mulS and mag operate on V3dT and double types respectively
    drag_force_component = mulS(v_ptr, km_coeff * mag(v_ptr));
    
    // acceleration = sub(gravity_vector_ptr, &drag_force_component)
    // Note: Assuming sub takes two const V3dT* and returns V3dT
    acceleration = sub(gravity_vector_ptr, &drag_force_component);
    
    // Add Coriolis acceleration if available
    // Check the flat_fire_only flag within the Coriolis structure
    if (!shot_props_ptr->coriolis.flat_fire_only) {
        // Coriolis_t_coriolis_acceleration_local(
        //     &shot_props_ptr->coriolis, ground_velocity_ptr, &coriolis_acceleration
        // )
        // Note: Assuming this function calculates Coriolis acceleration and stores it in the third argument
        Coriolis_t_coriolis_acceleration_local(
            &shot_props_ptr->coriolis, ground_velocity_ptr, &coriolis_acceleration
        );
        
        // acceleration = add(&acceleration, &coriolis_acceleration)
        // Note: Assuming add takes two const V3dT* and returns V3dT
        acceleration = add(&acceleration, &coriolis_acceleration);
    }
    
    return acceleration;
}