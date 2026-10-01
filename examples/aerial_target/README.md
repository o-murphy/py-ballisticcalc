# Aerial target lead

Lead (preemption) for an aerial target crossing the line of sight, found by iterating the
bullet's time of flight until it converges. Run it with:

```shell
uv run examples/aerial_target/crossing_lead.py
```

## Model

* the target flies at a constant speed, level, perpendicular to the line of sight;
* the target's look angle, height and speed are known;
* zero, ammo and atmosphere come from the `Shot`.

The bullet needs time `t` to reach the target, and the target moves while it flies, so the bullet
has to be aimed at the point where the target will be. That point depends on `t`, and `t` depends
on that point, so the example iterates:

1. `t` = time of flight to the target's current position;
2. move the target forward by `speed * t`;
3. `t` = time of flight to the new position; repeat until `t` changes less than 1 ms.

`Calculator.aim()` returns the time of flight and the vertical hold for a position in one call. The
look angle and slant distance of the predicted point are recomputed from exact 3D geometry on each
iteration, since the bullet flies in a vertical plane towards it.

## Output

```
Time of flight:           1.060 s
Distance to meeting point:   709.09 m
Target travel in flight:  53.00 m
Horizontal lead:          107.57 mil (363.05 MOA)
Vertical hold:            -0.45 mil
Iterations:               2 (converged)

Check: bullet time 1.060 s vs target time 1.060 s, miss -0.00 cm from the sight line
```

The check fires the shot with the hold applied: the bullet arrives on the sight line at the time
the target does.

## Notes

* Crossing targets converge in 2-3 iterations. For a fast target moving away at long range plain
  iteration can be slow, and there may be no solution at all if the target is faster than the bullet.
* Wind and spin drift are not part of the lead.
* Compared with a loop built from `barrel_elevation_for_target()` plus `fire()`, `aim()` needs one
  call per iteration and gives the same time of flight; the iteration count is the same.
