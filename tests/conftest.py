import os
import sys
from pathlib import Path


def _ensure_dev_env_for_tests():
    os.environ.setdefault("PYTHONNOUSERSITE", "1")

    root = Path(__file__).resolve().parents[1]
    venv = root / ".venv"
    in_venv = getattr(sys, "base_prefix", sys.prefix) != sys.prefix

    if venv.exists():
        try:
            active = Path(sys.prefix).resolve()
            if not (in_venv and str(active).startswith(str(venv.resolve()))):
                print(
                    (
                        "Warning: Tests are not running under repo .venv.\n"
                        f"Active: {active}\nExpected under: {venv}\n"
                        "Activate with .\\.venv\\Scripts\\activate or run via .venv\\Scripts\\python.exe -m pytest"
                    ),
                    file=sys.stderr,
                )
        except Exception:
            pass


_ensure_dev_env_for_tests()

import logging

import pytest

from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc.logger import logger

logger.setLevel(logging.DEBUG)


def pytest_addoption(parser):
    parser.addoption(
        "--engine",
        action="store",
        default=None,  # be sure to use the default value from _EngeneLoader
        help="Specify the engine entry point name",
    )


@pytest.fixture(scope="class")
def loaded_engine_instance(request):
    engine_name = request.config.getoption("--engine", None)
    logger.info(f"Attempting to load engine: '{engine_name}'")
    try:
        engine = _EngineLoader.load(engine_name)
        try:
            # probe:
            engine({})
        except Exception as e:
            raise Exception(f"Engine {engine} loaded but probe failed: {e}")
        print(f"Successfully loaded engine: {engine}")
        yield engine
    except Exception as e:
        pytest.exit(f"❌ Cannot start tests:\nFailed to load engine via _EngineLoader: {e}", returncode=1)
