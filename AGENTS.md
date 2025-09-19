# Project Layout
`py_ballisticcalc` is a package of ballistic calculators and utilities. The primary project is in Python.

* The project offers interchangeable calculation "engines". List them via:
```python
from py_ballisticcalc.interface import _EngineLoader
print("\nAvailable engines: " + str(sorted([e.name for e in _EngineLoader.iter_engines()])))
```

* Optional subproject in `py_ballisticcalc.exts` subfolder implements some engines in Cython, optimized for speed. See `py_ballisticcalc.exts/AGENTS.md`.

# Dev Install

```python
pip install -e .[dev]
pip install -e ./py_ballisticcalc.exts[dev]
```

Or via `uv`: `uv sync --dev --extra exts`

# Standards
* Google-style docstrings
* 120-char line-length limit with Black-style formatting
* `mkdocs` documentation
* Pylint score > 9/10
* 100% pass on `mypy` and `uv run ruff check`
* 100% pass on unit tests
* Scripts and files not intended for the public repo can be put in the git-excluded `./debug` folder.

# Test
Both projects have unit tests in their root `/tests`. `pytest.markers` are defined in `pyproject.toml` to focus tests.

* `py_ballisticcalc.exts/tests` only cover things unique to the Cython subproject.

* `pytest` will only run tests with one engine at a time. Default is `rk4_engine`. Use the `--engine` option to specify a different engine. Example: `pytest tests --engine="cythonized_rk4_engine"`

* `./scripts/testall.ps1` will test all engines, optionally with coverage, and create a summary.

## Other checks
* Docstrings: `pydocstyle .\py_ballisticcalc\`
* Docstring example tests: `.\scripts\run_doctest.py`
