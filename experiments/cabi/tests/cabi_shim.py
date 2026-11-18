"""A pytest plugin (-p cabi_shim): the tests of py_ballisticcalc.exts import CythonizedBaseTrajSeq, CythonizedBaseTrajData and
make_base_traj_data from py_ballisticcalc_exts.traj_data / ._test_helpers. Here those names are the ones of bcy (Cython over
the C ABI), so the unmodified tests of the C++ layer run against it.

    PYTHONPATH=cython/build:experiments/cabi/tests pytest -p cabi_shim <tests of py_ballisticcalc.exts/tests>
"""
import sys
import types

import bcy

pkg = types.ModuleType("py_ballisticcalc_exts")
pkg.__path__ = []
traj_data = types.ModuleType("py_ballisticcalc_exts.traj_data")
traj_data.CythonizedBaseTrajSeq = bcy.CythonizedBaseTrajSeq
traj_data.CythonizedBaseTrajData = bcy.CythonizedBaseTrajData
helpers = types.ModuleType("py_ballisticcalc_exts._test_helpers")
helpers.make_base_traj_data = bcy.make_base_traj_data
pkg.traj_data, pkg._test_helpers = traj_data, helpers
sys.modules.update({
    "py_ballisticcalc_exts": pkg,
    "py_ballisticcalc_exts.traj_data": traj_data,
    "py_ballisticcalc_exts._test_helpers": helpers,
})
