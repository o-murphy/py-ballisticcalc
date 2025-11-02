import logging
import faulthandler

import pytest

from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc.logger import logger

logger.setLevel(logging.DEBUG)

# Enable faulthandler early to get rich tracebacks on segfaults
faulthandler.enable()


def pytest_addoption(parser):
    parser.addoption(
        "--engine",
        action="store",
        default=None,
        help="Specify the engine entry point name",
    )


@pytest.fixture(scope="class")
def loaded_engine_instance(request):
    engine_name = request.config.getoption("--engine", None)
    # be sure to use the default cythonized engine
    if engine_name is None:
        engine_name = "cythonized_rk4_engine"
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
