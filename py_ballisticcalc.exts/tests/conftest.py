import logging

import pytest

from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc.logger import logger

logger.setLevel(logging.DEBUG)


def pytest_addoption(parser):
    parser.addoption(
        "--engine",
        action="store",
        default="cythonized_rk4_engine",
        help="Specify the engine entry point name"
    )


@pytest.fixture(scope="class")
def loaded_engine_instance(request):
    engine_name = request.config.getoption("--engine", None)
    print(f"\nAttempting to load engine: '{engine_name}'")

    try:
        engine = _EngineLoader.load(engine_name)
        print(f"Successfully loaded engine: {engine_name}")
        yield engine
    except Exception as e:
        pytest.fail(f"Failed to load engine '{engine_name}' via _EngineLoader: {e}")
