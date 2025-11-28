# Cython conventions for py-ballisticcalc

This document records the Cython conventions adopted by the project.
It explains naming, error handling, Global Interpreter Lock (GIL) usage, and why these choices were made.

**Goals**

- Keep hot numerical work free of the Python GIL to maximize throughput.
- Provide Python-friendly, well-tested public APIs while preserving C/C++-level performance.

## GIL and `nogil`

- `nogil` helpers operate on C types only (primitives, C structs, raw pointers).
- All allocations performed in `nogil` must use C allocation (malloc/realloc) and return raw pointers; wrappers must free or wrap these pointers and raise proper Python exceptions if needed.
- Wrappers acquire GIL (are standard Python `def`) and construct Python objects from C results.

### Naming conventions

- Nogil helpers: suffix with `_nogil` or `_c_nogil` (we use `_interpolate_nogil`, `_append_nogil`).
- Try-style helpers: prefix with `_try_` for functions that return a status instead of raising (e.g. `_try_grow`).
- C/C++-level internal implementations: prefix with `_` and end with `_c` for functions that are "C/C++-level but may be called with the GIL" (e.g. `_append_c`).
- Public Python-facing methods: plain names (e.g. `append`, `interpolate_at`). These are `def` wrappers that call into `cdef`/`nogil` helpers.

### Error handling conventions

- `nogil` functions must not raise Python exceptions.
    - Use status codes (`int` or `bint`) and/or out-parameters to signal errors.
    - Example convention:
        - return 1 for success, 0 for failure; or
        - return 0 for success and negative error codes for specific failures.
- Python wrappers map status codes to Python exceptions (MemoryError, IndexError, ValueError, etc.).
- For allocators: provide `_ensure_capacity_try_nogil` that attempts realloc and returns success/failure without raising.

#### Exception annotation on nogil

- `.pxd` declarations for `nogil` functions or module-level functions should have explicit exception values. Cython warns that cimporters calling them without the GIL will require exception checks. If you intend for these functions to never raise Cython exceptions, you must declare them `noexcept`.

- Declaring them `noexcept` in the `.pxd` is the clearest way to indicate that a function will not propagate a Python exception.

- Specify an explicit exception value (e.g., `except NULL` or `except False`) where appropriate to avoid implicit exception checks if the function *can* indicate an error via its return value but does not raise a Python exception.

### .pxd and API exposure

- Declare `nogil` helpers, `cdef` functions, and `enums` in `.pxd` so they can be `cimport`ed by other Cython modules and used without Python overhead.
- Keep public Python wrappers (`def` methods) unexposed in `.pxd` by default. This encourages other Cython modules to call the `nogil` helper or `cdef` function directly instead of the Python wrapper.

#### Examples (patterns used)

- Interpolation (nogil core):
```python
cdef enum InterpKey: KEY_TIME, KEY_MACH, KEY_POS_X, ...
cdef BCLIBC_BaseTrajData* _interpolate_nogil(self, Py_ssize_t idx, InterpKey key_kind, double key_value) nogil

def interpolate_at(self, idx, key_attribute, key_value):
    # map key_attribute -> InterpKey
    with nogil:
        outp = self._interpolate_nogil(idx, key_kind, key_value)
    if outp is NULL:
        raise IndexError(...)
    result = CythonizedBaseTrajData(...)
    free(outp)
    return result
```

- Append (nogil fast-path + GIL grow):
```python
cdef bint _ensure_capacity_try_nogil(self, size_t min_capacity) nogil
cdef void _append_nogil(self, double time, ...) nogil

def append(self, time, ...):
    if not self._ensure_capacity_try_nogil(self._length + 1):
        # acquire GIL and call a grow function that may raise MemoryError
        self._ensure_capacity(self._length + 1)
    with nogil:
        self._append_nogil(time, ...)
```

### Practical notes

- `nogil` is only legal on functions that return C types or are annotated to not return Python objects.
- `with nogil:` blocks are used to call `nogil` helpers but the block cannot contain Python operations.
- When calling `malloc` in `nogil`, check the return value and `return NULL` on failure; do not raise Python exceptions inside `nogil`.
- In `nogil` code you can’t safely pass Python `cdef class` instances (they carry Python object headers and refcounts).

### Why this approach

- Minimizes GIL contention in tight numeric loops (integration engine and interpolation hot paths).
- Provides explicit, auditable separation of concerns (numeric work vs Python object handling).
- Gives tests and Python scripts simple interfaces while guaranteeing C/C++-level callers can use the fastest path.

## When to use `cpdef` vs `cdef` + `def` wrapper

- Use `cpdef` when:
    - The function is small and its behavior is identical whether called from Python or Cython.
    - You want a convenient, single definition that exposes both a fast C/C++-level entrypoint (for cimports) and a Python-callable function without writing a separate wrapper.
    - The function does not need special GIL management (no `nogil` core) and does not require bespoke exception mapping or complex Python-object construction.

- Prefer `cdef` + `def` wrapper when:
    - The hot-path work must run without the GIL (you need a `nogil` numeric core) or you need tight control over GIL acquire/release.
    - The function must return Python objects, raise Python exceptions, or perform Python-side housekeeping that should only live in the wrapper.
    - You need different behavior or different APIs for C callers vs Python callers (for example, C callers get raw pointers or status codes while Python callers get high-level objects and exceptions).
    - You want to avoid exposing a C/C++-level symbol to other modules inadvertently; `cdef` keeps the C API internal unless you explicitly declare it in a `.pxd`.

- Rationale

    `cpdef` is convenient and can be slightly faster for Python callers than a handwritten wrapper, but it bundles the Python-callable surface with the C implementation. That reduces flexibility and clarity: you get less explicit control of error translation, GIL handling, and resource lifetimes. For numeric hot paths and any code that must be `nogil`-safe, the `cdef` + `def` wrapper pattern is safer and clearer: the `cdef` core can be `nogil` and return C-only results/statuses while the `def` wrapper handles Python conversions and raises exceptions. This separation also helps prevent `cimport` cycles that can occur when `cpdef` methods from different modules call each other.

- Practical decision rule

    - If the function is purely a utility that both Cython modules and Python code will call and it neither needs `nogil` nor special exception mapping, `cpdef` is acceptable.
    - If the function is a hot numeric path, manipulates raw buffers/pointers, or needs careful error/status handling, implement a `cdef` nogil core and a `def` wrapper.

## C helpers

For any object in the hot path we create a C helper as follows:

1. Define a C/C++ types in `<some>.h/.hpp`, and list helper functions.  Example: `typedef struct ... BCLIBC_ShotProps` and `void BCLIBC_ShotProps_release(BCLIBC_ShotProps*shot_props_ptr)`
2. Implement any helper functions in `<some>.c/.cpp`.  These are typically to allocate and free memory.  Example: `BCLIBC_ShotProps_release()`.
3. Copy the `struct` as a `ctypedef` to `<some>.pxd`.  (This could be automated at compile time but is not at present.)
4. Put any conversion logic in `<some>.pyx`.  E.g., `cdef BCLIBC_Wind BCLIBC_Wind_from_py(object w):`

## Memory / leak detection strategy

We intentionally avoid embedding ad‑hoc global allocation counters inside the C core. Instead we rely
on layered techniques that scale better and keep production code minimal:

1. Deterministic construction/destruction loops (stress tests)
     - Repeatedly build and discard objects (e.g. drag curves, Mach lists, trajectory buffers) inside
         a pytest `@pytest.mark.stress` test. If RSS or object counts trend upward unbounded, investigate.
     - Keep the loop count high enough to amplify tiny leaks (hundreds–thousands) but bounded to keep CI fast.

2. Python heap/object monitoring (snapshots and trend checks)
     - Use `tracemalloc` inside a `@pytest.mark.stress` test to obtain a before/after snapshot across a high‑iteration drag evaluation or trajectory generation loop. Rather than asserting on raw absolute bytes (which can be noisy across allocators/platforms), we:
         1. Warm up (one integration) to populate caches/one‑time allocations.
         2. Start tracing, run N evaluation batches, force a `gc.collect()` between batches.
         3. Compare snapshots; fail only if net retained size exceeds a conservative threshold (kept local to the test as a constant so CI adjustments are simple).
     - Example idiom (trimmed):

        ```python
        import tracemalloc, gc
        tracemalloc.start()
        snap0 = tracemalloc.take_snapshot()
        for _ in range(BATCHES):
            run_drag_evals()
            gc.collect()
        snap1 = tracemalloc.take_snapshot()
        total_diff = sum(stat.size_diff for stat in snap1.compare_to(snap0, 'filename'))
        assert total_diff < LEAK_THRESHOLD_BYTES
        ```
     - We deliberately scope thresholds and batch counts inside the test (no env vars) to keep behavior deterministic and self‑documenting.

3. Platform tools (C allocations / native leaks)
     - Linux / WSL: `valgrind --leak-check=full python -m pytest tests -k stress` (slow but definitive)
     - AddressSanitizer (ASan): build extension with `CFLAGS="-O2 -g -fsanitize=address"` &
         `LDFLAGS="-fsanitize=address"` then run stress tests; reports use‑after‑free, double free, leaks.
     - macOS: `leaks` tool or Instruments (Allocations & Leaks templates).
     - Windows: Visual Studio Diagnostics, Dr. Memory, or Application Verifier + Debug CRT (set
         `_CrtSetDbgFlag(_CRTDBG_ALLOC_MEM_DF | _CRTDBG_LEAK_CHECK_DF)` inside a small harness).

4. Cython boundary audits
     - Enable Cython annotation (`CYTHON_ANNOTATE=1`) to inspect Python interaction hot spots.
     - Review that every `malloc` / `realloc` / `calloc` has a matching `free` in normal and error paths.
     - Ensure early returns after partial allocation free prior blocks.

5. Monitoring RSS (coarse indicator)
     - Use `psutil.Process().memory_info().rss` sampled before/after a stress loop. Accept small (<1–2%) drift
         due to allocator fragmentation but investigate linear growth.

### When to escalate
Use lightweight Python tooling first (stress + tracemalloc). Escalate to Valgrind / ASan only when a leak
pattern is confirmed or a corruption (crash, inconsistent data) is suspected.

## Debugging tips
- Reproduce failure with a focused pytest call (pass the test path) to avoid long runs.
- Add temporary debug prints in Python-side filter rather than in C to avoid recompiles.
- To iterate on Cython code rapidly: keep `pyx` edits small and incremental, run `py -m pip install -e ./py_ballisticcalc.exts` to rebuild the extension in-place.

### Troubleshooting native issues
- Crash inside C function: rebuild with `-O0 -g` and run under `gdb --args python -m pytest ...`.
- Sporadic NaNs in trajectory: print intermediate Mach, density, drag values for the iteration where the
    NaN first appears; confirm inputs within expected ranges; check for division by zero in slope formulas.

## Contribution checklist
- Keep parity: match Python reference implementations for event semantics unless you intentionally change behavior (document that change).
- Add tests for any public behavioral change.
- Keep Cython numeric code focused on inner loops and return dense samples for Python post-processing.

### Tests
* `pytest ./py_ballisticcalc.exts/tests` for cython-specific tests.
* We use `@pytest.mark.stress` to keep stress tests separate.  To run those: `pytest ./py_ballisticcalc.exts/tests -m stress`
