"""Legacy compatibility shim for screen API.

This module is kept to avoid breaking old imports.
All runtime behavior is delegated to cv_core.compat_adapter.
"""

from cv_core.compat_adapter import ScreenCompat, screen, screenshot

VERBOSE = False
Screen = ScreenCompat

