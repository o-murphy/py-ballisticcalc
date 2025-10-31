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
        "--engine", action="store", default="cythonized_rk4_engine", help="Specify the engine entry point name"
    )


@pytest.fixture(scope="class")
def loaded_engine_instance(request):
    engine_name = request.config.getoption("--engine", None)
    logger.info(f"Attempting to load engine: '{engine_name}'")

    try:
        engine = _EngineLoader.load(engine_name)
        print(f"Successfully loaded engine: {engine_name}")
        yield engine
    except Exception as e:
        pytest.exit(f"❌ Cannot start tests:\nFailed to load engine via _EngineLoader: {e}", returncode=1)
