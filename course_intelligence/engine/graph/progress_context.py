"""Progress reporting via contextvars.

Allows pipeline nodes to report sub-step progress (e.g. "page 8/15")
without changing their function signatures. The processor graph sets
the callback before streaming; nodes call ``report_progress`` during
iteration.
"""

from __future__ import annotations

import contextvars
from typing import Callable, Optional

ProgressCallback = Callable[[str, dict], None]

_progress_cb: contextvars.ContextVar[Optional[ProgressCallback]] = (
    contextvars.ContextVar("progress_cb", default=None)
)


def set_progress_callback(cb: Optional[ProgressCallback]) -> None:
    """Set the active progress callback for the current context."""
    _progress_cb.set(cb)


def report_progress(step: str, current: int, total: int, unit: str) -> None:
    """Report sub-step progress if a callback is active.

    Args:
        step: The step name (e.g. "chunking").
        current: How many items have been processed.
        total: Total number of items.
        unit: What is being counted (e.g. "pages", "elements").
    """
    cb = _progress_cb.get()
    if cb is not None:
        cb(step, {"current": current, "total": total, "unit": unit})
