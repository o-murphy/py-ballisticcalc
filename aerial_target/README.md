# Aerial target shooting


## The chart below displays simple bullet and target trajectories crossing model
We have to calculate adjustment by x and y for the sight.
We uses simplified model, so it is assumed that 
* the target has constant velocity
* the target has constant flight direction angle relative to the sight line
* target doesn't change it's altitude
* We uses just 1 of [Aircraft principal axes](https://en.wikipedia.org/wiki/Aircraft_principal_axes) (Yaw)
* we have these parameters are known
  * target's velocity
  * target's flight direction
  * "look distance" target to  (along the sight line) or target distance along the ground
  * sight look angle
  * target's size (to accurate adjustment)

<img src="./assets/AerialTargetTrajectory.svg" alt="Aerial Target" style="width: 100%;">


## We can create a precalculated reticle for specific projectile and target
There the reticle example that was precalculated for the target size of ~3m, velocity - 50mps, look distance - 800m and the look angle - 20 degrees

<img src="./assets/AerialTargetReticle.svg" alt="Aerial Target" style="width: 100%;">