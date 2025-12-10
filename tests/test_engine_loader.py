from importlib.metadata import EntryPoint
from typing import cast
from types import SimpleNamespace

import pytest

from py_ballisticcalc.generics.engine import EngineProtocol, EngineFactoryProtocol
from py_ballisticcalc.interface import _EngineLoader
from py_ballisticcalc import Calculator


class TestEngineLoader:
    def test_entry_point_loaded(self, loaded_engine_instance):
        assert isinstance(loaded_engine_instance, EngineFactoryProtocol), "Not implements EngineProtocol"

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


@pytest.mark.extended
class TestEngineLoaderExtended:

    class DummyEP:
        def __init__(self, name: str, value: str, group: str, loader):
            self.name = name
            self.value = value
            self.group = group
            self._loader = loader

        def load(self):  # Mimic importlib.metadata.EntryPoint API
            return self._loader()


    def test_load_from_entry_import_error(self):
        def boom():
            raise ImportError("nope")

        ep = self.DummyEP("bad_engine", "x.y:Z", _EngineLoader._entry_point_group, boom)
        assert _EngineLoader._load_from_entry(cast(EntryPoint, ep)) is None


    def test_load_from_entry_type_error(self):
        # Return an object that is not an EngineProtocol
        ep = self.DummyEP("not_engine", "x.y:Z", _EngineLoader._entry_point_group, lambda: SimpleNamespace())
        assert _EngineLoader._load_from_entry(cast(EntryPoint, ep)) is None


    def test_load_with_none_uses_default_engine(self):
        # Should not raise and should return a callable class
        cls = _EngineLoader.load(None)
        assert callable(cls)
