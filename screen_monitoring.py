"""Legacy compatibility shim for monitoring API.

The old process/queue based monitoring is removed.
Use cv_core.compat_adapter.screen instead.
"""

from __future__ import annotations

from cv_core.compat_adapter import screen


def process_changes(*_args, **_kwargs):
    """Start new CV pipeline for backward compatibility."""
    screen.start()


def register_input_queue(_q):
    """No-op: queue injection is not used in new pipeline."""
    return None


def force_refresh_after_move(*args, **kwargs):
    """Backward-compatible proxy to new screen refresher."""
    dwell = kwargs.get("dwell", 0.6)
    if args and isinstance(args[0], (int, float)):
        dwell = args[0]
    screen.force_refresh_after_move(dwell=float(dwell))

