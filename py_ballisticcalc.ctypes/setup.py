#!/usr/bin/env python

"""setup.py of py_ballisticcalc.ctypes: builds the bclibc_ffi shared library into the wheel.

No Python extension is built: the library is plain C++ with a C ABI (``BCLIBCFFI_*``), loaded through ctypes, so it
does not depend on the interpreter. The wheel is therefore ``py3-none-<platform>``: one wheel per platform serves
every CPython, PyPy and GraalPy that platform has (the Cython wheels of ``py_ballisticcalc.exts`` serve CPython where
they are built; the main package's ``native`` extra picks between the two by environment markers, ``exts`` and ``ctypes`` are
an explicit choice).

The library is compiled with setuptools' compiler API from the sources the Cython extensions use (without the Python
binding) plus the C ABI wrapper, and copied to ``py_ballisticcalc_ctypes/_native_lib/`` before the package is
collected. The sources come from the repository's one bclibc submodule, or from a staged copy (see ``_bclibc.py``).

Environment variables:
    PY_BALLISTICCALC_NATIVE_LIB_DIR  directory with a prebuilt bclibc_ffi library; the compile step is skipped
    CC, CXX, CFLAGS, CXXFLAGS, LDFLAGS  toolchain; CXX compiles and links the C++ sources
    PY_BALLISTICCALC_BUILD_JOBS  number of sources compiled at once (default: the number of CPUs; 1 compiles one by one)
"""

import glob
import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _bclibc
from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

NATIVE_DIR = HERE / "py_ballisticcalc_ctypes" / "_native_lib"
BUILD_DIR = HERE / "build" / "native"

# the core sources the Cython extensions list, plus the C ABI wrapper
CORE_NAMES = (
    "base_types",
    "interp",
    "traj_data",
    "traj_filter",
    "engine",
    "euler",
    "rk4",
    "cash_karp",
    "dormand_prince",
    "tsitouras",
    "velocity_verlet",
)
# file patterns of the bclibc_ffi shared library per platform (lib<name>.so, lib<name>.dylib, <name>.dll)
LIB_PATTERNS = ("libbclibc_ffi*.so*", "libbclibc_ffi*.dylib", "bclibc_ffi*.dll")


def _target_kind() -> str:
    """The target (not the host): a cross-build sets _PYTHON_HOST_PLATFORM (cibuildwheel for macOS universal2)."""
    host = os.environ.get("_PYTHON_HOST_PLATFORM", "")
    # pyodide-build runs setup.py with the host interpreter and patches sysconfig to describe the target
    if "emscripten" in host or "emscripten" in sysconfig.get_platform():
        return "emscripten"
    if sys.platform == "darwin" or "macosx" in host or sysconfig.get_platform().startswith("macosx"):
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "unix"  # Linux, glibc and musl


def _msvc_arm() -> bool:
    """MSVC on ARM needs /fp:precise (the same condition as the Cython build)."""
    return sysconfig.get_platform().lower().startswith(("win-arm", "win_arm"))


def _has_static_libstdcxx(cxx: str) -> bool:
    """Whether the compiler finds libstdc++.a (glibc and musl toolchains alike); -print-file-name echoes the bare name if not."""
    try:
        found = subprocess.run(
            [cxx, "-print-file-name=libstdc++.a"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return os.path.isabs(found) and os.path.exists(found)


def _build_jobs() -> int:
    """How many sources are compiled at once: PY_BALLISTICCALC_BUILD_JOBS, else the number of CPUs (the Cython build uses
    all of them too)."""
    value = os.environ.get("PY_BALLISTICCALC_BUILD_JOBS", "")
    if value.isdigit() and int(value) > 0:
        return int(value)
    return os.cpu_count() or 1


def _compile_and_link(out_dir: Path) -> Path:
    """Compile bclibc and link the shared library into out_dir/lib; return that directory."""
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler

    source = _bclibc.bclibc_dir()
    src = source / "src"
    gen = _bclibc.write_version_header(source, out_dir / "gen")
    include_dirs = [str(source / "include"), str(src), str(gen)]
    core_sources = [str(src / f"{name}.cpp") for name in CORE_NAMES]
    ffi_source = str(src / "ffi" / "bclibc_ffi.cpp")
    version_script = src / "ffi" / "bclibc_ffi.version"

    kind = _target_kind()
    cc = new_compiler()
    customize_compiler(cc)
    obj_dir, lib_dir = out_dir / "obj", out_dir / "lib"

    if cc.compiler_type == "msvc":
        compile_args = ["/O2", "/W3", "/std:c++17", "/EHs-c-", "/GR-"]
        if _msvc_arm():
            compile_args.append("/fp:precise")
        link_args = ["/OPT:REF", "/OPT:ICF"]
        lib_name = "bclibc_ffi.dll"
        ffi_macros = [("BCLIBC_FFI_EXPORT", None), ("_WINDLL", None), ("NOMINMAX", None)]
    else:
        # the C++ driver compiles and links; CFLAGS/CXXFLAGS/LDFLAGS from the build environment are kept
        cxx = os.environ.get("CXX") or {"macos": "clang++", "emscripten": "em++"}.get(kind, "c++")
        env_compile = shlex.split(os.environ.get("CFLAGS", "")) + shlex.split(os.environ.get("CXXFLAGS", ""))
        env_link = shlex.split(os.environ.get("LDFLAGS", ""))
        if kind == "macos":  # cibuildwheel selects the architecture(s), universal2 included, with ARCHFLAGS
            archflags = shlex.split(os.environ.get("ARCHFLAGS", ""))
            env_compile, env_link = env_compile + archflags, env_link + archflags
        cc.compiler = [cxx]
        cc.compiler_cxx = [cxx, *env_compile]
        cc.compiler_so = [cxx, *env_compile]
        cc.linker_exe = [cxx, *env_link]
        cc.linker_so = [cxx, "-dynamiclib" if kind == "macos" else "-shared", *env_link]
        # C++ sources go through the *_cxx executables (setuptools 84): their defaults are Python's own, `-bundle ...` on macOS
        cc.compiler_so_cxx, cc.linker_so_cxx, cc.linker_exe_cxx = (
            list(cc.compiler_so),
            list(cc.linker_so),
            list(cc.linker_exe),
        )
        ffi_macros = []
        if kind == "emscripten":
            # a WebAssembly side module (Pyodide loads it with dlopen through ctypes). pyodide-build puts its own flags
            # (-O, -fPIC, -fwasm-exceptions, -sSUPPORT_LONGJMP=wasm) in CFLAGS/CXXFLAGS/LDFLAGS, which are kept above; there is
            # no version script or strip for wasm-ld, and the C++ runtime goes into the module
            lib_name = "libbclibc_ffi.so"
            compile_args = ["-std=c++17", "-Wall", "-fno-exceptions", "-fno-rtti", "-ffp-contract=off", "-fPIC"]
            link_args = ["-sSIDE_MODULE=1"]
        elif kind == "macos":
            lib_name = "libbclibc_ffi.dylib"
            compile_args = [
                "-O3", "-Wall", "-std=c++17", "-fno-exceptions", "-fno-rtti", "-stdlib=libc++", "-ffp-contract=off",
                "-fPIC", "-ffunction-sections", "-fdata-sections",
            ]  # fmt: skip
            link_args = ["-stdlib=libc++", "-Wl,-dead_strip", "-Wl,-x", "-install_name", f"@rpath/{lib_name}"]
        else:
            lib_name = "libbclibc_ffi.so"
            compile_args = [
                "-O3", "-Wall", "-std=c++17", "-fno-exceptions", "-fno-rtti", "-ffp-contract=off", "-fPIC",
                "-ffunction-sections", "-fdata-sections",
            ]  # fmt: skip
            # only the BCLIBCFFI_* symbols are exported; the C++ runtime goes into the library when the toolchain has it as
            # a static library (musl and glibc), so the wheel does not depend on the distribution's libstdc++
            link_args = [f"-Wl,--version-script={version_script}", "-Wl,--gc-sections", "-Wl,-strip-all"]
            if _has_static_libstdcxx(cxx):
                link_args += ["-static-libstdc++", "-static-libgcc"]

    # One source per call, each in a thread of its own: a call spawns the compiler and waits for it, so the compilers run side by
    # side. Every source has an object file of its own (its path under obj_dir), so nothing is written twice; the order of the
    # objects, and so the library, is that of the sources. The MSVC compiler prepares its environment on the first use: do it here.
    if hasattr(cc, "initialize") and not getattr(cc, "initialized", True):
        cc.initialize()

    def compile_one(job):
        source, macros = job
        return cc.compile(
            [source], output_dir=str(obj_dir), include_dirs=include_dirs, macros=macros, extra_postargs=compile_args
        )

    jobs = [(source, None) for source in core_sources] + [(ffi_source, ffi_macros)]
    with ThreadPoolExecutor(max_workers=min(_build_jobs(), len(jobs))) as pool:
        objects = [obj for objs in pool.map(compile_one, jobs) for obj in objs]
    cc.link_shared_object(objects, lib_name, output_dir=str(lib_dir), extra_postargs=link_args, target_lang="c++")
    return lib_dir


def _copy_library(from_dir: Path) -> None:
    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    found = []
    for pattern in LIB_PATTERNS:
        found += [Path(p) for p in glob.glob(str(from_dir / "**" / pattern), recursive=True)]
    if not found:
        raise RuntimeError(f"no bclibc_ffi library found under {from_dir}")
    for path in found:
        # copy the real file under the unversioned name the loader asks for (libbclibc_ffi.so, not .so.0.1.0)
        target = path.name
        if ".so." in target:
            target = target.split(".so.", 1)[0] + ".so"
        shutil.copyfile(path.resolve(), NATIVE_DIR / target)


def build_native_library() -> None:
    """Make the bclibc_ffi library available in py_ballisticcalc_ctypes/_native_lib/."""
    prebuilt = os.environ.get("PY_BALLISTICCALC_NATIVE_LIB_DIR")
    _copy_library(Path(prebuilt) if prebuilt else _compile_and_link(BUILD_DIR))


class build_py(_build_py):
    def run(self):
        build_native_library()
        super().run()


class sdist(_sdist):
    """Stages the bclibc sources into the package for the time of the sdist, so the archive builds anywhere."""

    def run(self):
        # a library left in the package by an earlier wheel build (it is package data) must not go into the archive: an sdist is
        # source, and a binary of another machine in it would be installed as if it were built here
        for stale in NATIVE_DIR.glob("*") if NATIVE_DIR.is_dir() else ():
            if stale.is_file():
                stale.unlink()  # the directory stays: it is a package directory of the build
        _bclibc.stage()
        try:
            super().run()
        finally:
            _bclibc.unstage()


class BinaryDistribution(Distribution):
    """The wheel is platform specific (it carries a library), though it has no extension module: its files go to the
    root of the wheel (platlib), not to the purelib data directory."""

    def has_ext_modules(self):
        return True


class bdist_wheel(_bdist_wheel):
    """No Python extension is built, so the wheel is py3-none-<platform>, not tagged by the building interpreter."""

    def get_tag(self):
        plat = (self.plat_name or sysconfig.get_platform()).replace("-", "_").replace(".", "_")
        return ("py3", "none", plat)


setup(distclass=BinaryDistribution, cmdclass={"build_py": build_py, "sdist": sdist, "bdist_wheel": bdist_wheel})
