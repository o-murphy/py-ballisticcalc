# Aerial target lead

Lead (preemption) for an aerial target, found by iterating the bullet's time of flight until it
converges. Each iteration is a single `Calculator.aim()` call.

| File | What it is |
|---|---|
| `crossing_lead.py` | Minimal example: a target crossing the line of sight, lead printed to the console |
| `lead.py` | Simulation with matplotlib animation: several target trajectories, realistic tracking, sight FOV check. `--fov wide\|narrow` selects the sight field of view |
| `air-target-lead-fov-comparison.html` | Browser tool (js-ballistics, WASM) comparing two sight FOVs on the same crossing target; drop an `.a7p` profile on it |

```shell
uv run examples/aerial_target/crossing_lead.py
uv run examples/aerial_target/lead.py --target-type figure8 --fov narrow
```

The HTML page loads its libraries from a CDN, so serve it or open it directly in a browser with
network access. It needs `js-ballistics` 3.1 or newer, the first release with `Calculator.aim()`.

## Model

The bullet needs time `t` to reach the target, and the target moves while the bullet flies, so the
bullet has to be aimed at the point where the target will be. That point depends on `t`, and `t`
depends on that point, so the examples iterate:

1. `t` = time of flight to the target's current position;
2. move the target forward by `speed * t`;
3. `t` = time of flight to the new position; repeat until `t` changes less than 1 ms.

`crossing_lead.py` and the HTML page recompute the look angle and slant distance of the predicted
point from exact 3D geometry on every iteration, since the bullet flies in a vertical plane towards it.
`lead.py` passes the predicted position's look angle and slant distance to `aim()` the same way.

## `crossing_lead.py` output

```
Time of flight:           1.060 s
Distance to meeting point:   709.09 m
Target travel in flight:  53.00 m
Windage lead (reticle):   75.99 mil (256.47 MOA)
Azimuth lead:             107.57 mil
Drop hold at meeting pt:  2.39 mil
Iterations:               2 (converged)

Check: bullet time 1.060 s vs target time 1.060 s, miss -0.00 cm from the sight line
```

* *Windage lead* is the lateral travel seen from the meeting distance: the lead to hold on the sight
  reticle. *Azimuth lead* is the change of horizontal bearing, for azimuth/elevation mounts. They
  differ because a sight looking up at 45° sees a lateral shift smaller than the horizontal bearing change.
* The check fires the shot with the hold applied: the bullet arrives on the sight line at the time
  the target does.

## Notes

* Crossing targets converge in 2-3 iterations. For a fast target moving away at long range plain
  iteration can be slow, and there may be no solution at all if the target is faster than the bullet.
* Wind and spin drift are not part of the lead.
* Compared with a loop built from `barrel_elevation_for_target()` plus `fire()`, `aim()` needs one
  call per iteration and gives the same time of flight; the iteration count is the same.
