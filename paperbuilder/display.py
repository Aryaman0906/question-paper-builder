"""Configure Windows rendering before creating any Tk window.

Tk 8.6 uses system-DPI awareness here: Windows renders at the system DPI
instead of bitmap-stretching an unaware window. Do not claim dynamic
per-monitor layout support; Tk 8.6 does not provide that consistently.
"""
import ctypes
import sys


def enable_windows_dpi_awareness():
    if sys.platform != 'win32':
        return 'not-windows'
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        context = user32.SetProcessDpiAwarenessContext
        context.argtypes = [ctypes.c_void_p]
        context.restype = ctypes.c_int
        if context(ctypes.c_void_p(-2)):  # DPI_AWARENESS_CONTEXT_SYSTEM_AWARE
            return 'system-aware'
        if ctypes.get_last_error() == 5:
            return 'already-configured'  # Respect an interpreter/host manifest.
    except (AttributeError, OSError):
        pass
    try:
        shcore = ctypes.WinDLL('shcore', use_last_error=True)
        awareness = shcore.SetProcessDpiAwareness
        awareness.argtypes = [ctypes.c_int]
        awareness.restype = ctypes.c_long
        result = awareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        if result == 0:
            return 'system-aware'
        if result & 0xFFFFFFFF == 0x80070005:
            return 'already-configured'
    except (AttributeError, OSError):
        pass
    try:
        legacy = ctypes.WinDLL('user32', use_last_error=True).SetProcessDPIAware
        legacy.argtypes = []
        legacy.restype = ctypes.c_int
        if legacy():
            return 'system-aware'
    except (AttributeError, OSError):
        pass
    return 'unavailable'  # An older host must still be able to start the app.
