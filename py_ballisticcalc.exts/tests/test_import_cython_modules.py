import importlib

import pytest

from py_ballisticcalc.interface import _EngineLoader

ENGINE_MODULES = {
    "euler_engine": ("CythonizedEulerIntegrationEngine", "cython+euler"),
    "rk4_engine": ("CythonizedRK4IntegrationEngine", "cython+rk4"),
    "velocity_verlet_engine": ("CythonizedVelocityVerletIntegrationEngine", "cython+verlet"),
    "cashkarp_engine": ("CythonizedCashKarpIntegrationEngine", "cython+rkck"),
    "dopri_engine": ("CythonizedDormandPrinceIntegrationEngine", "cython+dopri"),
    "tsitouras_engine": ("CythonizedTsitourasIntegrationEngine", "cython+tsitouras"),
}


def test_import_traj_data_extension():
    # Ensure compiled modules are loadable and expose expected symbols
    base = importlib.import_module("py_ballisticcalc_exts.traj_data")
    assert hasattr(base, "CythonizedBaseTrajSeq")


@pytest.mark.parametrize("module_name", ENGINE_MODULES)
def test_import_individual_extensions(module_name):
    class_name, _ = ENGINE_MODULES[module_name]
    module = importlib.import_module(f"py_ballisticcalc_exts.{module_name}")
    assert hasattr(module, class_name)


@pytest.mark.parametrize("module_name", ENGINE_MODULES)
def test_engine_entry_points_resolve(module_name):
    """Every extension engine is reachable via `cython+<method>` and `cython.<method>` entry points."""
    class_name, engine_id = ENGINE_MODULES[module_name]
    module = importlib.import_module(f"py_ballisticcalc_exts.{module_name}")
    expected = getattr(module, class_name)
    assert _EngineLoader.load(engine_id) is expected
    assert _EngineLoader.load(engine_id.replace("+", ".")) is expected
