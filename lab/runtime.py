"""Optional progress and cancellation for one in-flight SSI run."""
from __future__ import annotations

import contextvars
from threading import Event, Lock


class Cancelled(RuntimeError):
    """The caller stopped this run between scoring batches."""


class RunHook:
    def __init__(self):
        self.cancel = Event()
        self.evaluations = 0
        self._lock = Lock()

    def note(self, count: int) -> None:
        with self._lock:
            self.evaluations += int(count)


HOOK: contextvars.ContextVar[RunHook | None] = contextvars.ContextVar("ssi_run_hook", default=None)


def raise_if_cancelled() -> None:
    hook = HOOK.get()
    if hook is not None and hook.cancel.is_set():
        raise Cancelled("This run was cancelled.")


def wrap_value(value_fn):
    def wrapped(masks):
        raise_if_cancelled()
        values = value_fn(masks)
        hook = HOOK.get()
        if hook is not None:
            hook.note(len(masks))
        return values
    return wrapped
