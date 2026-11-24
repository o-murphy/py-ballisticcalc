"""Every engine has the same API: the engine protocol plus the extras of the cythonized engines.

``EngineProtocol`` (``py_ballisticcalc.generics.engine``) requires ``integrate``, ``zero_angle``, ``zero_point``,
``find_zero_angle`` and ``find_zero_point``.  The cythonized engines also have ``find_apex``, ``find_max_range`` and
``integrate_raw_at``, and every in-tree Python engine (``BaseIntegrationEngine`` and the SciPy engines) has them too.  The extras
are not part of the protocol yet (they join it, with the tiny binding, at the repin stage): this test is what will guard that
extension, so the day they move into ``EngineProtocol`` nothing may be missing from an engine.

Run per engine, e.g. ``pytest tests/test_engine_api_conformance.py --engine=python+rk4``.
"""

import inspect

import pytest

from py_ballisticcalc.generics.engine import EngineProtocol

pytestmark = pytest.mark.engine

#: Leading parameter names, as the cythonized engines (``base_engine.pyi``) and the protocol spell them.
REQUIRED = {
    "integrate": ("shot_info", "max_range", "dist_step", "time_step", "filter_flags", "dense_output"),
    "zero_angle": ("shot_info", "distance"),
    "zero_point": ("shot_info", "distance"),
    "find_zero_angle": ("shot_info", "distance", "lofted"),
    "find_zero_point": ("shot_info", "distance", "lofted"),
}
EXTRAS = {
    "find_apex": ("shot_info",),
    "find_max_range": ("shot_info", "angle_bracket_deg"),
    "integrate_raw_at": ("shot_info", "key_attribute", "target_value"),
}
TINY_REASON = "tiny binding gets them at the repin stage"


def _is_tiny(engine) -> bool:
    return engine.__module__.startswith("tiny_bclibc")


def _skip_tiny_extras(engine, name: str) -> None:
    if name in EXTRAS and _is_tiny(engine):
        pytest.skip(TINY_REASON)


def _parameters(method, name: str) -> tuple[str, ...]:
    try:
        signature = inspect.signature(method)
    except ValueError:  # a compiled method without an embedded signature (the cythonized engines)
        pytest.skip(f"{name}: no introspectable signature (compiled method)")
    return tuple(p for p in signature.parameters)


def test_engine_is_an_engine_protocol(loaded_engine_instance):
    """The runtime-checkable protocol (the five required methods)."""
    assert isinstance(loaded_engine_instance({}), EngineProtocol)


@pytest.mark.parametrize("name", [*REQUIRED, *EXTRAS])
def test_engine_has_the_method(loaded_engine_instance, name):
    _skip_tiny_extras(loaded_engine_instance, name)
    assert callable(getattr(loaded_engine_instance({}), name, None)), (
        f"{loaded_engine_instance.__name__}.{name} is missing"
    )


@pytest.mark.parametrize("name", [*REQUIRED, *EXTRAS])
def test_engine_method_signature_is_compatible(loaded_engine_instance, name):
    """The shared leading parameters have the names of the cythonized engines (callers may pass them by keyword)."""
    _skip_tiny_extras(loaded_engine_instance, name)
    expected = {**REQUIRED, **EXTRAS}[name]
    parameters = _parameters(getattr(loaded_engine_instance({}), name), name)
    assert parameters[: len(expected)] == expected, f"{name}{parameters} does not start with {expected}"
