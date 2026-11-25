"""A wall-clock bound for a test body that must not hang the whole suite."""

import faulthandler
import signal
from collections.abc import Callable
from typing import Any


class Hang(Exception):
    """The bounded call did not finish in time."""


# After the bound, the exception is raised again every second until the call ends (a single alarm can be swallowed, e.g.
# raised inside a finalizer or a trace callback, which then lets the call run unbounded), and if even that does not stop it
# (a long call inside C code that does not return to the interpreter) the process is killed with every thread's traceback.
_REPEAT_S = 1.0
_KILL_AFTER_S = 60.0


def run_with_time_bound(seconds: int, func: Callable[..., Any], *args: Any) -> Any:
    """Run func(*args); fail with Hang if it takes longer than `seconds` (Unix only; elsewhere no bound).

    Pyodide (WebAssembly) defines signal.SIGALRM but has no signal.setitimer, so both must be there."""
    if not (hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")):
        return func(*args)

    armed = True

    def _on_alarm(signum, frame):
        if armed:
            raise Hang(f"did not finish in {seconds} s")

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds, _REPEAT_S)
    try:
        faulthandler.dump_traceback_later(seconds + _KILL_AFTER_S, exit=True)
        backstop = True
    except (AttributeError, OSError, RuntimeError, ValueError):  # not available on this platform
        backstop = False
    try:
        return func(*args)
    finally:
        armed = False
        signal.setitimer(signal.ITIMER_REAL, 0)
        if backstop:
            faulthandler.cancel_dump_traceback_later()
        signal.signal(signal.SIGALRM, previous)
