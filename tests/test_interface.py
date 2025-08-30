from importlib.metadata import EntryPoint
from typing import cast
from types import SimpleNamespace

import pytest

from py_ballisticcalc.interface import Calculator, _EngineLoader

pytestmark = pytest.mark.extended

def test_calculator_getattr_missing_attribute_message(loaded_engine_instance):
    calc = Calculator(engine=loaded_engine_instance)
    with pytest.raises(AttributeError) as ei:
        _ = calc.this_method_does_not_exist  # type: ignore[attr-defined]
    assert "has no attribute" in str(ei.value)


def test_engine_loader_string_not_found_raises_value_error(monkeypatch):
    # Ensure there is no match from iter_engines and that direct EntryPoint fallback also fails
    monkeypatch.setattr(_EngineLoader, "iter_engines", classmethod(lambda cls: iter(())))
    with pytest.raises(ValueError):
        _ = _EngineLoader.load("totally_missing_engine")


class DummyEP:
    def __init__(self, name: str, value: str, group: str, loader):
        self.name = name
        self.value = value
        self.group = group
        self._loader = loader

    def load(self):  # Mimic importlib.metadata.EntryPoint API
        return self._loader()


def test_load_from_entry_import_error():
    def boom():
        raise ImportError("nope")

    ep = DummyEP("bad_engine", "x.y:Z", _EngineLoader._entry_point_group, boom)
    assert _EngineLoader._load_from_entry(cast(EntryPoint, ep)) is None


def test_load_from_entry_type_error():
    # Return an object that is not an EngineProtocol
    ep = DummyEP("not_engine", "x.y:Z", _EngineLoader._entry_point_group, lambda: SimpleNamespace())
    assert _EngineLoader._load_from_entry(cast(EntryPoint, ep)) is None


def test_load_with_none_uses_default_engine():
    # Should not raise and should return a callable class
    cls = _EngineLoader.load(None)
    assert callable(cls)
