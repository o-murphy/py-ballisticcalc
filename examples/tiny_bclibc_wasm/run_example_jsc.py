"""Example: the same run as run_example.py, pinned to JavaScriptCore on Linux.

JavaScriptCore is the engine behind Pythonista's JSContext; on Linux WebKitGTK ships it as a
library with GObject-introspection bindings, so Python can drive it the same way Pythonista
does through objc_util (create a context, evaluate a script, check the context's exception).
That makes this the closest desktop rehearsal of the Pythonista setup -- same engine, same JS
glue, same wasm module -- without an iOS device. (run_example.py picks Node on a desktop.)

Setup (Debian/Ubuntu):
    sudo apt install gir1.2-javascriptcoregtk-4.1 python3-gi
    examples/tiny_bclibc_wasm/build_wasm.sh

python3-gi is built for the distribution's own Python, so run with that interpreter, or from a
venv created with `--system-site-packages` and py_ballisticcalc installed into it:
    /usr/bin/python3 -m venv --system-site-packages .venv-jsc
    .venv-jsc/bin/pip install -e .
    .venv-jsc/bin/python examples/tiny_bclibc_wasm/run_example_jsc.py

iOS apps without the JIT entitlement (Pythonista among them) run JavaScriptCore without its
JIT; `JSC_useJIT=false` reproduces that here:
    JSC_useJIT=false .venv-jsc/bin/python examples/tiny_bclibc_wasm/run_example_jsc.py
"""

import os

# Must be set before the engine loads its module (on first Calculator construction).
os.environ["PYBALLISTICCALC_TINY_BCLIBC_WASM_RUNNER"] = "gi-jsc"

from run_example import main  # sibling script: its directory is on sys.path

if __name__ == "__main__":
    main()
