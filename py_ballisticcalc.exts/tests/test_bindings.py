"""The committed _bcffi.pxd matches bclibc_ffi.h."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# Appended, not inserted: a source checkout must not shadow the installed py_ballisticcalc_exts (it has no compiled _native).
HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))


@pytest.fixture
def regen():
    """regenerate_bindings.py and the bclibc sources are in a source checkout, not in a built wheel."""
    return pytest.importorskip("regenerate_bindings", reason="not a source checkout: the bindings are not checked here")


def test_pxd_covers_every_function_of_the_header(regen):
    import re

    text = (regen._bclibc.bclibc_dir() / regen.HEADER_RELATIVE).read_text()
    header = set(re.findall(r"BCLIBC_API\s+[\w\s\*]+?\b(BCLIBCFFI_\w+)\s*\(", text))
    assert header, "no BCLIBCFFI_* functions found in the header"
    assert header <= regen.functions(regen.OUT.read_text())


@pytest.mark.skipif(importlib.util.find_spec("autopxd") is None and shutil.which("autopxd") is None, reason="needs autopxd2")
def test_pxd_is_up_to_date(regen):
    assert regen.main(["--check"]) == 0, "_bcffi.pxd is stale: run `python regenerate_bindings.py`"


def test_version_guard():
    import py_ballisticcalc_exts as pkg

    pkg.check_versions("3.1.2", "3.1.2")
    with pytest.raises(AssertionError, match="Versions must match"):
        pkg.check_versions("3.1.2", "3.1.3")
