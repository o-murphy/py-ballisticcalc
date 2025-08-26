# CI helper: run cython-focused checks locally.
# - Builds extensions in-place
# - Runs the cython-specific pytest folder
# - Runs microbench

python -u setup.py build_ext --inplace ;
pytest -q py_ballisticcalc.exts/tests ;
python py_ballisticcalc.exts/tests/microbench.py
