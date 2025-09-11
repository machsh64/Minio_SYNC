from __future__ import annotations

import ctypes
import sys


def enable_acrylic(hwnd) -> bool:
    # Windows 10 (1809+) Acrylic blur
    try:
        accent_policy = ctypes.c_int * 4
        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int), ("GradientColor", ctypes.c_int), ("AnimationId", ctypes.c_int)]

        class WINCOMPATTRDATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]

        accent = ACCENTPOLICY()
        accent.AccentState = 4  # ACCENT_ENABLE_BLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = 0xBB000000  # AARRGGBB 半透明黑

        data = WINCOMPATTRDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.addressof(accent)
        data.SizeOfData = ctypes.sizeof(accent)

        set_attr = ctypes.windll.user32.SetWindowCompositionAttribute
        set_attr.argtypes = [ctypes.c_void_p, ctypes.POINTER(WINCOMPATTRDATA)]
        set_attr.restype = ctypes.c_int
        set_attr(hwnd, ctypes.byref(data))
        return True
    except Exception:
        return False


