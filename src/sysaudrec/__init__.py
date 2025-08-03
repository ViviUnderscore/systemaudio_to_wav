# -*- coding: utf-8 -*-
"""sysaudrec package init and NumPy 2.x compatibility shim."""

__all__ = ["__version__"]
__version__ = "0.1.1"

# NumPy 2.x compatibility shim for libs that still use np.fromstring on binary data.
# Redirects binary-mode calls to np.frombuffer when sep is "" or None.
try:
    import numpy as _np
    _orig_fromstring = _np.fromstring

    def _fromstring_compat(s, dtype=float, count=-1, sep=""):
        # Binary mode was removed in NumPy 2.x. Use frombuffer for bytes-like input.
        if (sep in ("", None)) and isinstance(s, (bytes, bytearray, memoryview)):
            return _np.frombuffer(s, dtype=dtype, count=count)
        # Fallback to original behavior for text mode or non-bytes inputs.
        return _orig_fromstring(s, dtype=dtype, count=count, sep=sep)

    def _parse_version(ver_str):
        parts = []
        for tok in str(ver_str).split("."):
            num = ""
            for ch in tok:
                if ch.isdigit():
                    num += ch
                else:
                    break
            parts.append(int(num or 0))
        while len(parts) < 2:
            parts.append(0)
        return tuple(parts[:2])

    if _parse_version(_np.__version__) >= (2, 0):
        _np.fromstring = _fromstring_compat  # type: ignore[attr-defined]
except Exception:
    # Best-effort patch only; safe to ignore failures.
    pass
