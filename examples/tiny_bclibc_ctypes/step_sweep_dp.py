"""Subclasses of TinyBclibcDoubleIntegrationEngine with different fixed
cStepMultiplier defaults -- double precision, so the baseline is a clean
375/375 (no known float32-precision noise) and any new failure at a higher
multiplier is unambiguously a real step-size accuracy regression, not
conflated with the 11 known SP-only failures.

Usage (from repo root):
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_ctypes.step_sweep_dp:DP_0_5   # baseline
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_ctypes.step_sweep_dp:DP_1_0
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_ctypes.step_sweep_dp:DP_2_0
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc_ctypes.step_sweep_dp:DP_4_0
    PYTHONPATH=examples uv run python scripts/benchmark.py --engine tiny_bclibc_ctypes.step_sweep_dp:DP_2_0 -r 1000 -w 100
"""

from . import TinyBclibcDoubleIntegrationEngine


def _make(multiplier: float):
    class _Engine(TinyBclibcDoubleIntegrationEngine):
        def __init__(self, config=None):
            merged = {**(config or {}), "cStepMultiplier": multiplier}
            super().__init__(merged)

    _Engine.__name__ = f"DP_{str(multiplier).replace('.', '_')}"
    return _Engine


DP_0_5 = _make(0.5)  # actual BCP firmware default (TINY_BCLIBC_Config_default())
DP_1_0 = _make(1.0)  # py-ballisticcalc's own BaseEngineConfigDict default
DP_2_0 = _make(2.0)
DP_4_0 = _make(4.0)
DP_8_0 = _make(8.0)
