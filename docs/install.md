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

If you have Python 3.10+ and `pip` installed, you're good to go.

[//]: # (py-ballisticcalc is also available on [conda]&#40;https://www.anaconda.com&#41; under the [conda-forge]&#40;https://conda-forge.org&#41;)

[//]: # (channel:)

[//]: # (```bash)

[//]: # (conda install py-ballisticcalc -c conda-forge)

[//]: # (```)

## Optional dependencies

py-ballisticcalc has the following optional dependencies:

* **[`exts`](internals/cython.md):** Cython based implementation of some classes to increase performance. [py_ballisticcalc.exts](https://pypi.org/project/py_ballisticcalc.exts) package.
* **`charts`:** Includes [matplotlib](https://matplotlib.org/) for creating [`charts`][py_ballisticcalc.trajectory_data.HitResult.plot] and [pandas](https://pandas.pydata.org/) for creating [`DataFrame tables`][py_ballisticcalc.trajectory_data.HitResult.dataframe].
* **[`scipy`](https://scipy.org/):** Installs support for the `SciPyIntegrationEngine`.

To install optional dependencies along with py-ballisticcalc:

=== "pip"

    ```bash
    # with the cython extensions:
    pip install "py-ballisticcalc[exts]"
    ```

    ```bash
    # with dependencies for charting:
    pip install "py-ballisticcalc[charts]"
    ```

=== "uv"

    ```bash
    # with the cython extensions:
    uv add "py-ballisticcalc[exts]"
    ```

    ```bash
    # with dependencies for charting:
    uv add "py-ballisticcalc[charts]"
    ```

You can also install requirements manually.  For example:

=== "pip"
    ```
    pip install py-ballisticcalc.exts pandas matplotlib
    ```

=== "uv"
    ```
    uv add py-ballisticcalc.exts pandas matplotlib
    ```

To install latest version from sources in editable mode:

```bash
git clone https://github.com/o-murphy/py-ballisticcalc
cd py-ballisticcalc
```

=== "pip"
    ```bash
    # from repo root
    py -m pip install -e .[dev]                        # main package editable
    py -m pip install -e ./py_ballisticcalc.exts[dev]  # build/install C extensions (optional)
    ```

=== "uv"
    ```bash
    # from repo root
    uv sync                        # main package editable
    uv sync --extra exts           # build/install C extensions (optional)
    ```