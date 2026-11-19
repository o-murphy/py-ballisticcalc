"""The ctypes engines raise what the Cython layer raises for the same kind of failure, and the size of the one struct they
read as bytes is the one the library was compiled with.

bclibc 2.2 gives every kind of its error a status code of its own (before, all but the solver kinds were
``BCLIBCFFI_ERR_GENERIC``); ``_raise`` maps them as Cython's ``except +`` did: a domain or argument error is a
``ValueError``, a value or index outside the data an ``IndexError``, the rest a ``RuntimeError``.
"""

import ctypes

import pytest

from py_ballisticcalc.exceptions import OutOfRangeError, SolverRuntimeError

native = pytest.importorskip("py_ballisticcalc_ctypes._native")


@pytest.fixture(scope="module", autouse=True)
def _library():
    try:
        native._load_library()
    except (ImportError, OSError) as exc:
        pytest.skip(f"the bclibc_ffi library is not built here: {exc}")


def _error(code: int, message: str = "boom", f=(0.0, 0.0, 0.0)):
    err = native._T.Error()
    err.code = code
    err.message = message.encode()
    err.f64_0, err.f64_1, err.f64_2 = f
    return err


@pytest.mark.parametrize(
    "name, exc",
    [
        ("BCLIBCFFI_ERR_DOMAIN", ValueError),
        ("BCLIBCFFI_ERR_INVALID_ARGUMENT", ValueError),
        ("BCLIBCFFI_ERR_OUT_OF_BOUNDS", IndexError),
        ("BCLIBCFFI_ERR_LOGIC", RuntimeError),
        ("BCLIBCFFI_ERR_RUNTIME", RuntimeError),
    ],
)
def test_error_kinds_raise_what_cython_raises(name, exc):
    code = getattr(native._G, name, None)
    if code is None:
        pytest.skip("the bindings are for a bclibc older than 2.2")
    with pytest.raises(exc, match="boom") as info:
        native._raise(_error(code))
    assert type(info.value) is exc


def test_solver_kinds_keep_their_types():
    G = native._G
    with pytest.raises(OutOfRangeError):
        native._raise(_error(G.BCLIBCFFI_ERR_OUT_OF_RANGE, f=(100.0, 50.0, 0.0)))
    with pytest.raises(SolverRuntimeError):
        native._raise(_error(G.BCLIBCFFI_ERR_SOLVER_RUNTIME))
    with pytest.raises(SolverRuntimeError):  # the C layer's own checks stay the generic one
        native._raise(_error(G.BCLIBCFFI_ERR_GENERIC))


def test_trajectory_data_size_is_the_one_the_library_reports():
    size = native._trajectory_data_size(native._G)
    if size is None:
        pytest.skip("the library reports no layout")
    assert size == native._TRAJ_FMT.size == ctypes.sizeof(native._T.TrajData)
    assert size in (124, 128)  # 124 on 32-bit x86 Linux, 128 elsewhere

