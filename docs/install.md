# Installation

Installation is as simple as:

=== "pip"

    ```bash
    pip install py-ballisticcalc
    ```

=== "uv"

    ```bash
    uv add py-ballisticcalc 
    ```

py-ballisticcalc has a few dependencies:

* [`typing-extensions`](https://pypi.org/project/typing-extensions/): Backport of the standard library [typing][] module.

If you've got Python 3.9+ and `pip` installed, you're good to go.

[//]: # (py-ballisticcalc is also available on [conda]&#40;https://www.anaconda.com&#41; under the [conda-forge]&#40;https://conda-forge.org&#41;)

[//]: # (channel:)

[//]: # (```bash)

[//]: # (conda install py-ballisticcalc -c conda-forge)

[//]: # (```)

## Optional dependencies

py-ballisticcalc has the following optional dependencies:

* `py_ballisticcalc.exts`: Cython based implementation of some classes to increase performance. [py_ballisticcalc.exts](https://pypi.org/project/py_ballisticcalc.exts) package.

[//]: # (* `RKBallistic`: Implementation of engine that uses Runge–Kutta methods to increase productivity. [py_ballisticcalc.exts]&#40;https://github.com/dbookstaber/RKBallistic&#41; repo.)

To install optional dependencies along with py-ballisticcalc:

=== "pip"

    ```bash
    # with the `py_ballisticcalc.exts` extra:
    pip install 'py-ballisticcalc[exts]'
    ```

    ```bash
    # with dependencies for data visualisation    
    pip install py-ballisticcalc[visualize]
    ```

=== "uv"

    ```bash
    # with the `py_ballisticcalc.exts` extra:
    uv add 'py-ballisticcalc[exts]'
    ```

    ```bash
    # with dependencies for data visualisation    
    uv add  'py-ballisticcalc[visualize]'
    ```

*Of course, you can also install requirements manually with `pip install py-ballisticcalc.exts pandas matplotlib`.*

To install latest version from sources in editable mode

```bash
git clone github.com/o-murphy/py-ballisticcalc
cd py-ballisticcalc
pip install -e .[dev]
# optionally install binary extensions
pip install -e ./py_ballisticcalc.exts[dev]
```