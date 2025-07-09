import pytest

from py_ballisticcalc.generics.engine import EngineProtocol


class TestEngineLoader:
    def test_entry_point_loaded(self, loaded_engine_instance):
        assert isinstance(loaded_engine_instance, EngineProtocol), "Not implements EngineProtocol"
