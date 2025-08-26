We'd love you to contribute to py_ballisticcalc!

## Issues

Questions, feature requests and bug reports are all welcome
as [discussions or issues](https://github.com/o-murphy/py-ballisticcalc/issues/new/choose).

[//]: # (**However, to report a security vulnerability, please see our [security policy]&#40;https://github.com/o-murphy/py-ballisticcalc/security/policy&#41;.**)

To make it as simple as possible for us to help you, please include the output of the following call in your issue:

```bash
python -c "from importlib.metadata import metadata; print(metadata('py-ballisticcalc')['Version'])"
```

Please try to always include the above unless you're unable to install py-ballisticcalc or **know** it's not relevant
to your question or feature request.

## Pull Requests

It should be extremely simple to get started and create a Pull Request.
py-ballisticcalc is released regularly so you should see your improvements release in a matter of days or weeks 🚀.

Unless your change is trivial (typo, docs tweak etc.), please create an issue to discuss the change before
creating a pull request.

If you're looking for something to get your teeth into, check out the
["help wanted"](https://github.com/o-murphy/py-ballisticcalc/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22)
label on github.

To make contributing as easy and fast as possible, you'll want to run tests and linting locally. Luckily,
py-ballisticcalc has few dependencies, and tests don't need access to databases, etc.
Because of this, setting up and running the tests should be very simple.

!!! note
    You should know the py-ballisticcalc requires [cython](https://cython.readthedocs.io/en/latest/src/quickstart/install.html) to compile py-ballisticcalc.exts
    module to get high productivity calculations

### Prerequisites

You'll need the following prerequisites:

- Any Python version between **Python 3.9 and 3.12**
- [**venv**](https://docs.python.org/3/library/venv.html) or [**uv**](https://docs.astral.sh/uv/getting-started/installation/) or other virtual environment tool
- **git**

### Installation and setup

Fork the repository on GitHub and clone your fork locally.

```bash
# Clone your fork and cd into the repo directory
git clone git@github.com:<your username>/py-ballisticcalc.git
cd py-ballisticcalc

# Setup virtual environment (we will use `venv` there)
python -m venv .venv
source .venv/bin/activate

# Install package in editable mode with `dev` requirements to local environment 
pip install -e .[dev]
```

If you want to contribute to cythonized extensions you can also install them in editable mode

```bash
pip install -e ./py_ballisticcalc.exts[dev]
```

### Check out a new branch and make your changes

Create a new branch for your changes.

```bash
# Checkout a new branch and make your changes
git checkout -b my-new-feature-branch
# Make your changes...
```

### Run tests and linting

Run tests and linting locally to make sure everything is working as expected.

```bash
# Run automated code linting
ruff check

# Run mypy static analysing 
mypy

# Run automated tests
pytest

# Run automated tests for specific engine
pytest --engine="cythonized_rk4_engine"  # via project.entry-points
pytest --engine="my_lib.my_engine:MyEngineClass"  # via entry point path 
```

### Coverage
We use `pytest-cov` to get coverage reports:
```shell
pytest --cov=py_ballisticcalc --cov-report=html  # for default engine
pytest --cov=py_ballisticcalc --cov-report=html --engine="scipy_engine"  # for custom engine 
```

To get coverage of Cython, set the environment variable `CYTHON_COVERAGE = '1'`, rebuild `py_ballisticcalc.exts` (from project root: `pip install -e py_ballisticcalc.exts`), then run:

```shell
python scripts\sync_cython_sources.py
pytest --engine="cythonized_rk4_engine" --cov=py_ballisticcalc --cov=py_ballisticcalc_exts --cov-report=html
```

### Documentation

If you've made any changes to the documentation (including changes to function signatures, class definitions, or
docstrings that will appear in the API documentation), make sure it builds successfully.

We use `mkdocs-material[imaging]` to support social previews.
You can find directions on how to install the required
dependencies [here](https://squidfunk.github.io/mkdocs-material/plugins/requirements/image-processing/).

```bash
# Install dependencies for docs building
pip install -e .[docs]

# Rebuild docs locally before commiting them to the branch   
mkdocs build

# Use this command to serve docs locally 
mkdocs serve
```

If this isn't working due to issues with the imaging plugin, try commenting out the `social` plugin line in `mkdocs.yml`
and running `mkdocs build` again.

### Commit and push your changes

Commit your changes, push your branch to GitHub, and create a pull request.

Please follow the pull request template and fill in as much information as possible. Link to any relevant issues and
include a description of your changes.

When your pull request is ready for review, add a comment with the message "please review" and we'll take a look as soon
as we can.

## Documentation style

Documentation is written in Markdown and built
using [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). API documentation is build from docstrings
using [mkdocstrings](https://mkdocstrings.github.io/).

### Code documentation

When contributing to py-ballisticcalc, please make sure that all code is well documented. The following should be
documented using properly formatted docstrings:

- Modules
- Class definitions
- Function definitions
- Module-level variables

py-ballisticcalc
uses [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) formatted
according to [PEP 257](https://www.python.org/dev/peps/pep-0257/) guidelines. (
See [Example Google Style Python Docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
for further examples.)

[pydocstyle](https://www.pydocstyle.org/en/stable/index.html) is used for linting docstrings. You can run
`pydocstyle .\py_ballisticcalc\` to check your docstrings.

Where this is a conflict between Google-style docstrings and pydocstyle linting, follow the pydocstyle linting hints.

Class attributes and function arguments should be documented in the format "name: description." When applicable, a
return type should be documented with just a description. Types are inferred from the signature.

```python
class Foo:
    """A class docstring.

    Attributes:
        bar: A description of bar. Defaults to "bar".
    """

    bar: str = 'bar'
```

```python
def bar(self, baz: int) -> str:
    """A function docstring.

    Args:
        baz: A description of `baz`.

    Returns:
        A description of the return value.
    """

    return 'bar'
```

You may include example code in docstrings. 

!!! note "Class and instance attributes"
    Class attributes should be documented in the class docstring.

    Instance attributes should be documented as "Args" in the `__init__` docstring.

### Documentation Style

In general, documentation should be written in a friendly, approachable style. It should be easy to read and understand, and should be as concise as possible while still being complete.

Code examples are encouraged but should be kept short and simple. However, every code example should be complete, self-contained, and runnable. (If you're not sure how to do this, ask for help!) We prefer print output to naked asserts, but if you're testing something that doesn't have a useful print output, asserts are fine.
