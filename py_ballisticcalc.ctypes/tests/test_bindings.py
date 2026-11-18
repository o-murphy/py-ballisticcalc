"""The committed ctypes bindings match bclibc_ffi.h."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import regenerate_bindings as regen  # noqa: E402


def test_bindings_cover_every_function_of_the_header():
    header = regen.functions(regen._header().read_text())
    module = regen.functions(regen.OUT.read_text())
    assert header, "no BCLIBCFFI_* functions found in the header"
    assert header <= module, f"missing from _native_gen.py: {sorted(header - module)}"


@pytest.mark.skipif(
    importlib.util.find_spec("ctypesgen") is None or shutil.which("cpp") is None, reason="needs ctypesgen and cpp"
)
def test_bindings_are_up_to_date():
    assert regen.main(["--check"]) == 0, "_native_gen.py is stale: run `python regenerate_bindings.py`"


def test_version_guard():
    import py_ballisticcalc_ctypes as pkg

    pkg.check_versions("3.1.2", "3.1.2")
    with pytest.raises(AssertionError, match="Versions must match"):
        pkg.check_versions("3.1.2", "3.1.3")
