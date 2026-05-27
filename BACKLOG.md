# Backlog

## Done (this session)

### CI: eliminate redundant builds after abi3 migration
- `pypi-publish.yml`: extracted `build-sdist` job — pure Python wheel + exts sdist built once on `ubuntu-latest` instead of 6× across OS matrix
- `pypi-publish.yml`: `publish` job now `needs: [build-sdist, build]`
- `pytest-cythonized-*.yml`: restored `3.13t` to full test matrix — ABI differs from `3.14t`

### CI: cp313t wheels restored
- `enable = ["cpython-freethreading"]` required in cibuildwheel 3.4 to include `cp313t-*`; the flag itself is deprecated but `cp313t` is silently skipped without it
- Will revisit when cibuildwheel provides a proper replacement

### fix: `CythonizedBaseTrajData.__str__`
- `__iter__` yields scalar values; `__str__` was unpacking each as `(name, value)` → `ValueError` on any call

---

## Pending

### bclibc: centralize conversion logic via `BCLIBC_Shot` (separate PR)

**Context:**  
bclibc is used from three wrappers: Python/Cython, Dart FFI, WASM C++.  
Each wrapper independently reimplements the same stateless physics/conversion math to assemble `BCLIBC_ShotProps` from user-facing inputs.  
The domain model (`Calculator`, `Weapon`, `Ammo`, `DragModel`, `Wind`, `Shot`) intentionally stays per-language — it serves as a shared interface between pure Python and Cythonized engines, and each ecosystem has its own idioms.  
The problem is not the domain model — it is the conversion logic below it.

**What is duplicated in every wrapper (~300–500 LOC each):**

| Logic | Complexity | Current state |
|-------|-----------|---------------|
| `cant_angle_rad` → `cant_cosine / cant_sine` | low | Cython: `bind.pyx`; FFI: internally; Dart/WASM: own impl |
| `latitude, azimuth, vel` → `BCLIBC_Coriolis` (10 pre-computed fields) | high | Python `Coriolis.create()` + `bind.pyx`; Dart/WASM: own impl |
| `temp_f, alt_ft, pressure_hpa` → `BCLIBC_Atmosphere` (`density_ratio`, `mach`) | medium | Python class + `BCLIBC_Atmosphere_fromPyObject`; Dart/WASM: own impl |
| drag table `[(Mach, CD)]` → `BCLIBC_Curve + BCLIBC_MachList` (PCHIP) | medium | `py_bind.cpp` (not in bclibc); FFI: internally; Dart/WASM: own impl |
| Miller stability coefficient | high | exists as `update_stability_coefficient()` but wrappers may not use it |
| Litz spin drift | low | exists as `spin_drift()` |

**`BCLIBC_ShotProps` vs `BCShotProps` divergence:**  
The C++ struct and the FFI struct have drifted: `cant_cosine/cant_sine` vs `cant_angle_rad`, `BCIntegrationMethod method` exists only in FFI, `stability_coefficient` missing from FFI. Changes to one do not automatically reflect in the other.

**Proposed solution — `BCLIBC_Shot` as assembly point:**

```
Python domain   →  bind.pyx fills BCLIBC_Shot  →  BCLIBC_Shot::to_shot_props()  →  engine
Dart domain     →  Dart FFI fills BCLIBC_Shot   →  BCLIBC_Shot::to_shot_props()  →  engine
WASM domain     →  JS fills BCLIBC_Shot         →  BCLIBC_Shot::to_shot_props()  →  engine
```

All physics conversion lives in `to_shot_props()` — once, in C++.  
Domain model stays per-language. No breaking change for Python users.

**Step 1 — factory functions (non-breaking, low effort):**

```cpp
// replaces 10 pre-computed fields
static BCLIBC_Coriolis BCLIBC_Coriolis::from_lat_az(
    double lat_rad, double az_rad, double vel_fps);

// replaces manual barometric formula in every wrapper
static BCLIBC_Atmosphere BCLIBC_Atmosphere::from_icao(
    double temp_f, double alt_ft, double pressure_hpa);

// replaces cant_cosine/cant_sine split
// (or add cant_angle_rad constructor to BCLIBC_ShotProps)

// replaces per-wrapper PCHIP building
static std::pair<BCLIBC_Curve, BCLIBC_MachList>
    build_drag_curve(const double* mach, const double* cd, size_t n);
```

**Step 2 — `BCLIBC_Shot` struct:**

```cpp
struct BCLIBC_Shot {
    // weapon
    double sight_height_ft;
    double twist_inch;

    // ammo
    double bc;
    double weight_grain, diameter_inch, length_inch;
    double muzzle_velocity_fps;

    // atmosphere (user-facing units, not pre-computed)
    double temp_f, altitude_ft, pressure_hpa;

    // drag table (raw Mach/CD pairs, not PCHIP)
    const double* mach;
    const double* cd;
    int drag_table_count;

    // winds
    const BCLIBC_Wind* winds;
    int wind_count;

    // aiming (raw angles, not pre-computed sin/cos)
    double look_angle_rad;
    double barrel_elevation_rad;
    double barrel_azimuth_rad;
    double cant_angle_rad;   // bclibc computes cos/sin internally
    double latitude_rad;     // bclibc computes sin_lat/cos_lat internally
    double azimuth_rad;      // bclibc computes sin_az/cos_az internally

    BCLIBC_Config config;

    // assembles BCLIBC_ShotProps — all conversion in one place
    BCLIBC_ShotProps to_shot_props() const;
};
```

After migration `bind.pyx` becomes a thin field mapper instead of a physics library.

**Step 3 — `BCLIBC_Calculator` (optional, later):**  
Wrapper around `BCLIBC_BaseEngine` exposing `integrate`, `find_zero_angle`, `find_apex`, `find_max_range` — the same interface every wrapper currently rebuilds independently.

**Notes:**
- Requires understanding how Dart FFI and WASM wrappers are structured before implementation
- Step 1 is safe to do first without Step 2
- Step 3 is independent of Steps 1–2
