"""WebAssembly hosts for the tiny_bclibc wasm engines: Pythonista's JSContext, or Node.

Both hosts are driven the same way: Python hands a JavaScript engine a source string, and gets
back the string the script evaluates to. All WebAssembly handling -- instantiating the module,
copying the input buffer into linear memory, calling an export, reading the output buffer back
-- lives in one JS snippet (`_GLUE`), so the JS a desktop test runs under Node is exactly the
JS that Pythonista's JSContext runs.

One engine call is one `evaluate()` round trip: the shot goes in as a JS array literal, and the
whole result comes back as a single comma-separated string of doubles. JS `Number.toString`
prints the shortest string that round-trips, so `float()` recovers every value bit-exactly
(including `NaN`/`Infinity`).

Hosts:
    JSContextRunner: Pythonista (iOS) -- JavaScriptCore's JSContext via objc_util. No
        subprocess, no network; WebAssembly is available in JSContext since iOS 14 (the
        constructor checks and raises if it isn't).
    GIJavaScriptCoreRunner: Linux -- WebKitGTK's JavaScriptCore through PyGObject: the same
        engine as iOS's JSContext, driven the same way (evaluate, check the context's exception).
        The closest desktop stand-in for Pythonista (`apt install gir1.2-javascriptcoregtk-4.1
        python3-gi`).
    NodeRunner: desktop -- one long-lived `node` subprocess speaking JSON lines. V8, not
        JavaScriptCore, but available everywhere.
"""

from __future__ import annotations

import atexit
import json
import math
import os
import shutil
import subprocess
from collections.abc import Sequence

__all__ = ("GIJavaScriptCoreRunner", "JSContextRunner", "NodeRunner", "WasmCallError", "WasmRunner", "default_runner")


class WasmCallError(RuntimeError):
    """A tbw_* export returned a non-zero TINY_BCLIBC_Status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"tiny_bclibc status {status}: {message}")
        self.status = status
        self.message = message


# Everything WebAssembly-related, evaluated once per JS context. Kept to ES5 + typed arrays so
# any JavaScriptCore with WebAssembly runs it.
_GLUE = r"""
globalThis.__tbw = (function () {
    var inst = null;
    function mem() { return inst.exports.memory.buffer; }
    function cstr(ptr) {
        var u8 = new Uint8Array(mem()), s = '';
        while (u8[ptr]) s += String.fromCharCode(u8[ptr++]);
        return s;
    }
    function writeInput(values) {
        var ptr = inst.exports.tbw_input(values.length);
        if (!ptr) throw new Error('tbw_input: out of memory');
        new Float64Array(mem(), ptr, values.length).set(values);
    }
    function result(rc) {
        if (rc !== 0) return 'E' + rc + ':' + cstr(inst.exports.tbw_last_error());
        var out = new Float64Array(mem(), inst.exports.tbw_output(), inst.exports.tbw_output_len());
        return Array.prototype.join.call(out, ',');
    }
    return {
        load: function (bytes) {
            inst = new WebAssembly.Instance(new WebAssembly.Module(new Uint8Array(bytes)), {});
            if (inst.exports._initialize) inst.exports._initialize();
            return inst.exports.tbw_sizeof_real() + ':' + cstr(inst.exports.tbw_version());
        },
        integrate: function (input, rangeLimitFt, rangeStepFt, timeStep, filterFlags) {
            writeInput(input);
            return result(inst.exports.tbw_integrate(rangeLimitFt, rangeStepFt, timeStep, filterFlags));
        },
        zeroPoint: function (input, distanceFt) {
            writeInput(input);
            return result(inst.exports.tbw_find_zero_point(distanceFt));
        }
    };
})();
'ok'
"""


def _js_number(x: float) -> str:
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    return repr(float(x))


def _js_array(values: Sequence[float]) -> str:
    return "[" + ",".join(_js_number(v) for v in values) + "]"


def _parse_result(text: str) -> list[float]:
    if text.startswith("E"):
        status, _, message = text[1:].partition(":")
        raise WasmCallError(int(status), message)
    return [float(v) for v in text.split(",")] if text else []


class WasmRunner:
    """Loads one tiny_bclibc wasm module into a JS engine and calls its tbw_* exports.

    Subclasses implement `evaluate(src) -> str` for their JS engine; everything else is shared.
    """

    sizeof_real: int
    version: str

    def evaluate(self, src: str) -> str:
        raise NotImplementedError

    def load_file(self, path: str) -> None:
        with open(path, "rb") as f:
            self.load_bytes(f.read())

    def load_bytes(self, wasm: bytes) -> None:
        self.evaluate(_GLUE)
        info = self.evaluate("__tbw.load([" + ",".join(map(str, wasm)) + "])")
        size, _, self.version = info.partition(":")
        self.sizeof_real = int(size)

    def integrate(
        self, shot: Sequence[float], range_limit_ft: float, range_step_ft: float, time_step: float, filter_flags: int
    ) -> list[float]:
        """tbw_integrate: returns the output buffer (header + rows) as floats."""
        return _parse_result(
            self.evaluate(
                f"__tbw.integrate({_js_array(shot)},{_js_number(range_limit_ft)},"
                f"{_js_number(range_step_ft)},{_js_number(time_step)},{int(filter_flags)})"
            )
        )

    def zero_point(self, shot: Sequence[float], distance_ft: float) -> list[float]:
        """tbw_find_zero_point: returns the output buffer (status, angle, one row) as floats."""
        return _parse_result(self.evaluate(f"__tbw.zeroPoint({_js_array(shot)},{_js_number(distance_ft)})"))


class JSContextRunner(WasmRunner):
    """JavaScriptCore via Pythonista's objc_util -- the host this engine exists for."""

    def __init__(self) -> None:
        from objc_util import ObjCClass  # type: ignore[import-not-found]  # Pythonista only

        self._ctx = ObjCClass("JSContext").alloc().init()
        kind = self.evaluate("typeof WebAssembly")
        if kind != "object":
            raise RuntimeError(f"WebAssembly is not available in this JSContext (typeof WebAssembly = {kind})")

    def evaluate(self, src: str) -> str:
        res = self._ctx.evaluateScript_(src)
        exc = self._ctx.exception()
        if exc:
            self._ctx.setException_(None)
            raise RuntimeError(f"[JS] {exc.toString()}")
        return str(res.toString())


class GIJavaScriptCoreRunner(WasmRunner):
    """WebKitGTK's JavaScriptCore via PyGObject -- JSContextRunner's desktop twin."""

    def __init__(self) -> None:
        import gi  # type: ignore[import-not-found]  # PyGObject, Linux

        gi.require_version("JavaScriptCore", "4.1")
        from gi.repository import JavaScriptCore  # type: ignore[import-not-found]

        self._ctx = JavaScriptCore.Context()
        kind = self.evaluate("typeof WebAssembly")
        if kind != "object":
            raise RuntimeError(f"WebAssembly is not available in this JSContext (typeof WebAssembly = {kind})")

    def evaluate(self, src: str) -> str:
        res = self._ctx.evaluate(src, -1)
        exc = self._ctx.get_exception()
        if exc:
            self._ctx.clear_exception()
            raise RuntimeError(f"[JS] {exc.to_string()}")
        return res.to_string()


_NODE_LOOP = r"""
const rl = require('readline').createInterface({ input: process.stdin });
rl.on('line', (line) => {
    let reply;
    try { reply = { ok: true, value: String((0, eval)(JSON.parse(line))) }; }
    catch (e) { reply = { ok: false, value: String(e && e.stack || e) }; }
    process.stdout.write(JSON.stringify(reply) + '\n');
});
"""


class NodeRunner(WasmRunner):
    """A long-lived `node` process evaluating one JSON-encoded script per line (desktop testing)."""

    def __init__(self, node: str | None = None) -> None:
        node = node or shutil.which("node")
        if not node:
            raise FileNotFoundError("node not found on PATH (needed by NodeRunner outside Pythonista)")
        self._proc = subprocess.Popen(
            [node, "-e", _NODE_LOOP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        atexit.register(self.close)

    def evaluate(self, src: str) -> str:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(json.dumps(src) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError(f"node exited (status {self._proc.poll()})")
        reply = json.loads(line)
        if not reply["ok"]:
            raise RuntimeError(f"[JS] {reply['value']}")
        return reply["value"]

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.stdin.close()  # type: ignore[union-attr]
            self._proc.wait(timeout=5)
        self._proc.stdout.close()  # type: ignore[union-attr]


def default_runner() -> WasmRunner:
    """Pick the host: $PYBALLISTICCALC_TINY_BCLIBC_WASM_RUNNER (jscontext|gi-jsc|node), else
    JSContext when objc_util is importable (Pythonista), else Node."""
    choice = os.environ.get("PYBALLISTICCALC_TINY_BCLIBC_WASM_RUNNER", "").lower()
    if choice == "jscontext":
        return JSContextRunner()
    if choice == "gi-jsc":
        return GIJavaScriptCoreRunner()
    if choice == "node":
        return NodeRunner()
    if choice:
        raise ValueError(
            f"PYBALLISTICCALC_TINY_BCLIBC_WASM_RUNNER={choice!r}: expected 'jscontext', 'gi-jsc' or 'node'"
        )
    try:
        import objc_util  # type: ignore[import-not-found]  # noqa: F401  # pylint: disable=unused-import
    except ImportError:
        return NodeRunner()
    return JSContextRunner()
