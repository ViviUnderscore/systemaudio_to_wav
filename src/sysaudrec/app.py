# -*- coding: utf-8 -*-
"""App entry point for sysaudrec."""

import ctypes
import platform
import sys
import logging
from typing import NoReturn

from sysaudrec.gui import RecorderWindow
from sysaudrec.paths import setup_logging


def _enable_hidpi_windows() -> None:
    """Enable better DPI scaling on Windows."""
    if platform.system().lower() == "windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-monitor DPI awareness
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # Fallback
            except Exception:
                pass


def main() -> NoReturn:
    log_path = setup_logging("sysaudrec")
    logging.getLogger(__name__).info(
        "Starting sysaudrec. Python=%s Platform=%s Log=%s",
        sys.version.split()[0],
        platform.platform(),
        log_path,
    )
    _enable_hidpi_windows()
    app = RecorderWindow()
    app.mainloop()
    logging.getLogger(__name__).info("Exiting sysaudrec.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
