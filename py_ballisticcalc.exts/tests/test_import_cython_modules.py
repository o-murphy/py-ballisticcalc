import importlib


def test_import_individual_extensions():
    # Ensure compiled modules are loadable and expose expected symbols
    base = importlib.import_module("py_ballisticcalc_exts.base_traj_seq")
    assert hasattr(base, "CBaseTrajSeq")

    euler = importlib.import_module("py_ballisticcalc_exts.euler_engine")
    assert hasattr(euler, "CythonizedEulerIntegrationEngine")

    rk4 = importlib.import_module("py_ballisticcalc_exts.rk4_engine")
    assert hasattr(rk4, "CythonizedRK4IntegrationEngine")

    # tdata = importlib.import_module("py_ballisticcalc_exts.trajectory_data")
    # assert hasattr(tdata, "TrajectoryDataT")
