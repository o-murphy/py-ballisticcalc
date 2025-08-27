import pytest

from py_ballisticcalc.generics.engine import EngineProtocol
from py_ballisticcalc import Calculator


class TestEngineLoader:
    def test_entry_point_loaded(self, loaded_engine_instance):
        assert isinstance(loaded_engine_instance, EngineProtocol), "Not implements EngineProtocol"

    def test_iter_engines_non_empty(self):
        engines = list(Calculator.iter_engines())
        assert any(ep.name.endswith('_engine') for ep in engines)

    def test_engine_loader_fallback_invalid(self):
        with pytest.raises(ValueError):
            _ = Calculator(engine='not_an_engine')

    def test_calculator_attr_missing(self, loaded_engine_instance):
        calc = Calculator(engine=loaded_engine_instance)
        # Missing attribute should raise AttributeError
        with pytest.raises(AttributeError):
            _ = getattr(calc, 'no_such_method')
