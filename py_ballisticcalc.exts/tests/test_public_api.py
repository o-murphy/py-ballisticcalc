"""The public surface of py_ballisticcalc_exts: names, entry points and the removed modules."""

import importlib
from importlib.metadata import entry_points

import pytest

import py_ballisticcalc_exts
from py_ballisticcalc import Calculator

PUBLIC = (
    "CythonizedBaseTrajData",
    "CythonizedBaseTrajSeq",
    "CythonizedBaseIntegrationEngine",
    "CythonizedEulerIntegrationEngine",
    "CythonizedRK4IntegrationEngine",
    "CythonizedVelocityVerletIntegrationEngine",
    "CythonizedCashKarpIntegrationEngine",
    "CythonizedDormandPrinceIntegrationEngine",
    "CythonizedTsitourasIntegrationEngine",
)

# method id -> class name
METHODS = {
    "euler": "CythonizedEulerIntegrationEngine",
    "rk4": "CythonizedRK4IntegrationEngine",
    "verlet": "CythonizedVelocityVerletIntegrationEngine",
    "rkck": "CythonizedCashKarpIntegrationEngine",
    "dopri": "CythonizedDormandPrinceIntegrationEngine",
    "tsitouras": "CythonizedTsitourasIntegrationEngine",
}


def test_all_lists_the_public_names():
    assert set(py_ballisticcalc_exts.__all__) == set(PUBLIC)


@pytest.mark.parametrize("name", PUBLIC)
def test_public_name_importable(name):
    assert getattr(py_ballisticcalc_exts, name).__name__ == name


@pytest.mark.parametrize("method", METHODS)
def test_entry_points_resolve(method):
    expected = getattr(py_ballisticcalc_exts, METHODS[method])
    from py_ballisticcalc.interface import _EngineLoader

    assert _EngineLoader.load(f"cython+{method}") is expected
    assert _EngineLoader.load(f"cython.{method}") is expected


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("sep", ["+", "."])
def test_calculator_engine_class(method, sep):
    calc = Calculator(engine=f"cython{sep}{method}")
    assert isinstance(calc._engine_instance, py_ballisticcalc_exts.CythonizedBaseIntegrationEngine)
    assert type(calc._engine_instance).__name__ == METHODS[method]


def test_entry_point_group_targets():
    eps = entry_points(group="py_ballisticcalc.engines.cython")
    by_name = {ep.name: ep for ep in eps if ep.value.startswith("py_ballisticcalc_exts")}
    assert set(METHODS) <= set(by_name)
    for method, cls in METHODS.items():
        assert by_name[method].load() is getattr(py_ballisticcalc_exts, cls)


def test_cabi_group_is_gone():
    assert not list(entry_points(group="py_ballisticcalc.engines.cabi"))


@pytest.mark.parametrize("module", ["bind", "traj_data", "base_engine", "engines", "result"])
def test_removed_modules_not_importable(module):
    with pytest.raises(ImportError):
        importlib.import_module(f"py_ballisticcalc_exts.{module}")
